from fastapi.testclient import TestClient
from backend.main import app
from backend.sample import sample_project

client=TestClient(app)


def test_api_calculation_and_reject_invalid_tree():
    sample=client.get('/api/sample').json()
    r=client.post('/api/calculate',json=sample)
    assert r.status_code==200 and r.json()['count']==61
    sample['root']['position']=0
    r=client.post('/api/calculate',json=sample)
    assert r.status_code==422


def test_storage_round_trip_and_update(tmp_path,monkeypatch):
    monkeypatch.setenv('WINFRAME_DB',str(tmp_path/'projects.db'))
    data=sample_project().model_dump()
    r=client.post('/api/projects',json=data);assert r.status_code==200
    id=r.json()['id']
    assert client.get('/api/projects/'+id).json()==data
    data['name']='测试窗型'
    assert client.put('/api/projects/'+id,json=data).status_code==200
    assert client.get('/api/projects').json()[0]['name']=='测试窗型'
    assert client.get('/api/projects/nonexistent').status_code==404


def test_invalid_input_never_saved(tmp_path,monkeypatch):
    monkeypatch.setenv('WINFRAME_DB',str(tmp_path/'projects.db'))
    data=sample_project().model_dump();data['width']=1
    assert client.post('/api/projects',json=data).status_code==422
    assert client.get('/api/projects').json()==[]


def test_incomplete_stock_draft_can_restore_but_cannot_cut():
    p=sample_project().model_dump()
    payload=dict(project=p,stocks=[],settings=dict(objective='cost'))
    assert client.post('/api/validate',json=payload).status_code==200
    assert client.post('/api/optimize',json=payload).status_code==422
    payload['stocks']=[dict(id='draft',stock_key='窗户外框',length=12000000,price_cents=0)]
    restored=client.post('/api/validate',json=payload)
    assert restored.status_code==200
    assert restored.json()['stocks'][0]['id']=='draft'
    refused=client.post('/api/optimize',json=payload)
    assert refused.status_code==422 and '单价' in refused.json()['detail']
