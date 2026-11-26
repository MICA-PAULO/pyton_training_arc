@echo off
rem Dubbelklik op dit bestand om de DOSI-scraper te starten.
rem Instellingen aanpassen? Open instellingen.toml in Kladblok of VS Code.

cd /d "%~dp0"
chcp 65001 >nul

where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

%PY% --version >nul 2>nul
if errorlevel 1 (
    echo Python is niet gevonden. Installeer Python via https://www.python.org/downloads/
    echo Vink tijdens de installatie "Add python.exe to PATH" aan.
    pause
    exit /b 1
)

echo Benodigde modules controleren...
%PY% -m pip install -q -r requirements.txt
%PY% -m dosi_scraper %*

echo.
pause
