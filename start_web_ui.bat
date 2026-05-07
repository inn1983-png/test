@echo off
chcp 65001 >nul
cd /d %~dp0

if "%AI_DRAMA_WEB_UI_HOST%"=="" set "AI_DRAMA_WEB_UI_HOST=127.0.0.1"
if "%AI_DRAMA_WEB_UI_PORT%"=="" set "AI_DRAMA_WEB_UI_PORT=1144"
if "%AI_DRAMA_LLM_BASE_URL%"=="" set "AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8080/v1/chat/completions"
if "%AI_DRAMA_LLM_MODEL%"=="" set "AI_DRAMA_LLM_MODEL=gemma-4-31B-it-Q4_K_M.gguf"
if "%AI_DRAMA_LLM_TEMPERATURE%"=="" set "AI_DRAMA_LLM_TEMPERATURE=0.1"
if "%AI_DRAMA_LLM_TIMEOUT_SEC%"=="" set "AI_DRAMA_LLM_TIMEOUT_SEC=6000"

echo 启动 AI 短剧工厂 Web UI...
echo 地址: http://%AI_DRAMA_WEB_UI_HOST%:%AI_DRAMA_WEB_UI_PORT%
echo LLM: %AI_DRAMA_LLM_BASE_URL%
echo MODEL: %AI_DRAMA_LLM_MODEL%
echo TEMP: %AI_DRAMA_LLM_TEMPERATURE%
echo TIMEOUT: %AI_DRAMA_LLM_TIMEOUT_SEC%
echo.

python start_web_ui.py
pause
