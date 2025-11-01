@echo off

cd xls2cfg

xls2cfg.exe --config=config-server.json --onlyExportChange
xls2cfg.exe --config=config-client.json --onlyExportChange
@REM python xls2cfg.py --config=config-server.json --onlyExportChange
@REM python xls2cfg.py --config=config-client.json --onlyExportChange
pause