@echo off
echo ========================================
echo   Hatena Blog Suite - Restart
echo ========================================

echo.
echo [1/4] Killing old Flask processes (port 5000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":5000"') do (
    echo   Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo [2/4] Killing old Vite processes (port 5173)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":5173"') do (
    echo   Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 2 /nobreak >nul

echo [3/4] Starting Flask (background)...
start "Flask" cmd /c "cd /d %~dp0 && python app.py"

echo [4/4] Starting Vite (background)...
start "Vite" cmd /c "cd /d %~dp0\editor-ui && npm run dev"

echo.
echo ========================================
echo   Done! 
echo   Flask: http://127.0.0.1:5000
echo   Vite:  http://localhost:5173
echo ========================================
pause
