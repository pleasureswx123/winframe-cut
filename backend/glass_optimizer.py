"""矩形玻璃贯通直切排版：整数坐标、独立刀缝、可追溯的逐刀切割顺序。"""
from copy import deepcopy
from fractions import Fraction
from time import monotonic
from .geometry import calculate, GeometryError


def split_space(rect, width, height, kerf, vertical_first):
    """先切一条料，再切出玻璃；每刀贯通当前余料，不允许内部挖切。"""
    current = dict(rect)
    cuts, remains = [], []
    for axis, extent in ([('x', width), ('y', height)] if vertical_first else [('y', height), ('x', width)]):
        size = 'w' if axis == 'x' else 'h'
        delta = current[size] - extent
        if delta == 0:
            continue
        if delta < kerf:
            return None
        before = dict(current)
        waste = dict(current)
        waste[axis] += extent
        waste[size] = kerf
        rest = dict(current)
        rest[axis] += extent + kerf
        rest[size] = delta - kerf
        current[size] = extent
        cuts.append(dict(axis=axis, at=before[axis]+extent, region=before,
                         kerf_rect=waste, kept=dict(current), remainder=rest))
        if rest[size] > 0:
            remains.append(rest)
    return current, remains, cuts


def optimize_glass(project):
    geometry = calculate(project)
    if geometry['glass_warnings']:
        raise GeometryError('；'.join(geometry['glass_warnings']))
    cfg = project.glass
    pieces = [dict(g, instance=f"{g['id']}@{q+1}") for g in geometry['glasses'] for q in range(g['quantity'])]
    if len(pieces) > 200:
        raise GeometryError('单次玻璃排版最多支持 200 块，请使用项目统一排料')
    return optimize_glass_pieces(pieces,cfg)


