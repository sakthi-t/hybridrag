"""
Configuration management for RAG Threads application.
Loads settings from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
    }
    
    # App settings
    APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://localhost:5000')
    MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', 100))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024  # Convert to bytes
    
    # Admin settings
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    
    # GitHub OAuth settings
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
    GITHUB_HOMEPAGE_URL = os.getenv('APP_BASE_URL', 'http://localhost:5000')
    GITHUB_CALLBACK_URL = f"{APP_BASE_URL}/auth/callback/github"
    
    # Chroma Cloud settings
    CHROMA_HOST = os.getenv('CHROMA_HOST', 'api.trychroma.com')
    CHROMA_API_KEY = os.getenv('CHROMA_API_KEY')
    CHROMA_TENANT = os.getenv('CHROMA_TENANT')
    CHROMA_DATABASE = os.getenv('CHROMA_DATABASE', 'raglocal')
    CHROMA_COLLECTION = 'raglocal_vectors'
    
    # Backblaze B2 settings
    B2_KEY_ID = os.getenv('backblazekeyid')
    B2_APPLICATION_KEY = os.getenv('backblazeapplicationkey')
    B2_BUCKET_NAME = os.getenv('backblazebucketname')
    B2_BUCKET_ID = os.getenv('backblazebucketid')
    B2_ENDPOINT = os.getenv('backblazebucketendpoint')
    B2_REGION = os.getenv('backblazeregion', 'us-east-005')
    
    # OpenAI settings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
    OPENAI_TEXT_EMBEDDING_MODEL = os.getenv('OPENAI_TEXT_EMBEDDING_MODEL', 'text-embedding-3-large')
    
    # Image embedding settings
    ENABLE_IMAGE_EMBEDDINGS = os.getenv('ENABLE_IMAGE_EMBEDDINGS', 'true').lower() == 'true'
    IMAGE_EMBEDDING_MODEL = os.getenv('IMAGE_EMBEDDING_MODEL', 'openai/clip-vit-base-patch32')
    
    # Chunking settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    
    # RAG settings
    TOP_K_CHUNKS = 5
    TOP_M_IMAGES = 3
    MAX_COMPLETION_TOKENS = 4000  # Increased for long responses
    ENABLE_STREAMING = True  # Enable streaming by default
    RAG_TEMPERATURE = 0.7


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
