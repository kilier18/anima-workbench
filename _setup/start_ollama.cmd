@echo off
chcp 65001 >nul
set "OLLAMA_HOST=127.0.0.1:11435"
set "OLLAMA_MODELS=D:\ollama-models"
"C:\Users\pinn\AppData\Local\Programs\Ollama\ollama.exe" serve > "D:\ComfyUI\_setup\ollama.log" 2> "D:\ComfyUI\_setup\ollama.err.log"
