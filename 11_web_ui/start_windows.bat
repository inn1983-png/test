@echo off
chcp 65001 >nul
cd /d %~dp0\..

echo 正在启动 AI Drama 00-06 测试控制台...
echo.

if "%AI_DRAMA_LLM_BASE_URL%"=="" (
  set "AI_DRAMA_LLM_BASE_URL=http://127.0.0.1:8000/v1/chat/completions"
)

if "%AI_DRAMA_LLM_MODEL%"=="" (
  echo 请输入你的本地 LLM 模型名。
  echo 例如：gemma-4-31b-it-q4 / gemma-3-27b / local-model
  set /p AI_DRAMA_LLM_MODEL=AI_DRAMA_LLM_MODEL: 
)

if "%AI_DRAMA_LLM_MODEL%"=="" (
  echo.
  echo [错误] AI_DRAMA_LLM_MODEL 不能为空。
  echo 请重新运行本脚本，并输入你的本地模型名。
  pause
  exit /b 1
)

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
