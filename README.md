# Transaction History Analyzer

A web application for uploading PDF bank statements, extracting transaction data, and filtering transactions by phone number.

## Features

✅ **PDF Upload** - Drag-and-drop PDF file upload with progress tracking  
✅ **Transaction Extraction** - Automatic table extraction using pdfplumber  
✅ **Phone Number Filtering** - Extract and filter transactions by phone number (10 digits starting with 0)  
✅ **Data Persistence** - Store transactions in Neon PostgreSQL  
✅ **Responsive UI** - Modern Vue 3 interface with real-time filtering  
✅ **Transaction Statistics** - Summary stats and analytics  

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
│   └── utils/                 # Utility functions
│       ├── pdf_parser.py      # PDF extraction with phone regex
│       └── validators.py      # File & PDF validators
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
│       │   └── index.js       # App store (transactions, filters)
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

6. **Start Flask server**
   ```bash
   python app.py
   ```
   Server runs on `http://localhost:5000`

### Frontend Setup

1. **Open new terminal and navigate to frontend**
   ```bash
   cd transaction_history/frontend
   ```

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
- `POST /api/upload` - Upload and process PDF statement

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

## Database Schema

### Transactions Table
```sql
CREATE TABLE transactions (
  id VARCHAR(36) PRIMARY KEY,
  date DATE NOT NULL,
  description VARCHAR(500) NOT NULL,
  amount FLOAT NOT NULL,
  type VARCHAR(10),  -- 'debit' or 'credit'
  balance FLOAT,
  reference VARCHAR(100),
  phone_number VARCHAR(20) INDEXED,  -- Extracted 10-digit number
  transactional_details TEXT,         -- Full row from PDF
  raw_data JSON,                      -- Original PDF row
  statement_id VARCHAR(100) INDEXED,  -- Source statement reference
  category VARCHAR(50),
  tags JSON,
  confidence FLOAT,
  manual_review BOOLEAN,
  extracted_at TIMESTAMP,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

## Performance Notes

- Indexes on `phone_number`, `date`, `statement_id` for fast filtering
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

### Phone filter shows no results
- Phone numbers must be exactly 10 digits starting with 0
- Check if transactional details column contains phone numbers in expected format

### Database connection error
- Verify Neon connection string in `.env`
- Check that DATABASE_URL is properly formatted: `postgresql://user:password@host/dbname`

## Next Steps / Future Enhancements

- [ ] User authentication and sessions
- [ ] Transaction categorization (auto-categorize by merchant)
- [ ] CSV/Excel export
- [ ] Duplicate detection across statements
- [ ] Balance reconciliation
- [ ] Mobile app
- [ ] Advanced analytics and charting
- [ ] Scheduled PDF upload support
- [ ] Multi-user collaboration

## License

MIT

## Support

For issues or questions, please create an issue in the repository.
