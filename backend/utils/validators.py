from werkzeug.utils import secure_filename
from pathlib import Path
import pdfplumber
from typing import Tuple

ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_pdf_file(filepath: str) -> Tuple[bool, str]:
    """
    Validate that PDF file is readable and contains extractable content
    
    Args:
        filepath: Path to PDF file
        
    Returns:
        Tuple (is_valid, message)
    """
    try:
        if not Path(filepath).exists():
            return False, "File not found"
        
        if Path(filepath).stat().st_size == 0:
            return False, "File is empty"
        
        with pdfplumber.open(filepath) as pdf:
            if len(pdf.pages) == 0:
                return False, "PDF has no pages"
            
            # Check first page has extractable content
            first_page = pdf.pages[0]
            text = first_page.extract_text()
            tables = first_page.extract_tables()
            
            if not text and not tables:
                return False, "Cannot extract content from PDF"
            
            return True, "Valid PDF"
    
    except pdfplumber.PDFFileError as e:
        return False, f"Invalid PDF format: {str(e)}"
    except Exception as e:
        return False, f"PDF validation error: {str(e)}"


def validate_file_upload(filename: str, file_size: int) -> Tuple[bool, str]:
    """
    Validate file before upload
    
    Args:
        filename: Original filename
        file_size: File size in bytes
        
    Returns:
        Tuple (is_valid, message)
    """
    # Check filename
    if not filename:
        return False, "No filename provided"
    
    # Check file extension
    if not allowed_file(filename):
        return False, "Only PDF files are allowed"
    
    # Check file size
    if file_size > MAX_FILE_SIZE:
        return False, f"File too large (max {MAX_FILE_SIZE // (1024*1024)}MB)"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, "Valid"


def secure_pdf_filename(original_filename: str, unique_prefix: str) -> str:
    """
    Create a secure filename for uploaded PDF
    
    Args:
        original_filename: Original filename from user
        unique_prefix: Prefix (usually timestamp) to ensure uniqueness
        
    Returns:
        Secured filename
    """
    filename = secure_filename(original_filename)
    if not filename:
        filename = "statement.pdf"
    
    return f"{unique_prefix}_{filename}"
