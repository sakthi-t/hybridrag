from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class MessageEvaluation(Base):
    __tablename__ = "message_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True)
    faithfulness_score = Column(Float, nullable=False)
    citation_precision_score = Column(Float, nullable=False)
    groundedness_score = Column(Float, nullable=False)
    rationale_json = Column(JSON, nullable=True)
    retrieval_type = Column(String(20), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    message = relationship("Message", back_populates="evaluations",
                           foreign_keys=[message_id])

    def as_dict(self):
        return {
            "faithfulness_score": self.faithfulness_score,
            "citation_precision_score": self.citation_precision_score,
            "groundedness_score": self.groundedness_score,
            "rationale": self.rationale_json or {},
            "retrieval_type": self.retrieval_type,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
