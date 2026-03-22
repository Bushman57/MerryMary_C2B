import pdfplumber
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFParseError(Exception):
    """Custom exception for PDF parsing errors"""
    pass


class TransactionExtractor:
    """Extract transactions from PDF bank statements"""
    
    # Regex pattern for phone numbers: 10 digits starting with 0
    PHONE_REGEX = re.compile(r'\b0\d{9}\b')
    
    # Common date formats in bank statements
    DATE_FORMATS = [
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%Y-%m-%d',
        '%d/%m/%y',
        '%d-%m-%y',
    ]
    
    def __init__(self):
        self.transactions = []
    
    @staticmethod
    def extract_phone_from_text(text: str) -> Optional[str]:
        r"""
        Extract phone number from text using regex pattern 0\d{9}
        
        Args:
            text: Text to search for phone number
            
        Returns:
            Phone number string or None if not found
        """
        if not text:
            return None
        
        match = TransactionExtractor.PHONE_REGEX.search(str(text))
        return match.group(0) if match else None

    @staticmethod
    def extract_third_token_from_details(text: Optional[str]) -> Optional[str]:
        """Third whitespace-separated token from transaction details (canonical id)."""
        if text is None:
            return None
        s = str(text).strip()
        if not s:
            return None
        parts = s.split()
        return parts[2] if len(parts) >= 3 else None
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[str]:
        """
        Parse various date formats and return ISO format string
        
        Args:
            date_str: Date string to parse
            
        Returns:
            ISO format date string (YYYY-MM-DD) or None if parsing fails
        """
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        for date_format in TransactionExtractor.DATE_FORMATS:
            try:
                date_obj = datetime.strptime(date_str, date_format)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    @staticmethod
    def parse_amount(amount_str: str) -> Optional[float]:
        """
        Parse amount string to float, handling various formats
        
        Args:
            amount_str: Amount string (may contain commas, spaces, currency symbols)
            
        Returns:
            Float amount or None if parsing fails
        """
        if not amount_str:
            return None
        
        try:
            # Remove common currency symbols and whitespace
            cleaned = str(amount_str).replace('$', '').replace('€', '').replace('£', '')
            cleaned = cleaned.replace(' ', '').strip()

            # Handle thousands separators and decimal marks in a locale-aware way.
            # Examples we expect:
            #   "700.00"        -> 700.00
            #   "10,000.00"     -> 10000.00
            #   "67,947.12"     -> 67947.12
            if ',' in cleaned and '.' in cleaned:
                # If both are present, assume comma is thousands separator and dot is decimal mark,
                # e.g. "10,000.00" or "67,947.12"
                last_comma = cleaned.rfind(',')
                last_dot = cleaned.rfind('.')
                if last_dot > last_comma:
                    # Typical case for statements like Statement_test.pdf
                    cleaned = cleaned.replace(',', '')
                else:
                    # Fallback: treat comma as decimal and dot as thousands
                    cleaned = cleaned.replace('.', '')
                    cleaned = cleaned.replace(',', '.')
            elif ',' in cleaned and '.' not in cleaned:
                # Only comma present – could be either thousands or decimal mark.
                # Heuristic: if there are exactly 3 digits after the comma, treat as thousands sep.
                parts = cleaned.split(',')
                if len(parts[-1]) == 3:
                    cleaned = ''.join(parts)
                else:
                    cleaned = cleaned.replace(',', '.')

            return float(cleaned)
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse amount: {amount_str}")
            return None
    
    def extract_transactions_from_pdf(
        self, 
        pdf_path: str,
        statement_id: str = None
    ) -> List[Dict]:
        """
        Extract ALL transactions from PDF (no filtering)
        
        Args:
            pdf_path: Path to PDF file
            statement_id: Statement ID for tracking source
            
        Returns:
            List of transaction dictionaries (all extracted rows)
            
        Raises:
            PDFParseError: If PDF cannot be parsed
        """
        self.transactions = []
        
        if not Path(pdf_path).exists():
            raise PDFParseError(f"PDF file not found: {pdf_path}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    raise PDFParseError("PDF has no pages")
                
                # Text-based, MPS-only extraction from all pages
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text() or ""
                    except Exception as page_err:
                        logger.error(f"Error extracting text from page {page_num}: {page_err}")
                        continue

                    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                    if not lines:
                        logger.debug(f"Page {page_num}: no text lines extracted, skipping")
                        continue

                    page_transactions = self._extract_transactions_from_lines(
                        lines, page_num, statement_id
                    )
                    self.transactions.extend(page_transactions)
        
        except pdfplumber.PDFFileError as e:
            raise PDFParseError(f"Invalid PDF file: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting PDF: {str(e)}")
            raise PDFParseError(f"Failed to extract PDF: {str(e)}")
        
        logger.info(f"✓ Extracted {len(self.transactions)} MPS transactions from {pdf_path}")
        return self.transactions

    def _extract_transactions_from_lines(
        self,
        lines: List[str],
        page_num: int,
        statement_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Text-based, MPS-only extraction from a list of lines on a page.

        A transaction is defined as a block of lines starting with "MPS ".
        All following lines until the next "MPS " (or end of page) belong
        to the same transaction.
        """
        transactions: List[Dict] = []

        current_details: List[str] = []
        current_tokens: List[str] = []

        def finalize_current() -> None:
            """Finalize current MPS block into a transaction, if possible."""
            if not current_details:
                return

            full_details = "\n".join(current_details)
            tokens = current_tokens[:]

            # Extract potential reference (e.g. S65528186)
            reference = None
            for tok in tokens:
                if re.fullmatch(r"S\d+", tok):
                    reference = tok
                    break

            # Extract date (first token that parses as a date)
            date_str = None
            for tok in tokens:
                parsed = TransactionExtractor.parse_date(tok)
                if parsed:
                    date_str = tok
                    date_iso = parsed
                    break
            else:
                date_iso = None

            if not date_iso:
                # Without a valid date we consider this block not a valid transaction
                logger.debug(
                    f"Skipping MPS block on page {page_num} due to missing parsable date: {full_details[:80]}..."
                )
                return

            # Collect numeric candidates after the date token
            amount_value: Optional[float] = None
            balance_value: Optional[float] = None

            if date_str and date_str in tokens:
                start_idx = tokens.index(date_str) + 1
            else:
                start_idx = 0

            numeric_candidates: List[float] = []
            for tok in tokens[start_idx:]:
                val = TransactionExtractor.parse_amount(tok)
                if val is not None:
                    numeric_candidates.append(val)

            if numeric_candidates:
                # Heuristic: first numeric after date is amount, last numeric is balance
                amount_value = numeric_candidates[0]
                balance_value = numeric_candidates[-1] if len(numeric_candidates) > 1 else None

            if amount_value is None:
                logger.debug(
                    f"Skipping MPS block on page {page_num} due to missing parsable amount: {full_details[:80]}..."
                )
                return

            # Determine credit/debit type – for these statements MPS are usually credits
            txn_type = "credit" if amount_value >= 0 else "debit"

            phone_number = TransactionExtractor.extract_phone_from_text(full_details)

            transaction = {
                "date": date_iso,
                "description": full_details[:500],
                "amount": amount_value,
                "type": txn_type,
                "balance": balance_value,
                "reference": reference,
                "phone_number": phone_number,
                "transaction_url": TransactionExtractor.extract_third_token_from_details(
                    full_details
                ),
                "transactional_details": full_details,
                "raw_data": {
                    "lines": current_details,
                    "tokens": tokens,
                },
                "statement_id": statement_id,
                "page": page_num,
                "confidence": 0.95 if phone_number else 0.9,
            }

            logger.info(
                f"✓ Parsed MPS tx on page {page_num}: {date_iso} | {amount_value} | {phone_number}"
            )
            transactions.append(transaction)

        for line in lines:
            if not line:
                continue

            # Start of new MPS transaction block
            if line.startswith("MPS "):
                # Finalize previous block (if any)
                finalize_current()

                current_details = [line]
                current_tokens = line.split()
                continue

            # Ignore lines outside of an MPS block
            if not current_details:
                continue

            # Continuation of current MPS block
            current_details.append(line)
            current_tokens.extend(line.split())

        # Finalize last block
        finalize_current()

        logger.info(
            f"Page {page_num}: Extracted {len(transactions)} MPS transactions from text lines"
        )
        return transactions
    
    def _parse_table(
        self, 
        table: List[List[str]], 
        page_num: int,
        statement_id: str = None
    ) -> List[Dict]:
        """
        Parse a single table from PDF page
        
        Handles multi-line transaction details by merging continuation rows
        before parsing as complete transactions.
        
        Args:
            table: Table data (list of rows)
            page_num: Page number in PDF
            statement_id: Statement ID
            
        Returns:
            List of parsed transaction dictionaries
        """
        if not table or len(table) < 2:
            return []
        
        # First pass: Merge multi-line transaction details
        merged_rows = self._merge_multi_line_rows(table)
        
        transactions = []
        
        # Second pass: Parse merged rows
        for row_idx, row in enumerate(merged_rows):
            # Skip completely empty rows
            if not row or all(not cell for cell in row):
                logger.debug(f"Skipping empty row {row_idx}")
                continue
            
            # Try to parse as transaction - let _parse_row do the validation
            transaction = self._parse_row(row, page_num, statement_id)
            if transaction:
                logger.debug(f"Row {row_idx}: ✓ Parsed as transaction")
                transactions.append(transaction)
            else:
                logger.debug(f"Row {row_idx}: Could not parse as valid transaction")
        
        return transactions
    
    def _merge_multi_line_rows(self, table: List[List[str]]) -> List[List[str]]:
        """
        Merge multi-line transaction details using "MPS " as transaction start marker
        
        Each transaction starts with "MPS " in the transaction details column.
        All subsequent rows until the next "MPS " are continuation lines that 
        belong to that transaction.
        
        Args:
            table: Raw extracted table rows
            
        Returns:
            Merged rows with multi-line details combined
        """
        merged: List[List[str]] = []
        current_row: Optional[List[str]] = None

        # Known markers that typically start a new transaction in common statements
        start_markers = ("MPS ", "EAZZY-MMONEY", "SMS CHARGE")

        logger.debug(f"Starting merge on table with {len(table)} rows")

        for row_idx, row in enumerate(table):
            if not row or all(not cell for cell in row):
                logger.debug(f"  Row {row_idx}: Empty row, skipping")
                continue

            # Clean cells
            row_clean = [str(c).strip() if c else '' for c in row]
            if not row_clean:
                continue

            details = row_clean[0]

            # Skip header-like rows that repeat column titles
            header_text = details.lower()
            if (
                "transaction details" in header_text
                and "payment reference" in " ".join(row_clean).lower()
            ):
                logger.debug(f"  Row {row_idx}: Detected header row, skipping")
                continue

            # Helper flags
            has_date = False
            has_amount = False
            if len(row_clean) > 2 and row_clean[2]:
                if TransactionExtractor.parse_date(row_clean[2]):
                    has_date = True
            # Try credit then debit as candidate amount columns if present
            if len(row_clean) > 3 and row_clean[3]:
                if TransactionExtractor.parse_amount(row_clean[3]) is not None:
                    has_amount = True
            if not has_amount and len(row_clean) > 4 and row_clean[4]:
                if TransactionExtractor.parse_amount(row_clean[4]) is not None:
                    has_amount = True

            starts_with_marker = any(details.startswith(m) for m in start_markers)
            looks_like_transaction_start = has_date and has_amount

            if starts_with_marker:
                # This row clearly starts a new transaction.
                if current_row:
                    merged.append(current_row)
                    logger.debug(
                        f"  Row {row_idx}: Found start marker - saved transaction #{len(merged)}"
                    )
                current_row = row_clean
                logger.debug(
                    f"  Row {row_idx}: Started new transaction with marker: {details[:80]}..."
                )
                continue

            if looks_like_transaction_start:
                # Row has both date and amount information. Decide whether this
                # completes the current transaction or starts a fresh one.
                if current_row:
                    current_has_date = False
                    if len(current_row) > 2 and current_row[2]:
                        if TransactionExtractor.parse_date(current_row[2]):
                            current_has_date = True

                    if current_has_date:
                        # Current transaction already has a date -> we treat this as a new one.
                        merged.append(current_row)
                        logger.debug(
                            f"  Row {row_idx}: New dated row -> saved previous transaction #{len(merged)}"
                        )
                        current_row = row_clean
                        logger.debug(
                            f"  Row {row_idx}: Started new transaction from dated row: {details[:80]}..."
                        )
                        continue
                    else:
                        # Current transaction is missing date/amount – this row likely completes it.
                        logger.debug(
                            f"  Row {row_idx}: Completing current transaction with date/amount row"
                        )
                        # Append textual details
                        if details:
                            current_row[0] = current_row[0] + '\n' + details
                        # Fill in other columns
                        for i in range(1, min(len(row_clean), len(current_row))):
                            if row_clean[i] and not current_row[i]:
                                current_row[i] = row_clean[i]
                                logger.debug(f"    Filled column {i}: {row_clean[i]}")
                        for i in range(len(current_row), len(row_clean)):
                            current_row.append(row_clean[i])
                        continue
                else:
                    # No current transaction – start one from this dated row.
                    current_row = row_clean
                    logger.debug(
                        f"  Row {row_idx}: Started first transaction from dated row: {details[:80]}..."
                    )
                    continue

            # Otherwise this is a continuation line (extra details, names, etc.)
            if current_row:
                if details:
                    current_row[0] = current_row[0] + '\n' + details
                    logger.debug(
                        f"  Row {row_idx}: Appended continuation to current transaction: {details[:80]}..."
                    )

                # Fill in other columns if they have data (payment ref, date, amounts, balance)
                for i in range(1, min(len(row_clean), len(current_row))):
                    if row_clean[i] and not current_row[i]:
                        current_row[i] = row_clean[i]
                        logger.debug(f"    Filled column {i}: {row_clean[i]}")

                # Add any extra columns at the end
                for i in range(len(current_row), len(row_clean)):
                    current_row.append(row_clean[i])
            else:
                # Orphaned continuation (no preceding start row) - skip it
                logger.debug(
                    f"  Row {row_idx}: Orphaned continuation (no current transaction), skipping: {details[:80]}..."
                )
                continue

        # Don't forget the last transaction
        if current_row:
            merged.append(current_row)
            logger.debug(f"  EOT: Saved final transaction #{len(merged)}")

        logger.info(
            f"✓ Merged {len(table)} extracted rows into {len(merged)} candidate transactions"
        )
        return merged
    
    def _parse_row(
        self, 
        row: List[str], 
        page_num: int,
        statement_id: str = None
    ) -> Optional[Dict]:
        """
        Parse a single row from table
        
        Handles bank statement with columns:
        [Transaction Details, Payment Reference, Value Date, Credit, Debit, Balance]
        
        Transaction details can span multiple lines - this method handles that.
        
        Args:
            row: Row data (list of cell values)
            page_num: Page number
            statement_id: Statement ID
            
        Returns:
            Transaction dictionary or None if row cannot be parsed
        """
        if not row or all(not cell for cell in row):
            return None
        
        # Clean row data - preserve multiline content in transaction details
        row = [str(cell).strip() if cell else '' for cell in row]
        
        # Skip rows with too few cells (need at least date and amount)
        non_empty_cells = [c for c in row if c]
        if len(non_empty_cells) < 3:
            logger.debug(f"Skipping row with insufficient data: {non_empty_cells}")
            return None
        
        # Column mapping for standard bank statement
        # [Transaction Details, Payment Ref, Value Date, Credit, Debit, Balance]
        try:
            transaction_details = row[0] if len(row) > 0 else ''
            payment_reference = row[1] if len(row) > 1 else ''
            date_str = row[2] if len(row) > 2 else ''
            credit = row[3] if len(row) > 3 else ''
            debit = row[4] if len(row) > 4 else ''
            balance_str = row[5] if len(row) > 5 else ''
            
            # Try to parse date - if fails, this is not a valid transaction row
            date = self.parse_date(date_str)
            if not date:
                logger.debug(f"Row has no valid date, skipping: {date_str}")
                return None
            
            # Parse credit and debit amounts
            credit_amount = self.parse_amount(credit) if credit else None
            debit_amount = self.parse_amount(debit) if debit else None
            
            # Use Credit column as the primary amount (Money In)
            # If credit exists, use it; otherwise use debit (Money Out)
            if credit_amount and credit_amount > 0:
                amount = credit_amount
                txn_type = 'credit'
            elif debit_amount and debit_amount > 0:
                amount = debit_amount
                txn_type = 'debit'
            else:
                logger.debug(f"No valid amount in Credit column: {credit}, Debit column: {debit}")
                return None
            
            # Use transaction details as description (can be multi-line)
            description = transaction_details if transaction_details else payment_reference
            if not description:
                logger.debug("No description found in transaction")
                return None
            
            # Extract phone number from transaction details
            phone_number = self.extract_phone_from_text(transaction_details)
            if not phone_number:
                # Also try payment reference
                phone_number = self.extract_phone_from_text(payment_reference)
            
            # Parse balance
            balance = self.parse_amount(balance_str) if balance_str else None
            
            transaction = {
                'date': date,
                'description': description[:500],
                'amount': amount,
                'type': txn_type,
                'balance': balance,
                'reference': payment_reference,
                'phone_number': phone_number,
                'transaction_url': TransactionExtractor.extract_third_token_from_details(
                    transaction_details
                ),
                'transactional_details': transaction_details,
                'raw_data': row,
                'statement_id': statement_id,
                'page': page_num,
                'confidence': 0.95 if phone_number else 0.85
            }
            
            logger.info(f"✓ Parsed: {date} | Amount: {amount} ({txn_type}) | Phone: {phone_number}")
            return transaction
        
        except Exception as e:
            logger.error(f"Error parsing row: {str(e)}, Row: {row}")
            return None
    
    @staticmethod
    def _determine_transaction_type(amount: float, row: List[str]) -> str:
        """
        Determine if transaction is debit or credit
        
        Args:
            amount: Transaction amount
            row: Full row data for context
            
        Returns:
            'debit' or 'credit'
        """
        if amount is None:
            return 'unknown'
        
        # Check for negative sign or common debit indicators
        if amount < 0:
            return 'debit'
        
        # Check if row contains debit/withdrawal indicators
        row_text = ' '.join(str(cell).lower() for cell in row if cell)
        if any(term in row_text for term in ['debit', 'withdrawal', 'charge', 'out']):
            return 'debit'
        
        return 'credit'
    
    def validate_extracted_transactions(self) -> Tuple[List[Dict], List[str]]:
        """
        Validate extracted transactions - returns ALL transactions
        Errors are logged but don't prevent storage
        
        Returns:
            Tuple (all_transactions, error_messages)
        """
        errors = []
        
        for idx, txn in enumerate(self.transactions):
            # Check if has critical fields
            if not txn.get('date'):
                errors.append(f"Transaction {idx}: Missing date")
            if not txn.get('description'):
                errors.append(f"Transaction {idx}: Missing description")
            if not txn.get('amount'):
                errors.append(f"Transaction {idx}: Missing amount")
        
        logger.info(f"Extracted {len(self.transactions)} transactions total")
        if errors:
            logger.warning(f"Found {len(errors)} potential issues: {errors[:5]}")
        
        # Return ALL transactions (don't filter)
        return self.transactions, errors
