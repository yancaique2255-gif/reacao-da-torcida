@echo off
cd /d "%~dp0"
set /p JOGO=Pasta do jogo: 
python -m nucleo.monitor "%JOGO%"
