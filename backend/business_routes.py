"""操作平台的客户、房屋和窗型接口。"""
from fastapi import APIRouter, Depends, Query
from .auth import User, require_user
from .business_models import CustomerInput, HouseInput, WindowInput
from . import business_service as service
from .window_materials import window_materials, preview_materials
from .project_optimizer import load_house, optimize_house_profiles, optimize_house_glass

router = APIRouter(prefix='/api', tags=['客户项目'])


@router.get('/customers')
def customers(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
              q: str = Query('', max_length=100), user: User = Depends(require_user)):
    return service.list_records('customers', user.id, page, page_size, q)


@router.post('/customers', status_code=201)
def create_customer(data: CustomerInput, user: User = Depends(require_user)):
    return service.save_record('customers', data, user.id)


@router.put('/customers/{id}')
def update_customer(id: str, data: CustomerInput, user: User = Depends(require_user)):
    return service.save_record('customers', data, user.id, id)


@router.get('/houses')
def houses(customer_id: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
           q: str = Query('', max_length=100), user: User = Depends(require_user)):
    return service.list_records('houses', user.id, page, page_size, q, customer_id)


@router.post('/houses', status_code=201)
def create_house(data: HouseInput, user: User = Depends(require_user)):
    return service.save_record('houses', data, user.id)


@router.put('/houses/{id}')
def update_house(id: str, data: HouseInput, user: User = Depends(require_user)):
    return service.save_record('houses', data, user.id, id)


@router.get('/windows')
def windows(house_id: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
            q: str = Query('', max_length=100), user: User = Depends(require_user)):
    return service.list_records('windows', user.id, page, page_size, q, house_id)


@router.post('/windows', status_code=201)
def create_window(data: WindowInput, user: User = Depends(require_user)):
    return service.save_record('windows', data, user.id)


@router.put('/windows/{id}')
def update_window(id: str, data: WindowInput, user: User = Depends(require_user)):
    return service.save_record('windows', data, user.id, id)


def register_record_routes(table):
    # 表名来自此固定清单，永不拼接客户端提供的 SQL 标识符。
    def read(id: str, user: User = Depends(require_user)):
        return service.get_record(table, id, user.id)

    def delete(id: str, user: User = Depends(require_user)):
        return service.delete_record(table, id, user.id)

    router.add_api_route('/' + table + '/{id}', read, methods=['GET'])
    router.add_api_route('/' + table + '/{id}', delete, methods=['DELETE'])


for table in ('customers', 'houses', 'windows'):
    register_record_routes(table)


@router.post('/houses/{id}/optimize')
def optimize_house(id: str, user: User = Depends(require_user)):
    house, windows = load_house(id, user.id)
    return optimize_house_profiles(windows, house['stocks'] if house['custom_profiles'] else window_materials(windows, 'profiles'), house['settings'])


@router.post('/houses/{id}/optimize-glass')
def optimize_house_glasses(id: str, user: User = Depends(require_user)):
    house, windows = load_house(id, user.id)
    return optimize_house_glass(windows, house['glass_groups'] if house['custom_glass'] else window_materials(windows, 'glass'))


@router.get('/houses/{id}/cutting-sources')
def cutting_sources(id: str, user: User = Depends(require_user)):
    _, windows = load_house(id, user.id)
    return dict(preview_materials(windows), windows=windows)
