# Transaction History Analyzer

A web application for uploading PDF bank statements, extracting transaction data, and filtering transactions by phone number.

## Features

✅ **PDF Upload** - Drag-and-drop PDF file upload with progress tracking  
✅ **Transaction Extraction** - Automatic table extraction using pdfplumber  
✅ **Phone Number Filtering** - Extract and filter transactions by phone number (10 digits starting with 0)  
✅ **Data Persistence** - Store transactions in Neon PostgreSQL  
✅ **Responsive UI** - Modern Vue 3 interface with real-time filtering  
✅ **Transaction Statistics** - Summary stats and analytics  
✅ **Google Sign-In** - Firebase Authentication; API routes verify ID tokens with Firebase Admin  
✅ **Duplicate handling** - Each transaction is keyed by a stable id derived from statement text (`transaction_url`: third whitespace-separated token in transaction details). Re-uploads skip rows already in the database; PostgreSQL enforces at most one row per non-null id. A maintenance script can backfill ids and remove historical duplicates.

## Tech Stack

### Backend
- **Flask** - Python web framework
- **SQLAlchemy** - ORM for database operations
- **pdfplumber** - PDF table extraction
- **Neon PostgreSQL** - Cloud-hosted PostgreSQL database
- **Gunicorn** - Production WSGI server

### Frontend
- **Vue 3** - JavaScript framework
- **Pinia** - State management
- **Vite** - Build tool
- **Axios** - HTTP client
- **Firebase** - Google Sign-In on the client
- **CSS3** - Styling with flexbox/grid

## Project Structure

```
transaction_history/
├── backend/                    # Flask API
│   ├── app.py                 # Flask application factory
│   ├── config.py              # Configuration management
│   ├── requirements.txt        # Python dependencies
│   ├── .env                   # Environment variables (Neon connection)
│   ├── models/                # SQLAlchemy models
│   │   └── transaction.py     # Transaction model with query helpers
│   ├── routes/                # API endpoints
│   │   ├── upload.py          # POST /api/upload endpoint
│   │   └── transactions.py    # GET /api/transactions, filtering, stats
│   ├── scripts/               # DB maintenance (e.g. transaction_url backfill / dedupe)
│   └── utils/                 # Utility functions
│       ├── pdf_parser.py      # PDF extraction with phone regex and transaction_url token
│       ├── validators.py      # File & PDF validators
│       └── firebase_auth.py   # Firebase Admin token verification
│
├── frontend/                   # Vue 3 SPA
│   ├── index.html             # HTML entry point
│   ├── vite.config.js         # Vite configuration
│   ├── package.json           # Node dependencies
│   ├── .env                   # API URL configuration
│   └── src/
│       ├── main.js            # Vue app entry
│       ├── App.vue            # Root component
│       ├── components/        # Vue components
│       │   ├── FileUpload.vue # Drag-drop upload
│       │   └── TransactionTable.vue # Table with filters
│       ├── store/             # Pinia state management
│       │   ├── index.js       # App store (transactions, filters)
│       │   └── auth.js        # Firebase auth + ID token for API
│       ├── firebase.js        # Firebase client initialization
│       └── utils/             # Utilities
│           └── api.js         # Axios API client
│
└── README.md                  # This file
```

## Setup Instructions

### Prerequisites

- **Python 3.9+** - For backend
- **Node.js 18+** - For frontend
- **Neon PostgreSQL** - Create a free account at https://neon.tech

### Backend Setup

1. **Clone and navigate to backend**
   ```bash
   cd transaction_history/backend
   ```

2. **Create Python virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Neon PostgreSQL**
   - Create account at https://neon.tech (free tier available)
   - Create new project and database
   - Copy connection string (format: `postgresql://user:password@host/database`)

