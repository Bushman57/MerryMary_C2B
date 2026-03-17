"""Helper functions for CSV generation"""
import csv
import io
from typing import List, Dict

def generate_csv_from_transactions(transactions: List[Dict]) -> str:
    """
    Generate CSV string from transaction data
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        CSV string with headers and data
    """
    if not transactions:
        return ""
    
    output = io.StringIO()
    
    # Define CSV columns based on transaction keys
    fieldnames = [
        'Date',
        'Transaction Details',
        'Payment Reference',
        'Credit (Money In)',
        'Debit (Money Out)',
        'Balance',
        'Phone Number',
        'Confidence'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for txn in transactions:
        writer.writerow({
            'Date': txn.get('date', ''),
            'Transaction Details': txn.get('description', ''),
            'Payment Reference': txn.get('reference', ''),
            'Credit (Money In)': txn.get('amount', '') if txn.get('type') == 'credit' else '',
            'Debit (Money Out)': txn.get('amount', '') if txn.get('type') == 'debit' else '',
            'Balance': txn.get('balance', ''),
            'Phone Number': txn.get('phone_number', ''),
            'Confidence': txn.get('confidence', '')
        })
    
    return output.getvalue()

def convert_transactions_to_download_format(transactions: List[Dict]) -> List[Dict]:
    """Convert transactions to format suitable for CSV preview"""
    converted = []
    for txn in transactions:
        converted.append({
            'date': txn.get('date', ''),
            'description': txn.get('description', ''),
            'reference': txn.get('reference', ''),
            'amount': txn.get('amount', ''),
            'type': txn.get('type', ''),
            'credit': txn.get('amount', '') if txn.get('type') == 'credit' else '',
            'debit': txn.get('amount', '') if txn.get('type') == 'debit' else '',
            'balance': txn.get('balance', ''),
            'phone_number': txn.get('phone_number', ''),
            'confidence': txn.get('confidence', '')
        })
    return converted
