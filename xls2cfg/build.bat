@echo off

pyinstaller -F ./xls2cfg.py --path=. --log-level=DEBUG
copy /y dist\xls2cfg.exe .
rmdir /S /Q dist
rmdir /S /Q build
del xls2cfg.spec

pause