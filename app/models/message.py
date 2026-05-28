"""
Message model for chat messages.
"""
from app.extensions import db
from datetime import datetime
import uuid
import json


class Message(db.Model):
    """Message model for chat messages."""
    
    __tablename__ = 'messages'
    
    # Primary key
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Thread association
    thread_id = db.Column(db.String(36), db.ForeignKey('threads.id'), nullable=False, index=True)
    
    # Message metadata
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    
    # Content stored as JSON to support structured content (text, citations, images)
    content_json = db.Column(db.JSON, nullable=False)
    # Example structure:
    # {
    #   "text": "message content",
    #   "citations": [{"page": 1, "chunk_id": "abc", "text": "..."}],
    #   "images": ["b2://path/to/image.png"]
    # }
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete
    
    # Relationships
    thread = db.relationship('Thread', back_populates='messages', foreign_keys='Message.thread_id')
    evaluations = db.relationship('MessageEvaluation', back_populates='message', lazy='dynamic')
    
    def set_content(self, text, citations=None, images=None):
        """Set message content with optional citations and images."""
        self.content_json = {
            'text': text,
            'citations': citations or [],
            'images': images or []
        }
    
    def get_text(self):
        """Get the text content of the message."""
        return self.content_json.get('text', '') if self.content_json else ''
    
    def get_citations(self):
        """Get citations from the message."""
        return self.content_json.get('citations', []) if self.content_json else []
    
    def get_images(self):
        """Get image references from the message."""
        return self.content_json.get('images', []) if self.content_json else []
    
    def is_deleted(self):
        """Check if message is soft-deleted."""
        return self.deleted_at is not None
    
    def is_user_message(self):
        """Check if this is a user message."""
        return self.role == 'user'
    
    def is_assistant_message(self):
        """Check if this is an assistant message."""
        return self.role == 'assistant'
    
    def __repr__(self):
        text = self.get_text()
        preview = text[:50] + '...' if len(text) > 50 else text
        return f'<Message {self.role}: {preview}>'
