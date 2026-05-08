@echo off
setlocal EnableExtensions

title Agent Canvas Start

set "ROOT=%~dp0"
set "BACKEND_PORT=7860"
set "FRONTEND_PORT=5173"

echo ========================================
echo   Agent Canvas Start
echo ========================================
echo.

echo Gemma is not started by this script. Use your own Gemma button.
echo.

call :port_listening %BACKEND_PORT%
if errorlevel 1 (
    echo Starting backend: http://127.0.0.1:%BACKEND_PORT%
    start "Agent Canvas Backend" cmd /k "cd /d ""%ROOT%"" && python run.py serve --host 127.0.0.1 --port %BACKEND_PORT%"
) else (
    echo Backend already running on port %BACKEND_PORT%.
)

call :port_listening %FRONTEND_PORT%
if errorlevel 1 (
    echo Starting frontend: http://127.0.0.1:%FRONTEND_PORT%
    start "Agent Canvas Frontend" cmd /k "cd /d ""%ROOT%frontend"" && npm run dev"
) else (
    echo Frontend already running on port %FRONTEND_PORT%.
)

echo.
echo App URL:
echo   http://127.0.0.1:%FRONTEND_PORT%
echo.
echo TTS is separate. Run the TTS start script in this folder when needed.
echo.
timeout /t 3 >nul
start "" "http://127.0.0.1:%FRONTEND_PORT%"
pause
exit /b 0

:port_listening
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
exit /b %ERRORLEVEL%
