#!/usr/bin/env bash
# 博客发布一次性脚本（smolagents 版）——委托给 blog-publish-smol.py。
# 用法: ./blog-publish-smol.sh <草稿路径> [--force] [--dry-run | --dry-run-agent]
set -euo pipefail
export PYTHONUTF8=1
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$DIR/../.venv/Scripts/python.exe"
if [ -x "$VENV_PY" ]; then
  exec "$VENV_PY" "$DIR/blog-publish-smol.py" "$@"
else
  exec python "$DIR/blog-publish-smol.py" "$@"
fi
