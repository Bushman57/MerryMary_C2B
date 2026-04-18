from datetime import datetime
from uuid import uuid4
from sqlalchemy import Index, text

from database import db


class Transaction(db.Model):
    """Transaction model for storing bank statement transactions"""
    __tablename__ = 'transactions'
    __table_args__ = (
        Index(
            'uq_transactions_transaction_url',
            'transaction_url',
            unique=True,
            postgresql_where=text('transaction_url IS NOT NULL'),
        ),
    )
    
    # Primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Match exact bank statement column names
    transaction_details = db.Column(db.Text, nullable=False, index=True)
    payment_reference = db.Column(db.String(255), index=True)
    value_date = db.Column(db.Date, nullable=False, index=True)
    credit = db.Column(db.Float)  # Money In
    debit = db.Column(db.Float)   # Money Out
    balance = db.Column(db.Float)
    
    # Extracted phone number from transaction details
    phone_number = db.Column(db.String(20), index=True)

    # Canonical id from transaction details (MPS: 3rd token / else 2nd on first line)
    transaction_url = db.Column(db.String(255), nullable=True)
    
    # Raw data from PDF extraction
    raw_data = db.Column(db.JSON)
    
    # Statement reference
    statement_id = db.Column(db.String(100), index=True)
    
    # Metadata
    confidence = db.Column(db.Float, default=1.0)
    manual_review = db.Column(db.Boolean, default=False)
    
    # Timestamps
    extracted_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            'id': self.id,
            'transaction_details': self.transaction_details,
            'payment_reference': self.payment_reference,
            'value_date': self.value_date.isoformat() if self.value_date else None,
            'credit': self.credit,
            'debit': self.debit,
            'balance': self.balance,
            'phone_number': self.phone_number,
            'transaction_url': self.transaction_url,
            'statement_id': self.statement_id,
            'metadata': {
                'confidence': self.confidence,
                'manual_review': self.manual_review,
                'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
                'created_at': self.created_at.isoformat() if self.created_at else None
            }
        }
    
    def __repr__(self):
        return f'<Transaction {self.id} - {self.value_date} - Credit: {self.credit}, Debit: {self.debit}>'
    
    @staticmethod
    def get_by_phone(phone_number, page=1, limit=50):
        """Query transactions by phone number with pagination"""
        return Transaction.query.filter_by(
            phone_number=phone_number
        ).paginate(page=page, per_page=limit)
    
    @staticmethod
    def get_by_statement(statement_id, page=1, limit=50):
        """Query transactions by statement ID with pagination"""
        return Transaction.query.filter_by(
            statement_id=statement_id
        ).paginate(page=page, per_page=limit)
    
    @staticmethod
    def get_statements():
        """Get all unique statements with transaction counts"""
        from sqlalchemy import func
        
        results = db.session.query(
            Transaction.statement_id,
            func.count(Transaction.id).label('count'),
            func.min(Transaction.extracted_at).label('extracted_at')
        ).filter(
            Transaction.statement_id.isnot(None)
        ).group_by(
            Transaction.statement_id
        ).order_by(
            Transaction.extracted_at.desc()
        ).all()
        
        return [
            {
                'statement_id': r[0],
                'transaction_count': r[1],
                'extracted_at': r[2].isoformat() if r[2] else None
            }
            for r in results
        ]
    
    @staticmethod
    def delete_by_statement(statement_id):
        """Delete all transactions for a statement"""
        count = Transaction.query.filter_by(statement_id=statement_id).delete()
        db.session.commit()
        return count
