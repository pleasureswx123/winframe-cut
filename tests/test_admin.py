"""管理端跨用户只读、账号禁用和历史窗型归属。"""
import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import create_user, Registration
from backend.database import connect
from backend.sample import sample_project


@pytest.fixture
def admin(authenticated_client):
    create_user(Registration(username='administrator',password='Safe-pass-12345'),role='admin')
    with TestClient(app) as client:
        data=client.post('/api/auth/login',json=dict(username='administrator',password='Safe-pass-12345')).json()
        client.headers['X-CSRF-Token']=data['csrf_token']
        yield client


def test_admin_views_and_disables_user(admin,authenticated_client,saved_house):
    owner=authenticated_client.get('/api/auth/me').json()['user']
    summary=admin.get('/api/admin/summary')
    assert summary.status_code==200
    assert summary.json()['users']==3 and summary.json()['houses']==1
    for table in ['customers','houses']:
        assert admin.get(f'/api/admin/users/{owner["id"]}/{table}').json()['total']==1
    response=admin.patch('/api/admin/users/'+owner['id'],json={'active':False})
    assert response.status_code==200
    assert authenticated_client.get('/api/houses').status_code==401
    me=admin.get('/api/auth/me').json()['user']
    assert admin.patch('/api/admin/users/'+me['id'],json={'active':False}).status_code==409


def test_legacy_assignment_is_explicit_and_atomic(admin,authenticated_client,saved_house):
    with connect() as db:
        db.execute('INSERT INTO windows(id,name,payload,updated) VALUES (?,?,?,?)',
                   ('legacy','旧窗型',json.dumps(sample_project().model_dump()),'2026-10-12'))
    assert authenticated_client.get('/api/windows').json()['total']==0
    assert authenticated_client.get('/api/admin/legacy').status_code==403
    assert admin.get('/api/admin/legacy').json()['total']==1
    assert admin.post('/api/admin/legacy/legacy/assign',json={'house_id':'missing'}).status_code==404
    assert admin.post('/api/admin/legacy/legacy/assign',json={'house_id':saved_house['id']}).status_code==200
    assert admin.post('/api/admin/legacy/legacy/assign',json={'house_id':saved_house['id']}).status_code==409
    assert authenticated_client.get('/api/windows/legacy').json()['house_id']==saved_house['id']
    assert admin.get('/api/admin/legacy').json()['total']==0


def test_admin_window_details_and_user_denial(admin,authenticated_client,saved_house):
    payload=dict(house_id=saved_house['id'],project=sample_project().model_dump())
    window=authenticated_client.post('/api/windows',json=payload).json()
    result=admin.get('/api/admin/windows/'+window['id'])
    assert result.status_code==200 and result.json()['project']==payload['project']
    assert authenticated_client.get('/api/admin/windows/'+window['id']).status_code==403


def test_password_reset_revokes_sessions_and_keeps_hash(admin, authenticated_client):
    from backend.auth import verify_password
    owner = authenticated_client.get('/api/auth/me').json()['user']
    endpoint = f'/api/admin/users/{owner["id"]}/password'
    with TestClient(app) as second:
        second.post('/api/auth/login', json=dict(username='regression',password='Safe-pass-12345'))
        response = admin.post(endpoint, json={'password':'New-pass-12345'})
        assert response.status_code == 200
        assert response.json() == {'ok': True}
        assert second.get('/api/auth/me').status_code == 401
    assert authenticated_client.get('/api/auth/me').status_code == 401
    assert authenticated_client.post('/api/auth/login', json=dict(username='regression',password='Safe-pass-12345')).status_code == 401
    assert authenticated_client.post('/api/auth/login', json=dict(username='regression',password='New-pass-12345')).status_code == 200
    with connect() as db:
        row = db.execute('SELECT password_hash FROM users WHERE id=?', (owner['id'],)).fetchone()
        assert row['password_hash'] != 'New-pass-12345'
        assert verify_password('New-pass-12345', row['password_hash'])
    assert 'New-pass-12345' not in admin.get('/api/admin/users').text


def test_password_reset_permissions_and_validation(admin, authenticated_client):
    owner = authenticated_client.get('/api/auth/me').json()['user']
    endpoint = f'/api/admin/users/{owner["id"]}/password'
    payload = {'password':'New-pass-12345'}
    with TestClient(app) as anonymous:
        assert anonymous.post(endpoint, json=payload).status_code == 401
    assert authenticated_client.post(endpoint, json=payload).status_code == 403
    assert admin.post(endpoint, json={'password':'short'}).status_code == 422
    assert admin.post(endpoint, json={**payload,'role':'admin'}).status_code == 422
    csrf = admin.headers.pop('X-CSRF-Token')
    assert admin.post(endpoint, json=payload).status_code == 403
    admin.headers['X-CSRF-Token'] = csrf
    me = admin.get('/api/auth/me').json()['user']
    assert admin.post(f'/api/admin/users/{me["id"]}/password', json=payload).status_code == 409
    assert admin.post('/api/admin/users/missing/password', json=payload).status_code == 404
    assert authenticated_client.get('/api/auth/me').status_code == 200
    admin.patch('/api/admin/users/'+owner['id'],json={'active':False})
    assert admin.post(endpoint,json=payload).status_code == 200
    assert authenticated_client.post('/api/auth/login',json=dict(username='regression',password='New-pass-12345')).status_code == 401
