"""
Authentication service for password hashing, verification, and OAuth logic.
"""
from authlib.integrations.flask_client import OAuth
from flask import current_app, session
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.extensions import db
import bcrypt
import uuid
from functools import wraps
from flask import redirect, url_for, jsonify, request


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self):
        self.oauth = OAuth()
        self._github = None
    
    def init_app(self, app):
        """Initialize OAuth with Flask app."""
        self.oauth.init_app(app)
        self._github = self.oauth.register(
            name='github',
            client_id=app.config.get('GITHUB_CLIENT_ID'),
            client_secret=app.config.get('GITHUB_CLIENT_SECRET'),
            access_token_url='https://github.com/login/oauth/access_token',
            access_token_params=None,
            authorize_url='https://github.com/login/oauth/authorize',
            authorize_params=None,
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )
    
    @property
    def github(self):
        """Get GitHub OAuth client."""
        return self._github
    
    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify a password against its hash."""
        if not password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @staticmethod
    def create_user(email, password=None, github_id=None, role='user'):
        """
        Create a new user.
        
        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            github_id: GitHub user ID (for OAuth users)
            role: User role ('user' or 'admin')
        
        Returns:
            User instance
        """
        # Check if email matches admin email
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if admin_email and email.lower() == admin_email.lower():
            role = 'admin'
        
        user = User(
            id=str(uuid.uuid4()),
            email=email.lower(),
            github_id=github_id,
            role=role
        )
        
        if password:
            user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Log the registration
        ActivityLog.log_action(
            user_id=user.id,
            action='register',
            target_type='user',
            target_id=user.id,
            metadata={'email': email, 'registration_method': 'github' if github_id else 'email'}
        )
        db.session.commit()
        
        return user
    
    @staticmethod
    def authenticate_user(email, password):
        """
        Authenticate a user with email and password.
        
        Args:
            email: User's email
            password: Plain text password
        
        Returns:
            User instance if authentication successful, None otherwise
        """
        user = User.query.filter_by(email=email.lower()).first()
        
        if not user or user.is_deleted():
            return None
        
        if not user.check_password(password):
            return None
        
        return user
    
    @staticmethod
    def login_user(user):
        """
        Log in a user by setting session variables.
        
        Args:
            user: User instance
        """
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_role'] = user.role
        
        # Log the login
        ActivityLog.log_action(
            user_id=user.id,
            action='login',
            target_type='user',
            target_id=user.id,
            metadata={'email': user.email}
        )
        db.session.commit()
    
    @staticmethod
    def logout_user():
        """Log out the current user by clearing session."""
        user_id = session.get('user_id')
        
        if user_id:
            # Log the logout
            ActivityLog.log_action(
                user_id=user_id,
                action='logout',
                target_type='user',
                target_id=user_id
            )
            db.session.commit()
        
        session.clear()
    
    @staticmethod
    def get_current_user():
        """
        Get the currently logged-in user.
        
        Returns:
            User instance if logged in, None otherwise
        """
        user_id = session.get('user_id')
        if not user_id:
            return None
        
        user = User.query.get(user_id)
        if not user or user.is_deleted():
            session.clear()
            return None
        
        return user
    
    @staticmethod
    def is_authenticated():
        """Check if a user is currently authenticated."""
        return 'user_id' in session
    
    @staticmethod
    def find_or_create_github_user(github_user_data):
        """
        Find existing user by GitHub ID or email, or create new user.
        
        Args:
            github_user_data: Dictionary with GitHub user data
        
        Returns:
            User instance
        """
        github_id = str(github_user_data.get('id'))
        email = github_user_data.get('email')
        
        # Try to find by GitHub ID
        user = User.query.filter_by(github_id=github_id).first()
        if user:
            return user
        
        # Try to find by email
        if email:
            user = User.query.filter_by(email=email.lower()).first()
            if user:
                # Link GitHub account to existing user
                user.github_id = github_id
                db.session.commit()
                return user
        
        # Create new user
        if not email:
            # GitHub might not provide email if user hasn't made it public
            email = f"github_{github_id}@placeholder.local"
        
        return AuthService.create_user(
            email=email,
            github_id=github_id
        )


# Decorator for routes that require authentication
def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        
        if not AuthService.is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
        
        # Attach user to request object for easy access in routes
        request.user = AuthService.get_current_user()
        
        if not request.user:
            return jsonify({'error': 'Authentication required'}), 401
        
        return f(*args, **kwargs)
    return decorated_function


# Decorator for routes that require admin role
def admin_required(f):
    """Decorator to require admin role for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = AuthService.get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        if not user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def _get_request_user():
    """Return the current user from request or session."""
    user = getattr(request, 'user', None)
    if user:
        return user
    return AuthService.get_current_user()


def owns_document(allow_global=False):
    """
    Decorator to require ownership of a document or admin access.

    Args:
        allow_global: Allow access to GLOBAL documents for non-admins.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app.models.document import Document

            user = _get_request_user()
            if not user:
                return jsonify({'error': 'Authentication required'}), 401

            document_id = kwargs.get('document_id') or kwargs.get('doc_id')
            if not document_id:
                try:
                    payload = request.get_json(silent=True) or {}
                except Exception:
                    payload = {}
                document_id = payload.get('document_id')
            if not document_id:
                return jsonify({'error': 'document_id is required'}), 400

            document = Document.query.filter_by(id=document_id, deleted_at=None).first()
            if not document:
                return jsonify({'error': 'Document not found'}), 404

            if user.is_admin():
                request.document = document
                return f(*args, **kwargs)

            if document.scope == 'GLOBAL' and allow_global:
                request.document = document
                return f(*args, **kwargs)

            if document.scope == 'ADMIN_ONLY':
                return jsonify({'error': 'Access denied'}), 403

            if document.owner_user_id != user.id:
                return jsonify({'error': 'Access denied'}), 403

            request.document = document
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def owns_thread(f):
    """Decorator to require ownership of a thread or admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models.thread import Thread

        user = _get_request_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        thread_id = kwargs.get('thread_id')
        if not thread_id:
            return jsonify({'error': 'thread_id is required'}), 400

        thread = Thread.query.filter_by(id=thread_id, deleted_at=None).first()
        if not thread:
            return jsonify({'error': 'Thread not found'}), 404

        if thread.user_id != user.id and not user.is_admin():
            return jsonify({'error': 'Access denied'}), 403

        request.thread = thread
        return f(*args, **kwargs)
    return decorated_function


# Global auth service instance
auth_service = AuthService()
