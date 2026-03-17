#!/usr/bin/env python
"""Debug script to inspect PDF extraction"""
import pdfplumber
import sys
from pathlib import Path

def inspect_pdf(pdf_path):
    """Inspect PDF structure and table extraction"""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ File not found: {pdf_path}")
        return
    
    print(f"📄 Analyzing PDF: {pdf_file.name}\n")
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📊 Total pages: {len(pdf.pages)}\n")
        
        total_rows = 0
        
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"\n{'='*60}")
            print(f"PAGE {page_num}")
            print(f"{'='*60}")
            
            tables = page.extract_tables()
            
            if not tables:
                print("  ⚠️  No tables found on this page")
                continue
            
            print(f"  Found {len(tables)} table(s)")
            
            for table_idx, table in enumerate(tables, 1):
                print(f"\n  TABLE {table_idx}:")
                print(f"    Rows: {len(table)}")
                print(f"    Columns: {len(table[0]) if table else 0}")
                
                # Show first few rows
                print(f"\n    First 3 rows:")
                for row_idx, row in enumerate(table[:3]):
                    print(f"      Row {row_idx}: {row}")
                
                # Show last few rows
                if len(table) > 3:
                    print(f"\n    Last 3 rows:")
                    for row_idx, row in enumerate(table[-3:], len(table) - 3):
                        print(f"      Row {row_idx}: {row}")
                
                total_rows += len(table)
        
        print(f"\n\n{'='*60}")
        print(f"TOTAL ROWS EXTRACTED: {total_rows}")
        print(f"{'='*60}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_pdf.py <path_to_pdf>")
        print("\nExample: python debug_pdf.py uploads/statement.pdf")
        sys.exit(1)
    
    inspect_pdf(sys.argv[1])
