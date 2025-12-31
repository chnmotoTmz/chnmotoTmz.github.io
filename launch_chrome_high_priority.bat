@echo off
setlocal

:: Define Chrome path
set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME_PATH%" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

if not exist "%CHROME_PATH%" (
    echo Chrome not found at standard locations.
    echo Please edit this script to set the correct path.
    pause
    exit /b 1
)

echo Launching Chrome from: "%CHROME_PATH%"
echo With high priority flags...

start "" "%CHROME_PATH%" --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows --keep-alive-for-test

echo Done.
pause