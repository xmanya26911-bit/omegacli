@echo off
title OMEGA Web Server
echo.
echo ? Starting OMEGA Web Server...
echo.
start /B python D:\TERMINALCLI\omega\omega_server.py
timeout /t 2 /nobreak >nul
echo ? Server running at: http://192.168.1.3:8080
echo ? From laptop:     http://192.168.1.3:8080
echo.
pause
