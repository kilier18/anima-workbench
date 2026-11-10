@echo off
chcp 65001 >nul
set "PY=D:\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe"
cd /d "D:\ComfyUI\webui"
"%PY%" -u assistant.py > "D:\ComfyUI\webui\assistant.log" 2> "D:\ComfyUI\webui\assistant.err.log"
exit /b %ERRORLEVEL%
