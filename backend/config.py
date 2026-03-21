import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    """Base configuration"""
    BASE_DIR = Path(__file__).parent
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', 10))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # Ensure uploads folder exists
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@localhost/transaction_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('FLASK_ENV') == 'development'
    
    # Connection pooling for Neon (handles connection timeouts)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 3600,  # Recycle connections every 1 hour
        'pool_pre_ping': True,  # Test connections before using
        'max_overflow': 10,
        'connect_args': {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
        }
    }
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JSON_SORT_KEYS = False

    # Firebase Admin (Google Sign-In ID token verification)
    # Set FIREBASE_CREDENTIALS_JSON to the full service account JSON as a single-line string (Render).
    # Or set GOOGLE_APPLICATION_CREDENTIALS to a path to the JSON file (local).
    # For local dev without Firebase, set FIREBASE_AUTH_DISABLED=true
    FIREBASE_CREDENTIALS_JSON = os.getenv('FIREBASE_CREDENTIALS_JSON')
    FIREBASE_AUTH_DISABLED = os.getenv('FIREBASE_AUTH_DISABLED', '').lower() in (
        '1',
        'true',
        'yes',
    )
    ALLOWED_EMAILS = [
        e.strip().lower()
        for e in os.getenv('ALLOWED_EMAILS', '').split(',')
        if e.strip()
    ]
    # Comma-separated Firebase Auth UIDs (from Firebase Console → Authentication → Users).
    # If non-empty, only these users may call protected APIs (takes precedence over ALLOWED_EMAILS).
    ALLOWED_FIREBASE_UIDS = [
        u.strip()
        for u in os.getenv('ALLOWED_FIREBASE_UIDS', '').split(',')
        if u.strip()
    ]


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
