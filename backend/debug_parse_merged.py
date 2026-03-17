#!/usr/bin/env python
"""Debug parsing of merged results"""
import pdfplumber
import sys
import logging
from pathlib import Path
from utils.pdf_parser import TransactionExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def debug_parse_merged(pdf_path):
    """Parse all merged transactions and show which pass/fail"""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    extractor = TransactionExtractor()
    
    print(f"📄 Testing parse on all merged transactions\n")
    
    total_tables = 0
    parsed_ok = 0
    parsed_fail = 0
    failed_rows = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            
            if not tables:
                continue
            
            for table_idx, table in enumerate(tables, 1):
                total_tables += 1
                
                # Merge the table
                merged = extractor._merge_multi_line_rows(table)
                
                if not merged:
                    continue
                
                # Parse each merged row
                for row in merged:
                    result = extractor._parse_row(row, page_num, "debug")
                    
                    if result:
                        parsed_ok += 1
                        print(f"✓ Table {total_tables}: {result['date']} | {result['amount']:10.2f} | {result['description'][:40]}")
                    else:
                        parsed_fail += 1
                        row_str = [str(c)[:20] if c else '(empty)' for c in row]
                        failed_rows.append((total_tables, row_str))
                        print(f"✗ Table {total_tables}: PARSE FAILED")
                        print(f"    Details: {row[0][:60] if row else '(empty)'}...")
                        print(f"    Ref: {row[1] if len(row) > 1 else '(empty)'}  Date: {row[2] if len(row) > 2 else '(empty)'}  Amount: {row[3] if len(row) > 3 else '(empty)'}")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY:")
    print(f"  Total tables: {total_tables}")
    print(f"  ✓ Parsed OK: {parsed_ok}")
    print(f"  ✗ Parse failed: {parsed_fail}")
    print(f"  Success rate: {100*parsed_ok/total_tables:.1f}%")
    
    if failed_rows:
        print(f"\n❌ Failed to parse {len(failed_rows)} rows. First few:")
        for table_num, row_str in failed_rows[:5]:
            print(f"  Table {table_num}: {row_str}")
    print(f"{'='*80}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_parse_merged.py <path_to_pdf>")
        sys.exit(1)
    
    debug_parse_merged(sys.argv[1])
