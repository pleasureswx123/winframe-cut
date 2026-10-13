"""库存余料参与排料，但不得算作采购或被试算扣减。"""
import pytest
from backend.models import Stock, GlassStock, GlassSettings, CutSettings, TICKS as T
from backend.optimizer import solve_group, solve_large_group
from backend.glass_optimizer import optimize_glass_pieces
from tests.test_profile_improvements import parts


@pytest.mark.parametrize('solver',[solve_group,solve_large_group])
def test_profile_inventory_replaces_new_purchase(solver):
    stocks=[Stock(id='new',stock_key='p',length=6000*T,price_cents=1000),
            Stock(id='old',stock_key='p',length=1200*T,available=3,supply='inventory')]
    for objective in ['bars','cost']:
        r=solver('p',parts([1100]*4),stocks,CutSettings(kerf=0,objective=objective,time_limit=3))
        assert sum(b['supply']=='purchase' for b in r['bars']) == 1
        # 同样采购一根时，采购长度相同，不强迫浪费库存。
        assert sum(b['supply']=='inventory' for b in r['bars']) <= 3
    r=solver('p',parts([1100]*3),stocks,CutSettings(kerf=0,time_limit=3))
    assert len(r['bars']) == 3 and all(b['supply']=='inventory' for b in r['bars'])
    assert sum(b['price_cents'] for b in r['bars']) == 0


def test_glass_inventory_separated_from_purchase():
    pieces=[dict(id=str(i),instance=str(i),width=400*T,height=300*T,area=120000*T*T) for i in range(3)]
    cfg=GlassSettings(objective='cost',stocks=[GlassStock(id='new',width=1200*T,height=300*T,price_cents=1000),GlassStock(id='old',width=400*T,height=300*T,available=3,supply='inventory')])
    r=optimize_glass_pieces(pieces,cfg)
    assert r['purchase_count']==0 and r['inventory_count']==3
    assert r['cost_cents']==0 and r['purchase']==[]
    assert r['inventory_usage'][0]['count']==3
    assert cfg.stocks[1].available==3


@pytest.mark.parametrize('cls,dimensions',[(Stock,dict(stock_key='p',length=T)),(GlassStock,dict(width=T,height=T))])
def test_inventory_requires_finite_quantity(cls,dimensions):
    with pytest.raises(ValueError):cls(id='old',supply='inventory',**dimensions)


def test_project_overrides_persist_without_deducting_inventory(authenticated_client,saved_house):
    from tests.test_project_api import seed
    client=authenticated_client
    w=seed(client,saved_house)
    key=w['project']['profiles']['window_bead']['stock_key']
    base=client.get('/api/houses/'+saved_house['id']+'/cutting-sources').json()
    payload={k:saved_house[k] for k in ('customer_id','name','address','layout','notes','stocks','settings','glass_groups')}
    payload.update(custom_profiles=True,custom_glass=True,stocks=base['profiles']['data'],glass_groups=base['glass']['data'])
    payload['stocks'].append(dict(id='old-bead',stock_key=key,length=1200*T,available=3,supply='inventory'))
    cfg=payload['glass_groups']['透明玻璃']
    cfg['stocks'].append(dict(id='old-glass',width=1000*T,height=1000*T,available=2,supply='inventory'))
    assert client.put('/api/houses/'+saved_house['id'],json=payload).status_code==200
    for _ in range(2):
        for endpoint in ('optimize','optimize-glass'):
            response=client.post('/api/houses/'+saved_house['id']+'/'+endpoint)
            assert response.status_code==200,response.text
            r=response.json()
            assert r['inventory_count']>=1
            assert r['purchase_count']==sum(x['count'] for x in r['purchase'])
    after=client.get('/api/houses/'+saved_house['id']).json()
    assert after['custom_profiles'] and after['custom_glass']
    assert after['stocks'][-1]['available']==3
    assert after['glass_groups']['透明玻璃']['stocks'][-1]['available']==2
    assert client.get('/api/windows/'+w['id']).json()['stocks']==w['stocks']
    # 明确保存空配置必须生效，不能偷偷回退窗型中的采购料。
    payload['stocks']=[]
    assert client.put('/api/houses/'+saved_house['id'],json=payload).status_code==200
    assert client.post('/api/houses/'+saved_house['id']+'/optimize').status_code==422


def test_inventory_quantity_is_a_shared_upper_bound():
    pieces=[dict(id=str(i),instance=str(i),width=400*T,height=300*T,area=120000*T*T) for i in range(4)]
    cfg=GlassSettings(stocks=[GlassStock(id='new',width=400*T,height=300*T),GlassStock(id='old',width=400*T,height=300*T,available=3,supply='inventory')])
    r=optimize_glass_pieces(pieces,cfg)
    assert r['inventory_count']==3 and r['purchase_count']==1
    assert r['inventory_usage'][0]['remaining']==0
    assert r['primary_proven']
