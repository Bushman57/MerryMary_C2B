---
name: text-based-mps-parser
overview: Replace the current pdfplumber table-based transaction extraction with a text-based parser that reconstructs MPS-only transactions from raw text lines, ignoring EAZZY-MMONEY and similar entries, and cleaning the data appropriately.
todos:
  - id: text-extract-layer
    content: Switch `extract_transactions_from_pdf` to use raw text extraction per page instead of `extract_tables()`.
    status: completed
  - id: mps-record-grouping
    content: Implement `_extract_transactions_from_lines` that groups MPS-starting lines into full records and ignores non-MPS segments.
    status: completed
  - id: field-cleaning
    content: Wire parse_date/parse_amount/phone extraction into the new text-based MPS record parsing.
    status: completed
  - id: integration-check
    content: Verify `/preview-csv` and `/upload` correctly use the new text-based MPS-only parser and produce the expected counts for `Statement_test.pdf`.
    status: completed
isProject: false
---

## Goal

Build a **text-based, MPS-only** transaction parser for bank statements like `statement_test.pdf`, replacing the current table-based logic in `[backend/utils/pdf_parser.py](backend/utils/pdf_parser.py)`. The new parser should:

- Extract from **raw text** instead of `extract_tables()`.
- **Only** capture transactions whose details start with `"MPS "`.
- **Ignore** `EAZZY-MMONEY` and other non-MPS blocks.
- Reconstruct multi-line transactions correctly.
- Provide clean date/amount/phone data for storage and CSV.

## High-Level Approach

```mermaid
flowchart LR
  pdfFile[PDF file] --> textExtract[Extract raw text (per page)]
  textExtract --> lines[Split into lines]
  lines --> groupRecords[Group lines into MPS-based records]
  groupRecords --> parseRecords[Parse each record: date, amount, phone, balance]
  parseRecords --> txns[List of transaction dicts]
  txns --> uploadApi[Existing upload/preview endpoints]
```



## Design Details

### 1. Extract Raw Text (Not Tables)

- In `TransactionExtractor.extract_transactions_from_pdf`:
  - Stop relying on `page.extract_tables()` from `pdfplumber`.
  - Instead, for each page:
    - Use `page.extract_text(x_tolerance=..., y_tolerance=...)` (with reasonable defaults) to get the **full text block**.
    - Split by newline into a list of **logical lines**.
  - Maintain page numbers for context (each transaction can record its source page).

### 2. Reconstruct Transactions from Lines (MPS-only)

- Define a new helper in `[backend/utils/pdf_parser.py](backend/utils/pdf_parser.py)`, e.g. `def _extract_transactions_from_lines(self, lines: List[str], page_num: int, statement_id: str) -> List[Dict]:` that:
  - Iterates over the lines sequentially.
  - Implements a **simple state machine**:
    - **Start of transaction**: A line starting with `"MPS "`.
      - This becomes the **anchor line** for a new record.
      - Initialize a `current_record` with:
        - `details_lines = [anchor_line]`.
        - temporary placeholders for `payment_ref`, `date_str`, `credit_str`, `debit_str`, `balance_str`.
    - **Continuation lines**:
      - Subsequent lines until the next `"MPS "` (or until the end of page) are treated as part of the same record.
      - For each continuation line:
        - Append to `details_lines`.
        - Also scan the line with patterns to capture **reference**, **date**, **amount**, and **balance** if present, e.g.:
          - Detect reference tokens like `S\d+` (e.g. `S65528186`).
          - Detect date pattern `dd/mm/yyyy` or similar (already handled by `parse_date`).
          - Detect numeric patterns for credit/amount (`parse_amount`).
          - The last numeric in the record likely corresponds to **balance**.
    - **End of transaction**:
      - When a new `"MPS "` line appears, or when the lines end, **finalize** the current record:
        - Join `details_lines` with `"\n"` into `transaction_details`.
        - Use the collected `date_str`, credit/debit string, and balance string to populate structured fields:
          - `date = parse_date(date_str)`.
          - `credit_amount = parse_amount(credit_str)` etc.
        - Derive `type` (credit/debit) based on which amount field parsed successfully.
        - Derive `phone_number` by running `extract_phone_from_text` against the **full details text**.
        - Build a transaction dict matching the shape already used downstream.
