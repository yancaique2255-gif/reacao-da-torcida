@echo off
cd /d "%~dp0"
echo Cortando os gols anotados no painel da gravacao.
echo Para digitar os horarios na mao, use: python -m nucleo.esteira cortar --gols 21:37:00
python -u -m nucleo.esteira cortar
pause
