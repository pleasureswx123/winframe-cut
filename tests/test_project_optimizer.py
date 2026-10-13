"""跨窗型材排料必须共享原料并完整保留制作来源。"""
import pytest
from backend.models import Stock, CutSettings
from backend.geometry import GeometryError


def piece(window, number=1, length=4000):
    return dict(id='frame-1', instance=f'{window}:frame-1@{number}', label='外框', category='window_frame',
                category_label='窗户外框', stock_key='同型材', width=100, length=length, short_length=length,
                angle=90, source=dict(window_id=window, window_name=window, floor='二楼', room='卧室', unit=number, part_id='frame-1'))


def test_shared_bars_reduce_purchase():
    from backend.optimizer import optimize_parts
    stock = [Stock(id='raw', stock_key='同型材', length=10000)]
    settings = CutSettings(kerf=0)
    a, b = [piece('a')], [piece('b')]
    separate = optimize_parts(a, stock, settings)['bar_count'] + optimize_parts(b, stock, settings)['bar_count']
    result = optimize_parts(a + b, stock, settings)
    assert result['bar_count'] == 1 < separate
    pieces = result['groups'][0]['bars'][0]['pieces']
    assert {p['source']['window_id'] for p in pieces} == {'a', 'b'}
    assert len({p['instance'] for p in pieces}) == 2


def test_house_stock_is_consumed_once():
    from backend.optimizer import optimize_parts
    stock = [Stock(id='raw', stock_key='同型材', length=10000, available=1)]
    with pytest.raises(GeometryError):
        optimize_parts([piece('a', length=6000), piece('b', length=6000)], stock, CutSettings(kerf=0))


def test_large_project_is_complete_and_conserves_length():
    from backend.optimizer import optimize_parts
    parts = [piece('large', n, 4000) for n in range(501)]
    result = optimize_parts(parts, [Stock(id='raw', stock_key='同型材', length=10000)], CutSettings(kerf=0))
    bars = result['groups'][0]['bars']
    assert len(bars) == 251
    actual = [p for bar in bars for p in bar['pieces']]
    assert len(actual) == len({p['instance'] for p in actual}) == 501
    assert all(sum(p['length'] for p in b['pieces']) + b['loss'] + b['remnant'] == b['length'] for b in bars)
    # 重复长度较少的大项目也进入聚合精确求解。
    assert result['primary_proven'] is True


def test_same_material_with_different_width_is_rejected():
    from backend.optimizer import optimize_parts
    a, b = piece('a'), piece('b')
    b['width'] = 200
    with pytest.raises(GeometryError, match='宽'):
        optimize_parts([a, b], [Stock(id='raw', stock_key='同型材', length=10000)], CutSettings())


def test_large_project_timeout_rejects_partial_result(monkeypatch):
    import backend.optimizer as optimizer
    ticks = iter([0, 100])
    monkeypatch.setattr(optimizer, 'monotonic', lambda: next(ticks, 100))
    with pytest.raises(GeometryError, match='时'):
        optimizer.optimize_parts([piece('large', n) for n in range(501)],
            [Stock(id='raw', stock_key='同型材', length=10000)], CutSettings(time_limit=1))
