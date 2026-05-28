"""
IngestionJob model for tracking PDF processing jobs.
"""
from app.extensions import db
from datetime import datetime
import uuid


class IngestionJob(db.Model):
    """IngestionJob model for tracking PDF processing jobs."""
    
    __tablename__ = 'ingestion_jobs'
    
    # Primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Associated document
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    
    # Job status
    status = db.Column(db.String(20), nullable=False, default='QUEUED', index=True)
    # Values: 'QUEUED', 'RUNNING', 'DONE', 'FAILED'
    
    # Progress tracking (0-100)
    progress = db.Column(db.Integer, nullable=False, default=0)
    
    # Error information (if failed)
    error = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = db.relationship('Document', back_populates='ingestion_jobs',
                             foreign_keys='IngestionJob.document_id')
    
    def is_queued(self):
        """Check if job is queued."""
        return self.status == 'QUEUED'
    
    def is_running(self):
        """Check if job is running."""
        return self.status == 'RUNNING'
    
    def is_done(self):
        """Check if job is completed."""
        return self.status == 'DONE'
    
    def is_failed(self):
        """Check if job has failed."""
        return self.status == 'FAILED'
    
    def mark_running(self):
        """Mark job as running."""
        self.status = 'RUNNING'
        self.progress = 0
        self.updated_at = datetime.utcnow()
    
    def update_progress(self, progress):
        """Update job progress (0-100)."""
        self.progress = max(0, min(100, progress))
        self.updated_at = datetime.utcnow()
    
    def mark_done(self):
        """Mark job as completed."""
        self.status = 'DONE'
        self.progress = 100
        self.updated_at = datetime.utcnow()
    
    def mark_failed(self, error_message):
        """Mark job as failed with error message."""
        self.status = 'FAILED'
        self.error = error_message
        self.updated_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<IngestionJob {self.id} ({self.status} - {self.progress}%)>'
