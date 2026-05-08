@echo off
setlocal EnableExtensions

title IndexTTS WebUI Start

set "ROOT=%~dp0"
set "TTS_ROOT=%ROOT%index-tts"
set "TTS_PYTHON=%TTS_ROOT%\.venv\Scripts\python.exe"
set "TTS_WEBUI=%TTS_ROOT%\webui.py"
set "TTS_PORT=7861"

echo ========================================
echo   IndexTTS WebUI Start
echo ========================================
echo.

call :port_listening %TTS_PORT%
if not errorlevel 1 (
    echo IndexTTS WebUI already running on port %TTS_PORT%.
    start "" "http://127.0.0.1:%TTS_PORT%"
    pause
    exit /b 0
)

if not exist "%TTS_ROOT%" (
    echo ERROR: IndexTTS root not found:
    echo   %TTS_ROOT%
    pause
    exit /b 1
)

if not exist "%TTS_PYTHON%" (
    echo ERROR: IndexTTS venv Python not found:
    echo   %TTS_PYTHON%
    pause
    exit /b 1
)

if not exist "%TTS_WEBUI%" (
    echo ERROR: webui.py not found:
    echo   %TTS_WEBUI%
    pause
    exit /b 1
)

if not exist "%TTS_ROOT%\checkpoints\config.yaml" (
    echo ERROR: IndexTTS model config not found:
    echo   %TTS_ROOT%\checkpoints\config.yaml
    pause
    exit /b 1
)

echo Starting IndexTTS WebUI: http://127.0.0.1:%TTS_PORT%
echo.
start "IndexTTS WebUI" cmd /k "cd /d ""%TTS_ROOT%"" && ""%TTS_PYTHON%"" webui.py --host 127.0.0.1 --port %TTS_PORT% --model_dir checkpoints --fp16"

timeout /t 8 >nul
start "" "http://127.0.0.1:%TTS_PORT%"
pause
exit /b 0

:port_listening
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
exit /b %ERRORLEVEL%
