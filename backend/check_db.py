#!/usr/bin/env python
"""Check what transactions are in the database"""
from app import create_app
from models.transaction import Transaction

app = create_app()

with app.app_context():
    # Get all transactions
    transactions = Transaction.query.all()
    
    print(f"\n📊 Total transactions in database: {len(transactions)}\n")
    
    if transactions:
        print("Latest 10 transactions:")
        print("-" * 100)
        for txn in transactions[-10:]:
            print(f"ID: {txn.id}")
            print(f"  Date: {txn.value_date}")
            print(f"  Details: {txn.transaction_details[:60]}...")
            print(f"  Ref: {txn.payment_reference}")
            print(f"  Credit: {txn.credit}, Debit: {txn.debit}")
            print(f"  Phone: {txn.phone_number}")
            print(f"  Statement: {txn.statement_id}")
            print("-" * 100)
        
        # Group by statement
        statements = {}
        for txn in transactions:
            stmt_id = txn.statement_id
            if stmt_id not in statements:
                statements[stmt_id] = []
            statements[stmt_id].append(txn)
        
        print(f"\n📋 Transactions by statement:")
        for stmt_id, txns in statements.items():
            print(f"  {stmt_id}: {len(txns)} rows")
