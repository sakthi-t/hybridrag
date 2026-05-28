from app.models.user import User
from app.models.document import Document
from app.models.thread import Thread
from app.models.message import Message
from app.extensions import db


def test_user_document_thread_message_crud(app):
    with app.app_context():
        user = User(email='u1@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

        document = Document(
            owner_user_id=user.id,
            title='Doc',
            original_filename='doc.pdf',
            size_bytes=123,
            b2_object_key='users/u/documents/d/doc.pdf',
            scope='USER_PRIVATE'
        )
        db.session.add(document)
        db.session.flush()

        thread = Thread(
            user_id=user.id,
            document_id=document.id,
            title='Thread'
        )
        db.session.add(thread)
        db.session.flush()

        message = Message(thread_id=thread.id, role='user')
        message.set_content('Hello')
        db.session.add(message)
        db.session.commit()

        loaded_user = User.query.get(user.id)
        loaded_doc = Document.query.get(document.id)
        loaded_thread = Thread.query.get(thread.id)
        loaded_message = Message.query.get(message.id)

        assert loaded_user.email == 'u1@example.com'
        assert loaded_doc.title == 'Doc'
        assert loaded_thread.title == 'Thread'
        assert loaded_message.get_text() == 'Hello'
