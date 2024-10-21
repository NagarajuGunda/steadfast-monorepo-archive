@echo off
setlocal enabledelayedexpansion

REM
cd steadfast-app
echo Installing app dependencies...
call npm install
if !errorlevel! neq 0 (
    echo Error occurred while installing app dependencies.
    goto :error
)
cd ..

REM
cd steadfast-api
echo Installing API dependencies...
call npm install
if !errorlevel! neq 0 (
    echo Error occurred while installing API dependencies.
    goto :error
)
cd ..

REM 
cd steadfast-websocket
echo Installing WebSocket...
echo Installing Flattrade dependencies...
cd flattrade
call pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo Error occurred while installing WebSocket dependencies for Flattrade.
    goto :error
)
cd ..

echo Installing Shoonya dependencies...
cd shoonya
call pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo Error occurred while installing WebSocket dependencies for Shoonya.
    goto :error
)
cd ..\..

echo Repositories cloned and dependencies installed successfully.
goto :end

:error
echo An error occurred. Please check the output above for details.

:end
pause
endlocal