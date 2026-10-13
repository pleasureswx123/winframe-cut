"""密码派生、服务端会话和请求权限；客户端不能指定身份。"""
from datetime import datetime, timezone
from hashlib import scrypt, sha256
import hmac
import os
import secrets
import sqlite3
import time
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .database import connect

COOKIE = 'winframe_session'
SESSION_SECONDS = 12 * 60 * 60


def now():
    return datetime.now(timezone.utc).isoformat()


class User(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    active: bool


class Credentials(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=3, max_length=40, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(min_length=1, max_length=128)

    @field_validator('username')
    @classmethod
    def normalize(cls, value):
        return value.lower()


class Registration(Credentials):
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(default='', max_length=80)


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f'scrypt${salt.hex()}${digest.hex()}'


def verify_password(password, encoded):
    try:
        scheme, salt, digest = encoded.split('$')
        if scheme != 'scrypt':
            return False
        actual = scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual.hex(), digest)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return sha256(token.encode()).hexdigest()


def public_user(row):
    return User(**{key: row[key] for key in User.model_fields})


def create_user(data: Registration, role='user'):
    user_id = uuid4().hex
    password_hash = hash_password(data.password)
    try:
        with connect() as db:
            db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)', (
                user_id, data.username, data.display_name.strip() or data.username,
                password_hash, role, 1, now()))
            return public_user(db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone())
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, '用户名已被注册') from exc


def check_origin(request: Request):
    origin = request.headers.get('origin')
    expected = os.getenv('WINFRAME_PUBLIC_ORIGIN', str(request.base_url).rstrip('/')).rstrip('/')
    if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and origin != expected):
        raise HTTPException(403, '请求来源不受信任')


def require_user(request: Request):
    token = request.cookies.get(COOKIE, '')
    if not token:
        raise HTTPException(401, '请先登录')
    with connect() as db:
        row = db.execute('''SELECT u.*,s.csrf_token,s.expires FROM sessions s
                            JOIN users u ON u.id=s.user_id WHERE s.token_hash=?''', (token_hash(token),)).fetchone()
    if not row or not row['active'] or row['expires'] <= int(time.time()):
        raise HTTPException(401, '登录已失效，请重新登录')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        check_origin(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), row['csrf_token']):
            raise HTTPException(403, '请求校验失败，请刷新页面后重试')
    request.state.csrf_token = row['csrf_token']
    return public_user(row)


def require_admin(request: Request):
    user = require_user(request)
    if user.role != 'admin':
        raise HTTPException(403, '需要管理员权限')
    return user


def ensure_super_admin():
    """首次启动创建指定超级管理员，后续启动不覆盖账号设置。"""
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute("SELECT role FROM users WHERE username='admin'").fetchone()
        if existing:
            if existing['role'] != 'admin':
                raise RuntimeError('admin 用户名已被普通账号占用，请先由管理员处理冲突')
            return
        db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)', (
            uuid4().hex, 'admin', '超级管理员', hash_password('admin123'), 'admin', 1, now()))
