@echo off
cd /d "%~dp0"
echo.
echo Cole as URLs das lives, separadas por espaco, e diga de que torcida sao.
echo Rode uma vez por torcida. Exemplo:
echo   python -m nucleo.esteira canais santos-x-palmeiras --torcida santos --importar URL1 URL2
echo.
set /p TIME_=Nome do jogo (ex: santos-x-palmeiras): 
set /p TORCIDA=Torcida deste lote (vazio = neutro): 
set /p URLS=Cole as URLs: 
python -u -m nucleo.esteira canais "%TIME_%" --torcida "%TORCIDA%" --importar %URLS%
pause
