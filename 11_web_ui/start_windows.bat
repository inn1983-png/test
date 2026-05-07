@echo off
chcp 65001 >nul
cd /d %~dp0\..
echo 正在启动 AI Drama 00-06 测试控制台...
echo.
python 11_web_ui\app.py
pause
