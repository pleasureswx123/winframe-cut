#!/bin/sh
# 使用平台的 Python 3.12，构建独立发布包。
set -eu
cd "$(dirname "$0")"
exec python scripts/build_vefaas.py
