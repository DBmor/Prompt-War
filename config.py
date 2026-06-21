import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class."""
    # IMPORTANT: SECRET_KEY should be provided via env in production.
    # Use a local development fallback if none is set so session cookies work.
    SECRET_KEY = os.getenv('SECRET_KEY') or os.getenv('FLASK_SECRET_KEY') or 'dev-secret-key'
    
    # Database URI - defaults to local SQLite file if DATABASE_URL is not set
    # Example for MySQL: mysql+pymysql://user:password@host:port/dbname
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    # Secure session cookie settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes') or os.getenv('FLASK_ENV', '').lower() == 'production'
    SESSION_COOKIE_SAMESITE = 'Lax'

