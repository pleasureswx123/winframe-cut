#!/bin/sh
# 发布包根目录启动；不在实例冷启动时安装依赖。
set -eu
cd "$(dirname "$0")"
exec python start_vefaas.py
