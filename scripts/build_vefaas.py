"""在 Linux Python 3.12 中构建包含静态页面和依赖的独立发布包。"""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
NODE_VERSION = '24.14.1'


def run(args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def node_environment(work):
    env = os.environ.copy()
    # 复用满足 Vite 要求的构建环境；没有 Node 时从官方获取固定版本。
    if shutil.which('node') and shutil.which('npm'):
        version = subprocess.check_output(['node', '-p', 'process.versions.node'], text=True).strip()
        major, minor, *_ = map(int, version.split('.'))
        if (major == 22 and minor >= 12) or major >= 24:
            return env
    arch = {'x86_64': 'x64', 'aarch64': 'arm64'}.get(platform.machine())
    if not arch:
        raise RuntimeError('当前构建 CPU 架构不受支持')
    name = f'node-v{NODE_VERSION}-linux-{arch}'
    filename = f'{name}.tar.gz'
    base = f'https://nodejs.org/dist/v{NODE_VERSION}/'
    print(f'下载前端构建工具：{filename}', flush=True)
    with urlopen(base + 'SHASUMS256.txt', timeout=120) as response:
        checksums = dict((parts[1], parts[0]) for line in response.read().decode().splitlines() if (parts := line.split()))
    archive = work / filename
    with urlopen(base + filename, timeout=120) as response, archive.open('wb') as dest:
        shutil.copyfileobj(response, dest)
    with archive.open('rb') as source:
        actual_checksum = hashlib.file_digest(source, 'sha256').hexdigest()
    if actual_checksum != checksums[filename]:
        raise RuntimeError('Node.js 下载校验失败')
    with tarfile.open(archive) as bundle:
        bundle.extractall(work, filter='data')
    env['PATH'] = str(work / name / 'bin') + os.pathsep + env['PATH']
    return env


def main():
    if platform.system() != 'Linux' or sys.version_info[:2] != (3, 12):
        raise RuntimeError('请在 Linux Python 3.12 构建环境运行；不要上传 Windows 虚拟环境')
    destination = ROOT / '.vefaas' / 'artifact'
    destination.parent.mkdir(exist_ok=True)
    # 临时目录隔离 npm 安装，不使用开发机已有的 node_modules 或业务数据。
    with tempfile.TemporaryDirectory(prefix='winframe-build-') as folder:
        work = Path(folder)
        frontend = work / 'frontend'
        frontend.mkdir()
        for name in ['package.json', 'package-lock.json', 'tsconfig.json', 'vite.config.ts', 'index.html']:
            shutil.copy2(ROOT / name, frontend / name)
        for name in ['src', 'public']:
            shutil.copytree(ROOT / name, frontend / name)
        env = node_environment(work)
        run(['npm', 'ci', '--include=dev', '--no-audit', '--no-fund'], cwd=frontend, env=env)
        run(['npm', 'run', 'build'], cwd=frontend, env=env)
        artifact = work / 'artifact'
        artifact.mkdir()
        shutil.copytree(frontend / 'dist', artifact / 'dist')
        shutil.copytree(ROOT / 'backend', artifact / 'backend', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copy2(ROOT / 'run.sh', artifact / 'run.sh')
        (artifact / 'run.sh').chmod(0o755)
        shutil.copy2(ROOT / 'scripts/start_vefaas.py', artifact / 'start_vefaas.py')
        shutil.copy2(ROOT / 'requirements.lock.txt', artifact / 'requirements.lock.txt')
        # --target 把依赖包含在产物中，避免依赖构建机系统安装目录。
        installer = ['uv', 'pip', 'install', '--python', sys.executable] if shutil.which('uv') else [sys.executable, '-m', 'pip', 'install']
        run(installer + ['--target', str(artifact / '.python'), '-r', str(ROOT / 'requirements.lock.txt')])
        check_env = os.environ.copy()
        check_env['PYTHONPATH'] = str(artifact / '.python')
        run([sys.executable, '-c', 'import backend.main, uvicorn; from backend.sample import sample_project; from backend.geometry import calculate; assert calculate(sample_project())["count"] == 61'], cwd=artifact, env=check_env)
        # 只替换此脚本专用的生成目录，不接触 data、dist 或用户文件。
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(artifact, destination)
    print('构建完成：产物路径 .vefaas/artifact；启动命令 sh run.sh', flush=True)


if __name__ == '__main__':
    main()
