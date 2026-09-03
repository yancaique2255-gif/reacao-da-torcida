@echo off
cd /d "%~dp0"
set /p TIME_=Nome do jogo no cadastro: 
set /p MANDANTE=Mandante: 
set /p VISITANTE=Visitante: 
echo.
echo Liga para acompanhar o placar (ENTER = nao acompanhar):
echo   copa-do-brasil   brasileirao   supercopa
set /p LIGA=Liga: 
if "%LIGA%"=="" (
  python -u -m nucleo.esteira gravar "%TIME_%" "%MANDANTE%" "%VISITANTE%"
) else (
  python -u -m nucleo.esteira gravar "%TIME_%" "%MANDANTE%" "%VISITANTE%" --liga "%LIGA%"
)
pause
