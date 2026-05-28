"""
Message evaluation model for LLM-judge scores.
"""
from app.extensions import db
from datetime import datetime
import uuid


class MessageEvaluation(db.Model):
    """Stores evaluation metrics for assistant messages."""

    __tablename__ = 'message_evaluations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = db.Column(db.String(36), db.ForeignKey('messages.id'), nullable=False, index=True)

    faithfulness_score = db.Column(db.Float, nullable=False)
    citation_precision_score = db.Column(db.Float, nullable=False)
    groundedness_score = db.Column(db.Float, nullable=False)
    rationale_json = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    message = db.relationship('Message', back_populates='evaluations', foreign_keys='MessageEvaluation.message_id')

    def as_dict(self):
        return {
            'faithfulness_score': self.faithfulness_score,
            'citation_precision_score': self.citation_precision_score,
            'groundedness_score': self.groundedness_score,
            'rationale': self.rationale_json or {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
