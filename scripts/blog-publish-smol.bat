@echo off
REM 博客发布一次性脚本（smolagents 版）——委托给 blog-publish-smol.py，统一内容+确定性 git 逻辑。
REM 用法: blog-publish-smol.bat <草稿路径> [--force] [--dry-run | --dry-run-agent]
REM 与 blog-publish.bat 的区别: 本脚本依赖仓库 .venv 中的 smolagents/litellm，故优先用 venv 的 python。
setlocal
set "PYTHONUTF8=1"
set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%~dp0..\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
  "%VENV_PY%" "%SCRIPT_DIR%blog-publish-smol.py" %*
) else (
  python "%SCRIPT_DIR%blog-publish-smol.py" %*
)
exit /b %ERRORLEVEL%
