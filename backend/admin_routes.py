"""管理平台只通过独立受保护接口查看全体用户数据。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from .auth import User, public_user, require_admin, Registration, create_user, hash_password
from .database import connect
from .business_service import list_records, serialize
from .models import StrictModel, Project
from .geometry import calculate

router = APIRouter(prefix='/api/admin', tags=['管理平台'])


@router.post('/users', status_code=201)
def add_user(data: Registration, user: User = Depends(require_admin)):
    return create_user(data)


@router.get('/users')
def users(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
          q: str = Query('', max_length=100), user: User = Depends(require_admin)):
    with connect() as db:
        count = db.execute('SELECT COUNT(*) FROM users WHERE instr(username,?)>0 OR instr(display_name,?)>0', (q,q)).fetchone()[0]
        rows = db.execute('SELECT * FROM users WHERE instr(username,?)>0 OR instr(display_name,?)>0 ORDER BY created DESC LIMIT ? OFFSET ?', (q,q,page_size,(page-1)*page_size)).fetchall()
    return {'items': [public_user(row) for row in rows], 'total': count, 'page':page, 'page_size':page_size}


class UserStatus(StrictModel):
    active: bool


class Assignment(StrictModel):
    house_id: str = Field(min_length=1, max_length=80)


@router.get('/summary')
def summary(user: User = Depends(require_admin)):
    with connect() as db:
        return {table:db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                for table in ('users','customers','houses','windows')}


@router.patch('/users/{id}')
def update_user(id: str, data: UserStatus, user: User = Depends(require_admin)):
    if id == user.id and not data.active:
        raise HTTPException(409, '不能禁用当前管理员账号')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        target = db.execute('SELECT * FROM users WHERE id=?', (id,)).fetchone()
        if not target:
            raise HTTPException(404, '用户不存在')
        if target['role'] == 'admin':
            raise HTTPException(409, '平台管理接口只能启停普通用户')
        db.execute('UPDATE users SET active=? WHERE id=?', (int(data.active),id))
        if not data.active:
            db.execute('DELETE FROM sessions WHERE user_id=?', (id,))
    return {'ok':True}


class PasswordReset(StrictModel):
    password: str = Field(min_length=10, max_length=128)


@router.post('/users/{id}/password')
def reset_password(id: str, data: PasswordReset, user: User = Depends(require_admin)):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        target = db.execute('SELECT role FROM users WHERE id=?', (id,)).fetchone()
        if not target:
            raise HTTPException(404, '用户不存在')
        if target['role'] == 'admin':
            raise HTTPException(409, '此功能仅用于重置普通用户密码')
        # 密码变更与撤销所有会话必须在同一事务内完成。
        db.execute('UPDATE users SET password_hash=? WHERE id=?', (hash_password(data.password), id))
        db.execute('DELETE FROM sessions WHERE user_id=?', (id,))
    return {'ok': True}


@router.get('/users/{id}/{table}')
def user_records(id: str, table: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                 q: str = Query('', max_length=100), customer_id: str | None = None, house_id: str | None = None,
                 user: User = Depends(require_admin)):
    if table not in ('customers','houses','windows'):
        raise HTTPException(404, '未知数据类型')
    return list_records(table,id,page,page_size,q,customer_id if table=='houses' else house_id)


@router.get('/windows/{id}')
def window_details(id: str, user: User = Depends(require_admin)):
    with connect() as db:
        row = db.execute('SELECT * FROM windows WHERE id=?', (id,)).fetchone()
    if not row:
        raise HTTPException(404, '窗型不存在')
    result = serialize(row)
    result['geometry'] = calculate(Project.model_validate(result['project']))
    return result


@router.get('/legacy')
def legacy(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(require_admin)):
    with connect() as db:
        total = db.execute('SELECT COUNT(*) FROM windows WHERE owner_id IS NULL').fetchone()[0]
        rows = db.execute('SELECT * FROM windows WHERE owner_id IS NULL ORDER BY updated DESC LIMIT ? OFFSET ?', (page_size,(page-1)*page_size)).fetchall()
    return {'items':[serialize(r) for r in rows],'total':total,'page':page,'page_size':page_size}


@router.post('/legacy/{id}/assign')
def assign_legacy(id: str, data: Assignment, user: User = Depends(require_admin)):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        window = db.execute('SELECT * FROM windows WHERE id=?', (id,)).fetchone()
        if not window:
            raise HTTPException(404, '窗型不存在')
        if window['owner_id'] is not None:
            raise HTTPException(409, '此窗型已有归属，不能重复分配')
        house = db.execute('SELECT * FROM houses WHERE id=?', (data.house_id,)).fetchone()
        if not house:
            raise HTTPException(404, '目标房屋项目不存在')
        db.execute('UPDATE windows SET owner_id=?,house_id=? WHERE id=?', (house['owner_id'],house['id'],id))
    return {'ok':True}
