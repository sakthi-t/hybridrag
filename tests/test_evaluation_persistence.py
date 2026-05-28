from app.extensions import db
from app.models.message import Message
from app.models.message_evaluation import MessageEvaluation


def test_message_evaluation_persists(app):
    with app.app_context():
        message = Message(thread_id='thread-1', role='assistant')
        message.set_content('Answer')
        db.session.add(message)
        db.session.flush()

        evaluation = MessageEvaluation(
            message_id=message.id,
            faithfulness_score=0.9,
            citation_precision_score=0.8,
            groundedness_score=0.85,
            rationale_json={'notes': 'ok'}
        )
        db.session.add(evaluation)
        db.session.commit()

        loaded = MessageEvaluation.query.filter_by(message_id=message.id).first()
        assert loaded is not None
        assert loaded.faithfulness_score == 0.9
        assert loaded.citation_precision_score == 0.8
        assert loaded.groundedness_score == 0.85
