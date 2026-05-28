from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(36), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    actor = relationship("User", back_populates="activity_logs", foreign_keys=[actor_user_id])

    @staticmethod
    def log_action(db, user_id, action, target_type=None, target_id=None, metadata=None):
        log = ActivityLog(
            actor_user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata,
        )
        db.add(log)
        return log

    def get_metadata(self, key, default=None):
        if not self.metadata_json:
            return default
        return self.metadata_json.get(key, default)

    def __repr__(self):
        return f"<ActivityLog {self.action} by {self.actor_user_id} at {self.created_at}>"
