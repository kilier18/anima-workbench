@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "DIR=%~dp0"
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

set "TARGET=%DIR%"
if not "%~2"=="" set "TARGET=%~2"

set "PS=powershell.exe"
where pwsh >nul 2>&1 && set "PS=pwsh.exe"

if "%~1"=="" (
  "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Dir "%TARGET%"
) else (
  "%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Dir "%TARGET%" -Only %~1
)

if errorlevel 1 (
  echo.
  echo  Installer returned an error. Please send the output above.
  pause
)
exit /b 0
