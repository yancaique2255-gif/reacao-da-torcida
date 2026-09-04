@echo off
cd /d "%~dp0"
echo.
echo Cole as URLs das lives, separadas por espaco, e diga de que torcida sao.
echo Rode uma vez por torcida. Exemplo:
echo   python -m nucleo.esteira canais santos-x-palmeiras --torcida santos --importar URL1 URL2
echo.
set /p TIME_=Nome do jogo (ex: santos-x-palmeiras): 
:torcida
set "TORCIDA="
set /p TORCIDA=Torcida deste lote (ex: inter, gremio): 
if not defined TORCIDA (
  echo   Sem torcida nao da para cadastrar: o estudio publica so o lado que perdeu,
  echo   e canal sem torcida ficaria de fora do video sem ninguem perceber.
  echo   Se este canal e narracao, sem lado, digite: neutro
  goto torcida
)
set /p URLS=Cole as URLs: 
python -u -m nucleo.esteira canais "%TIME_%" --torcida "%TORCIDA%" --importar %URLS%
pause
