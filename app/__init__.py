"""
Flask application factory for RAG Threads application.
"""
from flask import Flask, request, redirect
from app.config import Config
from app.extensions import db, migrate


def create_app(config_class=Config):
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models (required for Alembic auto-detection)
    from app import models  # noqa: F401
    
    # Initialize OAuth
    from app.services.auth_service import auth_service
    auth_service.init_app(app)
    
    # Register blueprints
    from app.routes import auth, documents, threads, chat, admin, views
    
    # Views blueprint (HTML pages) - no prefix
    app.register_blueprint(views.bp)
    
    # API blueprints
    app.register_blueprint(auth.bp)
    app.register_blueprint(documents.documents_bp)
    app.register_blueprint(documents.uploads_bp)
    app.register_blueprint(threads.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(admin.bp)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404
    
    @app.errorhandler(403)
    def forbidden(error):
        return {"error": "Forbidden"}, 403
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Internal server error"}, 500

    @app.before_request
    def enforce_app_base_url():
        """Ensure OAuth callbacks use the configured base URL for consistent sessions."""
        base_url = app.config.get('APP_BASE_URL')
        if not base_url:
            return None
        # Respect reverse-proxy headers (Railway/Cloud) to avoid http/https redirect loops
        forwarded_proto = request.headers.get('X-Forwarded-Proto')
        scheme = forwarded_proto or request.scheme
        current_base = f"{scheme}://{request.host}".rstrip('/')
        if current_base != base_url.rstrip('/'):
            return redirect(base_url.rstrip('/') + request.full_path, code=302)
    
    # Start background ingestion worker
    from app.workers.ingestion_worker import start_ingestion_worker
    start_ingestion_worker(app)
    
    return app
