from collections import Counter
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import Project, Node, GlassStock, TICKS as T
from backend.geometry import calculate, GeometryError
from backend.sample import sample_project
from backend.glass_optimizer import optimize_glass


def single(w=400, h=300, quantity=1):
    p=sample_project()
    p.width=(w+90)*T;p.height=(h+90)*T;p.quantity=quantity
    p.root=Node(id='root')
    return p


def stock(w,h,id='原板',price=0,available=None):
    return GlassStock(id=id,width=w*T,height=h*T,price_cents=price,available=available)


def verify(plan,project):
    """重放每刀：必须切当前已有矩形，保证可加工、无重叠且面积守恒。"""
    instances=[]
    for sheet in plan['sheets']:
        leaves=[dict(x=0,y=0,w=sheet['width'],h=sheet['height'])]
        for cut in sheet['cuts']:
            assert cut['region'] in leaves
            leaves.remove(cut['region'])
            axis=cut['axis'];size='w' if axis=='x' else 'h'
            r=cut['region'];kept=cut['kept'];rest=cut['remainder'];loss=cut['kerf_rect']
            assert kept[size]+rest[size]+loss[size]==r[size]
            assert loss[size]==project.glass.kerf
            assert cut['at']==kept[axis]+kept[size]
            assert rest[axis]==cut['at']+project.glass.kerf
            leaves.append(kept)
            if rest['w']>0 and rest['h']>0:leaves.append(rest)
        for piece in sheet['pieces']:
            assert piece['rect'] in leaves
            leaves.remove(piece['rect'])
            instances.append(piece['instance'])
            expected=(piece['height'],piece['width']) if piece['rotated'] else (piece['width'],piece['height'])
            assert (piece['rect']['w'],piece['rect']['h'])==expected
        assert sorted(map(str,leaves))==sorted(map(str,sheet['remnants']))
        assert sheet['glass_area']+sheet['remnant_area']+sheet['loss_area']==sheet['width']*sheet['height']
    expected=[f"{g['id']}@{q+1}" for g in calculate(project)['glasses'] for q in range(project.quantity)]
    assert Counter(instances)==Counter(expected)


def test_glass_blender_dimensions_counts_and_overlap():
    g=calculate(sample_project())
    assert g['glass_count']==10
    assert Counter((x['width']//T,x['height']//T) for x in g['glasses'])==Counter({(432,470):4,(970,470):2,(970,894):1,(372,834):1,(372,252):1,(372,544):1})
    assert all(x['overlap']==dict(x=15*T,y=15*T) for x in g['glasses'])
    assert sum('bead' in x['category'] for x in g['parts'])==4*len(g['glasses'])


def test_custom_deduction_decimal_and_empty():
    p=single();p.glass.width_deduction=40002;p.glass.height_deduction=20000
    g=calculate(p)['glasses'][0]
    assert g['width']==410*T-2 and g['height']==320*T
    assert g['rect']['x']==30*T+20001
    p.root.kind='empty'
    assert calculate(p)['glass_count']==0 and optimize_glass(p)['sheet_count']==0


def test_invalid_glass_and_bead_coverage_block_cutting():
    p=single();p.glass.width_deduction=500*T
    with pytest.raises(GeometryError):calculate(p)
    p=single();p.glass.width_deduction=60*T
    assert calculate(p)['glass_warnings']
    with pytest.raises(GeometryError,match='覆盖'):optimize_glass(p)


@pytest.mark.parametrize('kerf,expected',[(0,1),(3,2)])
def test_zero_and_nonzero_kerf_changes_stock_count(kerf,expected):
    p=single(400,300,2);p.glass.allow_rotate=False;p.glass.kerf=kerf*T
    p.glass.stocks=[stock(800,300)]
    plan=optimize_glass(p)
    assert plan['sheet_count']==expected
    verify(plan,p)


def test_exact_fit_rotation_and_forbidden_rotation():
    p=single(400,300);p.glass.stocks=[stock(300,400)]
    plan=optimize_glass(p)
    assert plan['sheets'][0]['pieces'][0]['rotated']
    assert not plan['sheets'][0]['cuts']
    verify(plan,p)
    p.glass.allow_rotate=False
    with pytest.raises(GeometryError,match='无法放入'):optimize_glass(p)


def test_inventory_and_cost_objective():
    p=single(400,300,2)
    p.glass.stocks=[stock(800,300,'大板',1000),stock(400,300,'小板',100)]
    p.glass.objective='cost'
    plan=optimize_glass(p)
    assert plan['sheet_count']==2 and plan['cost_cents']==200
    assert not plan['primary_proven']
    verify(plan,p)
    p.glass.objective='sheets'
    assert optimize_glass(p)['sheet_count']==1
    p.glass.stocks=[stock(400,300,available=1)]
    with pytest.raises(GeometryError,match='完整'):optimize_glass(p)


@pytest.mark.parametrize('kerf',[0,1,3,2001])
def test_baseline_every_cut_and_batch_area_conservation(kerf):
    p=sample_project();p.quantity=2;p.glass.kerf=kerf
    plan=optimize_glass(p)
    verify(plan,p)
    assert len([x for s in plan['sheets'] for x in s['pieces']])==20


def test_legacy_json_defaults_api_and_glass_storage(authenticated_client,saved_house):
    client=authenticated_client
    data=single().model_dump();data.pop('glass')
    legacy=Project.model_validate(data)
    assert legacy.glass.width_deduction==30*T and legacy.glass.kerf==0
    r=client.post('/api/optimize-glass',json=data)
    assert r.status_code==200 and r.json()['sheet_count']==1
    data=single().model_dump();data['glass']['kerf']=6000;data['glass']['width_deduction']=50000
    id=client.post('/api/windows',json={'house_id':saved_house['id'],'project':data}).json()['id']
    assert client.get('/api/projects/'+id).json()['glass']==data['glass']
    data['glass']['kerf']=-1
    assert client.post('/api/optimize-glass',json=data).status_code==422


def test_no_stock_and_batch_limit():
    p=single();p.glass.stocks=[]
    with pytest.raises(GeometryError,match='原板'):optimize_glass(p)
    p=sample_project();p.quantity=21
    with pytest.raises(GeometryError,match='200'):optimize_glass(p)
