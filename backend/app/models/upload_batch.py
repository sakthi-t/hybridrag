from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    total_files = Column(Integer, nullable=False)
    total_size_bytes = Column(BigInteger, nullable=False)
    status = Column(String(20), default="pending")
    recommended_retrieval_type = Column(String(20), nullable=True)
    user_confirmed_type = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
