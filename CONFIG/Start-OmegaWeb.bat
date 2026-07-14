@echo off
title OMEGA Web Server
cd /d "%~dp0"
echo.
echo ? Starting OMEGA Web Server...
echo.
start /B python omega_server.py
timeout /t 2 /nobreak >nul
echo ? Server running at: http://localhost:8080
echo ? Open in any browser on any device on this network.
echo.
pause
