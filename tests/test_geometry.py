import json
import random
from collections import Counter
from pathlib import Path
import pytest
from pydantic import ValidationError
from backend.models import Project, Node, TICKS as T, CATEGORIES
from backend.sample import sample_project
from backend.geometry import calculate, GeometryError


def test_live_blender_baseline_every_polygon():
    """不仅比数量，还比对从实时 Blender 导出的全部构件顶点与材质。"""
    fixture=json.loads((Path(__file__).parent/'fixtures'/'blender-baseline.json').read_text(encoding='utf-8'))
    material_map=dict(zip(['窗户外框材质','窗户中挺材质','窗户压线材质','窗扇外框材质','窗扇中挺材质','窗扇压线材质'],CATEGORIES))
    expected=Counter((material_map[o['material']],tuple(sorted(tuple(v) for v in o['polygon']))) for o in fixture['objects'])
    g=calculate(sample_project())
    actual=Counter((o['category'],tuple(sorted(tuple(v) for v in o['polygon']))) for o in g['parts'])
    assert actual==expected
    assert g['count']==61 and g['total_length']==43870*T


def test_sample_lengths():
    g=calculate(sample_project())
    assert [(r['count'],r['total_length']//T) for r in g['summary']]==[(4,8000),(8,7728),(28,16704),(8,5544),(1,402),(12,5492)]
    bar=next(p for p in g['parts'] if p['id']=='sash-bar-M')
    assert bar['start']==[1538*T,854*T] and bar['end']==[1940*T,854*T]


def test_quantity_and_blank_window():
    p=sample_project();p.root=Node(id='root',kind='glass');p.quantity=3
    g=calculate(p)
    assert len(g['parts'])==8 and g['count']==24
    assert all(v['quantity']==3 for v in g['parts'])


def test_all_six_widths_independently_change_geometry():
    p=sample_project()
    for c,w in zip(CATEGORIES,[40,10,25,35,12,20]):p.profiles[c].width=w*T
    g=calculate(p)
    assert g['count']==61
    bar=next(p for p in g['parts'] if p['id']=='sash-bar-M')
    assert bar['length']==(1960-1509-70)*T
    beads=[p for p in g['parts'] if p['category']=='sash_bead']
    assert all(p['width']==20*T for p in beads)
    assert next(p for p in beads if p['id']=='sash-top-L')['length']==(848-574-40)*T


def test_empty_removes_only_beads():
    p=sample_project();p.root=Node(id='root',kind='empty')
    assert calculate(p)['count']==4


def test_decimal_widths_half_micron_boundaries_are_exact():
    p=sample_project();p.root=Node(id='root',kind='split',axis='x',position=1000*T,children=[Node(id='a'),Node(id='b')])
    p.profiles['window_mullion'].width=16002  # 8.001 mm
    g=calculate(p);a=next(r for r in g['regions'] if r['id']=='a');b=next(r for r in g['regions'] if r['id']=='b')
    assert a['rect']['x']+a['rect']['w']==1000*T-8001
    assert b['rect']['x']==1000*T+8001
    bead=next(p for p in g['parts'] if p['id']=='a-T')
    assert bead['center'][0]==(a['rect']['x']*2+a['rect']['w'])/2
    assert all(isinstance(c,int) for part in g['parts'] for point in part['polygon'] for c in point)


@pytest.mark.parametrize('width,height,frame,mullion,bead',[(1500,1800,40,12,20),(2700,2500,50,20,25),(2400,3000,18,6,12)])
def test_custom_dimensions_and_widths(width,height,frame,mullion,bead):
    p=sample_project();p.width=width*T;p.height=height*T
    p.profiles['window_frame'].width=frame*T;p.profiles['window_mullion'].width=mullion*T;p.profiles['window_bead'].width=bead*T
    p.root=Node(id='root',kind='split',axis='y',position=height*T//2,children=[Node(id='a'),Node(id='b')])
    g=calculate(p);bar=next(x for x in g['parts'] if x['category']=='window_mullion')
    assert bar['length']==(width-2*frame)*T
    assert len(g['parts'])==13
    assert sum(r['rect']['h'] for r in g['regions'] if r['id'] in ['a','b'])+(mullion+2*frame)*T==height*T


def test_random_split_conservation():
    rng=random.Random(36)
    for _ in range(100):
        p=sample_project();p.width=rng.randint(800,5000)*T;p.height=rng.randint(800,5000)*T
        p.profiles['window_frame'].width=rng.randint(10,70)*T
        p.profiles['window_mullion'].width=rng.randint(4,30)*T
        p.profiles['window_bead'].width=rng.randint(8,40)*T
        axis=rng.choice(['x','y']);extent=p.width if axis=='x' else p.height
        p.root=Node(id='root',kind='split',axis=axis,position=extent//2,children=[Node(id='a'),Node(id='b')])
        g=calculate(p);regions={r['id']:r['rect'] for r in g['regions']};a,b=regions['a'],regions['b']
        f=p.profiles['window_frame'].width;t=p.profiles['window_mullion'].width
        assert (a['w']+b['w'] if axis=='x' else a['h']+b['h'])+t+2*f==extent
        for part in g['parts']:
            assert part['length']>0 and part['short_length']>0
            assert all(0<=x<=p.width and 0<=y<=p.height for x,y in part['polygon'])


@pytest.mark.parametrize('position',[0,30*T,2000*T])
def test_reject_out_of_bounds(position):
    p=sample_project();p.root=Node(id='root',kind='split',axis='x',position=position,children=[Node(id='a'),Node(id='b')])
    with pytest.raises(GeometryError):calculate(p)


def test_reject_too_narrow_for_beads():
    p=sample_project();p.root=Node(id='root',kind='split',axis='x',position=70*T,children=[Node(id='a'),Node(id='b')])
    with pytest.raises(GeometryError):calculate(p)


def test_reject_nested_sash_duplicate_ids_and_hidden_nodes():
    p=sample_project();p.root=Node(id='r',kind='sash',children=[Node(id='s',kind='sash',children=[Node(id='g')])])
    with pytest.raises(GeometryError):calculate(p)
    p.root=Node(id='r',kind='split',axis='x',position=1000*T,children=[Node(id='g'),Node(id='g')])
    with pytest.raises(GeometryError):calculate(p)
    with pytest.raises(ValidationError):Node(id='root',kind='glass',children=[Node(id='extra')])


def test_validate_input_integer_precision_and_material_identity():
    data=sample_project().model_dump();data['width']=100.5
    with pytest.raises(ValidationError):Project.model_validate(data)
    data=sample_project().model_dump();data['profiles']['window_mullion']['stock_key']=data['profiles']['window_frame']['stock_key']
    with pytest.raises(ValidationError):Project.model_validate(data)


def test_reject_part_id_collision():
    p=sample_project();p.root=Node(id='W',kind='glass')
    with pytest.raises(GeometryError,match='冲突'):calculate(p)
