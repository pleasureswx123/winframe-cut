"""API 回归使用临时账号和数据库，不触碰开发存档。"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import create_user, Registration


@pytest.fixture
def authenticated_client(tmp_path, monkeypatch):
    monkeypatch.setenv('WINFRAME_DB', str(tmp_path / 'regression.db'))
    with TestClient(app) as client:
        credentials = {'username': 'regression', 'password': 'Safe-pass-12345'}
        create_user(Registration(**credentials))
        response = client.post('/api/auth/login', json=credentials)
        client.headers['X-CSRF-Token'] = response.json()['csrf_token']
        yield client


@pytest.fixture
def saved_house(authenticated_client):
    customer = authenticated_client.post('/api/customers', json={'name': '回归客户'}).json()
    return authenticated_client.post('/api/houses', json={'name': '回归房屋', 'customer_id': customer['id']}).json()
