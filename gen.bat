@echo off

if exist Output\Server rmdir /S /Q Output\Server
if exist Output\Client rmdir /S /Q Output\Client

cd xls2cfg
xls2cfg.exe --config=config-server.json
@REM python xls2cfg.py --config=config-server.json
if %errorlevel% neq 0 (
    pause
    exit /b %errorlevel%
)
xls2cfg.exe --config=config-client.json
@REM python xls2cfg.py --config=config-client.json
if %errorlevel% neq 0 (
    pause
    exit /b %errorlevel%
)
cd ..