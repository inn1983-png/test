@echo off
chcp 65001 >nul
cd /d %~dp0\..

echo 正在启动 AI Drama 00-06 测试控制台...
echo.

if "%AI_DRAMA_LLM_BASE_URL%"=="" (
  set "AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8080/v1/chat/completions"
)

if "%AI_DRAMA_LLM_MODEL%"=="" set "AI_DRAMA_LLM_MODEL=gemma-4-31B-it-Q4_K_M.gguf"
if "%AI_DRAMA_LLM_TEMPERATURE%"=="" set "AI_DRAMA_LLM_TEMPERATURE=0.1"
if "%AI_DRAMA_LLM_TIMEOUT_SEC%"=="" set "AI_DRAMA_LLM_TIMEOUT_SEC=240"
if "%AI_DRAMA_UI_PORT%"=="" set "AI_DRAMA_UI_PORT=1144"

echo.
echo 当前配置：
echo AI_DRAMA_LLM_BASE_URL=%AI_DRAMA_LLM_BASE_URL%
echo AI_DRAMA_LLM_MODEL=%AI_DRAMA_LLM_MODEL%
echo AI_DRAMA_LLM_TEMPERATURE=%AI_DRAMA_LLM_TEMPERATURE%
echo AI_DRAMA_LLM_TIMEOUT_SEC=%AI_DRAMA_LLM_TIMEOUT_SEC%
echo AI_DRAMA_UI_PORT=%AI_DRAMA_UI_PORT%
echo.
echo 请确认你的本地 LLM 服务已经启动。
echo.

python 11_web_ui\app.py
pause
