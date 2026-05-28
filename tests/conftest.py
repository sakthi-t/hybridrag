import os
import pytest
from app import create_app
from app.extensions import db


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_EMAIL = "admin@example.com"
    MAX_UPLOAD_MB = 100
    APP_BASE_URL = None
    CHROMA_COLLECTION = "test_collection"


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
