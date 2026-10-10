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
