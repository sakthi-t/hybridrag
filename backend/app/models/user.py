from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    clerk_user_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    role = Column(String(20), nullable=False, default="user")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    documents = relationship("Document", back_populates="owner", lazy="dynamic",
                             foreign_keys="Document.owner_user_id")
    threads = relationship("Thread", back_populates="user", lazy="dynamic",
                           foreign_keys="Thread.user_id")
    activity_logs = relationship("ActivityLog", back_populates="actor", lazy="dynamic",
                                 foreign_keys="ActivityLog.actor_user_id")

    def is_admin(self):
        return self.role == "admin"

    def is_deleted(self):
        return self.deleted_at is not None

    def __repr__(self):
        return f"<User {self.email}>"
