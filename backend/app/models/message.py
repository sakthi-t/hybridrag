from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    thread = relationship("Thread", back_populates="messages", foreign_keys=[thread_id])
    evaluations = relationship("MessageEvaluation", back_populates="message", lazy="dynamic")

    def set_content(self, text, citations=None, images=None):
        self.content_json = {
            "text": text,
            "citations": citations or [],
            "images": images or [],
        }

    def get_text(self):
        return (self.content_json or {}).get("text", "")

    def get_citations(self):
        return (self.content_json or {}).get("citations", [])

    def get_images(self):
        return (self.content_json or {}).get("images", [])

    def is_deleted(self):
        return self.deleted_at is not None

    def __repr__(self):
        text = self.get_text()
        preview = text[:50] + "..." if len(text) > 50 else text
        return f"<Message {self.role}: {preview}>"
