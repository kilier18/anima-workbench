@echo off
chcp 65001 >nul
rem 安装目录由本脚本位置推导（_setup 的上一级）；换盘不用改
for %%i in ("%~dp0..") do set "ROOT=%%~fi"
set "PY=%ROOT%\ComfyUI_windows_portable\python_embeded\python.exe"

rem Output dir follows webui\data\wb_config.json (page button: gear -> dir)
set "OUTDIR="
"%PY%" "%ROOT%\_setup\get_outdir.py" > "%TEMP%\wb_outdir.txt" 2>nul
if exist "%TEMP%\wb_outdir.txt" (
  set /p OUTDIR=<"%TEMP%\wb_outdir.txt"
  del "%TEMP%\wb_outdir.txt" >nul 2>&1
)
if not defined OUTDIR set "OUTDIR=%ROOT%\output"
if not exist "%OUTDIR%" mkdir "%OUTDIR%" 2>nul

cd /d "%ROOT%\ComfyUI_windows_portable\ComfyUI"
"%PY%" -s main.py --windows-standalone-build --lowvram --use-pytorch-cross-attention --preview-method none --port 8188 --listen 127.0.0.1 --output-directory "%OUTDIR%" --extra-model-paths-config "%ROOT%\extra_model_paths.yaml" > "%ROOT%\_setup\comfy.log" 2> "%ROOT%\_setup\comfy.err.log"
exit /b %ERRORLEVEL%
