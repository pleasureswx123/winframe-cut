"""本机项目存档，SQLite 事务写入；路径不接受用户输入。"""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4


def connect():
    path=Path(os.getenv('WINFRAME_DB', str(Path(__file__).resolve().parents[1]/'data'/'projects.db')))
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, payload TEXT NOT NULL, updated TEXT NOT NULL)')
    return db


def list_projects():
    with connect() as db:
        return [dict(id=r[0],name=r[1],updated=r[2]) for r in db.execute('SELECT id,name,updated FROM projects ORDER BY updated DESC')]


def save_project(project, id=None):
    id=id or uuid4().hex;updated=datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute('INSERT INTO projects VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,payload=excluded.payload,updated=excluded.updated',
            (id,project.name,json.dumps(project.model_dump(),ensure_ascii=False),updated))
    return dict(id=id,name=project.name,updated=updated)


def read_project(id):
    with connect() as db:
        row=db.execute('SELECT payload FROM projects WHERE id=?',(id,)).fetchone()
        return json.loads(row[0]) if row else None
