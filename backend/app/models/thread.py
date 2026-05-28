from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Thread(Base):
    __tablename__ = "threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="threads", foreign_keys=[user_id])
    document = relationship("Document", back_populates="threads", foreign_keys=[document_id])
    messages = relationship("Message", back_populates="thread", lazy="dynamic",
                            cascade="all, delete-orphan")

    def is_deleted(self):
        return self.deleted_at is not None

    def can_be_accessed_by(self, user):
        if self.is_deleted():
            return False
        return str(self.user_id) == str(user.id)

    def __repr__(self):
        return f"<Thread {self.title}>"
