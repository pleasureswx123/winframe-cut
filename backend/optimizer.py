"""按原料型号隔离排料，使用 CP-SAT；所有容量约束都是整数。"""
from collections import defaultdict, Counter
from decimal import Decimal, ROUND_CEILING
from time import monotonic
from ortools.sat.python import cp_model
from .models import OptimizeRequest
from .geometry import calculate, GeometryError


def cut_allowance(angle: int, kerf: int):
    # 45° 每端折算后的轴向锯缝向上取整，独立双端切割，不共享斜口。
    if angle == 45:
        end = int((Decimal(kerf)*Decimal(2).sqrt()).to_integral_value(rounding=ROUND_CEILING))
        return end, end
    return 0, kerf


def optimize(request: OptimizeRequest):
    geometry=calculate(request.project)
    if geometry['count']>400:
        raise GeometryError('单次最多排料 400 根构件，请拆分生产批次')
    parts=[]
    for p in geometry['parts']:
        for n in range(request.project.quantity):
            parts.append(dict(p,instance=f"{p['id']}@{n+1}"))
    return optimize_parts(parts,request.stocks,request.settings)


def optimize_parts(parts, stocks, settings):
    if len(parts)>5000:
        raise GeometryError('整项目单次最多排料 5000 根构件，请减少项目制作数量')
    if len({p['instance'] for p in parts})!=len(parts):
        raise GeometryError('构件来源编号重复，无法排料')
    groups=defaultdict(list)
    widths={}
    for p in parts:
        key=p['stock_key']
        if key in widths and widths[key]!=p['width']:
            raise GeometryError(f'型号 {key} 在不同窗型中的条宽不一致，请使用不同材料型号')
        widths[key]=p['width']
        front,back=cut_allowance(p['angle'],settings.kerf)
        groups[key].append(dict(p,front_loss=front,back_loss=back,occupied=p['length']+front+back))
    results=[]
    for key,parts in groups.items():
        available_stocks=[s for s in stocks if s.stock_key==key and s.available!=0]
        if not available_stocks:
            labels=' / '.join(dict.fromkeys(p['category_label'] for p in parts))
            reason='对应规格的可用数量均为 0，请修改库存或留空表示可采购' if any(s.stock_key==key for s in stocks) else '缺少同型号原料规格，请在型材原料规格中补充；型号必须完全一致'
            raise GeometryError(f'{labels}（型号：{key}）：{reason}')
        if settings.objective=='cost' and any(s.supply=='purchase' and s.purchase_price<=0 for s in available_stocks):
            raise GeometryError(f'型号 {key} 按成本排料前，请填写所有可用规格的单价（必须大于零）')
        results.append(solve_group(key,parts,available_stocks,settings))
    bars=[b for g in results for b in g['bars']]
    purchase=defaultdict(lambda:dict(count=0,cost_cents=0));inventory=defaultdict(lambda:dict(count=0,cost_cents=0))
    for b in bars:
        p=(inventory if b['supply']=='inventory' else purchase)[b['stock_id']];p.update(stock_id=b['stock_id'],stock_key=b['stock_key'],length=b['length'],price_cents=b['price_cents'])
        p['count']+=1;p['cost_cents']+=b['price_cents']
    for s in stocks:
        if s.supply=='inventory':
            row=inventory.setdefault(s.id,dict(stock_id=s.id,stock_key=s.stock_key,length=s.length,price_cents=0,count=0,cost_cents=0))
            row.update(available=s.available,remaining=s.available-row['count'])
    return dict(groups=results,purchase=list(purchase.values()),inventory_usage=list(inventory.values()),
        purchase_count=sum(b['supply']=='purchase' for b in bars),inventory_count=sum(b['supply']=='inventory' for b in bars),bar_count=len(bars),
        cost_cents=sum(b['price_cents'] for b in bars),total_stock=sum(b['length'] for b in bars),
        total_parts=sum(p['length'] for ps in groups.values() for p in ps),
        total_loss=sum(b['loss'] for b in bars),total_remnant=sum(b['remnant'] for b in bars),
        reusable_remnant=sum(b['reusable_remnant'] for b in bars),scrap_remnant=sum(b['scrap_remnant'] for b in bars),
        largest_remnant=max((b['remnant'] for b in bars),default=0),
        status='OPTIMAL' if all(g['status']=='OPTIMAL' for g in results) else 'FEASIBLE',
        primary_proven=all(g['primary_proven'] for g in results),settings=settings.model_dump(),
        manufacturing_rule='直切每根预留一道锯缝；45° 外框两端独立切割，各预留向上取整的 √2 × 刀片厚度；不共用斜口。端部修整按轴向总占用计入。')


