@echo off
chcp 65001 >nul 2>&1
title Stock Research System

echo ============================================
echo   Stock Research System - One-Click Start
echo ============================================
echo.

:: ---- Configuration ----
set BACKEND_PORT=8003
set FRONTEND_PORT=5173
set BACKEND_DIR=%~dp0backend
set FRONTEND_DIR=%~dp0frontend
set BACKEND_PID_FILE=%~dp0.backend.pid
set FRONTEND_PID_FILE=%~dp0.frontend.pid

:: ---- Kill any existing processes on these ports ----
echo [1/5] Checking for existing processes...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    echo       Killing existing backend process (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    echo       Killing existing frontend process (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: ---- Start Backend ----
echo [2/5] Starting backend (port %BACKEND_PORT%)...
cd /d "%BACKEND_DIR%"
start /B "" cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% 2>&1"
for /f "tokens=2" %%i in ('tasklist /fi "WINDOWTITLE eq " /fo csv /nh 2^>nul ^| findstr /i "python"') do (
    echo %%i> "%BACKEND_PID_FILE%"
)

:: ---- Wait for Backend to be ready ----
echo [3/5] Waiting for backend to be ready...
set RETRY=0
:wait_backend
set /a RETRY+=1
if %RETRY% gtr 30 (
    echo       ERROR: Backend failed to start within 30 seconds.
    echo       Please check backend logs.
    pause
    exit /b 1
)
curl -s http://localhost:%BACKEND_PORT%/api/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_backend
)
echo       Backend is ready!

:: ---- Start Frontend ----
echo [4/5] Starting frontend (port %FRONTEND_PORT%)...
cd /d "%FRONTEND_DIR%"
start /B "" cmd /c "npm run dev 2>&1"

:: ---- Wait for Frontend to be ready ----
echo [5/5] Waiting for frontend to be ready...
set RETRY=0
:wait_frontend
set /a RETRY+=1
if %RETRY% gtr 30 (
    echo       ERROR: Frontend failed to start within 30 seconds.
    echo       Please check frontend logs.
    pause
    exit /b 1
)
curl -s http://localhost:%FRONTEND_PORT%/ >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_frontend
)
echo       Frontend is ready!

:: ---- Open Browser ----
echo.
echo ============================================
echo   All services started successfully!
echo.
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo   Backend:  http://localhost:%BACKEND_PORT%
echo ============================================
echo.
echo   Press any key to STOP all services...
echo.

start http://localhost:%FRONTEND_PORT%

:: ---- Wait for user to press a key ----
pause >nul

:: ---- Cleanup ----
echo.
echo Stopping services...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
del "%BACKEND_PID_FILE%" >nul 2>&1
del "%FRONTEND_PID_FILE%" >nul 2>&1
echo All services stopped.
timeout /t 2 /nobreak >nul
