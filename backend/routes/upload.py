from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import RequestEntityTooLarge
from pathlib import Path
from datetime import datetime
import hashlib
import logging

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
        
        # Store extracted transactions; skip rows without transaction_url or URL already in DB
        stored_count = 0
        skipped_existing_url = 0
        skipped_no_url = 0
        pending_urls = set()
        batch_size = 10  # Insert in smaller batches
        try:
            for i in range(0, len(transactions), batch_size):
                batch = transactions[i:i + batch_size]
                
                logger.info(f"Processing batch {i//batch_size + 1}: rows {i} to {min(i + batch_size, len(transactions))}")
                
                for idx, txn_data in enumerate(batch):
                    try:
                        txn_url = txn_data.get('transaction_url')
                        if not txn_url:
                            skipped_no_url += 1
                            logger.debug(
                                f"  ⏭️  Row {i + idx}: Skipped (no transaction_url token)"
                            )
                            continue

                        if txn_url in pending_urls:
                            skipped_existing_url += 1
                            logger.debug(
                                f"  ⏭️  Row {i + idx}: Skipped duplicate URL in file "
                                f"{txn_url}"
                            )
                            continue

                        existing = Transaction.query.filter_by(
                            transaction_url=txn_url
                        ).first()
                        if existing:
                            skipped_existing_url += 1
                            logger.debug(
                                f"  ⏭️  Row {i + idx}: Skipped existing transaction_url "
                                f"{txn_url}"
                            )
                            continue

                        # Map extracted data to database column names
                        credit_amount = None
                        debit_amount = None
                        if txn_data.get('type') == 'credit':
                            credit_amount = txn_data.get('amount')
                        else:
                            debit_amount = txn_data.get('amount')
                        
                        transaction = Transaction(
                            transaction_details=txn_data['description'],
                            payment_reference=txn_data.get('reference'),
                            value_date=txn_data['date'],
                            credit=credit_amount,
                            debit=debit_amount,
                            balance=txn_data.get('balance'),
                            phone_number=txn_data.get('phone_number'),
                            transaction_url=txn_url,
                            raw_data=txn_data.get('raw_data'),
                            statement_id=statement_id,
                            confidence=txn_data.get('confidence', 0.8),
                            manual_review=False
                        )
                        db.session.add(transaction)
                        pending_urls.add(txn_url)
                        stored_count += 1
                        logger.debug(f"  ✓ Row {i + idx}: Added {txn_data['date']} | {txn_data['amount']}")
                    except Exception as row_error:
                        logger.error(f"  ✗ Row {i + idx}: Error - {str(row_error)}")
                        raise
                
                try:
                    db.session.commit()
                    logger.info(f"✓ Committed batch: {min(i + batch_size, len(transactions))}/{len(transactions)} transactions")
                except Exception as commit_error:
                    db.session.rollback()
                    logger.error(f"✗ BATCH COMMIT FAILED at row {i}: {str(commit_error)}")
                    raise
            
            logger.info(f"✓ Stored {stored_count} transactions (skipped_no_url={skipped_no_url}, skipped_existing_url={skipped_existing_url})")
        
        except Exception as e:
            db.session.rollback()
            filepath.unlink()
            logger.error(f"Database error: {str(e)}")
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        
        filepath.unlink()
        
        stored_transactions = db.session.query(Transaction).filter_by(
            statement_id=statement_id
        ).limit(10).all()

        total_in_file = len(transactions)
        return jsonify({
            'success': True,
            'statement_id': statement_id,
            'filename': filename,
            'rows_updated': stored_count,
            'transaction_count': stored_count,
            'skipped_existing_url': skipped_existing_url,
            'skipped_no_url': skipped_no_url,
            'parsed_count': total_in_file,
            'sample_transactions': [t.to_dict() for t in stored_transactions],
            'message': (
                f'✓ Stored {stored_count} new transactions'
                f' (parsed {total_in_file}; skipped {skipped_existing_url} existing URL(s), '
                f'{skipped_no_url} without URL token)'
            ),
        }), 200
    
    except RequestEntityTooLarge:
        return jsonify({
            'error': f'File too large (max {current_app.config["MAX_UPLOAD_SIZE_MB"]}MB)'
        }), 413
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Processing error: {str(e)}'}), 500
