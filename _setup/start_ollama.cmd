@echo off
chcp 65001 >nul
set "OLLAMA_HOST=127.0.0.1:11435"
set "ROOT=%~dp0.."
set "OLLAMA_MODELS=%ROOT%\..\ollama-models"
set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA_EXE%" set "OLLAMA_EXE=ollama"
"%OLLAMA_EXE%" serve > "%ROOT%\_setup\ollama.log" 2> "%ROOT%\_setup\ollama.err.log"