- **Ignore non-MPS content**:
  - Lines that do not fall within an `MPS` block (e.g. `EAZZY-MMONEY`, headers, account summary, statement footer) are **never added to a record**, so they are naturally excluded.

### 3. Cleaning and Parsing Logic

- **Dates**:
  - Keep using `parse_date` from `TransactionExtractor`.
  - For this statement, ensure `'%d/%m/%Y'` is included (already present) so `10/03/2026` etc. parse correctly.
- **Amounts & Balance**:
  - Reuse and, if needed, slightly refine `parse_amount` to correctly handle formats like `700.00`, `10,000.00`, `67,947.12`.
  - Heuristic for each record:
    - The first parsed numeric after the date is the **credit/debit amount**.
    - The last parsed numeric in the record is the **balance**.
- **References & Phone Numbers**:
  - Keep using `PHONE_REGEX` (`0\d{9}`) across the concatenated `transaction_details` to extract the main phone number.
  - Extract reference IDs with a regex like `S\d+` and store in `reference`.

### 4. Replace Table-based Logic with Text-based Logic

- In `extract_transactions_from_pdf`:
  - Replace the table loop (`page.extract_tables()` and `_parse_table`) with a call to the new text-based pipeline:
    - For each page: get text → split to lines → `_extract_transactions_from_lines` → aggregate transactions.
- Remove or deprecate `_parse_table` and `_merge_multi_line_rows` usage from the main flow (they can remain in code if helpful for future debugging, but they won’t be used for the live parser).
- Keep the public behavior of `extract_transactions_from_pdf` the same (returns a list of transaction dicts with `date`, `description`, `amount`, `type`, `balance`, `reference`, `phone_number`, `raw_data`, `statement_id`, `page`, `confidence`).

### 5. Wire Through Existing Endpoints (No API Changes)

- Ensure `[backend/routes/upload.py](backend/routes/upload.py)` continues to:
  - Call `TransactionExtractor().extract_transactions_from_pdf(...)` in `/upload` and `/preview-csv`.
  - Use returned transactions to:
    - Generate CSV via `generate_csv_from_transactions`.
    - Store to DB via the `Transaction` model.
- No changes required in the frontend or API shapes; the only visible change should be **more accurate MPS-only transaction counts**.

### 6. Validation & Tuning

- **Local debugging**:
  - Add a small debug helper (or reuse `debug_parse_merged.py` pattern) that:
    - Reads raw text from `Statement_test.pdf`.
    - Runs the new `_extract_transactions_from_lines` on it.
    - Prints per-transaction summaries: `date | amount | phone | first 40 chars of details`.
  - Use this to verify that only MPS blocks are included and that counts match what you see in `Statement_test.pdf`.
- **End-to-end check**:
  - Upload `Statement_test.pdf` via the existing frontend flow.
  - Confirm that the **extracted count equals the number of visible MPS transactions** in the PDF.
  - Confirm the CSV preview and stored DB rows are consistent with that count.

## Implementation Todos (Updated for New Approach)

- **text-extract-layer**: Update `extract_transactions_from_pdf` in `[backend/utils/pdf_parser.py](backend/utils/pdf_parser.py)` to iterate pages, call `extract_text`, and split into lines instead of using `extract_tables()`.
- **mps-record-grouping**: Implement `_extract_transactions_from_lines` that groups consecutive lines starting with `"MPS "` into transactions, ignores non-MPS segments, and captures reference/date/amount/balance from within the group.
- **field-cleaning**: Reuse/refine `parse_date`, `parse_amount`, and `extract_phone_from_text` to clean and parse fields from the reconstructed MPS groups.
- **integration-check**: Ensure `/upload` and `/preview-csv` in `[backend/routes/upload.py](backend/routes/upload.py)` work unchanged with the new text-based parser and verify with `Statement_test.pdf`.

