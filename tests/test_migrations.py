"""迁移必须保留无主存档，不把它们分配给公开注册用户。"""
import json
import sqlite3
from backend.sample import sample_project


def test_legacy_migration_is_idempotent(tmp_path, monkeypatch):
    from backend.database import connect
    path = tmp_path / 'old.db'
    monkeypatch.setenv('WINFRAME_DB', str(path))
    payload = json.dumps(sample_project().model_dump(), ensure_ascii=False)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE projects (id TEXT PRIMARY KEY,name TEXT,payload TEXT,updated TEXT)')
        db.execute('INSERT INTO projects VALUES (?,?,?,?)', ('legacy', '旧窗型', payload, '2026-10-12'))
    for _ in range(2):
        with connect() as db:
            assert db.execute('SELECT payload FROM projects').fetchone()[0] == payload
            row = db.execute('SELECT owner_id,house_id,payload FROM windows WHERE id=?', ('legacy',)).fetchone()
            assert row['owner_id'] is None and row['house_id'] is None
            assert row['payload'] == payload
            assert db.execute('SELECT COUNT(*) FROM windows').fetchone()[0] == 1


def test_failed_migration_rolls_back_old_database(tmp_path, monkeypatch):
    import pytest
    from backend.database import connect
    path = tmp_path / 'broken.db'
    monkeypatch.setenv('WINFRAME_DB', str(path))
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE projects (id TEXT PRIMARY KEY,name TEXT,payload TEXT,updated TEXT)')
        db.execute("INSERT INTO projects VALUES ('old',NULL,'{}','2026-10-12')")
    with pytest.raises(sqlite3.IntegrityError):
        with connect():
            pass
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM projects').fetchone()[0] == 1
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [('projects',)]


def test_version_one_project_configuration_is_preserved(tmp_path,monkeypatch):
    from backend.database import connect, SCHEMA
    path=tmp_path/'version-one.db'
    monkeypatch.setenv('WINFRAME_DB',str(path))
    with sqlite3.connect(path) as db:
        for statement in SCHEMA:db.execute(statement)
        db.execute("INSERT INTO houses(id,owner_id,customer_id,name,stocks,created,updated) VALUES ('h','u','c','旧项目','[]','old','old')")
        db.execute('PRAGMA user_version=1')
    for _ in range(2):
        with connect() as db:
            row=db.execute("SELECT * FROM houses WHERE id='h'").fetchone()
            assert row['name']=='旧项目' and row['stocks']=='[]'
            assert row['custom_profiles']==row['custom_glass']==0
            assert db.execute('PRAGMA user_version').fetchone()[0]==2
