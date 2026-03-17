#!/usr/bin/env python
"""Direct SQL migration to fix database schema"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

def migrate_database():
    """Drop and recreate transactions table with correct schema"""
    
    # Get database URL from environment
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in .env file")
        return False
    
    try:
        print(f"🔗 Connecting to database...")
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Drop existing table
        print("🗑️  Dropping existing 'transactions' table...")
        cursor.execute("DROP TABLE IF EXISTS transactions CASCADE")
        print("✓ Table dropped")
        
        # Create new table with correct schema
        print("📝 Creating new 'transactions' table...")
        create_sql = """
        CREATE TABLE transactions (
            id VARCHAR(36) PRIMARY KEY,
            transaction_details TEXT NOT NULL,
            payment_reference VARCHAR(255),
            value_date DATE NOT NULL,
            credit FLOAT,
            debit FLOAT,
            balance FLOAT,
            phone_number VARCHAR(20),
            raw_data JSONB,
            statement_id VARCHAR(100),
            confidence FLOAT DEFAULT 1.0,
            manual_review BOOLEAN DEFAULT FALSE,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_sql)
        print("✓ Table created with new schema")
        
        # Create indexes
        print("📌 Creating indexes...")
        cursor.execute("CREATE INDEX idx_transaction_details ON transactions(transaction_details)")
        cursor.execute("CREATE INDEX idx_payment_reference ON transactions(payment_reference)")
        cursor.execute("CREATE INDEX idx_value_date ON transactions(value_date)")
        cursor.execute("CREATE INDEX idx_phone_number ON transactions(phone_number)")
        cursor.execute("CREATE INDEX idx_statement_id ON transactions(statement_id)")
        print("✓ Indexes created")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database migration completed successfully!")
        print("\nNew schema:")
        print("  ✓ transaction_details (TEXT, required)")
        print("  ✓ payment_reference (VARCHAR)")
        print("  ✓ value_date (DATE, required)")
        print("  ✓ credit (FLOAT) - Money In")
        print("  ✓ debit (FLOAT) - Money Out")
        print("  ✓ balance (FLOAT)")
        print("  ✓ phone_number (VARCHAR)")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == '__main__':
    success = migrate_database()
    exit(0 if success else 1)
