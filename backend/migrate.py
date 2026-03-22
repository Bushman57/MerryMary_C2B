#!/usr/bin/env python
"""Database migration script to update schema"""
import os
from app import create_app
from database import db
from models.transaction import Transaction

def migrate():
    """Drop and recreate tables with new schema"""
    app = create_app()
    
    with app.app_context():
        print("Connecting to database...")
        
        try:
            # Drop the existing transactions table
            print("Dropping existing 'transactions' table...")
            db.session.execute(db.text("DROP TABLE IF EXISTS transactions CASCADE"))
            db.session.commit()
            print("✓ Table dropped")
        except Exception as e:
            print(f"✗ Error dropping table: {e}")
            db.session.rollback()
            return False
        
        try:
            # Create tables with new schema
            print("Creating 'transactions' table with new schema...")
            db.create_all()
            print("✓ Table created with new columns:")
            print("  - transaction_details")
            print("  - payment_reference")
            print("  - value_date")
            print("  - credit")
            print("  - debit")
            print("  - balance")
            print("  - phone_number")
            print("  - transaction_url (partial unique when set)")
            return True
        except Exception as e:
            print(f"✗ Error creating table: {e}")
            return False

if __name__ == '__main__':
    success = migrate()
    if success:
        print("\n✓ Migration completed successfully!")
    else:
        print("\n✗ Migration failed!")
        exit(1)