5. **Set up environment variables**
   ```bash
   # Copy example
   cp .env.example .env
   
   # Edit .env and add your Neon connection string
   # DATABASE_URL=postgresql://... (from Neon)
   ```

   **Firebase Admin (production or full local testing)**  
   - In [Firebase Console](https://console.firebase.google.com), create a project, enable **Authentication → Google**, and add a **Web** app to get client config for the frontend.  
   - In Project settings → **Service accounts**, generate a new private key (JSON).  
   - Backend: set `FIREBASE_CREDENTIALS_PATH` to the JSON file path (on Render, secret files are under `/etc/secrets/...`), or set `GOOGLE_APPLICATION_CREDENTIALS` to a local file path, or paste the JSON as one line in `FIREBASE_CREDENTIALS_JSON`.  
   - For local quick testing **without** Firebase, set `FIREBASE_AUTH_DISABLED=true` in `backend/.env` (do not use in production).

6. **Start Flask server**
   ```bash
   python app.py
   ```
   Server runs on `http://localhost:5000`

   **Production (e.g. Render):** Gunicorn should bind to `$PORT` and typically use `--workers 1` for faster cold boots; see [deployment.md](deployment.md). With `FLASK_ENV=production`, the app does not run `db.create_all()` on startup unless you set `ENABLE_DB_CREATE_ALL=true`.

### Frontend Setup

1. **Open new terminal and navigate to frontend**
   ```bash
   cd transaction_history/frontend
   ```

   Copy `frontend/.env.example` to `frontend/.env` and set:
   - `VITE_API_BASE_URL` (e.g. `http://localhost:5000/api` or your Render API URL with `/api`)
   - `VITE_FIREBASE_*` values from Firebase Console → Project settings → Your apps (Web).

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```
   Frontend runs on `http://localhost:5173`

## Usage

1. **Open browser** → `http://localhost:5173`
2. **Upload PDF** → Click upload zone or drag-drop a bank statement PDF
3. **View Transactions** → Table appears with extracted transactions
4. **Filter by Phone** → Use dropdown to filter transactions by phone number (10 digits starting with 0)
5. **Sort & Analyze** → Sort by date, amount, or description; view statistics

## API Endpoints

### Upload
- `POST /api/upload` - Upload and process PDF statement (response includes `skipped_existing_url` and `skipped_no_url` when rows are skipped for deduplication)

### Transactions
- `GET /api/transactions` - Get all transactions with optional filters
  - Query params: `phone`, `statement_id`, `page`, `limit`, `sort_by`, `sort_order`
- `GET /api/transactions/:id` - Get transaction by ID
- `GET /api/transactions/phone/:phone_number` - Get transactions by phone number

### Statements
- `GET /api/statements` - Get all uploaded statements with counts
- `GET /api/statements/:statement_id` - Get transactions for a statement
- `DELETE /api/statements/:statement_id` - Delete statement and transactions

### Statistics
- `GET /api/transactions/stats/summary` - Get summary statistics

## Deduplication and `transaction_url`

- **Identity**: From the **first line** of transaction details: MPS-style lines use the **third** token (e.g. `MPS 254791859862 UCBAV90KI3 …` → `UCBAV90KI3`). Lines **without** the `MPS ` prefix use the **second** token (the payment detail code, e.g. `254… UDH3116RGT …` → `UDH3116RGT`, or `254… UE15Q35HHC …` → `UE15Q35HHC`). That value is stored as `transaction_url`.
- **On upload**: Rows without that token are skipped; if `transaction_url` already exists in the database, the row is skipped and tallies are returned in the upload response (`skipped_existing_url`, `skipped_no_url`).
- **Database**: A partial unique index on `transaction_url` (where not null) prevents duplicate ids at insert time once the schema is applied.
- **Existing data**: From `backend/`, run `python scripts/dedupe_transaction_url.py --help`. Typical one-time upgrade: `python scripts/dedupe_transaction_url.py --all` (adds column if needed, drops legacy composite uniqueness, backfills tokens, removes duplicate rows while printing per-key tallies, creates the unique index). Run against your Neon `DATABASE_URL` with the same `.env` as the app.

## Phone Number Extraction

- **Pattern**: `0\d{9}` (10-digit numbers starting with 0)
- **Extraction**: Phone numbers extracted from "transactional details" column in PDF
- **Storage**: Indexed in database for fast filtering
- **Example**: `0766200372` → Extracted and searchable

## PDF Format Support

The extractor works best with:
- Machine-generated PDFs with tabular data
- Standard bank statement format (date, description, amount, balance columns)
- Single or multi-page statements

Non-`MPS` Equity-style lines must match a **two-letter prefix + 8 alphanumeric** payment code on the same line as a Kenyan phone (e.g. `UD…`, `UE…`). Allowed prefixes are configurable in `backend/.env` via **`TRANSACTION_DETAIL_CODE_PREFIXES`** (comma-separated, default `UD`). For statements that use codes starting with `UE` (or others), set e.g. `TRANSACTION_DETAIL_CODE_PREFIXES=UD,UE` and restart the API.

## Database Schema

See [`backend/models/transaction.py`](backend/models/transaction.py) for the authoritative model. Notable columns:

| Column | Role |
|--------|------|
| `transaction_details` | Description / details text from the statement |
| `value_date` | Transaction date |
| `credit` / `debit` | Money in / out |
| `balance` | Running balance when present |
| `phone_number` | Local `0\d{9}`; `254\d{9}` in text is normalized to the same form |
| `transaction_url` | MPS: 3rd token on first line; non-MPS: 2nd token (payment detail code); **unique** (when not null) for deduplication |
| `statement_id` | Hash-derived id for the source PDF |
| `raw_data` | JSON from extraction |

Fresh installs using [`backend/migrate_direct.py`](backend/migrate_direct.py) get a matching PostgreSQL definition including the partial unique index on `transaction_url`.

## Performance Notes

- Indexes on `phone_number`, `value_date`, `statement_id`, and partial unique index on `transaction_url` (non-null) for filtering and deduplication
- Pagination (max 500 per page) to handle large datasets
- XHR upload with progress tracking
- Client-side sorting and filtering for responsive UX

## Troubleshooting

### "Invalid PDF" error
- Ensure PDF contains tabular data (not scanned image)
- PDF should have standard bank statement format

### "No transactions found"
- PDF may not have recognized table structure
- Check that required columns exist (date, description, amount)
- If lines use a payment code prefix other than `UD` (e.g. `UE15Q35HHC`), add it to **`TRANSACTION_DETAIL_CODE_PREFIXES`** in `backend/.env` (see **PDF Format Support** above)

### Phone filter shows no results
- Phone numbers must be exactly 10 digits starting with 0
- Check if transactional details column contains phone numbers in expected format

### Database connection error
- Verify Neon connection string in `.env`
- Check that DATABASE_URL is properly formatted: `postgresql://user:password@host/dbname`

## Next Steps / Future Enhancements

- [x] User authentication (Firebase Google Sign-In + Admin token verification on API)
- [ ] Transaction categorization (auto-categorize by merchant)
- [ ] CSV/Excel export
- [x] Duplicate detection across statements (`transaction_url` + upload skip + optional `scripts/dedupe_transaction_url.py`)
- [ ] Balance reconciliation
- [ ] Mobile app
- [ ] Advanced analytics and charting
- [ ] Scheduled PDF upload support
- [ ] Multi-user collaboration

## License

MIT

## Support

For issues or questions, please create an issue in the repository.
