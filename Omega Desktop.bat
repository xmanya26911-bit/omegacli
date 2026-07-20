@echo off
title Ω OMEGA Desktop

:: Launch the Omega Desktop app
:: Requires the Tauri build to be completed first

set "APP_DIR=%~dp0apps\desktop"
set "TAURI_EXE=%APP_DIR%\src-tauri\target\release\Omega.exe"

if exist "%TAURI_EXE%" (
    start "" "%TAURI_EXE%"
) else (
    echo [Ω] Desktop app not built yet.
    echo [Ω] Run: cd apps\desktop ^&^& npx tauri build --ci
    echo.
    pause
)
