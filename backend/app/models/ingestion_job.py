from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="QUEUED", index=True)
    progress = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True)
    chunk_count = Column(Integer, nullable=True)
    chunks_rejected = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship("Document", back_populates="ingestion_jobs",
                            foreign_keys=[document_id])

    def is_queued(self):
        return self.status == "QUEUED"

    def is_running(self):
        return self.status == "RUNNING"

    def is_done(self):
        return self.status == "DONE"

    def is_failed(self):
        return self.status == "FAILED"

    def mark_running(self):
        self.status = "RUNNING"
        self.progress = 0
        self.updated_at = datetime.utcnow()

    def update_progress(self, progress):
        self.progress = max(0, min(100, progress))
        self.updated_at = datetime.utcnow()

    def mark_done(self):
        self.status = "DONE"
        self.progress = 100
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message):
        self.status = "FAILED"
        self.error = error_message
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return f"<IngestionJob {self.id} ({self.status} - {self.progress}%)>"
