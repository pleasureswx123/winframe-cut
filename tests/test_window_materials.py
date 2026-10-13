"""验证窗型原料自动汇总和共享库存冲突，使用独立测试数据库。"""
import copy
import pytest
from backend.window_materials import window_materials, preview_materials
from backend.geometry import GeometryError
from backend.sample import sample_project
from backend.models import TICKS
from tests.test_project_api import seed


def window(id='a'):
    p = sample_project().model_dump()
    p['root'] = dict(id='root', kind='glass', children=[])
    p['glass']['stocks'][0]['available'] = 10
    return dict(id=id,name=id,floor='一层',room='卧室',glass_material='透明',project=p,
                stocks=[dict(id=id+'-stock',stock_key='窗户外框',length=6000*TICKS,price_cents=100,available=10)])


def test_duplicate_inventory_not_added():
    a, b = window(), window('b')
    stocks = window_materials([a,b], 'profiles')
    assert len(stocks) == 1 and stocks[0]['available'] == 10
    glass = window_materials([a,b], 'glass')['透明']['stocks']
    assert len(glass) == 1 and glass[0]['available'] == 10
    assert window_materials([b,a], 'profiles') == stocks


@pytest.mark.parametrize('field,value',[('available',11),('available',None),('price_cents',200)])
def test_conflicting_inventory_or_price_blocks(field,value):
    a, b = window(), window('b')
    b['stocks'][0][field] = value
    with pytest.raises(GeometryError,match='单价或共享库存不一致'):
        window_materials([a,b],'profiles')
    assert preview_materials([a,b])['glass']['error'] == ''


def test_other_lengths_and_glass_materials_stay_separate():
    a, b = window(), window('b')
    b['stocks'][0]['length'] = 5000*TICKS
    b['glass_material'] = '磨砂'
    assert len(window_materials([a,b],'profiles')) == 2
    assert set(window_materials([a,b],'glass')) == {'透明','磨砂'}


def test_glass_rule_conflict_but_deductions_can_differ():
    a, b = window(), window('b')
    b['project']['glass']['width_deduction'] += 2*TICKS
    assert len(window_materials([a,b],'glass')) == 1
    b['project']['glass']['allow_rotate'] = False
    with pytest.raises(GeometryError,match='旋转'):
        window_materials([a,b],'glass')


def test_project_uses_window_stocks_without_house_configuration(authenticated_client,saved_house):
    client=authenticated_client
    a=seed(client,saved_house,quantity=2)
    seed(client,saved_house)
    source=client.get('/api/houses/'+saved_house['id']+'/cutting-sources')
    assert source.status_code==200,source.text
    assert source.json()['profiles']['data']
    for endpoint in ['optimize','optimize-glass']:
        result=client.post('/api/houses/'+saved_house['id']+'/'+endpoint)
        assert result.status_code==200,result.text
    # 窗型原料发生修改后，下一次计算立即使用最新存档，不回退到项目配置。
    payload={k:a[k] for k in ('house_id','floor','room','glass_material','project','stocks','settings')}
    next(stock for stock in payload['stocks'] if stock['stock_key']==payload['project']['profiles']['window_frame']['stock_key'])['available']=1
    assert client.put('/api/windows/'+a['id'],json=payload).status_code==200
    result=client.post('/api/houses/'+saved_house['id']+'/optimize')
    assert result.status_code==422 and '共享库存' in result.json()['detail']
