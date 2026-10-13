"""账号生命周期和权限边界通过真实 HTTP 请求验证。"""
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('WINFRAME_DB', str(tmp_path / 'auth.db'))
    with TestClient(app) as value:
        yield value


def register(client, username='owner-one'):
    result=client.post('/api/auth/login',json={'username':'admin','password':'admin123'})
    client.headers['X-CSRF-Token']=result.json()['csrf_token']
    return client.post('/api/admin/users', json={
        'username': username, 'password': 'Safe-pass-12345', 'display_name': '测试用户'})


def login(client, username='owner-one'):
    result = client.post('/api/auth/login', json={'username': username, 'password': 'Safe-pass-12345'})
    assert result.status_code == 200, result.text
    client.headers['X-CSRF-Token'] = result.json()['csrf_token']
    return result.json()


def test_registration_cannot_grant_admin(client):
    response = client.post('/api/auth/register', json={
        'username': 'intruder', 'password': 'Safe-pass-12345', 'role': 'admin'})
    assert response.status_code == 403
    assert register(client).status_code == 201
    result = login(client)
    assert result['user']['role'] == 'user'
    assert 'password' not in str(result)
    assert client.get('/api/auth/me').json()['user']['username'] == 'owner-one'
    assert client.get('/api/admin/users').status_code == 403


def test_logout_revokes_session(client):
    register(client)
    login(client)
    cookie = client.cookies.get('winframe_session')
    assert client.post('/api/auth/logout').status_code == 200
    client.cookies.set('winframe_session', cookie)
    assert client.get('/api/auth/me').status_code == 401


def test_csrf_rejects_missing_token(client):
    register(client)
    login(client)
    del client.headers['X-CSRF-Token']
    assert client.post('/api/auth/logout').status_code == 403
    assert client.get('/api/auth/me').status_code == 200


def test_disabled_user_session_is_rejected(client):
    from backend.database import connect
    register(client)
    user = login(client)['user']
    with connect() as db:
        db.execute('UPDATE users SET active=0 WHERE id=?', (user['id'],))
    assert client.get('/api/auth/me').status_code == 401


def test_expired_session_is_rejected(client):
    from backend.database import connect
    register(client)
    login(client)
    with connect() as db:
        db.execute('UPDATE sessions SET expires=?', (int(time.time()) - 1,))
    assert client.get('/api/auth/me').status_code == 401


def test_duplicate_username_is_normalized(client):
    assert register(client, 'Same-Name').status_code == 201
    assert register(client, 'same-name').status_code == 409
    assert login(client, 'SAME-NAME')['user']['username'] == 'same-name'


def test_concurrent_registration_has_one_winner(client):
    def attempt(_):
        with TestClient(app) as other:
            return register(other, 'concurrent').status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == [201, 409]


def test_login_throttles_failures(client):
    for _ in range(8):
        response = client.post('/api/auth/login', json={'username': 'missing', 'password': 'wrong-password'})
    assert response.status_code == 429


def test_external_origin_cannot_login(client):
    assert register(client).status_code == 201
    response = client.post('/api/auth/login', headers={'Origin': 'https://evil.example'}, json={
        'username': 'owner-one', 'password': 'Safe-pass-12345'})
    assert response.status_code == 403


def test_password_and_session_not_stored_in_plaintext(client):
    from backend.database import connect
    register(client)
    login(client)
    with connect() as db:
        password = db.execute('SELECT password_hash FROM users WHERE username="owner-one"').fetchone()[0]
        token = db.execute('SELECT token_hash FROM sessions').fetchone()[0]
    assert 'Safe-pass-12345' not in password
    assert token != client.cookies.get('winframe_session')
