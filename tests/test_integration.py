import json
from app.extensions import db
from app.models.document import Document
from app.models.ingestion_job import IngestionJob


def _register_and_login(client, email):
    client.post('/auth/register', json={'email': email, 'password': 'password123'})
    client.post('/auth/login', json={'email': email, 'password': 'password123'})


def test_document_access_rules(client, app):
    _register_and_login(client, 'user@example.com')

    with app.app_context():
        doc = Document(
            owner_user_id='owner-id',
            title='Admin Doc',
            original_filename='doc.pdf',
            size_bytes=10,
            b2_object_key='users/u/documents/d/doc.pdf',
            scope='ADMIN_ONLY'
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    response = client.get(f'/api/documents/{doc_id}')
    assert response.status_code == 403


def test_thread_access_rules(client, app):
    _register_and_login(client, 'user@example.com')

    with app.app_context():
        doc = Document(
            owner_user_id='owner-id',
            title='User Doc',
            original_filename='doc.pdf',
            size_bytes=10,
            b2_object_key='users/u/documents/d/doc.pdf',
            scope='USER_PRIVATE'
        )
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    response = client.post('/api/threads', json={'document_id': doc_id, 'title': 'My Thread'})
    assert response.status_code == 403


def test_confirm_upload_creates_job(client, app, monkeypatch):
    _register_and_login(client, 'user@example.com')

    monkeypatch.setattr(
        'app.services.storage_service.StorageService.object_exists',
        lambda *_args, **_kwargs: True
    )

    response = client.post(
        '/api/documents/confirm',
        json={'object_key': 'users/u/documents/d/doc.pdf', 'title': 'Doc', 'size_bytes': 100}
    )
    assert response.status_code == 201
    data = response.get_json()

    with app.app_context():
        job = IngestionJob.query.get(data['job_id'])
        assert job is not None
