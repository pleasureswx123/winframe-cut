"""大批量型材的多策略搜索与局部合并；只返回完整方案。"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from random import Random
from time import monotonic


def layout_score(bins, stocks, settings):
    count = sum(stocks[b['stock']].supply == 'purchase' for b in bins)
    cost = sum(stocks[b['stock']].purchase_price for b in bins)
    length = sum(stocks[b['stock']].length for b in bins if stocks[b['stock']].supply == 'purchase')
    short = sum(b['remaining'] for b in bins if b['remaining'] < settings.reusable_min)
    largest = max((b['remaining'] for b in bins), default=0)
    primary = (cost, count, length) if settings.objective == 'cost' else (count, length)
    return (*primary, len(bins), short, -largest)


def improve(bins, stocks, capacities, weights, settings, deadline):
    """释放低负载整料，再把剩余整料换成更合适的规格，库存始终共享。"""
    # 局部搜索有界，避免大项目的二次扫描耗尽全部求解时间。
    for donor in sorted(range(len(bins)), key=lambda i: capacities[bins[i]['stock']]-bins[i]['remaining'])[:80]:
        if monotonic() >= deadline:
            break
        if donor >= len(bins):
            continue
        trial = deepcopy(bins)
        source = trial.pop(donor)
        complete = True
        for wi, count in enumerate(source['counts']):
            for _ in range(count):
                choices = [(b['remaining']-weights[wi], i) for i, b in enumerate(trial) if b['remaining'] >= weights[wi]]
                if not choices or monotonic() >= deadline:
                    complete = False
                    break
                target = trial[min(choices)[1]]
                target['remaining'] -= weights[wi]
                target['counts'][wi] += 1
            if not complete:
                break
        if complete and layout_score(trial, stocks, settings) < layout_score(bins, stocks, settings):
            bins = trial
    # 在相同采购规格内交换构件，降低短废料并集中余料。
    checked = 0
    for i in range(len(bins)):
        if checked >= 80 or monotonic() >= deadline:
            break
        for j in range(i+1, len(bins)):
            if checked >= 80 or monotonic() >= deadline:
                break
            checked += 1
            a, b = bins[i], bins[j]
            original = layout_score(bins, stocks, settings)
            accepted = False
            for wi in [k for k, n in enumerate(a['counts']) if n][:24]:
                for wj in [k for k, n in enumerate(b['counts']) if n][:24]:
                    if monotonic() >= deadline:
                        return bins
                    delta = weights[wi]-weights[wj]
                    if not delta or a['remaining']+delta < 0 or b['remaining']-delta < 0:
                        continue
                    a['remaining'] += delta; b['remaining'] -= delta
                    if layout_score(bins, stocks, settings) < original:
                        a['counts'][wi] -= 1; a['counts'][wj] += 1
                        b['counts'][wj] -= 1; b['counts'][wi] += 1
                        accepted = True
                        break
                    a['remaining'] -= delta; b['remaining'] += delta
                if accepted:
                    break
    used = Counter(b['stock'] for b in bins)
    for b in bins:
        if monotonic() >= deadline:
            break
        old = b['stock']
        load = capacities[old]-b['remaining']
        choices = [j for j, s in enumerate(stocks) if capacities[j] >= load and
                   (s.available is None or used[j]-(j == old) < s.available)]
        def score(j):
            s = stocks[j]
            return (s.purchase_price, s.supply=='purchase', s.length) if settings.objective == 'cost' else (s.supply=='purchase', s.length)
        j = min(choices, key=score)
        if score(j) < score(old):
            used[old] -= 1
            used[j] += 1
            b['stock'], b['remaining'] = j, capacities[j]-load
    return bins


def search_layout(parts, stocks, settings, weights, deadline):
    trim = settings.trim_start+settings.trim_end
    capacities = [s.length-trim for s in stocks]
    index = {w: i for i, w in enumerate(weights)}
    descending = sorted((p['occupied'] for p in parts), reverse=True)
    orders = [descending, list(reversed(descending))]
    for seed in range(4):
        order = list(descending)
        Random(42+seed).shuffle(order)
        orders.append(order)
    best, best_score = None, None
    for order in orders:
        for policy in ([3,0,1,2,4,5] if any(s.supply=='inventory' for s in stocks) else range(3)):
            if monotonic() >= deadline:
                return best
            bins, used = [], Counter()
            for weight in order:
                if monotonic() >= deadline:
                    return best
                fits = [(b['remaining']-weight, i) for i, b in enumerate(bins) if b['remaining'] >= weight]
                if fits:
                    b = bins[min(fits)[1]]
                else:
                    possible = [j for j, s in enumerate(stocks) if capacities[j] >= weight and not (policy>=3 and s.supply=='inventory') and
                                (s.available is None or used[j] < s.available)]
                    if not possible:
                        break
                    def stock_score(j):
                        s, cap = stocks[j], capacities[j]
                        if settings.objective == 'cost':
                            return (s.supply=='purchase', (Fraction(s.purchase_price, cap) if policy % 3 == 0 else s.purchase_price if policy % 3 == 1
                                     else Fraction(s.purchase_price, max(1, cap//weight))), s.length)
                        return (s.supply=='purchase', (-cap if policy % 3 == 0 else cap if policy % 3 == 1 else cap % weight), s.purchase_price)
                    j = min(possible, key=stock_score)
                    b = dict(stock=j, remaining=capacities[j], counts=[0]*len(weights))
                    bins.append(b)
                    used[j] += 1
                b['remaining'] -= weight
                b['counts'][index[weight]] += 1
            else:
                # 先保留完整解；局部搜索或后续策略超时不能丢弃它。
                score = layout_score(bins, stocks, settings)
                if best_score is None or score < best_score:
                    best, best_score = deepcopy(bins), score
                local_deadline = min(deadline, monotonic()+max(0.01, (deadline-monotonic())/36))
                bins = improve(bins, stocks, capacities, weights, settings, local_deadline)
                score = layout_score(bins, stocks, settings)
                if score < best_score:
                    best, best_score = bins, score
    return best
