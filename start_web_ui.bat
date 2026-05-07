@echo off
chcp 65001 >nul
cd /d %~dp0

if "%AI_DRAMA_WEB_UI_HOST%"=="" set "AI_DRAMA_WEB_UI_HOST=127.0.0.1"
if "%AI_DRAMA_WEB_UI_PORT%"=="" set "AI_DRAMA_WEB_UI_PORT=1144"

echo 启动 AI 短剧工厂 Web UI...
echo 地址: http://%AI_DRAMA_WEB_UI_HOST%:%AI_DRAMA_WEB_UI_PORT%
echo.

python start_web_ui.py
pause
