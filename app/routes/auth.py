"""
Authentication routes for login, logout, registration, and OAuth.
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, current_app
from app.services.auth_service import auth_service, login_required
from app.models.user import User
from app.extensions import db
import re

bp = Blueprint('auth', __name__, url_prefix='/auth')


def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """
    Validate password strength.
    Requires at least 8 characters.
    """
    return len(password) >= 8


@bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user with email and password.
    
    Request JSON:
        {
            "email": "user@example.com",
            "password": "securepassword"
        }
    
    Returns:
        201: User created successfully
        400: Validation error
        409: User already exists
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    # Validate email
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate password
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    if not validate_password(password):
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email.lower()).first()
    if existing_user and not existing_user.is_deleted():
        return jsonify({'error': 'User with this email already exists'}), 409
    
    # Create user
    try:
        user = auth_service.create_user(email=email, password=password)
        
        # Auto-login the user
        auth_service.login_user(user)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500


@bp.route('/login', methods=['POST'])
def login():
    """
    Login with email and password.
    
    Request JSON:
        {
            "email": "user@example.com",
            "password": "password"
        }
    
    Returns:
        200: Login successful
        400: Validation error
        401: Invalid credentials
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Authenticate user
    user = auth_service.authenticate_user(email, password)
    
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Login user
    auth_service.login_user(user)
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role
        }
    }), 200


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Logout the current user.
    
    Returns:
        200: Logout successful
    """
    auth_service.logout_user()
    
    return jsonify({
        'message': 'Logout successful'
    }), 200


@bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """
    Get current user information.
    
    Returns:
        200: User information
        401: Not authenticated
    """
    user = auth_service.get_current_user()
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'created_at': user.created_at.isoformat()
        }
    }), 200


@bp.route('/github', methods=['GET'])
def github_login():
    """
    Initiate GitHub OAuth login.
    
    Returns:
        Redirect to GitHub authorization page
    """
    redirect_uri = current_app.config.get('GITHUB_CALLBACK_URL') or url_for('auth.github_callback', _external=True)
    return auth_service.github.authorize_redirect(redirect_uri)


@bp.route('/callback/github', methods=['GET'])
def github_callback():
    """
    GitHub OAuth callback handler.
    
    Returns:
        Redirect to home page or error page
    """
    try:
        # Get access token from GitHub
        token = auth_service.github.authorize_access_token()
        
        # Get user info from GitHub
        resp = auth_service.github.get('user', token=token)
        github_user = resp.json()
        
        # Get user's email if not in profile
        if not github_user.get('email'):
            emails_resp = auth_service.github.get('user/emails', token=token)
            emails = emails_resp.json()
            # Find primary email
            for email_obj in emails:
                if email_obj.get('primary'):
                    github_user['email'] = email_obj.get('email')
                    break
            # If no primary, use first email
            if not github_user.get('email') and emails:
                github_user['email'] = emails[0].get('email')
        
        # Find or create user
        user = auth_service.find_or_create_github_user(github_user)
        
        # Login user
        auth_service.login_user(user)
        
        # Redirect to chat or admin panel after login
        if user.is_admin():
            return redirect(url_for('views.admin'))
        return redirect(url_for('views.chat'))
        
    except Exception as e:
        current_app.logger.error(f"GitHub OAuth error: {str(e)}")
        return jsonify({'error': 'GitHub authentication failed', 'details': str(e)}), 500
