"""从窗型存档汇总共享原料；同规格库存只记一次。"""
from hashlib import sha256
from .geometry import calculate, GeometryError
from .models import Project, Stock, GlassSettings
from pydantic import ValidationError


def source_name(window):
    return f"{window['name']}（{window.get('floor', '')} {window.get('room', '')}，编号 {window['id']}）"


def merge_stock(pool, owners, key, stock, window):
    name = source_name(window)
    if key in pool:
        previous = pool[key]
        if (previous['price_cents'], previous['available']) != (stock['price_cents'], stock['available']):
            raise GeometryError(f'同规格原料的单价或共享库存不一致：{owners[key]} 与 {name}。请在对应窗型中统一后保存；共享库存不累加。')
        return
    pool[key] = dict(stock, id='共享-' + sha256(repr(key).encode()).hexdigest()[:16])
    owners[key] = name


def window_materials(windows, mode):
    pool, owners, groups, rules_owner = {}, {}, {}, {}
    for window in windows:
        try:
            project = Project.model_validate(window['project'])
            geometry = calculate(project)
            if mode == 'profiles':
                required = {part['stock_key'] for part in geometry['parts']}
                for raw in window.get('stocks', []):
                    stock = Stock.model_validate(raw).model_dump()
                    if stock['stock_key'] in required:
                        merge_stock(pool, owners, (stock['stock_key'], stock['length'], stock['supply']), stock, window)
            elif geometry['glasses']:
                material = window['glass_material']
                cfg = project.glass.model_dump()
                rules = ('kerf', 'allow_rotate', 'objective')
                if material in groups and any(groups[material][k] != cfg[k] for k in rules):
                    raise GeometryError(f'玻璃材料 {material} 的刀缝、旋转或优化目标不一致：{rules_owner[material]} 与 {source_name(window)}。请在窗型中统一后保存。')
                if material not in groups:
                    groups[material] = dict(cfg, stocks=[])
                    rules_owner[material] = source_name(window)
                for stock in cfg['stocks']:
                    merge_stock(pool, owners, (material, stock['width'], stock['height'], stock['supply']), stock, window)
        except (ValidationError, GeometryError) as exc:
            raise GeometryError(f'窗型 {source_name(window)} 的原料参数无效：{exc}') from exc
    if mode == 'profiles':
        return list(pool.values())
    for key, stock in pool.items():
        groups[key[0]]['stocks'].append(stock)
    for material, cfg in groups.items():
        if len(cfg['stocks']) > 30:
            raise GeometryError(f'玻璃材料 {material} 的不同原板规格超过 30 种，请先整理窗型原板规格')
        GlassSettings.model_validate(cfg)
    return groups


def preview_materials(windows):
    result = {}
    for mode in ('profiles', 'glass'):
        try:
            result[mode] = dict(data=window_materials(windows, mode), error='')
        except GeometryError as exc:
            result[mode] = dict(data=[] if mode == 'profiles' else {}, error=str(exc))
    return result
