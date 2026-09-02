"""Configuracao do projeto: padroes e sobreposicao pelo arquivo do usuario."""
import json
from pathlib import Path

PADROES = {
    "biblioteca": r"G:\REACAO DA TORCIDA",
    "altura_maxima": 720,
    "segundos_antes": 8,
    "segundos_depois": 12,
    "janela_antes": 30,
    "janela_depois": 180,
    "limiar_confianca_db": 6.0,
    "duracao_pedaco": 600,
    "teto_canais": 20,
    "disco_minimo_gb": 60,
    "caminho_ytdlp": r"C:\yt-dlp\yt-dlp.exe",
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
}

PADRAO_ARQUIVO = Path(__file__).resolve().parent.parent / "dados" / "config.json"


def carregar(caminho: Path | None = PADRAO_ARQUIVO) -> dict:
    """Devolve os padroes com o arquivo do usuario sobreposto por cima."""
    valores = dict(PADROES)
    if caminho is not None and Path(caminho).is_file():
        do_usuario = json.loads(Path(caminho).read_text(encoding="utf-8"))
        valores.update(do_usuario)
    return valores
