from .models import Project, TICKS, CATEGORIES, LABELS


def sample_project():
    def glass(id): return dict(id=id,kind='glass')
    def split(id,axis,mm,a,b): return dict(id=id,kind='split',axis=axis,position=mm*TICKS,children=[a,b])
    def sash(id,child): return dict(id=id,kind='sash',children=[child])
    def row(id,left,center,right):
        return split(id+'-split-left','x',496,left,split(id+'-split-right','x',1504,center,right))
    top=row('top',glass('top-left'),glass('top-center'),glass('top-right'))
    mid=row('middle',sash('sash-left',glass('sash-left-glass')),glass('middle-glass'),
        sash('sash-right',split('sash-bar','y',854,glass('sash-top'),glass('sash-bottom'))))
    bottom=row('bottom',glass('bottom-left'),glass('bottom-center'),glass('bottom-right'))
    return Project.model_validate(dict(name='2000 方窗 · Blender 基准',width=2000*TICKS,height=2000*TICKS,
        profiles={k:dict(width=(8 if 'mullion' in k else 30)*TICKS,stock_key=LABELS[k]) for k in CATEGORIES},
        root=split('upper','y',534,top,split('lower','y',1466,mid,bottom))))
