from app.models.user import User
from app.services.auth_service import auth_service
from app.extensions import db


def test_user_registration_and_login_flow(client):
    response = client.post(
        '/auth/register',
        json={'email': 'user@example.com', 'password': 'password123'}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['user']['email'] == 'user@example.com'

    response = client.post(
        '/auth/login',
        json={'email': 'user@example.com', 'password': 'password123'}
    )
    assert response.status_code == 200

    response = client.get('/auth/me')
    assert response.status_code == 200
    me = response.get_json()
    assert me['user']['email'] == 'user@example.com'


def test_invalid_login_rejected(client):
    response = client.post(
        '/auth/login',
        json={'email': 'missing@example.com', 'password': 'password123'}
    )
    assert response.status_code == 401


def test_admin_auto_assign(client, app):
    with app.app_context():
        user = auth_service.create_user('admin@example.com', password='password123')
        assert user.role == 'admin'
