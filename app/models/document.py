"""
Document model for uploaded PDFs.
"""
from app.extensions import db
from datetime import datetime
import uuid


class Document(db.Model):
    """Document model for uploaded PDFs."""
    
    __tablename__ = 'documents'
    
    # Primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Ownership
    owner_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Scope/visibility
    scope = db.Column(db.String(20), nullable=False, default='USER_PRIVATE', index=True)
    # Values: 'GLOBAL', 'USER_PRIVATE', 'ADMIN_ONLY'
    
    # Document metadata
    title = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    size_bytes = db.Column(db.BigInteger, nullable=False)
    
    # Storage reference
    b2_object_key = db.Column(db.String(500), nullable=False, unique=True)
    # Format: users/<user_id>/documents/<doc_id>/<filename>
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete
    deleted_by_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    owner = db.relationship('User', back_populates='documents', foreign_keys='Document.owner_user_id')
    threads = db.relationship('Thread', back_populates='document', lazy='dynamic',
                             foreign_keys='Thread.document_id')
    ingestion_jobs = db.relationship('IngestionJob', back_populates='document', lazy='dynamic',
                                   foreign_keys='IngestionJob.document_id')
    
    def is_deleted(self):
        """Check if document is soft-deleted."""
        return self.deleted_at is not None
    
    def is_global(self):
        """Check if document is globally visible."""
        return self.scope == 'GLOBAL'
    
    def is_private(self):
        """Check if document is user-private."""
        return self.scope == 'USER_PRIVATE'
    
    def is_admin_only(self):
        """Check if document is admin-only."""
        return self.scope == 'ADMIN_ONLY'
    
    def can_be_viewed_by(self, user):
        """Check if user can view this document."""
        if self.is_deleted():
            return False
        if user.is_admin():
            return True
        if self.is_global():
            return True
        if self.is_private() and self.owner_user_id == user.id:
            return True
        return False
    
    def __repr__(self):
        return f'<Document {self.title} ({self.scope})>'
