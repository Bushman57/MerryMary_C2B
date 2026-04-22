from flask import Blueprint, request, jsonify
from sqlalchemy import func
from datetime import datetime, timedelta
import logging

from database import db
from models.transaction import Transaction

logger = logging.getLogger(__name__)
transactions_bp = Blueprint('transactions', __name__)


def _is_super_admin() -> bool:
    return bool(getattr(request, 'is_super_admin', False))


def _restricted_date_window():
    """
    For non-super-admins, enforce a 7-day window ending at latest value_date in DB.
    Returns (window_start, window_end). If there is no data, both are None.
    """
    if _is_super_admin():
        return None, None

    max_date = db.session.query(func.max(Transaction.value_date)).scalar()
    if not max_date:
        return None, None
    return max_date - timedelta(days=6), max_date


def _apply_access_window(query):
    """Apply date restriction for non-super-admin users and return (query, access_meta)."""
    window_start, window_end = _restricted_date_window()
    if window_start and window_end:
        query = query.filter(
            Transaction.value_date >= window_start,
            Transaction.value_date <= window_end
        )
        access = {
            'access_scope': 'restricted_last_7_days',
            'effective_start_date': window_start.isoformat(),
            'effective_end_date': window_end.isoformat(),
        }
        return query, access

    if _is_super_admin():
        return query, {'access_scope': 'full'}

    return query, {
        'access_scope': 'restricted_last_7_days',
        'effective_start_date': None,
        'effective_end_date': None,
    }


