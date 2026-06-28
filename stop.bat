@echo off
chcp 65001 >nul 2>&1
echo Stopping Stock Research System...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8003" ^| findstr "LISTENING"') do (
    echo   Stopping backend (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo   Stopping frontend (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

echo Done.
timeout /t 1 /nobreak >nul