def solve_group(key,parts,stocks,settings):
    deadline=monotonic()+settings.time_limit
    if len(parts)>200 and (len(parts)>1000 or len({p['occupied'] for p in parts})>12):
        return solve_large_group(key,parts,stocks,settings,deadline)
    fallback=None
    if len(parts)>200:
        # 先留完整可行方案；聚合求解超时仍可交付，不退回部分构件。
        try:
            fallback=solve_large_group(key,parts,stocks,settings,min(deadline,monotonic()+settings.time_limit/5))
        except GeometryError:
            pass
    trim=settings.trim_start+settings.trim_end
    capacities=[s.length-trim for s in stocks]
    if any(p['occupied']>max(capacities) for p in parts):
        bad=next(p for p in parts if p['occupied']>max(capacities))
        raise GeometryError(f"型号 {key} 的构件 {bad['id']} 加上锯缝及修整后超过所有原料长度")
    grouped=defaultdict(list)
    for p in parts:grouped[p['occupied']].append(p)
    weights=sorted(grouped,reverse=True);demands=[len(grouped[w]) for w in weights]
    bins=len(parts)
    # 无限供应规格的首次适应解给出根数上界，成本目标不可使用此上界。
    if settings.objective=='bars' and not any(s.supply=='inventory' for s in stocks):
        infinite=[cap for s,cap in zip(stocks,capacities) if s.available is None]
        if infinite and max(infinite)>=max(weights):
            loads=[]
            for p in sorted(parts,key=lambda p:p['occupied'],reverse=True):
                for i,load in enumerate(loads):
                    if load+p['occupied']<=max(infinite):loads[i]+=p['occupied'];break
                else:loads.append(p['occupied'])
            bins=len(loads)
    model=cp_model.CpModel()
    use=[model.new_bool_var(f'u{b}') for b in range(bins)]
    choice=[[model.new_bool_var(f's{b}_{j}') for j in range(len(stocks))] for b in range(bins)]
    counts=[[model.new_int_var(0,min(demands[i],max(capacities)//w),f'n{b}_{i}') for i,w in enumerate(weights)] for b in range(bins)]
    loads=[]
    for b in range(bins):
        model.add(sum(choice[b])==use[b])
        load=sum(counts[b][i]*w for i,w in enumerate(weights));loads.append(load)
        model.add(load<=sum(choice[b][j]*capacities[j] for j in range(len(stocks))))
        model.add(sum(counts[b])>=use[b])
        if b:
            model.add(use[b-1]>=use[b]);model.add(loads[b-1]>=load)
    for i,d in enumerate(demands):model.add(sum(counts[b][i] for b in range(bins))==d)
    for j,s in enumerate(stocks):
        if s.available is not None:model.add(sum(choice[b][j] for b in range(bins))<=s.available)
    bar_count=sum(choice[b][j] for b in range(bins) for j,s in enumerate(stocks) if s.supply=='purchase')
    cost=sum(choice[b][j]*s.purchase_price for b in range(bins) for j,s in enumerate(stocks))
    purchased=sum(choice[b][j]*s.length for b in range(bins) for j,s in enumerate(stocks) if s.supply=='purchase')
    objectives=[bar_count,purchased] if settings.objective=='bars' else [cost,bar_count,purchased]
    objectives.append(sum(use))
    # 主采购目标固定后，减少无法回收的短废料，再集中最长余料。
    short_remnants=[];remnants=[]
    max_length=max(s.length for s in stocks)
    for b in range(bins):
        rem=model.new_int_var(0,max_length,f'rem{b}')
        model.add(rem==sum(choice[b][j]*capacities[j] for j in range(len(stocks)))-loads[b])
        reusable=model.new_bool_var(f'reusable{b}')
        threshold=max(1,settings.reusable_min)
        model.add(rem>=threshold).only_enforce_if(reusable)
        model.add(rem<threshold).only_enforce_if(reusable.Not())
        short=model.new_int_var(0,max_length,f'short{b}')
        model.add(short==0).only_enforce_if(reusable)
        model.add(short==rem).only_enforce_if(reusable.Not())
        remnants.append(rem);short_remnants.append(short)
    largest=model.new_int_var(0,max_length,'largest_remnant')
    model.add_max_equality(largest,remnants)
    objectives.extend([sum(short_remnants),-largest])
    best=None;primary_proven=False;all_proven=True;primary_bound=0;primary_value=None
    for stage,objective in enumerate(objectives):
        remaining=deadline-monotonic()
        if remaining<0.01:all_proven=False;break
        model.minimize(objective)
        solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=remaining
        solver.parameters.num_search_workers=4;solver.parameters.random_seed=42
        status=solver.solve(model)
        if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
            if status==cp_model.INFEASIBLE:
                raise GeometryError(f'型号 {key} 的库存数量不足，无法完成全部构件')
            if best is None:
                if fallback is not None:return fallback
                raise GeometryError(f'型号 {key} 在时限内未找到可行方案，请延长求解时间或减少批量')
            all_proven=False;break
        best=[(next(j for j in range(len(stocks)) if solver.value(choice[b][j])),[solver.value(c) for c in counts[b]]) for b in range(bins) if solver.value(use[b])]
        value=solver.value(objective)
        if stage==0:
            primary_proven=status==cp_model.OPTIMAL;primary_bound=solver.best_objective_bound;primary_value=value
        if status!=cp_model.OPTIMAL:all_proven=False;break
        model.add(objective==value)
        if stage+1<len(objectives):
            model.add(objectives[stage+1]<=solver.value(objectives[stage+1]))
    if best is None:
        if fallback is not None:return fallback
        raise GeometryError('时限内未找到排料结果，请延长求解时间')
    result=render_group(key,parts,stocks,settings,grouped,weights,best,all_proven,primary_proven,primary_bound,primary_value)
    if fallback is not None:
        def score(plan):
            bars=plan['bars'];cost=sum(b['price_cents'] for b in bars);bought=[b for b in bars if b['supply']=='purchase'];length=sum(b['length'] for b in bought)
            primary=(cost,len(bought),length) if settings.objective=='cost' else (len(bought),length)
            return (*primary,len(bars),sum(b['scrap_remnant'] for b in bars),-max(b['remnant'] for b in bars))
        if score(fallback)<score(result):return fallback
    return result


def render_group(key,parts,stocks,settings,grouped,weights,best,all_proven=False,primary_proven=False,primary_bound=0,primary_value=None):
    trim=settings.trim_start+settings.trim_end
    pools={w:list(ps) for w,ps in grouped.items()};bars=[]
    for number,(j,cs) in enumerate(best,1):
        stock=stocks[j];cursor=settings.trim_start;segments=[];loss=trim
        for i,n in enumerate(cs):
            for _ in range(n):
                p=pools[weights[i]].pop();end=cursor+p['occupied']
                segments.append(dict(instance=p['instance'],part_id=p['id'],label=p['label'],category=p['category'],length=p['length'],short_length=p['short_length'],angle=p['angle'],
                    from_tick=cursor,to_tick=end,front_loss=p['front_loss'],back_loss=p['back_loss'],cut_start=cursor+p['front_loss'],cut_end=cursor+p['front_loss']+p['length']))
                if 'source' in p:segments[-1]['source']=p['source']
                cursor=end;loss+=p['front_loss']+p['back_loss']
        remnant=stock.length-settings.trim_end-cursor
        assert remnant>=0 and sum(p['length'] for p in segments)+loss+remnant==stock.length
        bars.append(dict(id=f'{key}-{number}',stock_id=stock.id,stock_key=key,length=stock.length,price_cents=stock.purchase_price,supply=stock.supply,
            pieces=segments,loss=loss,remnant=remnant,reusable_remnant=remnant if remnant>=settings.reusable_min else 0,
            scrap_remnant=remnant if remnant<settings.reusable_min else 0,trim_start=settings.trim_start,trim_end=settings.trim_end))
    assert all(not ps for ps in pools.values())
    expected=Counter(p['instance'] for p in parts)
    actual=Counter(p['instance'] for b in bars for p in b['pieces'])
    if actual!=expected:
        raise RuntimeError('排料完整性校验失败：构件遗漏或重复')
    return dict(stock_key=key,status='OPTIMAL' if all_proven else 'FEASIBLE',primary_proven=primary_proven,
        primary_bound=primary_bound,primary_value=primary_value,bars=bars)


def solve_large_group(key,parts,stocks,settings,deadline=None):
    """多策略搜索并合并整料，保留完整最好解；不宣称已证明最优。"""
    from .profile_search import search_layout
    if deadline is None:deadline=monotonic()+settings.time_limit
    grouped=defaultdict(list)
    for p in parts:grouped[p['occupied']].append(p)
    weights=sorted(grouped,reverse=True)
    if monotonic()>=deadline:
        raise GeometryError(f'型号 {key} 在时限内未完成全部构件，请延长时限')
    best=search_layout(parts,stocks,settings,weights,deadline)
    if best is None:
        raise GeometryError(f'型号 {key} 当前搜索未找到完整方案，请延长时限并核对原料长度和库存；不代表已证明无解')
    return render_group(key,parts,stocks,settings,grouped,weights,[(b['stock'],b['counts']) for b in best])
