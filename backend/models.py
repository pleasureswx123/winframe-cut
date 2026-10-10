"""长度统一使用整数刻度：1 mm = 2000 刻度，支持半个微米的分区边界。"""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

TICKS = 2000
CATEGORIES = ['window_frame', 'window_mullion', 'window_bead', 'sash_frame', 'sash_mullion', 'sash_bead']
LABELS = dict(zip(CATEGORIES, ['窗户外框', '窗户中挺', '窗户压线', '窗扇外框', '窗扇中挺', '窗扇压线']))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Node(StrictModel):
    id: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    kind: Literal['glass', 'empty', 'split', 'sash'] = 'glass'
    axis: Literal['x', 'y'] | None = None
    position: int | None = None
    children: list['Node'] = Field(default_factory=list, max_length=2)

    @model_validator(mode='after')
    def shape(self):
        if self.kind == 'split':
            if self.axis is None or self.position is None or len(self.children) != 2:
                raise ValueError('中挺必须有方向、中心线坐标和两个子区域')
        elif self.kind == 'sash':
            if len(self.children) != 1 or self.axis is not None or self.position is not None:
                raise ValueError('窗扇必须且只能包含一个内部区域')
        elif self.children or self.axis is not None or self.position is not None:
            raise ValueError('玻璃或留空区域不能携带隐藏的分区数据')
        return self


class Profile(StrictModel):
    width: int = Field(gt=0, le=1000*TICKS)
    stock_key: str = Field(min_length=1, max_length=60)
    @model_validator(mode='after')
    def precision(self):
        if self.width % 2:
            raise ValueError('型材宽度最多支持三位毫米小数')
        return self


class GlassStock(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    width: int = Field(gt=0, le=100000*TICKS)
    height: int = Field(gt=0, le=100000*TICKS)
    price_cents: int = Field(default=0, ge=0, le=10000000)
    available: int | None = Field(default=None, ge=0, le=500)


class GlassSettings(StrictModel):
    width_deduction: int = Field(default=30*TICKS, ge=0, le=1000*TICKS)
    height_deduction: int = Field(default=30*TICKS, ge=0, le=1000*TICKS)
    kerf: int = Field(default=0, ge=0, le=20*TICKS)
    allow_rotate: bool = True
    objective: Literal['sheets', 'cost'] = 'sheets'
    stocks: list[GlassStock] = Field(default_factory=lambda: [GlassStock(id='示例板材-2440x1830', width=2440*TICKS, height=1830*TICKS)], max_length=30)

    @model_validator(mode='after')
    def check(self):
        if self.width_deduction % 2 or self.height_deduction % 2:
            raise ValueError('玻璃宽高总减量最多支持三位毫米小数')
        if len({s.id for s in self.stocks}) != len(self.stocks):
            raise ValueError('玻璃原板规格编号不能重复')
        return self


class Project(StrictModel):
    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=100)
    width: int = Field(gt=0, le=100000*TICKS)
    height: int = Field(gt=0, le=100000*TICKS)
    quantity: int = Field(default=1, ge=1, le=100)
    profiles: dict[str, Profile]
    root: Node
    glass: GlassSettings = Field(default_factory=GlassSettings)
    @model_validator(mode='after')
    def check_profiles(self):
        if set(self.profiles) != set(CATEGORIES):
            raise ValueError('必须完整提供六类型材参数')
        if self.width % 2 or self.height % 2:
            raise ValueError('整体尺寸最多支持三位毫米小数')
        widths = {}
        for p in self.profiles.values():
            if p.stock_key in widths and widths[p.stock_key] != p.width:
                raise ValueError('相同原料型号不能配置不同的型材宽度')
            widths[p.stock_key] = p.width
        return self


class Stock(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    stock_key: str = Field(min_length=1, max_length=60)
    length: int = Field(gt=0, le=100000*TICKS)
    price_cents: int = Field(default=0, ge=0, le=10000000)
    available: int | None = Field(default=None, ge=0, le=500)


class CutSettings(StrictModel):
    kerf: int = Field(default=3*TICKS, ge=0, le=20*TICKS)
    trim_start: int = Field(default=0, ge=0, le=1000*TICKS)
    trim_end: int = Field(default=0, ge=0, le=1000*TICKS)
    objective: Literal['bars', 'cost'] = 'bars'
    time_limit: int = Field(default=10, ge=1, le=30)


class OptimizeRequest(StrictModel):
    project: Project
    stocks: list[Stock] = Field(default_factory=list, max_length=40)
    settings: CutSettings = Field(default_factory=CutSettings)
    @model_validator(mode='after')
    def unique(self):
        if len({s.id for s in self.stocks}) != len(self.stocks):
            raise ValueError('原料规格编号不能重复')
        return self
