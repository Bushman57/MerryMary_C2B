#!/usr/bin/env python
"""
Backfill transaction_url (third whitespace token), tally duplicates, remove extras.

Keeps the row with the earliest created_at (then smallest id) per transaction_url.

From the backend directory:

  python scripts/dedupe_transaction_url.py --schema
  python scripts/dedupe_transaction_url.py
  python scripts/dedupe_transaction_url.py --create-index

Or: python scripts/dedupe_transaction_url.py --all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import func, text

from app import create_app
from database import db
from models.transaction import Transaction
from utils.pdf_parser import TransactionExtractor


def run_schema() -> None:
    """Add transaction_url column and remove legacy composite uniqueness."""
    db.session.execute(
        text(
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS transaction_url VARCHAR(255)"
        )
    )
    db.session.execute(
        text(
            "ALTER TABLE transactions DROP CONSTRAINT IF EXISTS uq_transactions_statement_txn"
        )
    )
    db.session.execute(text("DROP INDEX IF EXISTS uq_transactions_statement_txn"))
    db.session.commit()
    print("Schema: column added (if missing), old unique constraint/index dropped.")


def run_backfill(batch_size: int = 500) -> int:
    """Set transaction_url where NULL using third token of transaction_details."""
    updated = 0
    last_id = ""
    while True:
        q = Transaction.query.filter(Transaction.transaction_url.is_(None))
        if last_id:
            q = q.filter(Transaction.id > last_id)
        rows = q.order_by(Transaction.id).limit(batch_size).all()
        if not rows:
            break
        batch_updated = 0
        for row in rows:
            token = TransactionExtractor.extract_third_token_from_details(
                row.transaction_details
            )
            if token:
                row.transaction_url = token
                batch_updated += 1
        updated += batch_updated
        last_id = rows[-1].id
        db.session.commit()
        print(
            f"  Backfill: batch of {len(rows)} rows (through id={last_id}), "
            f"set token on {batch_updated}"
        )
    print(f"Backfill complete: populated transaction_url on {updated} rows total.")
    return updated


def run_dedupe() -> int:
    """Print per-URL duplicate tallies and delete all but one row per transaction_url."""
    dup_keys = (
        db.session.query(Transaction.transaction_url, func.count(Transaction.id))
        .filter(Transaction.transaction_url.isnot(None))
        .group_by(Transaction.transaction_url)
        .having(func.count(Transaction.id) > 1)
        .all()
    )

    if not dup_keys:
        print("Dedupe: no duplicate transaction_url values found.")
        return 0

    total_removed = 0
    print("Duplicate transaction_url tallies:")
    for url, cnt in dup_keys:
        print(f"  {url}: {cnt} rows")

    for url, cnt in dup_keys:
        rows = (
            Transaction.query.filter_by(transaction_url=url)
            .order_by(Transaction.created_at.asc(), Transaction.id.asc())
            .all()
        )
        keep = rows[0]
        for r in rows[1:]:
            db.session.delete(r)
            total_removed += 1
        print(f"  Kept id={keep.id} for {url}, removed {cnt - 1}")

    db.session.commit()
    print(f"Dedupe complete: removed {total_removed} duplicate rows.")
    return total_removed


def run_create_index() -> None:
    db.session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_transactions_transaction_url
            ON transactions (transaction_url)
            WHERE transaction_url IS NOT NULL
            """
        )
    )
    db.session.commit()
    print("Created partial unique index uq_transactions_transaction_url (if not present).")


def main() -> None:
    parser = argparse.ArgumentParser(description="transaction_url backfill and dedupe")
    parser.add_argument(
        "--schema",
        action="store_true",
        help="ADD COLUMN transaction_url and drop legacy uq_transactions_statement_txn",
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="CREATE partial unique index on transaction_url (after duplicates removed)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run schema, backfill, dedupe, create-index",
    )
    parser.add_argument(
        "--only-dedupe",
        action="store_true",
        help="Only dedupe (no backfill)",
    )
    parser.add_argument(
        "--only-backfill",
        action="store_true",
        help="Only backfill",
    )
    args = parser.parse_args()

    if args.only_dedupe and args.only_backfill:
        parser.error("Cannot combine --only-dedupe and --only-backfill")

    app = create_app()
    with app.app_context():
        if args.all:
            run_schema()
            run_backfill()
            run_dedupe()
            run_create_index()
            return

        if args.schema:
            run_schema()

        if args.only_dedupe:
            run_dedupe()
        elif args.only_backfill:
            run_backfill()
        else:
            run_backfill()
            run_dedupe()

        if args.create_index:
            run_create_index()


if __name__ == "__main__":
    main()
