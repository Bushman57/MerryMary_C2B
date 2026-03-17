# Changelog

## Version 1.0.0 (Initial Release)

### Backend
- ✅ Flask REST API with CORS support
- ✅ PostgreSQL / Neon database integration
- ✅ PDF upload endpoint with file validation
- ✅ PDF table extraction using pdfplumber
- ✅ Phone number extraction (regex pattern: 0\d{9})
- ✅ Transaction model with ORM relationships
- ✅ Filtering endpoints (by phone, statement, date)
- ✅ Pagination support (max 500 per page)
- ✅ Transaction statistics endpoints
- ✅ File cleanup after processing
- ✅ Comprehensive error handling

### Frontend
- ✅ Vue 3 SPA with Composition API
- ✅ Drag-and-drop file upload component
- ✅ Upload progress bar
- ✅ Responsive transaction table
- ✅ Phone number filtering dropdown
- ✅ Sorting by date, amount, description
- ✅ Real-time transaction statistics
- ✅ Pinia state management
- ✅ Axios HTTP client
- ✅ Modern CSS styling with gradients
- ✅ Mobile responsive design

### Features
- PDF upload and processing
- Transaction extraction from PDF tables
- Phone number extraction and filtering (10 digits starting with 0)
- Real-time data storage in Neon PostgreSQL
- Transaction statistics (total, debits, credits, unique phones)
- Pagination and sorting
- Error handling and user feedback

### Known Limitations
- Single-user (no auth)
- PDF format: machine-generated tables only (no OCR for scans)
- Phone filter: exact match only (no partial search)
- Temp files deleted after processing (no archive)
