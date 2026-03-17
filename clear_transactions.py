"""
Utility script to delete ALL rows from the transactions table.

Usage (from the backend directory):

    python clear_transactions.py

This will:
- Create the Flask app using the existing app factory
- Open an application context
- Delete all Transaction rows
- Commit the change and print how many rows were removed
"""

from app import create_app
from database import db
from models.transaction import Transaction


def clear_all_transactions() -> int:
    """Delete all rows from the transactions table and return the count."""
    deleted = Transaction.query.delete()
    db.session.commit()
    return deleted


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        count = clear_all_transactions()
        print(f"Deleted {count} transactions from the database.")