@transactions_bp.route('/transactions', methods=['GET'])
def get_transactions():
    """
    Get transactions with optional filtering and pagination
    
    Query Parameters:
        phone: Filter by phone number (e.g., 0766200372)
        statement_id: Filter by statement ID
        page: Page number (default: 1)
        limit: Results per page (default: 50, max: 500)
        sort_by: Field to sort by (value_date, credit, debit, balance)
        sort_order: asc or desc (default: desc)
    
    Returns:
        JSON with paginated transactions and metadata
    """
    try:
        # Get query parameters
        phone = request.args.get('phone', type=str)
        statement_id = request.args.get('statement_id', type=str)
        page = request.args.get('page', default=1, type=int)
        limit = request.args.get('limit', default=50, type=int)
        sort_by = request.args.get('sort_by', default='value_date', type=str)
        sort_order = request.args.get('sort_order', default='desc', type=str)

        # Optional date range filters (YYYY-MM-DD)
        start_date_str = request.args.get('start_date', type=str)
        end_date_str = request.args.get('end_date', type=str)
        
        # Validate pagination
        page = max(1, page)
        limit = min(500, max(1, limit))  # Max 500 per page
        
        # Build query
        query = Transaction.query
        
        # Apply filters
        if phone:
            query = query.filter_by(phone_number=phone)
        
        if statement_id:
            query = query.filter_by(statement_id=statement_id)

        # Apply optional date range filters (only for super admins; non-admins are forced to access window)
        # Expect dates as ISO strings (YYYY-MM-DD), matching stored value_date
        try:
            if start_date_str and _is_super_admin():
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                query = query.filter(Transaction.value_date >= start_date)
            if end_date_str and _is_super_admin():
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                query = query.filter(Transaction.value_date <= end_date)
        except ValueError:
            return jsonify({'error': 'Invalid start_date or end_date format. Use YYYY-MM-DD.'}), 400

        query, access = _apply_access_window(query)
        
        # Apply sorting
        if sort_by in ['value_date', 'credit', 'debit', 'balance']:
            sort_column = getattr(Transaction, sort_by)
            if sort_order.lower() == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        else:
            # Default sort by value_date descending
            query = query.order_by(Transaction.value_date.desc())
        
        # Get paginated results
        paginated = query.paginate(page=page, per_page=limit)
        
        return jsonify({
            'success': True,
            'transactions': [t.to_dict() for t in paginated.items],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            },
            'filters': {
                'phone': phone,
                'statement_id': statement_id,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'sort_by': sort_by,
                'sort_order': sort_order
            },
            'access': access
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500


@transactions_bp.route('/transactions/<transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """
    Get a single transaction by ID
    
    Returns:
        JSON with transaction details or 404 if not found
    """
    try:
        query = Transaction.query.filter_by(id=transaction_id)
        query, access = _apply_access_window(query)
        transaction = query.first()
        
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        return jsonify({
            'success': True,
            'transaction': transaction.to_dict(),
            'access': access
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting transaction: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500


@transactions_bp.route('/statements', methods=['GET'])
def get_statements():
    """
    Get all uploaded statements with transaction counts
    
    Returns:
        JSON with list of statements
    """
    try:
        query = db.session.query(
            Transaction.statement_id,
            func.count(Transaction.id).label('count'),
            func.min(Transaction.extracted_at).label('extracted_at')
        ).filter(
            Transaction.statement_id.isnot(None)
        )
        query, access = _apply_access_window(query)
        results = query.group_by(
            Transaction.statement_id
        ).order_by(
            Transaction.extracted_at.desc()
        ).all()

        statements = [
            {
                'statement_id': r[0],
                'transaction_count': r[1],
                'extracted_at': r[2].isoformat() if r[2] else None
            }
            for r in results
        ]
        
        return jsonify({
            'success': True,
            'statements': statements,
            'total': len(statements),
            'access': access
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting statements: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500


@transactions_bp.route('/statements/<statement_id>', methods=['GET'])
def get_statement_transactions(statement_id):
    """
    Get all transactions for a specific statement
    
    Query Parameters:
        page: Page number (default: 1)
        limit: Results per page (default: 50)
    
    Returns:
        JSON with paginated transactions for the statement
    """
    try:
        page = request.args.get('page', default=1, type=int)
        limit = request.args.get('limit', default=50, type=int)
        
        # Validate pagination
        page = max(1, page)
        limit = min(500, max(1, limit))
        
        # Get transactions for statement
        query = Transaction.query.filter_by(statement_id=statement_id)
        query, access = _apply_access_window(query)
        paginated = query.paginate(page=page, per_page=limit)
        
        return jsonify({
            'success': True,
            'statement_id': statement_id,
            'transactions': [t.to_dict() for t in paginated.items],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            },
            'access': access
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting statement transactions: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500


@transactions_bp.route('/transactions/phone/<phone_number>', methods=['GET'])
def get_transactions_by_phone(phone_number):
    """
    Get all transactions for a specific phone number
    
    Query Parameters:
        page: Page number (default: 1)
        limit: Results per page (default: 50)
    
    Returns:
        JSON with paginated transactions for the phone number
    """
    try:
        page = request.args.get('page', default=1, type=int)
        limit = request.args.get('limit', default=50, type=int)
        
        # Validate pagination
        page = max(1, page)
        limit = min(500, max(1, limit))
        
        # Get transactions for phone
        query = Transaction.query.filter_by(phone_number=phone_number)
        query, access = _apply_access_window(query)
        paginated = query.paginate(page=page, per_page=limit)
        
        return jsonify({
            'success': True,
            'phone_number': phone_number,
            'transactions': [t.to_dict() for t in paginated.items],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            },
            'access': access
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting transactions by phone: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500


@transactions_bp.route('/statements/<statement_id>', methods=['DELETE'])
def delete_statement(statement_id):
    """
    Delete all transactions for a statement
    
    Returns:
        JSON with count of deleted transactions
    """
    try:
        count = Transaction.delete_by_statement(statement_id)
        
        return jsonify({
            'success': True,
            'statement_id': statement_id,
            'deleted_count': count,
            'message': f'Deleted {count} transactions'
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting statement: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500


@transactions_bp.route('/transactions/stats/summary', methods=['GET'])
def get_transaction_stats():
    """
    Get summary statistics about all transactions
    
    Returns:
        JSON with transaction statistics
    """
    try:
        base_query = Transaction.query
        base_query, access = _apply_access_window(base_query)
        total = base_query.count()
        by_type = db.session.query(
            Transaction.type,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total_amount')
        ).filter(
            Transaction.id.in_(base_query.with_entities(Transaction.id))
        ).group_by(Transaction.type).all()
        
        by_phone = db.session.query(
            Transaction.phone_number,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total_amount')
        ).filter(
            Transaction.phone_number.isnot(None),
            Transaction.id.in_(base_query.with_entities(Transaction.id))
        ).group_by(
            Transaction.phone_number
        ).order_by(
            func.count(Transaction.id).desc()
        ).limit(20).all()
        
        stats_by_type = [
            {
                'type': r[0],
                'count': r[1],
                'total_amount': float(r[2]) if r[2] else 0
            }
            for r in by_type
        ]
        
        stats_by_phone = [
            {
                'phone_number': r[0],
                'count': r[1],
                'total_amount': float(r[2]) if r[2] else 0
            }
            for r in by_phone
        ]
        
        return jsonify({
            'success': True,
            'summary': {
                'total_transactions': total,
                'by_type': stats_by_type,
                'top_phone_numbers': stats_by_phone
            },
            'access': access
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500
