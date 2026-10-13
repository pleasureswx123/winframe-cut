"""数据库连接与版本化迁移；旧无主窗型只进入管理员待分配区。"""
from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3


SCHEMA = [
    '''CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
       display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
       role TEXT NOT NULL CHECK(role IN ('user','admin')),
       active INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL)''',
    '''CREATE TABLE sessions (token_hash TEXT PRIMARY KEY,
       user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
       csrf_token TEXT NOT NULL, expires INTEGER NOT NULL)''',
    '''CREATE TABLE login_attempts (id INTEGER PRIMARY KEY, username TEXT NOT NULL,
       address TEXT NOT NULL, attempted INTEGER NOT NULL)''',
    '''CREATE TABLE customers (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
       name TEXT NOT NULL, phone TEXT NOT NULL DEFAULT '', address TEXT NOT NULL DEFAULT '',
       notes TEXT NOT NULL DEFAULT '', created TEXT NOT NULL, updated TEXT NOT NULL)''',
    '''CREATE TABLE houses (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
       customer_id TEXT NOT NULL REFERENCES customers(id), name TEXT NOT NULL,
       address TEXT NOT NULL DEFAULT '', layout TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
       stocks TEXT NOT NULL DEFAULT '[]', settings TEXT NOT NULL DEFAULT '{}',
       glass_groups TEXT NOT NULL DEFAULT '{}', created TEXT NOT NULL, updated TEXT NOT NULL)''',
    '''CREATE TABLE windows (id TEXT PRIMARY KEY, owner_id TEXT REFERENCES users(id),
       house_id TEXT REFERENCES houses(id), name TEXT NOT NULL, floor TEXT NOT NULL DEFAULT '',
       room TEXT NOT NULL DEFAULT '', glass_material TEXT NOT NULL DEFAULT '默认玻璃',
       payload TEXT NOT NULL, stocks TEXT NOT NULL DEFAULT '[]', settings TEXT NOT NULL DEFAULT '{}',
       updated TEXT NOT NULL, CHECK ((owner_id IS NULL) = (house_id IS NULL)))''',
    'CREATE INDEX customers_owner ON customers(owner_id,updated)',
    'CREATE INDEX houses_parent ON houses(owner_id,customer_id,updated)',
    'CREATE INDEX windows_parent ON windows(owner_id,house_id,updated)',
    'CREATE INDEX sessions_user ON sessions(user_id)',
    'CREATE INDEX attempts_time ON login_attempts(attempted)',
]


def migrate(db):
    # 写锁使并发首次注册只执行一次迁移；失败时整笔回滚。
    db.execute('BEGIN IMMEDIATE')
    try:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version > 2:
            raise RuntimeError('数据库版本高于当前程序，请使用匹配版本，禁止降级写入')
        if version == 0:
            for statement in SCHEMA:
                db.execute(statement)
            legacy = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='projects'").fetchone()
            if legacy:
                db.execute('INSERT INTO windows(id,name,payload,updated) SELECT id,name,payload,updated FROM projects')
            db.execute('PRAGMA user_version=1')
        if version < 2:
            db.execute('ALTER TABLE houses ADD COLUMN custom_profiles INTEGER NOT NULL DEFAULT 0')
            db.execute('ALTER TABLE houses ADD COLUMN custom_glass INTEGER NOT NULL DEFAULT 0')
            db.execute('PRAGMA user_version=2')
        db.commit()
    except BaseException:
        db.rollback()
        raise


@contextmanager
def connect():
    path = Path(os.getenv('WINFRAME_DB', str(Path(__file__).resolve().parents[1] / 'data' / 'projects.db')))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=15000')
    try:
        migrate(db)
        with db:
            yield db
    finally:
        db.close()
