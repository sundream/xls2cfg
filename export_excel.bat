@echo off

del /q /s ExcelOutputClient
del /q /s ExcelOutputServer

cd xls2cfg
xls2cfg.exe --config=config-server.json
xls2cfg.exe --config=config-client.json
@REM python xls2cfg.py --config=config-server.json
@REM python xls2cfg.py --config=config-client.json

pause