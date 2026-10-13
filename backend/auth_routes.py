"""账号接口：账号由管理平台发放，会话使用 HttpOnly Cookie。"""
import os
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from .auth import (COOKIE, SESSION_SECONDS, Credentials, User, check_origin,
                   public_user, require_user, token_hash, verify_password)
from .database import connect

router = APIRouter(prefix='/api/auth', tags=['账号'])


@router.post('/register')
def register():
    raise HTTPException(403, '不开放自行注册，请联系管理员获取账号')


@router.post('/login')
def login(data: Credentials, request: Request, response: Response):
    check_origin(request)
    current = int(time.time())
    address = request.client.host if request.client else 'unknown'
    with connect() as db:
        db.execute('DELETE FROM login_attempts WHERE attempted < ?', (current - 900,))
        count = db.execute('SELECT COUNT(*) FROM login_attempts WHERE username=?', (data.username,)).fetchone()[0]
        ip_count = db.execute('SELECT COUNT(*) FROM login_attempts WHERE address=?', (address,)).fetchone()[0]
        if count >= 6 or ip_count >= 30:
            raise HTTPException(429, '尝试过于频繁，请 15 分钟后重试')
        row = db.execute('SELECT * FROM users WHERE username=?', (data.username,)).fetchone()
        # 不存在的账号也执行相同成本的派生，减少账号枚举时序差异。
        encoded = row['password_hash'] if row else 'scrypt$' + '00' * 16 + '$' + '00' * 32
        valid = verify_password(data.password, encoded) and row is not None and bool(row['active'])
        if not valid:
            db.execute('INSERT INTO login_attempts(username,address,attempted) VALUES (?,?,?)', (data.username, address, current))
        else:
            db.execute('DELETE FROM login_attempts WHERE username=?', (data.username,))
            db.execute('DELETE FROM sessions WHERE expires<=?', (current,))
            previous = request.cookies.get(COOKIE)
            if previous:
                db.execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(previous),))
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (token_hash(token), row['id'], csrf, current + SESSION_SECONDS))
    if not valid:
        raise HTTPException(401, '用户名或密码错误，或账号不可用')
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite='lax',
                        secure=os.getenv('WINFRAME_COOKIE_SECURE', 'false').lower() == 'true', path='/')
    response.headers['Cache-Control'] = 'no-store'
    return {'user': public_user(row), 'csrf_token': csrf}


@router.get('/me')
def me(request: Request, response: Response, user: User = Depends(require_user)):
    response.headers['Cache-Control'] = 'no-store'
    return {'user': user, 'csrf_token': request.state.csrf_token}


@router.post('/logout')
def logout(request: Request, response: Response, user: User = Depends(require_user)):
    with connect() as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?', (token_hash(request.cookies[COOKIE]),))
    response.delete_cookie(COOKIE, path='/')
    return {'ok': True}
