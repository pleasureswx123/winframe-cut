"""玻璃跨窗共享原板、材料隔离和大项目完整性。"""
from copy import deepcopy
from backend.glass_optimizer import optimize_glass_pieces
from backend.models import TICKS as T
import pytest
from backend.models import GlassSettings, GlassStock
from backend.geometry import GeometryError


def glass(window, number=1):
    return dict(id='glass-1', instance=f'{window}:glass-1@{number}', width=4000, height=4000, area=16000000,
                source=dict(window_id=window, window_name=window, floor='一楼', room='客厅', unit=number, part_id='glass-1'))


def cfg(available=None):
    return GlassSettings(stocks=[GlassStock(id='board', width=10000, height=5000, available=available)])


def test_glass_shared_board_and_unique_sources():
    from backend.glass_optimizer import optimize_glass_pieces
    result = optimize_glass_pieces([glass('a'), glass('b')], cfg())
    assert result['sheet_count'] == 1
    assert {p['source']['window_id'] for p in result['sheets'][0]['pieces']} == {'a', 'b'}
    assert all('source' in c for c in result['sheets'][0]['cuts'])


def test_glass_limited_stock_shared_once():
    from backend.glass_optimizer import optimize_glass_pieces
    with pytest.raises(GeometryError):
        optimize_glass_pieces([glass('a', n) for n in range(3)], cfg(1))


def test_large_glass_project_is_complete():
    from backend.glass_optimizer import optimize_glass_pieces
    result = optimize_glass_pieces([glass('a', n) for n in range(201)], cfg())
    pieces = [p for sheet in result['sheets'] for p in sheet['pieces']]
    assert len(pieces) == len({p['instance'] for p in pieces}) == 201
    assert result['sheet_count'] == 101
    assert result['total_glass_area'] + result['loss_area'] + result['remnant_area'] == result['total_stock_area']


@pytest.mark.parametrize('kerf', [0, 3 * T])
def test_project_layout_preserves_large_reusable_remnant(kerf):
    """同样两张原板时，避免先找到的分散布局抢占更完整的余料方案。"""
    dimensions = [(432, 470), (970, 470), (432, 470), (372, 834), (970, 894),
                  (372, 252), (372, 544), (432, 470), (970, 470), (432, 470),
                  (556, 910), (1316, 265), (1316, 607)]
    pieces = [dict(id=f'g{i}', instance=f'w:g{i}@1', width=w*T, height=h*T, area=w*h*T*T,
                   source=dict(window_id='w', part_id=f'g{i}', unit=1))
              for i, (w, h) in enumerate(dimensions)]
    settings = GlassSettings(kerf=kerf, stocks=[GlassStock(id='board', width=2440*T, height=1830*T, available=2)])
    original = deepcopy(pieces)
    result = optimize_glass_pieces(pieces, settings)
    assert pieces == original
    assert result['sheet_count'] == result['lower_bound'] == 2
    assert result['primary_proven']
    largest = max(r['w']*r['h'] for s in result['sheets'] for r in s['remnants'])
    if kerf == 0:
        assert largest >= 3_400_000*T*T
    found = []
    for sheet in result['sheets']:
        leaves = [dict(x=0, y=0, w=sheet['width'], h=sheet['height'])]
        for cut in sheet['cuts']:
            assert cut['region'] in leaves
            leaves.remove(cut['region'])
            size = 'w' if cut['axis'] == 'x' else 'h'
            assert cut['kerf_rect'][size] == kerf
            assert cut['kept'][size] + kerf + cut['remainder'][size] == cut['region'][size]
            leaves.append(cut['kept'])
            if cut['remainder']['w'] > 0 and cut['remainder']['h'] > 0:
                leaves.append(cut['remainder'])
        for p in sheet['pieces']:
            leaves.remove(p['rect'])
            assert p['source']['part_id'] == p['part_id']
            found.append(p['instance'])
        assert sorted(map(str, leaves)) == sorted(map(str, sheet['remnants']))
        assert sheet['glass_area'] + sheet['loss_area'] + sheet['remnant_area'] == sheet['width']*sheet['height']
    assert sorted(found) == sorted(p['instance'] for p in pieces)
