@echo off
chcp 65001 >nul
rem 安装目录由本脚本位置推导（_setup 的上一级）；换盘不用改
for %%i in ("%~dp0..") do set "ROOT=%%~fi"
set "PY=%ROOT%\ComfyUI_windows_portable\python_embeded\python.exe"
cd /d "%ROOT%\webui"
"%PY%" -u assistant.py > "%ROOT%\webui\assistant.log" 2> "%ROOT%\webui\assistant.err.log"
exit /b %ERRORLEVEL%
