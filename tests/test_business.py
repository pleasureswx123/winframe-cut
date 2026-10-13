"""用户隔离必须在所有业务层级和引用关系上成立。"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import create_user, Registration
from backend.sample import sample_project


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setenv('WINFRAME_DB', str(tmp_path / 'business.db'))
    values = []
    for name in ['owner-a', 'owner-b']:
        client = TestClient(app)
        create_user(Registration(username=name,password='Safe-pass-12345'))
        data = client.post('/api/auth/login', json={'username': name, 'password': 'Safe-pass-12345'}).json()
        client.headers['X-CSRF-Token'] = data['csrf_token']
        values.append(client)
    yield values
    for client in values:
        client.close()


def hierarchy(client):
    c = client.post('/api/customers', json={'name': 'A客户', 'phone': '13800000000'})
    assert c.status_code == 201, c.text
    customer = c.json()
    h = client.post('/api/houses', json={'name': '三层自建房', 'customer_id': customer['id']})
    assert h.status_code == 201, h.text
    house = h.json()
    payload = dict(house_id=house['id'], floor='二楼', room='卧室',
                   project=sample_project().model_dump(), stocks=[], settings={})
    w = client.post('/api/windows', json=payload)
    assert w.status_code == 201, w.text
    return customer, house, w.json(), payload


def test_cross_user_resources_are_inaccessible(clients):
    owner, other = clients
    customer, house, window, payload = hierarchy(owner)
    for kind, obj in [('customers', customer), ('houses', house), ('windows', window)]:
        assert other.get(f'/api/{kind}/{obj["id"]}').status_code == 404
        assert other.delete(f'/api/{kind}/{obj["id"]}').status_code == 404
        assert other.get(f'/api/{kind}').json()['total'] == 0
    assert other.put('/api/windows/' + window['id'], json=payload).status_code == 404
    assert other.post('/api/windows', json=payload).status_code == 404
    assert other.post('/api/houses', json={'name': '非法挂接', 'customer_id': customer['id']}).status_code == 404
    assert other.put('/api/customers/' + customer['id'], json={'name': '改名'}).status_code == 404
    assert other.put('/api/houses/' + house['id'], json={'name': '改名', 'customer_id': customer['id']}).status_code == 404


def test_crud_round_trip_and_nonempty_delete(clients):
    client, _ = clients
    customer, house, window, payload = hierarchy(client)
    assert client.delete('/api/customers/' + customer['id']).status_code == 409
    assert client.delete('/api/houses/' + house['id']).status_code == 409
    payload['project']['name'] = '主卧窗'
    payload['stocks'] = [dict(id='raw', stock_key='型材', length=12000000, available=2, price_cents=200)]
    assert client.put('/api/windows/' + window['id'], json=payload).status_code == 200
    restored = client.get('/api/windows/' + window['id']).json()
    assert restored['room'] == '卧室' and restored['floor'] == '二楼'
    assert restored['project']['name'] == '主卧窗'
    assert restored['stocks'][0]['available'] == 2
    assert client.get('/api/windows', params={'house_id': house['id'], 'q': '主卧'}).json()['total'] == 1
    assert client.get('/api/windows', params={'q': '不存在'}).json()['total'] == 0
    assert client.delete('/api/windows/' + window['id']).status_code == 200
    assert client.delete('/api/houses/' + house['id']).status_code == 200
    assert client.delete('/api/customers/' + customer['id']).status_code == 200


def test_anonymous_business_and_legacy_routes_are_protected(clients):
    with TestClient(app) as client:
        for path in ['/api/customers', '/api/houses', '/api/windows', '/api/projects', '/api/sample']:
            assert client.get(path).status_code == 401
        for path in ['/api/calculate', '/api/optimize-glass', '/api/projects']:
            assert client.post(path, json=sample_project().model_dump()).status_code == 401


def test_rejects_invalid_window_before_saving(clients):
    client, _ = clients
    _, _, _, payload = hierarchy(client)
    payload['project']['width'] = 1
    assert client.post('/api/windows', json=payload).status_code == 422
    assert client.get('/api/windows').json()['total'] == 1


def test_pagination_and_multiple_houses(clients):
    client, _ = clients
    customer = client.post('/api/customers', json={'name': '多房业主'}).json()
    for index in range(3):
        assert client.post('/api/houses', json={'customer_id': customer['id'], 'name': f'房屋{index}'}).status_code == 201
    result = client.get('/api/houses', params={'customer_id': customer['id'], 'page_size': 2, 'page': 2}).json()
    assert result['total'] == 3 and len(result['items']) == 1
