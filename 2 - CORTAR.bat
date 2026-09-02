@echo off
cd /d "%~dp0"
set /p JOGO=Pasta do jogo:
echo Informe o horario exato em que a reacao aparece na gravacao.
set /p GOLS=Horarios separados por espaco (ex: 21:37:00 22:05:30):
python -m nucleo.esteira cortar "%JOGO%" --gols %GOLS%
pause
