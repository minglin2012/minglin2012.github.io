#!/usr/bin/env bash
# 博客发布一次性脚本（reasonix run）——委托给 blog-publish.py，统一内容+确定性 git 逻辑。
# 用法: bash blog-publish.sh <草稿路径> [--force]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$SCRIPT_DIR/blog-publish.py" "$@"