def optimize_glass_pieces(pieces,cfg):
    deadline=monotonic()+30
    if len({p['instance'] for p in pieces})!=len(pieces):
        raise GeometryError('玻璃来源编号重复')
    if not pieces:
        return dict(status='EMPTY', primary_proven=True, sheet_count=0, purchase_count=0, inventory_count=0, inventory_usage=[], cost_cents=0,
                    total_stock_area=0, total_glass_area=0, loss_area=0, remnant_area=0, sheets=[], purchase=[], lower_bound=0)
    if len(pieces) > 2000:
        raise GeometryError('整项目单次最多排版 2000 块玻璃，请减少项目制作数量')
    stocks = [s for s in cfg.stocks if s.available != 0]
    if not stocks:
        raise GeometryError('请填写可用的玻璃原板规格')
    if cfg.objective == 'cost' and any(s.supply == 'purchase' and s.price_cents <= 0 for s in stocks):
        raise GeometryError('按金额排玻璃时，所有可用原板必须填写大于零的单价')

    def options(piece, rect, direction):
        orientations = [(piece['width'], piece['height'], False)]
        if cfg.allow_rotate and piece['width'] != piece['height']:
            orientations.append((piece['height'], piece['width'], True))
        for w, h, rotated in orientations:
            if w <= rect['w'] and h <= rect['h']:
                result = split_space(rect, w, h, cfg.kerf, direction)
                if result is not None:
                    yield w, h, rotated, result

    for piece in pieces:
        if not any(list(options(piece, dict(x=0, y=0, w=s.width, h=s.height), True)) for s in stocks):
            raise GeometryError(f"玻璃 {piece['instance']} 无法放入任何可用原板（请核对尺寸、旋转及刀缝）")

    # 多种排序、贯通方向及余料选择组合寻找更省板的可行方案，不冒充全局最优。
    orders = [lambda p: p['area'], lambda p: max(p['width'], p['height']),
              lambda p: p['width'], lambda p: p['height']]
    best, best_score = None, None
    for order in orders:
        ordered = sorted(pieces, key=lambda p: (order(p), p['area'], p['instance']), reverse=True)
        for direction in [True, False]:
            for policy in range(6 if any(s.supply == 'inventory' for s in stocks) else 3):
                if monotonic()>deadline and best is not None:
                    continue
                sheets, used = [], {}
                for piece in ordered:
                    if monotonic()>deadline:
                        break
                    candidates = []
                    for si, sheet in enumerate(sheets):
                        for ri, rect in enumerate(sheet['remnants']):
                            for w, h, rotated, result in options(piece, rect, direction):
                                score = (rect['w']*rect['h']-w*h, min(rect['w']-w, rect['h']-h)) if policy % 3 != 1 else (min(rect['w']-w, rect['h']-h), rect['w']*rect['h']-w*h)
                                candidates.append((score, si, ri, w, h, rotated, result))
                    if candidates:
                        _, si, ri, w, h, rotated, result = min(candidates, key=lambda c: c[0])
                        sheet = sheets[si]
                        sheet['remnants'].pop(ri)
                    else:
                        choices = []
                        for stock in stocks:
                            if policy >= 3 and stock.supply == 'inventory':continue
                            if stock.available is not None and used.get(stock.id, 0) >= stock.available:
                                continue
                            rect = dict(x=0, y=0, w=stock.width, h=stock.height)
                            for w, h, rotated, result in options(piece, rect, direction):
                                area = stock.width*stock.height
                                capacity = max((stock.width+cfg.kerf)//(w+cfg.kerf) * ((stock.height+cfg.kerf)//(h+cfg.kerf)), 1)
                                if cfg.objective == 'cost':
                                    score = ((stock.purchase_price if policy % 3 == 0 else Fraction(stock.purchase_price, capacity) if policy % 3 == 1 else Fraction(stock.purchase_price, area)), area)
                                else:
                                    score = ((area if policy == 0 else -capacity if policy == 1 else -area), stock.purchase_price)
                                score = (stock.supply == 'purchase', *score)
                                choices.append((score, stock, w, h, rotated, result))
                        if not choices:
                            break
                        _, stock, w, h, rotated, result = min(choices, key=lambda c: c[0])
                        used[stock.id] = used.get(stock.id, 0)+1
                        sheet = dict(id=f'G{len(sheets)+1}', stock_id=stock.id, width=stock.width, height=stock.height,
                                     price_cents=stock.purchase_price, supply=stock.supply, pieces=[], cuts=[], remnants=[])
                        sheets.append(sheet)
                    placed, remains, cuts = result
                    sheet['pieces'].append(dict(instance=piece['instance'], part_id=piece['id'],
                        width=piece['width'], height=piece['height'], rotated=rotated, rect=placed))
                    if 'source' in piece:sheet['pieces'][-1]['source']=piece['source']
                    sheet['remnants'].extend(remains)
                    for cut in cuts:
                        sheet['cuts'].append(dict(cut, index=len(sheet['cuts'])+1, instance=piece['instance']))
                        if 'source' in piece:sheet['cuts'][-1]['source']=piece['source']
                else:
                    price = sum(s['price_cents'] for s in sheets)
                    area = sum(s['width']*s['height'] for s in sheets)
                    bought=[s for s in sheets if s['supply']=='purchase']
                    purchased_area=sum(s['width']*s['height'] for s in bought)
                    score = (price, len(bought), purchased_area, len(sheets)) if cfg.objective == 'cost' else (len(bought), purchased_area, price, len(sheets))
                    # 张数、采购面积和费用相同时，优先保留完整的大块余料。
                    remnants = sorted((r['w']*r['h'] for sheet in sheets for r in sheet['remnants']), reverse=True)
                    loss = sum(c['kerf_rect']['w']*c['kerf_rect']['h'] for sheet in sheets for c in sheet['cuts'])
                    score += (loss, tuple(-a for a in remnants), sum(len(sheet['cuts']) for sheet in sheets))
                    if best_score is None or score < best_score:
                        best, best_score = deepcopy(sheets), score
    if best is None:
        raise GeometryError('当前搜索未找到完整玻璃排版。请增加可用板材、调整规格或允许旋转；这不代表已证明无解。')
    expected = {p['instance'] for p in pieces}
    actual = [p['instance'] for s in best for p in s['pieces']]
    assert len(actual) == len(expected) and set(actual) == expected
    purchase, inventory = {}, {}
    for sheet in best:
        sheet['glass_area'] = sum(p['width']*p['height'] for p in sheet['pieces'])
        sheet['loss_area'] = sum(c['kerf_rect']['w']*c['kerf_rect']['h'] for c in sheet['cuts'])
        sheet['remnant_area'] = sum(r['w']*r['h'] for r in sheet['remnants'])
        assert sheet['glass_area']+sheet['loss_area']+sheet['remnant_area'] == sheet['width']*sheet['height']
        row = (inventory if sheet['supply']=='inventory' else purchase).setdefault(sheet['stock_id'], dict(stock_id=sheet['stock_id'], width=sheet['width'], height=sheet['height'], count=0, cost_cents=0))
        row['count'] += 1
        row['cost_cents'] += sheet['price_cents']
    for s in cfg.stocks:
        if s.supply=='inventory':
            row=inventory.setdefault(s.id,dict(stock_id=s.id,width=s.width,height=s.height,count=0,cost_cents=0))
            row.update(available=s.available,remaining=s.available-row['count'])
    total = sum(p['area'] for p in pieces)
    inventory_area=sum(s.width*s.height*s.available for s in stocks if s.supply=='inventory')
    max_area=max((s.width*s.height for s in stocks if s.supply=='purchase'),default=1)
    lower=(max(0,total-inventory_area)+max_area-1)//max_area
    bought_count=sum(s['supply']=='purchase' for s in best)
    proven=cfg.objective=='sheets' and bought_count==lower
    return dict(status='OPTIMAL_PRIMARY' if proven else 'FEASIBLE', primary_proven=proven,
        lower_bound=lower, sheet_count=len(best), purchase_count=bought_count, inventory_count=len(best)-bought_count, inventory_usage=list(inventory.values()), cost_cents=sum(s['price_cents'] for s in best),
        total_stock_area=sum(s['width']*s['height'] for s in best), total_glass_area=total,
        loss_area=sum(s['loss_area'] for s in best), remnant_area=sum(s['remnant_area'] for s in best),
        sheets=best, purchase=list(purchase.values()))
