#!/usr/bin/env python
"""Debug merge logic to see why we're only getting 6 transactions"""
import pdfplumber
import sys
import logging
from pathlib import Path
from utils.pdf_parser import TransactionExtractor

# Configure logging to see debug messages
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def debug_merge_logic(pdf_path):
    """Test the merge logic on the actual PDF"""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    extractor = TransactionExtractor()
    
    print(f"📄 Testing merge logic on: {pdf_file.name}\n")
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📊 Total pages: {len(pdf.pages)}\n")
        
        total_merged = 0
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n{'='*80}")
            print(f"PAGE {page_num}")
            print(f"{'='*80}")
            
            tables = page.extract_tables()
            
            if not tables:
                print("  ⚠️  No tables on this page")
                continue
            
            for table_idx, table in enumerate(tables, 1):
                print(f"\n  TABLE {table_idx}: {len(table)} raw rows\n")
                
                # Show first few raw rows
                print(f"  First 5 raw rows from pdfplumber:")
                for i, row in enumerate(table[:5]):
                    print(f"    Row {i}: {[c[:20] if c else '(empty)' for c in row]}")
                
                # Apply merge
                print(f"\n  Applying merge logic...")
                merged = extractor._merge_multi_line_rows(table)
                
                print(f"\n  ✓ Result: {len(merged)} merged transactions\n")
                
                # Show merged transactions
                for i, row in enumerate(merged):
                    details = row[0][:40] if row and row[0] else '(empty)'
                    date = row[2] if len(row) > 2 else '(no date)'
                    amount = row[3] if len(row) > 3 else '(no amount)'
                    print(f"    Txn {i+1}: {details}... | Date: {date} | Amount: {amount}")
                
                total_merged += len(merged)
        
        print(f"\n\n{'='*80}")
        print(f"TOTAL MERGED TRANSACTIONS: {total_merged}")
        print(f"{'='*80}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_merge_logic.py <path_to_pdf>")
        sys.exit(1)
    
    debug_merge_logic(sys.argv[1])
