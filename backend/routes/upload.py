from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import RequestEntityTooLarge
from pathlib import Path
from datetime import datetime
import hashlib
import logging
from uuid import uuid4

from database import db
from models.transaction import Transaction
from utils.validators import (
    validate_file_upload,
    validate_pdf_file,
    secure_pdf_filename,
)
from utils.pdf_parser import TransactionExtractor, PDFParseError

logger = logging.getLogger(__name__)
upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload and process a PDF transaction statement
    Extract ALL transactions and store in Neon PostgreSQL
    
    Returns:
        JSON response with number of transactions stored
    """
    # Validate request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file before processing
    is_valid, message = validate_file_upload(file.filename, len(file.read()))
    file.seek(0)  # Reset file pointer
    
    if not is_valid:
        return jsonify({'error': message}), 400
    
    try:
        # Create unique filename for storage
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_pdf_filename(file.filename, timestamp)
        filepath = Path(current_app.config['UPLOAD_FOLDER']) / filename

        # Save file
        file.save(str(filepath))
        logger.info(f"File saved: {filepath}")

        # Compute a stable statement_id based on PDF contents so
        # re-uploading the same file reuses the same statement reference.
        with open(filepath, "rb") as f:
            file_bytes = f.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        # Use a shorter prefix for readability while remaining very unlikely to collide
        statement_id = file_hash[:32]

        # If this statement was already processed before, short-circuit and
        # return existing transactions instead of inserting duplicates.
        existing_q = db.session.query(Transaction).filter_by(statement_id=statement_id)
        existing_count = existing_q.count()
        if existing_count > 0:
            logger.info(
                f"Statement {statement_id} already processed, returning existing "
                f"{existing_count} transactions"
            )
            filepath.unlink(missing_ok=True)
            existing_sample = existing_q.limit(10).all()
            return jsonify(
                {
                    "success": True,
                    "statement_id": statement_id,
                    "filename": filename,
                    "rows_updated": 0,
                    "transaction_count": existing_count,
                    "duplicates_skipped": existing_count,
                    "sample_transactions": [t.to_dict() for t in existing_sample],
                    "message": (
                        f"Statement already processed. Reused {existing_count} "
                        "existing transactions."
                    ),
                }
            ), 200

        # Validate PDF file
        is_valid, message = validate_pdf_file(str(filepath))
        if not is_valid:
            filepath.unlink()  # Delete invalid file
            return jsonify({'error': f'Invalid PDF: {message}'}), 400
        
        # Extract ALL transactions from PDF
        extractor = TransactionExtractor()
        try:
            transactions = extractor.extract_transactions_from_pdf(
                str(filepath),
                statement_id=statement_id
            )
        except PDFParseError as e:
            filepath.unlink()
            return jsonify({'error': f'PDF parsing failed: {str(e)}'}), 400
        
        if not transactions:
            filepath.unlink()
            return jsonify({
                'error': 'No transactions found in PDF',
                'transaction_count': 0
            }), 400
        
        logger.info(f"Extracted {len(transactions)} transactions from PDF")
        
        # Store ALL extracted transactions in database in batches to avoid connection timeouts
        stored_count = 0
        duplicate_count = 0
        batch_size = 10  # Insert in smaller batches
        try:
            for i in range(0, len(transactions), batch_size):
                batch = transactions[i:i + batch_size]
                
                logger.info(f"Processing batch {i//batch_size + 1}: rows {i} to {min(i + batch_size, len(transactions))}")
                
                for idx, txn_data in enumerate(batch):
                    try:
                        # Skip transaction if it already exists for this statement
                        existing = Transaction.query.filter_by(
                            statement_id=statement_id,
                            transaction_details=txn_data['description'],
                            value_date=txn_data['date'],
                            credit=txn_data.get('amount') if txn_data.get('type') == 'credit' else None,
                            debit=txn_data.get('amount') if txn_data.get('type') != 'credit' else None,
                        ).first()

                        if existing:
                            duplicate_count += 1
                            logger.debug(
                                f"  ⏭️  Row {i + idx}: Skipped duplicate "
                                f"{txn_data['date']} | {txn_data.get('amount')}"
                            )
                            continue

                        # Map extracted data to database column names
                        # Determine if amount is credit or debit based on transaction type
                        credit_amount = None
                        debit_amount = None
                        if txn_data.get('type') == 'credit':
                            credit_amount = txn_data.get('amount')
                        else:
                            debit_amount = txn_data.get('amount')
                        
                        transaction = Transaction(
                            transaction_details=txn_data['description'],  # From Transaction Details column
                            payment_reference=txn_data.get('reference'),  # From Payment Reference column
                            value_date=txn_data['date'],  # From Value Date column
                            credit=credit_amount,  # Credit (Money In)
                            debit=debit_amount,  # Debit (Money Out)
                            balance=txn_data.get('balance'),
                            phone_number=txn_data.get('phone_number'),  # Extracted for filtering
                            raw_data=txn_data.get('raw_data'),
                            statement_id=statement_id,
                            confidence=txn_data.get('confidence', 0.8),
                            manual_review=False
                        )
                        db.session.add(transaction)
                        stored_count += 1
                        logger.debug(f"  ✓ Row {i + idx}: Added {txn_data['date']} | {txn_data['amount']}")
                    except Exception as row_error:
                        logger.error(f"  ✗ Row {i + idx}: Error - {str(row_error)}")
                        raise
                
                # Commit each batch to avoid connection timeouts
                try:
                    db.session.commit()
                    logger.info(f"✓ Committed batch: {min(i + batch_size, len(transactions))}/{len(transactions)} transactions")
                except Exception as commit_error:
                    db.session.rollback()
                    logger.error(f"✗ BATCH COMMIT FAILED at row {i}: {str(commit_error)}")
                    raise
            
            logger.info(f"✓ Successfully stored {stored_count} transactions in Neon database")
        
        except Exception as e:
            db.session.rollback()
            filepath.unlink()
            logger.error(f"Database error: {str(e)}")
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        
        # Clean up uploaded file
        filepath.unlink()
        
        # Get stored transactions for display
        stored_transactions = db.session.query(Transaction).filter_by(
            statement_id=statement_id
        ).limit(10).all()

        # Return success response with row count
        return jsonify({
            'success': True,
            'statement_id': statement_id,
            'filename': filename,
            'rows_updated': stored_count,
            'transaction_count': stored_count,
            'duplicates_skipped': duplicate_count,
            'sample_transactions': [t.to_dict() for t in stored_transactions],
            'message': (
                f'✓ Stored {stored_count} new transactions'
                + (f', skipped {duplicate_count} duplicates' if duplicate_count else '')
                + ' in Neon database'
            )
        }), 200
    
    except RequestEntityTooLarge:
        return jsonify({
            'error': f'File too large (max {current_app.config["MAX_UPLOAD_SIZE_MB"]}MB)'
        }), 413
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Processing error: {str(e)}'}), 500
