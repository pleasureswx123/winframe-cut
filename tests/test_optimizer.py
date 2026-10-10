from collections import Counter
import pytest
from backend.models import Stock, CutSettings, OptimizeRequest, TICKS as T, CATEGORIES
from backend.sample import sample_project
from backend.geometry import calculate, GeometryError
from backend.optimizer import optimize, cut_allowance, solve_group


def part(id,mm,angle=90,kerf=0):
    f,b=cut_allowance(angle,kerf)
    return dict(id=id,instance=id+'@1',label=id,category='window_bead',length=mm*T,short_length=mm*T,angle=angle,front_loss=f,back_loss=b,occupied=mm*T+f+b)


def test_kerf_projection_rounds_up():
    assert cut_allowance(90,3*T)==(0,6000)
    assert cut_allowance(45,3*T)==(8486,8486)
    assert cut_allowance(45,0)==(0,0)


def test_sample_complete_coverage_and_stock_conservation():
    p=sample_project();p.quantity=2
    req=OptimizeRequest(project=p,stocks=[Stock(id=k,stock_key=p.profiles[k].stock_key,length=6000*T) for k in CATEGORIES],settings=CutSettings(time_limit=3))
    plan=optimize(req)
    expected={part['id']+'@'+str(i+1) for part in calculate(p)['parts'] for i in range(2)}
    actual=[]
    for group in plan['groups']:
        for b in group['bars']:
            actual.extend(x['instance'] for x in b['pieces'])
            assert sum(x['length'] for x in b['pieces'])+b['loss']+b['remnant']==b['length']
            assert b['remnant']>=0
            assert all(p.profiles[x['category']].stock_key==group['stock_key'] for x in b['pieces'])
            assert all(x['to_tick']<=y['from_tick'] for x,y in zip(b['pieces'],b['pieces'][1:]))
    assert len(actual)==122 and set(actual)==expected
    assert plan['total_stock']==plan['total_parts']+plan['total_loss']+plan['total_remnant']


def test_known_bin_packing_optimum():
    parts=[part(str(i),v) for i,v in enumerate([6,5,3,2,2,2])]
    result=solve_group('p',parts,[Stock(id='s',stock_key='p',length=10*T)],CutSettings(kerf=0,time_limit=3))
    assert len(result['bars'])==2 and result['primary_proven']


def test_cost_can_choose_more_short_bars():
    parts=[part(str(i),4) for i in range(4)]
    stocks=[Stock(id='long',stock_key='p',length=20*T,price_cents=1000),Stock(id='short',stock_key='p',length=8*T,price_cents=200)]
    result=solve_group('p',parts,stocks,CutSettings(kerf=0,objective='cost',time_limit=3))
    assert len(result['bars'])==2 and sum(b['price_cents'] for b in result['bars'])==400
    assert result['primary_proven']


def test_stock_limit_and_mixed_lengths():
    parts=[part(str(i),6) for i in range(3)]
    stocks=[Stock(id='a',stock_key='p',length=12*T,available=1),Stock(id='b',stock_key='p',length=6*T,available=1)]
    result=solve_group('p',parts,stocks,CutSettings(kerf=0,time_limit=3))
    assert Counter(b['stock_id'] for b in result['bars'])=={'a':1,'b':1}
    stocks[1].available=0
    with pytest.raises(GeometryError):solve_group('p',parts,stocks,CutSettings(kerf=0,time_limit=3))


def test_kerf_and_trim_prevent_overfilled_bar():
    parts=[part(str(i),500,kerf=3*T) for i in range(2)]
    result=solve_group('p',parts,[Stock(id='s',stock_key='p',length=1006*T)],CutSettings(kerf=3*T,trim_start=T,trim_end=T,time_limit=3))
    assert len(result['bars'])==2
    assert all(b['loss']==5*T for b in result['bars'])


def test_oversize_rejected_without_partial_plan():
    with pytest.raises(GeometryError):solve_group('p',[part('a',6000,45,3*T)],[Stock(id='s',stock_key='p',length=6000*T)],CutSettings())


def test_same_length_different_angles_keep_identity():
    parts=[part('square',100,90,3*T),part('mitre',100,45,3*T)]
    result=solve_group('p',parts,[Stock(id='s',stock_key='p',length=1000*T)],CutSettings(time_limit=3))
    ps=result['bars'][0]['pieces']
    assert {p['instance'] for p in ps}=={'square@1','mitre@1'}
    assert {p['angle']:p['front_loss']+p['back_loss'] for p in ps}=={90:6000,45:16972}


def test_saved_english_keys_do_not_silently_mix_chinese_stocks():
    p=sample_project()
    old=[Stock(id=k,stock_key=p.profiles[k].stock_key,length=6000*T) for k in CATEGORIES]
    for k in CATEGORIES:p.profiles[k].stock_key=k
    with pytest.raises(GeometryError,match='窗户外框.*window_frame.*型号必须完全一致'):
        optimize(OptimizeRequest(project=p,stocks=old))
    matched=old+[Stock(id='new-'+k,stock_key=k,length=6000*T) for k in CATEGORIES]
    plan=optimize(OptimizeRequest(project=p,stocks=matched))
    assert plan['bar_count']==10
    assert all(b['stock_id'].startswith('new-') for g in plan['groups'] for b in g['bars'])
    for stock in matched:
        if stock.stock_key=='window_frame':stock.available=0
    with pytest.raises(GeometryError,match='可用数量均为 0'):
        optimize(OptimizeRequest(project=p,stocks=matched))
