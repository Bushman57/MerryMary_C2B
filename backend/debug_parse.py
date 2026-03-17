#!/usr/bin/env python
"""Debug script to see which rows pass/fail parsing"""
import pdfplumber
import sys
from pathlib import Path
from utils.pdf_parser import TransactionExtractor

def debug_parse_pdf(pdf_path):
    """Extract and show parsing results for each row"""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    extractor = TransactionExtractor()
    
    print(f"📄 Analyzing PDF: {pdf_file.name}\n")
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📊 Total pages: {len(pdf.pages)}\n")
        
        total_rows = 0
        parsed_ok = 0
        parsed_fail = 0
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n{'='*80}")
            print(f"PAGE {page_num}")
            print(f"{'='*80}")
            
            tables = page.extract_tables()
            
            if not tables:
                print("  ⚠️  No tables found on this page")
                continue
            
            for table_idx, table in enumerate(tables, 1):
                print(f"\n  TABLE {table_idx}: {len(table)} rows, {len(table[0]) if table else 0} columns\n")
                
                for row_idx, row in enumerate(table):
                    total_rows += 1
                    
                    # Try parsing
                    result = extractor._parse_row(row, page_num, "debug")
                    
                    if result:
                        parsed_ok += 1
                        print(f"  ✓ Row {row_idx:3d}: {result['date']} | {result['amount']:10.2f} ({result['type']:6s}) | {result['description'][:40]}")
                    else:
                        parsed_fail += 1
                        # Show why it failed
                        row_clean = [str(c).strip() if c else '' for c in row]
                        date_str = row_clean[2] if len(row_clean) > 2 else ''
                        credit = row_clean[3] if len(row_clean) > 3 else ''
                        debit = row_clean[4] if len(row_clean) > 4 else ''
                        print(f"  ✗ Row {row_idx:3d}: FAILED | Date:{date_str:12s} | Credit:{credit:10s} | Debit:{debit:10s} | Details:{row_clean[0][:30]}")
        
        print(f"\n\n{'='*80}")
        print(f"SUMMARY:")
        print(f"  Total rows extracted: {total_rows}")
        print(f"  ✓ Parsed successfully: {parsed_ok}")
        print(f"  ✗ Parse failed: {parsed_fail}")
        print(f"  Success rate: {parsed_ok}/{total_rows} ({100*parsed_ok/total_rows:.1f}%)")
        print(f"{'='*80}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_parse.py <path_to_pdf>")
        sys.exit(1)
    
    debug_parse_pdf(sys.argv[1])
