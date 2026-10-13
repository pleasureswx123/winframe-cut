"""项目排料从已授权的存档读取全部窗型，按材料隔离。"""
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import create_user, Registration
from backend.sample import sample_project
from backend.models import TICKS


def seed(client, house, material='透明玻璃', quantity=1):
    p = sample_project().model_dump()
    p.update(name='卧室窗', width=500*TICKS, height=500*TICKS, quantity=quantity,
             root=dict(id='root', kind='glass', children=[]))
    response = client.post('/api/windows', json=dict(house_id=house['id'], glass_material=material,
                                                    floor='二楼', room='卧室', project=p, stocks=[dict(id=k, stock_key=k, length=6000*TICKS) for k in {v['stock_key'] for v in p['profiles'].values()}]))
    assert response.status_code == 201
    return response.json()


def configure(client, house):
    p = sample_project()
    fields = ('customer_id','name','address','layout','notes','stocks','settings','glass_groups')
    data = {k: house[k] for k in fields}
    data['stocks'] = [dict(id=k,stock_key=k,length=6000*TICKS) for k in {v.stock_key for v in p.profiles.values()}]
    data['glass_groups'] = {key:p.glass.model_dump() for key in ['透明玻璃','磨砂玻璃']}
    assert client.put('/api/houses/'+house['id'], json=data).status_code == 200


def test_project_uses_all_saved_windows_and_material_groups(authenticated_client, saved_house):
    client = authenticated_client
    a = seed(client, saved_house, quantity=2)
    b = seed(client, saved_house, '磨砂玻璃')
    configure(client, saved_house)
    response = client.post(f'/api/houses/{saved_house["id"]}/optimize')
    assert response.status_code == 200, response.text
    sources = [p['source'] for g in response.json()['groups'] for bar in g['bars'] for p in bar['pieces']]
    assert {s['window_id'] for s in sources} == {a['id'],b['id']}
    assert {s['unit'] for s in sources if s['window_id']==a['id']} == {1,2}
    response = client.post(f'/api/houses/{saved_house["id"]}/optimize-glass')
    assert response.status_code == 200, response.text
    result = response.json()
    assert {g['material'] for g in result['groups']} == {'透明玻璃','磨砂玻璃'}
    assert sum(len(s['pieces']) for s in result['sheets']) == 3
    assert len({s['id'] for s in result['sheets']}) == len(result['sheets'])


def test_project_rejects_empty_and_missing_material(authenticated_client, saved_house):
    client = authenticated_client
    for endpoint in ['optimize','optimize-glass']:
        assert client.post(f'/api/houses/{saved_house["id"]}/{endpoint}').status_code == 422
    window = seed(client, saved_house)
    payload = {k: window[k] for k in ('house_id', 'floor', 'room', 'glass_material', 'project', 'stocks', 'settings')}
    payload['project']['glass']['stocks'] = []
    assert client.put('/api/windows/' + window['id'], json=payload).status_code == 200
    result = client.post(f'/api/houses/{saved_house["id"]}/optimize-glass')
    assert result.status_code == 422 and '透明玻璃' in result.json()['detail']


def test_other_user_cannot_optimize_house(authenticated_client, saved_house):
    with TestClient(app) as other:
        credentials = dict(username='other-owner',password='Safe-pass-12345')
        create_user(Registration(**credentials))
        result=other.post('/api/auth/login',json=credentials).json()
        other.headers['X-CSRF-Token']=result['csrf_token']
        for endpoint in ['optimize','optimize-glass']:
            assert other.post(f'/api/houses/{saved_house["id"]}/{endpoint}').status_code == 404


def test_invalid_saved_window_blocks_entire_project(authenticated_client, saved_house):
    import json
    from backend.database import connect
    client = authenticated_client
    valid = seed(client, saved_house)
    invalid = seed(client, saved_house)
    configure(client, saved_house)
    with connect() as db:
        payload = json.loads(db.execute('SELECT payload FROM windows WHERE id=?', (invalid['id'],)).fetchone()[0])
        payload['width'] = 1
        db.execute('UPDATE windows SET payload=? WHERE id=?', (json.dumps(payload), invalid['id']))
        db.commit()
    for endpoint in ['optimize', 'optimize-glass']:
        response = client.post(f'/api/houses/{saved_house["id"]}/{endpoint}')
        assert response.status_code == 422
        assert '卧室窗' in response.json()['detail']
    assert client.get('/api/windows/' + valid['id']).status_code == 200
