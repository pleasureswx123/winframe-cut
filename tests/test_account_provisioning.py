"""账号必须由管理平台发放，默认管理员初始化不能覆盖已有密码。"""
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import verify_password
from backend.database import connect


def test_admin_bootstrap_and_account_provisioning(tmp_path, monkeypatch):
    monkeypatch.setenv('WINFRAME_DB', str(tmp_path / 'accounts.db'))
    with TestClient(app) as client:
        credentials = dict(username='worker-one', password='Worker-12345', display_name='制作用户')
        assert client.post('/api/auth/register', json=credentials).status_code == 403
        assert client.post('/api/admin/users', json=credentials).status_code == 401
        result = client.post('/api/auth/login', json=dict(username='admin', password='admin123'))
        assert result.status_code == 200
        client.headers['X-CSRF-Token'] = result.json()['csrf_token']
        assert result.json()['user']['role'] == 'admin'
        assert client.post('/api/admin/users', json={**credentials, 'role':'admin'}).status_code == 422
        assert client.post('/api/admin/users', json=credentials).status_code == 201
        assert client.post('/api/admin/users', json=credentials).status_code == 409
        client.post('/api/auth/logout')
        result = client.post('/api/auth/login', json=dict(username='worker-one', password='Worker-12345'))
        assert result.status_code == 200
        client.headers['X-CSRF-Token'] = result.json()['csrf_token']
        assert client.post('/api/admin/users', json=dict(username='blocked', password='Worker-12345')).status_code == 403
    with connect() as db:
        row = db.execute("SELECT password_hash FROM users WHERE username='admin'").fetchone()
        assert verify_password('admin123', row['password_hash'])
        db.execute("UPDATE users SET display_name='保留名称' WHERE username='admin'")
    with TestClient(app) as client:
        with connect() as db:
            assert db.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 1
            assert db.execute("SELECT display_name FROM users WHERE username='admin'").fetchone()[0] == '保留名称'
