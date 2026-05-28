"""
Views - Server-rendered HTML page routes.
"""
from flask import Blueprint, render_template, redirect, url_for, session, current_app
from app.services.auth_service import auth_service

bp = Blueprint('views', __name__)


def get_current_user_for_template():
    """Get current user info for templates."""
    user = auth_service.get_current_user()
    if not user:
        return None
    
    admin_email = current_app.config.get('ADMIN_EMAIL')
    return {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'is_admin': user.email == admin_email
    }


@bp.route('/')
def index():
    """Redirect to chat if logged in, otherwise to login."""
    if 'user_id' in session:
        return redirect(url_for('views.chat'))
    return redirect(url_for('views.login'))


@bp.route('/login')
def login():
    """Login/signup page."""
    # Redirect to chat if already logged in
    if 'user_id' in session:
        return redirect(url_for('views.chat'))
    
    return render_template('auth/login.html')


@bp.route('/chat')
def chat():
    """Main chat interface."""
    # Require authentication
    if 'user_id' not in session:
        return redirect(url_for('views.login'))
    
    user = get_current_user_for_template()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    
    return render_template('chat/index.html', user=user)


@bp.route('/activity')
def activity():
    """User activity log and documents page (non-admin)."""
    if 'user_id' not in session:
        return redirect(url_for('views.login'))

    user = get_current_user_for_template()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))

    # Admins can also access, but this is intended for regular users
    return render_template('activity/index.html', user=user)


@bp.route('/admin')
def admin():
    """Admin panel (admin only)."""
    # Require authentication
    if 'user_id' not in session:
        return redirect(url_for('views.login'))
    
    user = get_current_user_for_template()
    if not user:
        session.clear()
        return redirect(url_for('views.login'))
    
    # Require admin
    if not user['is_admin']:
        return redirect(url_for('views.chat'))
    
    return render_template('admin/index.html', user=user)
