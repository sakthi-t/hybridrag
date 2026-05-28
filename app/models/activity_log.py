"""
ActivityLog model for audit trail.
"""
from app.extensions import db
from datetime import datetime
import uuid


class ActivityLog(db.Model):
    """ActivityLog model for audit trail."""
    
    __tablename__ = 'activity_logs'
    
    # Primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Actor (user who performed the action)
    actor_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Action details
    action = db.Column(db.String(50), nullable=False, index=True)
    # Examples: 'login', 'logout', 'upload_document', 'delete_document', 
    #           'create_thread', 'delete_thread', 'delete_user', etc.
    
    # Target of the action
    target_type = db.Column(db.String(50), nullable=True)  # 'document', 'user', 'thread', etc.
    target_id = db.Column(db.String(36), nullable=True)
    
    # Additional metadata as JSON
    metadata_json = db.Column(db.JSON, nullable=True)
    # Example: {"document_title": "foo.pdf", "scope": "GLOBAL"}
    
    # Timestamp
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    actor = db.relationship('User', back_populates='activity_logs', foreign_keys='ActivityLog.actor_user_id')
    
    @staticmethod
    def log_action(user_id, action, target_type=None, target_id=None, metadata=None):
        """
        Create a new activity log entry.
        
        Args:
            user_id: ID of the user performing the action
            action: Action name (e.g., 'upload_document')
            target_type: Type of target (e.g., 'document')
            target_id: ID of the target
            metadata: Additional metadata as dict
        
        Returns:
            ActivityLog instance
        """
        log = ActivityLog(
            actor_user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata
        )
        db.session.add(log)
        return log
    
    def get_metadata(self, key, default=None):
        """Get a specific metadata value."""
        if not self.metadata_json:
            return default
        return self.metadata_json.get(key, default)
    
    def __repr__(self):
        return f'<ActivityLog {self.action} by {self.actor_user_id} at {self.created_at}>'
