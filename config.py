import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class."""
    # IMPORTANT: SECRET_KEY must come from environment in production.
    # Fallback is empty to avoid accidentally using a known default in prod.
    SECRET_KEY = os.getenv('SECRET_KEY') or None
    
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
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'

