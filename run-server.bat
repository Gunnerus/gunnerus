@echo off
SET venvpython=..\env\Scripts\python.exe
title Reserver Dev Server 

:START:
echo Checking for model changes and migrations
%venvpython% manage.py makemigrations | find /i "No changes detected"
if errorlevel 1 (
	echo.
	echo Migrations made, press any key to apply
	pause
	%venvpython% manage.py migrate
)

echo.
echo Starting server
%venvpython% manage.py runserver

echo.
echo Server stopped or crashed, press any key to restart
pause
goto:START