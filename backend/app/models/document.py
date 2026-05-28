from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    scope = Column(String(20), nullable=False, default="USER_PRIVATE", index=True)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    b2_object_key = Column(String(500), nullable=False, unique=True)
    file_type = Column(String(20), nullable=False, default="pdf")
    upload_batch_id = Column(UUID(as_uuid=True), ForeignKey("upload_batches.id"), nullable=True)
    retrieval_type = Column(String(20), nullable=False, default="vector")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="documents", foreign_keys=[owner_user_id])
    threads = relationship("Thread", back_populates="document", lazy="dynamic",
                           foreign_keys="Thread.document_id")
    ingestion_jobs = relationship("IngestionJob", back_populates="document", lazy="dynamic",
                                  foreign_keys="IngestionJob.document_id")

    def is_deleted(self):
        return self.deleted_at is not None

    def can_be_viewed_by(self, user):
        if self.is_deleted():
            return False
        return str(self.owner_user_id) == str(user.id)

    def __repr__(self):
        return f"<Document {self.title} ({self.scope})>"
