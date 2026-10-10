"""veFaaS 发布包启动入口。"""
import os
from pathlib import Path
import sys


def listen_port(environ):
    port = int(environ.get('_FAAS_RUNTIME_PORT') or environ.get('PORT') or '8000')
    if not 1024 <= port <= 65535 or port == 9990:
        raise ValueError('监听端口必须在 1024～65535 之间且不能为 9990')
    return port


def check_artifact(root):
    for relative in ['dist/index.html', 'backend/main.py', '.python/uvicorn/__init__.py']:
        if not (root / relative).is_file():
            raise RuntimeError(f'发布包缺少 {relative}，请先执行 sh build.sh 并选择 .vefaas/artifact 作为构建产物')


def main():
    root = Path(__file__).resolve().parent
    check_artifact(root)
    port = listen_port(os.environ)
    os.chdir(root)
    sys.path.insert(0, str(root / '.python'))
    # 未配置持久化时仅用于临时试部署，不能把 /tmp 当成业务存储。
    os.environ.setdefault('WINFRAME_DB', '/tmp/winframe/projects.db')
    import uvicorn
    print(f'窗序启动：0.0.0.0:{port}', flush=True)
    uvicorn.run('backend.main:app', host='0.0.0.0', port=port, workers=1)


if __name__ == '__main__':
    main()
