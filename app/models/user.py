"""
User model for authentication and authorization.
"""
from app.extensions import db
from datetime import datetime
import uuid
import bcrypt


class User(db.Model):
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    # Primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Authentication fields
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth-only users
    github_id = db.Column(db.String(255), nullable=True, index=True, unique=True)
    
    # Authorization
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user' or 'admin'
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete
    
    # Relationships
    documents = db.relationship('Document', back_populates='owner', lazy='dynamic',
                               foreign_keys='Document.owner_user_id')
    threads = db.relationship('Thread', back_populates='user', lazy='dynamic',
                            foreign_keys='Thread.user_id')
    activity_logs = db.relationship('ActivityLog', back_populates='actor', lazy='dynamic',
                                   foreign_keys='ActivityLog.actor_user_id')
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Verify the user's password."""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'
    
    def is_deleted(self):
        """Check if user is soft-deleted."""
        return self.deleted_at is not None
    
    def __repr__(self):
        return f'<User {self.email}>'
