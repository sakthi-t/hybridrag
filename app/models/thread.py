"""
Thread model for chat conversations.
"""
from app.extensions import db
from datetime import datetime
import uuid


class Thread(db.Model):
    """Thread model for chat conversations."""
    
    __tablename__ = 'threads'
    
    # Primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Ownership
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Associated document
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    
    # Thread metadata
    title = db.Column(db.String(255), nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete
    deleted_by_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', back_populates='threads', foreign_keys='Thread.user_id')
    document = db.relationship('Document', back_populates='threads', foreign_keys='Thread.document_id')
    messages = db.relationship('Message', back_populates='thread', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    def is_deleted(self):
        """Check if thread is soft-deleted."""
        return self.deleted_at is not None
    
    def can_be_accessed_by(self, user):
        """Check if user can access this thread."""
        if self.is_deleted():
            return False
        if user.is_admin():
            return True  # Admin can access all threads (configurable)
        return self.user_id == user.id
    
    def __repr__(self):
        return f'<Thread {self.title}>'
