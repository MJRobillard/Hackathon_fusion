@echo off
REM Helper script to run AONP commands in WSL
REM Usage: run_in_wsl.bat <command>

echo ========================================
echo Running in WSL (Ubuntu)
echo ========================================

REM Get the current directory path for WSL
set "CURRENT_DIR=%CD%"
set "WSL_PATH=/mnt/c/%CURRENT_DIR:C:\=%"
set "WSL_PATH=%WSL_PATH:\=/%"

if "%1"=="" (
    echo Usage: run_in_wsl.bat [command]
    echo.
    echo Examples:
    echo   run_in_wsl.bat test-core       - Run core tests
    echo   run_in_wsl.bat test-full       - Run full acceptance tests
    echo   run_in_wsl.bat quick-start     - Run quick start demo
    echo   run_in_wsl.bat install         - Install dependencies in WSL
    echo   run_in_wsl.bat check-openmc    - Check OpenMC installation
    echo   run_in_wsl.bat shell           - Open WSL shell in project dir
    exit /b 1
)

if "%1"=="test-core" (
    wsl -e bash -c "cd '%WSL_PATH%' && python3 tests/test_core_only.py"
    exit /b %ERRORLEVEL%
)

if "%1"=="test-full" (
    wsl -e bash -c "cd '%WSL_PATH%' && python3 tests/test_acceptance.py"
    exit /b %ERRORLEVEL%
)

if "%1"=="quick-start" (
    wsl -e bash -c "cd '%WSL_PATH%' && python3 quick_start.py"
    exit /b %ERRORLEVEL%
)

if "%1"=="install" (
    wsl -e bash -c "cd '%WSL_PATH%' && bash setup_linux.sh"
    exit /b %ERRORLEVEL%
)

if "%1"=="check-openmc" (
    wsl -e bash -c "python3 -c 'import openmc; print(f\"OpenMC {openmc.__version__} installed\")' 2>&1 || echo 'OpenMC not installed'"
    exit /b %ERRORLEVEL%
)

if "%1"=="shell" (
    wsl -e bash -c "cd '%WSL_PATH%' && exec bash"
    exit /b %ERRORLEVEL%
)

REM Default: run custom command
wsl -e bash -c "cd '%WSL_PATH%' && %*"

