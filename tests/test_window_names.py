"""自动命名随存档持久化，自定义名称不随位置变化。"""
from backend.sample import sample_project


def test_auto_and_custom_window_names(authenticated_client,saved_house):
    client=authenticated_client
    project=sample_project().model_dump()
    project.update(name_mode='auto',name='旧名称')
    payload=dict(house_id=saved_house['id'],floor=' 一层 ',room=' 主卧东窗 ',project=project)
    result=client.post('/api/windows',json=payload)
    assert result.status_code==201,result.text
    window=result.json()
    assert window['name']==window['project']['name']=='一层·主卧东窗'
    payload['room']='客厅南窗'
    result=client.put('/api/windows/'+window['id'],json=payload)
    assert result.json()['name']=='一层·客厅南窗'
    payload['project'].update(name_mode='custom',name='W-001')
    result=client.put('/api/windows/'+window['id'],json=payload)
    assert result.json()['name']=='W-001'
    payload['room']='厨房'
    assert client.put('/api/windows/'+window['id'],json=payload).json()['name']=='W-001'
    assert client.get('/api/windows/'+window['id']).json()['project']['name_mode']=='custom'


def test_old_names_preserved_and_auto_length_bounded(authenticated_client,saved_house):
    project=sample_project().model_dump();project.pop('name_mode',None)
    result=authenticated_client.post('/api/windows',json=dict(house_id=saved_house['id'],floor='二层',room='卧室',project=project))
    assert result.status_code==201 and result.json()['name']==project['name']
    project.update(name_mode='auto',name='未命名窗型')
    result=authenticated_client.post('/api/windows',json=dict(house_id=saved_house['id'],floor='层'*60,room='窗'*100,project=project))
    assert result.status_code==201 and len(result.json()['name'])==100
