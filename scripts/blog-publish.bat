@echo off
REM 博客发布一次性脚本（reasonix run）——委托给 blog-publish.py，统一内容+确定性 git 逻辑。
REM 用法: blog-publish.bat <草稿路径> [--force]
setlocal
set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%blog-publish.py" %*
exit /b %ERRORLEVEL%
