@echo off
cd /d "%~dp0"
if not exist "dados\canais.json" copy /Y "dados\canais.exemplo.json" "dados\canais.json" >nul
echo Escolha no YouTube as lives com mais visualizacoes.
echo Cole as URLs exatas em dados\canais.json e marque ativo como true.
notepad "dados\canais.json"
set /p TIME_=Time da torcida (ex: cruzeiro):
python -m nucleo.esteira canais "%TIME_%"
pause
