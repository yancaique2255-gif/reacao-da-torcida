@echo off
cd /d "%~dp0"
set /p JOGO=Pasta do jogo:
start "" http://127.0.0.1:8770
python -m nucleo.esteira estudio "%JOGO%"
