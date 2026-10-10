"""按区域树生成实体清单，计算不依赖画布像素和 Blender 浮点坐标。"""
from dataclasses import dataclass
from .models import Project, Node, TICKS, LABELS


class GeometryError(ValueError):
    pass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    def inset(self, size):
        r = Rect(self.x+size, self.y+size, self.w-2*size, self.h-2*size)
        if r.w <= 0 or r.h <= 0:
            raise GeometryError('区域太小，无法容纳所设置的型材宽度')
        return r

    def json(self):
        return dict(x=self.x, y=self.y, w=self.w, h=self.h)


def calculate(project: Project):
    parts, regions, splits = [], [], []
    glasses, glass_warnings = [], []
    seen = set()

    def add(pid, category, label, r, length, polygon=None, short=None, start=None, end=None):
        if length <= 0:
            raise GeometryError(f'{label}长度必须大于零')
        profile = project.profiles[category]
        points = polygon or [[r.x,r.y],[r.x+r.w,r.y],[r.x+r.w,r.y+r.h],[r.x,r.y+r.h]]
        parts.append(dict(id=pid, category=category, category_label=LABELS[category], label=label,
            stock_key=profile.stock_key, width=profile.width, length=length,
            short_length=short if short is not None else length,
            angle=45 if short is not None else 90, quantity=project.quantity,
            rect=r.json(), polygon=points, start=start, end=end,
            center=[r.x+r.w/2,r.y+r.h/2]))

    def frame(prefix, category, label, r):
        f=project.profiles[category].width
        inner=r.inset(f)
        x,y,w,h=r.x,r.y,r.w,r.h
        add(prefix+'-T',category,label+'上框',Rect(x,y,w,f),w,[[x,y],[x+w,y],[x+w-f,y+f],[x+f,y+f]],w-2*f)
        add(prefix+'-B',category,label+'下框',Rect(x,y+h-f,w,f),w,[[x+f,y+h-f],[x+w-f,y+h-f],[x+w,y+h],[x,y+h]],w-2*f)
        add(prefix+'-L',category,label+'左框',Rect(x,y,f,h),h,[[x,y],[x+f,y+f],[x+f,y+h-f],[x,y+h]],h-2*f)
        add(prefix+'-R',category,label+'右框',Rect(x+w-f,y,f,h),h,[[x+w,y],[x+w,y+h],[x+w-f,y+h-f],[x+w-f,y+f]],h-2*f)
        return inner

    def walk(node: Node, r: Rect, context='window', depth=0):
        if depth>24 or len(seen)>=100:
            raise GeometryError('最多支持 100 个区域节点、24 层分隔')
        if node.id in seen:
            raise GeometryError('区域编号重复')
        seen.add(node.id)
        info=dict(id=node.id,kind=node.kind,context=context,rect=r.json())
        regions.append(info)
        if node.kind=='split':
            category=context+'_mullion'; t=project.profiles[category].width
            p=node.position; half=t//2
            low,high=(r.x,r.x+r.w) if node.axis=='x' else (r.y,r.y+r.h)
            if p-half<=low or p+half>=high:
                raise GeometryError(f'区域 {node.id} 的中挺越界：中心线必须位于 {(low+half)/TICKS:g} 与 {(high-half)/TICKS:g} mm 之间')
            if node.axis=='x':
                bar=Rect(p-half,r.y,t,r.h); a=Rect(r.x,r.y,p-half-r.x,r.h); b=Rect(p+half,r.y,r.x+r.w-p-half,r.h)
                start,end=[p,r.y],[p,r.y+r.h];length=r.h
            else:
                bar=Rect(r.x,p-half,r.w,t);a=Rect(r.x,r.y,r.w,p-half-r.y);b=Rect(r.x,p+half,r.w,r.y+r.h-p-half)
                start,end=[r.x,p],[r.x+r.w,p];length=r.w
            add(node.id+'-M',category,'竖中挺' if node.axis=='x' else '横中挺',bar,length,start=start,end=end)
            splits.append(dict(id=node.id,axis=node.axis,position=p,context=context,start=start,end=end,rect=r.json()))
            walk(node.children[0],a,context,depth+1);walk(node.children[1],b,context,depth+1)
        elif node.kind=='sash':
            if context=='sash':
                raise GeometryError('窗扇内部不能再次嵌套窗扇')
            inner=frame(node.id+'-F','sash_frame','窗扇',r)
            walk(node.children[0],inner,'sash',depth+1)
        elif node.kind=='glass':
            category=context+'_bead';t=project.profiles[category].width
            info['opening']=r.inset(t).json()
            dx,dy=project.glass.width_deduction,project.glass.height_deduction
            if r.w<=dx or r.h<=dy:
                raise GeometryError(f'区域 {node.id} 的玻璃宽高总减量过大，玻璃尺寸必须大于零')
            gr=Rect(r.x+dx//2,r.y+dy//2,r.w-dx,r.h-dy)
            info['glass']=gr.json()
            overlap=dict(x=t-dx//2,y=t-dy//2)
            if min(overlap.values())<=0:
                glass_warnings.append(f'区域 {node.id} 的玻璃没有被四边压线有效覆盖，请减小玻璃总减量或增大压线宽度')
            glasses.append(dict(id=node.id+'-G',region_id=node.id,context=context,
                label='窗扇玻璃' if context=='sash' else '固定玻璃',width=gr.w,height=gr.h,
                quantity=project.quantity,rect=gr.json(),area=gr.w*gr.h,overlap=overlap))
            add(node.id+'-T',category,'上压线',Rect(r.x,r.y,r.w,t),r.w)
            add(node.id+'-B',category,'下压线',Rect(r.x,r.y+r.h-t,r.w,t),r.w)
            add(node.id+'-L',category,'左压线',Rect(r.x,r.y+t,t,r.h-2*t),r.h-2*t)
            add(node.id+'-R',category,'右压线',Rect(r.x+r.w-t,r.y+t,t,r.h-2*t),r.h-2*t)

    inner=frame('W','window_frame','窗户',Rect(0,0,project.width,project.height))
    walk(project.root,inner)
    if len({p['id'] for p in parts})!=len(parts):
        raise GeometryError('区域编号与构件编号冲突，请使用其他区域编号')
    summary=[]
    for category,label in LABELS.items():
        ps=[p for p in parts if p['category']==category]
        summary.append(dict(category=category,label=label,count=len(ps)*project.quantity,total_length=sum(p['length'] for p in ps)*project.quantity))
    return dict(parts=parts,regions=regions,splits=splits,summary=summary,
        glasses=glasses,glass_count=len(glasses)*project.quantity,glass_area=sum(g['area'] for g in glasses)*project.quantity,glass_warnings=glass_warnings,
        count=len(parts)*project.quantity,total_length=sum(p['length'] for p in parts)*project.quantity,
        unit='1/2000 mm',coordinate_system='左上角原点，X 向右、Y 向下；Blender Y 为相反数')
