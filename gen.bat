@echo off

del /q /s output\client
del /q /s output\server

cd xls2cfg
@REM xls2cfg.exe --config=config-server.json
@REM xls2cfg.exe --config=config-client.json
python xls2cfg.py --config=config-server.json
python xls2cfg.py --config=config-client.json

pause