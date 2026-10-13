"""型材省料目标、共享库存与余料分级回归。"""
from collections import Counter
import pytest
from backend.models import Stock, CutSettings, TICKS as T
from backend.optimizer import solve_group, solve_large_group


def parts(lengths):
    return [dict(id=str(i), instance=f'{i}@1', label=str(i), category='window_bead',
                 length=n*T, short_length=n*T, angle=90, front_loss=0, back_loss=0, occupied=n*T)
            for i, n in enumerate(lengths)]


def verify(result, expected, stocks):
    bars = result['bars']
    assert Counter(p['instance'] for b in bars for p in b['pieces']) == Counter(p['instance'] for p in expected)
    counts = Counter(b['stock_id'] for b in bars)
    assert all(s.available is None or counts[s.id] <= s.available for s in stocks)
    for b in bars:
        assert sum(p['length'] for p in b['pieces']) + b['loss'] + b['remnant'] == b['length']
        assert b['reusable_remnant'] + b['scrap_remnant'] == b['remnant']


def test_recovery_threshold_and_concentrated_remnants():
    ps = parts([4000, 4000, 3000, 3000])
    stocks = [Stock(id='s', stock_key='p', length=10000*T)]
    cfg = CutSettings(kerf=0, reusable_min=5000*T, time_limit=3)
    r = solve_group('p', ps, stocks, cfg)
    assert sorted(b['remnant'] for b in r['bars']) == [0, 6000*T]
    assert r['status'] == 'OPTIMAL'
    verify(r, ps, stocks)


@pytest.mark.parametrize('solver', [solve_group, solve_large_group])
def test_large_batch_uses_shorter_stock_with_same_bar_count(solver):
    ps = parts([1000]*201)
    stocks = [Stock(id='long',stock_key='p',length=6500*T), Stock(id='short',stock_key='p',length=6000*T)]
    r = solver('p', ps, stocks, CutSettings(kerf=0,time_limit=3))
    assert len(r['bars']) == 34
    assert sum(b['length'] for b in r['bars']) == 204000*T
    verify(r, ps, stocks)


def test_large_search_alternative_order_recovers_finite_inventory():
    # 降序最佳适应会把 6+3、5+2+2 放入两根，最后一个 2 无处可放。
    ps = parts([6,5,3,2,2,2])
    stocks = [Stock(id='s',stock_key='p',length=10*T,available=2)]
    r = solve_large_group('p', ps, stocks, CutSettings(kerf=0,time_limit=3))
    assert len(r['bars']) == 2
    verify(r, ps, stocks)


def test_large_cost_compares_total_price_not_only_unit_price():
    ps = parts([4]*201)
    stocks = [Stock(id='long',stock_key='p',length=10*T,price_cents=100), Stock(id='short',stock_key='p',length=4*T,price_cents=45)]
    r = solve_large_group('p', ps, stocks, CutSettings(kerf=0,objective='cost',time_limit=3))
    assert sum(b['price_cents'] for b in r['bars']) == 201*45
    verify(r, ps, stocks)


def test_legacy_settings_recovery_default_and_validation():
    assert CutSettings().reusable_min == 500*T
    with pytest.raises(ValueError): CutSettings(reusable_min=-1)


def test_large_search_returns_complete_best_when_later_trial_times_out(monkeypatch):
    import backend.profile_search as search
    ticks = iter([0]*5 + [100]*100)
    monkeypatch.setattr(search, 'monotonic', lambda: next(ticks, 100))
    ps = parts([4,4])
    cfg = CutSettings(kerf=0)
    stocks = [Stock(id='s',stock_key='p',length=10*T)]
    result = search.search_layout(ps, stocks, cfg, [4*T], deadline=10)
    assert result is not None
    assert sum(sum(b['counts']) for b in result) == 2


def test_reusable_threshold_includes_exact_boundary():
    ps = parts([5500])
    stocks = [Stock(id='s',stock_key='p',length=6000*T)]
    r = solve_group('p', ps, stocks, CutSettings(kerf=0, reusable_min=500*T))
    assert r['bars'][0]['reusable_remnant'] == 500*T
    assert r['bars'][0]['scrap_remnant'] == 0


def test_recovery_targets_never_override_purchase_goal():
    ps = parts([5500])
    stocks = [Stock(id='short',stock_key='p',length=5600*T),Stock(id='long',stock_key='p',length=6500*T)]
    r = solve_group('p', ps, stocks, CutSettings(kerf=0,reusable_min=500*T))
    assert r['bars'][0]['stock_id'] == 'short'
    assert r['bars'][0]['scrap_remnant'] == 100*T


def test_local_exchange_reduces_short_scrap_without_more_stock():
    from time import monotonic
    from backend.profile_search import improve
    stocks = [Stock(id='s', stock_key='p', length=10*T)]
    bins = [dict(stock=0, remaining=2*T, counts=[2,0]), dict(stock=0, remaining=4*T, counts=[0,2])]
    result = improve(bins, stocks, [10*T], [4*T,3*T], CutSettings(kerf=0,reusable_min=3*T), monotonic()+1)
    assert sorted(b['remaining'] for b in result) == [3*T,3*T]
    assert [sum(b['counts'][i] for b in result) for i in range(2)] == [2,2]


def test_aggregate_solver_timeout_keeps_greedy_complete_plan(monkeypatch):
    import backend.optimizer as optimizer
    monkeypatch.setattr(optimizer.cp_model.CpSolver, 'solve', lambda *args, **kwargs: optimizer.cp_model.UNKNOWN)
    ps = parts([1000]*201)
    stocks = [Stock(id='s',stock_key='p',length=6000*T)]
    result = solve_group('p', ps, stocks, CutSettings(kerf=0,time_limit=3))
    assert len(result['bars']) == 34
    assert result['primary_proven'] is False
    verify(result, ps, stocks)


def test_project_persists_recovery_setting_and_returns_totals(authenticated_client, saved_house):
    from tests.test_project_api import seed
    client = authenticated_client
    seed(client, saved_house)
    payload = {k:saved_house[k] for k in ('customer_id','name','address','layout','notes','stocks','settings','glass_groups')}
    payload['settings']['reusable_min'] = 800*T
    response = client.put('/api/houses/'+saved_house['id'], json=payload)
    assert response.status_code == 200
    assert client.get('/api/houses/'+saved_house['id']).json()['settings']['reusable_min'] == 800*T
    response = client.post('/api/houses/'+saved_house['id']+'/optimize')
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['settings']['reusable_min'] == 800*T
    assert result['reusable_remnant'] + result['scrap_remnant'] == result['total_remnant']
    assert result['reusable_remnant'] == sum(b['reusable_remnant'] for g in result['groups'] for b in g['bars'])
