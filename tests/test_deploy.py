"""发布包启动检查，不依赖云平台。"""
import importlib.util
from pathlib import Path

import pytest


def launcher():
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'start_vefaas.py'
    spec = importlib.util.spec_from_file_location('start_vefaas', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_platform_port_precedes_generic_port():
    module = launcher()
    assert module.listen_port({'_FAAS_RUNTIME_PORT': '8123', 'PORT': '9000'}) == 8123
    assert module.listen_port({'PORT': '8124'}) == 8124
    assert module.listen_port({}) == 8000


@pytest.mark.parametrize('value', ['abc', '0', '65536', '9990'])
def test_invalid_port_rejected(value):
    with pytest.raises(ValueError):
        launcher().listen_port({'_FAAS_RUNTIME_PORT': value})


def test_incomplete_artifact_rejected(tmp_path):
    with pytest.raises(RuntimeError, match='构建'):
        launcher().check_artifact(tmp_path)


def test_dependency_install_ignores_platform_package_sources(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'build_vefaas.py'
    spec = importlib.util.spec_from_file_location('build_vefaas', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv('PIP_INDEX_URL', 'https://invalid.example/simple')
    monkeypatch.setenv('PIP_EXTRA_INDEX_URL', 'https://invalid.example/extra')
    monkeypatch.setenv('UV_DEFAULT_INDEX', 'https://invalid.example/uv')
    calls = []
    monkeypatch.setattr(module, 'run', lambda args, **kwargs: calls.append((args, kwargs)))
    module.install_dependencies(tmp_path)
    args, options = calls[0]
    assert args[:5] == [module.sys.executable, '-m', 'pip', '--isolated', 'install']
    assert args[args.index('--index-url') + 1] == 'https://pypi.org/simple'
    assert args[args.index('--target') + 1] == str(tmp_path / '.python')
    assert options['env']['PIP_CONFIG_FILE'] == module.os.devnull
    assert not any(key.startswith(('PIP_', 'UV_')) for key in options['env'] if key != 'PIP_CONFIG_FILE')
