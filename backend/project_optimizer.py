"""从项目的同一数据库快照收集全部窗型，再进行跨窗统一排料。"""
from collections import defaultdict
from pydantic import ValidationError
from .database import connect
from .business_service import owned, serialize
from .models import Project, Stock, CutSettings, GlassSettings
from .geometry import calculate, GeometryError
from .optimizer import optimize_parts
from .glass_optimizer import optimize_glass_pieces


def load_house(house_id, owner_id):
    with connect() as db:
        db.execute('BEGIN')
        house = serialize(owned(db, 'houses', house_id, owner_id))
        rows = db.execute('SELECT * FROM windows WHERE house_id=? AND owner_id=? ORDER BY id', (house_id, owner_id)).fetchall()
        windows = [serialize(row) for row in rows]
    if not windows:
        raise GeometryError('项目还没有已保存的窗型，请先创建并保存窗型')
    return house, windows


def collect(windows, kind):
    parts = []
    for window in windows:
        try:
            project = Project.model_validate(window['project'])
            geometry = calculate(project)
            if kind == 'glasses' and geometry['glass_warnings']:
                raise GeometryError('；'.join(geometry['glass_warnings']))
        except (GeometryError, ValidationError) as exc:
            raise GeometryError(f"窗型 {window['name']}（{window['floor']} {window['room']}）：{exc}") from exc
        for piece in geometry[kind]:
            for unit in range(1, project.quantity + 1):
                source = dict(window_id=window['id'], window_name=window['name'], floor=window['floor'],
                              room=window['room'], unit=unit, part_id=piece['id'])
                parts.append(dict(piece, instance=f"{window['id']}:{piece['id']}@{unit}", source=source,
                                  material=window['glass_material']))
                limit = 5000 if kind == 'parts' else 2000
                if len(parts) > limit:
                    raise GeometryError(f'项目构件数超过本次排料上限 {limit}，请减少制作数量')
    return parts


def optimize_house_profiles(windows, stocks, settings):
    parts = collect(windows, 'parts')
    if not parts:
        raise GeometryError('项目没有可排料的型材构件')
    return optimize_parts(parts, [Stock.model_validate(s) for s in stocks], CutSettings.model_validate(settings))


def optimize_house_glass(windows, glass_groups):
    groups = defaultdict(list)
    for piece in collect(windows, 'glasses'):
        groups[piece['material']].append(piece)
    if not groups:
        raise GeometryError('项目没有可排版的玻璃')
    results = []
    for material, pieces in groups.items():
        if material not in glass_groups:
            raise GeometryError(f'玻璃材料 {material} 尚未配置项目原板规格')
        try:
            result = optimize_glass_pieces(pieces, GlassSettings.model_validate(glass_groups[material]))
        except GeometryError as exc:
            raise GeometryError(f'玻璃材料 {material}：{exc}') from exc
        for sheet in result['sheets']:
            sheet['id'] = f'{material}/{sheet["id"]}'
            sheet['material'] = material
        for purchase in result['purchase']+result['inventory_usage']:
            purchase['material'] = material
        results.append(dict(result, material=material))
    totals = {key: sum(result[key] for result in results) for key in (
        'sheet_count','purchase_count','inventory_count','cost_cents','total_stock_area','total_glass_area','loss_area','remnant_area','lower_bound')}
    proven = all(r['primary_proven'] for r in results)
    return dict(totals, groups=results, sheets=[s for r in results for s in r['sheets']],
                purchase=[p for r in results for p in r['purchase']], inventory_usage=[p for r in results for p in r['inventory_usage']], primary_proven=proven,
                status='OPTIMAL_PRIMARY' if proven else 'FEASIBLE')
