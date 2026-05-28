"""
Extensions module for shared instances of Flask extensions.
This module initializes extension objects that are shared across the application.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Database extension
db = SQLAlchemy()

# Migration extension
migrate = Migrate()

# Note: Other extensions (Chroma client, B2 client, OpenAI client) 
# will be initialized in services rather than as global extensions
# to allow for better dependency injection and testing
