@echo off
REM Setup script for local DeepSeek via Ollama (Windows)
REM Downloads and installs Ollama, then pulls the smallest DeepSeek model

echo =========================================
echo Local DeepSeek Setup via Ollama
echo =========================================
echo.

REM Check if Ollama is already installed
where ollama >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo [OK] Ollama is already installed
    ollama --version
) else (
    echo Installing Ollama...
    echo Please download and install Ollama from: https://ollama.com/download/windows
    echo After installation, restart this script.
    pause
    exit /b 1
)

echo.
echo Starting Ollama service...
echo Note: On Windows, Ollama runs as a service automatically
timeout /t 3 /nobreak >nul

echo.
echo Downloading DeepSeek-R1:1.5B model (smallest available, ~1GB)...
echo This may take a few minutes depending on your connection.
echo.

REM Pull the smallest DeepSeek model
ollama pull deepseek-r1:1.5b

echo.
echo =========================================
echo Setup Complete!
echo =========================================
echo.
echo Model downloaded: deepseek-r1:1.5b
echo.
echo To use local DeepSeek in your application:
echo   1. Set in your .env file:
echo      RUN_LOCAL=true
echo.
echo   2. Or set before running:
echo      set RUN_LOCAL=true
echo.
echo   3. Ensure Ollama is running (should start automatically)
echo.
echo   4. Test the model:
echo      ollama run deepseek-r1:1.5b "Hello, world!"
echo.
echo Optional environment variables:
echo   LOCAL_DEEPSEEK_MODEL=deepseek-r1:1.5b
echo   LOCAL_DEEPSEEK_URL=http://localhost:11434
echo.

REM Test the model
echo Testing model availability...
ollama list | findstr "deepseek-r1:1.5b" >nul
if %ERRORLEVEL% == 0 (
    echo [OK] Model is available and ready to use
) else (
    echo [WARNING] Model not found. Try: ollama pull deepseek-r1:1.5b
)

echo.
echo Done!
pause
