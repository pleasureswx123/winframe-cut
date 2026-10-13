"""客户、房屋项目与窗型存档的业务输入模型。"""
from pydantic import Field, field_validator, model_validator
from .models import StrictModel, Project, Stock, CutSettings, GlassSettings


class CustomerInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(default='', max_length=40)
    address: str = Field(default='', max_length=300)
    notes: str = Field(default='', max_length=2000)

    @field_validator('name')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('名称不能为空')
        return value.strip()


class HouseInput(StrictModel):
    custom_profiles: bool = False
    custom_glass: bool = False
    customer_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(default='', max_length=300)
    layout: str = Field(default='', max_length=100)
    notes: str = Field(default='', max_length=2000)
    stocks: list[Stock] = Field(default_factory=list, max_length=200)
    settings: CutSettings = Field(default_factory=CutSettings)
    glass_groups: dict[str, GlassSettings] = Field(default_factory=dict, max_length=50)

    @model_validator(mode='after')
    def consistent(self):
        if not self.name.strip():
            raise ValueError('项目名称不能为空')
        if len({s.id for s in self.stocks}) != len(self.stocks):
            raise ValueError('原料规格编号不能重复')
        if any(not k.strip() or len(k) > 100 for k in self.glass_groups):
            raise ValueError('玻璃材料名称必须为 1 至 100 个字符')
        return self


class WindowInput(StrictModel):
    house_id: str = Field(min_length=1, max_length=80)
    floor: str = Field(default='', max_length=60)
    room: str = Field(default='', max_length=100)
    glass_material: str = Field(default='默认玻璃', min_length=1, max_length=100)
    project: Project
    stocks: list[Stock] = Field(default_factory=list, max_length=40)
    settings: CutSettings = Field(default_factory=CutSettings)

    @model_validator(mode='after')
    def consistent(self):
        # 名称模式随窗型存档保存，旧的自定义名称不覆盖。
        if 'name_mode' not in self.project.model_fields_set and self.project.name == '未命名窗型':
            self.project.name_mode = 'auto'
        if self.project.name_mode == 'auto':
            self.project.name = '·'.join(x.strip() for x in (self.floor, self.room) if x.strip())[:100] or '未命名窗型'
        elif not self.project.name.strip():
            raise ValueError('请输入窗型名称')
        if not self.glass_material.strip():
            raise ValueError('玻璃材料不能为空')
        if len({s.id for s in self.stocks}) != len(self.stocks):
            raise ValueError('原料规格编号不能重复')
        return self
