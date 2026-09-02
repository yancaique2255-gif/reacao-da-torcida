@echo off
cd /d "%~dp0"
set /p TIME_=Time da torcida escolhida:
set /p MANDANTE=Mandante:
set /p VISITANTE=Visitante:
python -m nucleo.esteira gravar "%TIME_%" "%MANDANTE%" "%VISITANTE%"
pause
