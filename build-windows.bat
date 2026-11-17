@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0build-windows.ps1" (
    echo The Windows build script is missing: build-windows.ps1
    echo Extract the entire repository folder before building.
    echo.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-windows.ps1"
set "BUILD_EXIT=%ERRORLEVEL%"

if not "%BUILD_EXIT%"=="0" (
    echo.
    echo The build failed. See build-log.txt for details.
    pause
)

exit /b %BUILD_EXIT%
