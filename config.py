import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'super-secret-key-change-in-production')
    
    # Database URI - defaults to local SQLite file if DATABASE_URL is not set
    # Example for MySQL: mysql+pymysql://user:password@host:port/dbname
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

