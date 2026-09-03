"""Acha a live NOVA de um canal cuja live antiga acabou.

Live encerrada nao volta: o canal abre outra, com outro endereco. Religar na
mesma URL para sempre e so gastar tentativa. Quem descobre a substituta e o
proprio YouTube, pela pagina `/live` do canal - e o yt-dlp ainda devolve o
endereco do canal a partir do video velho, mesmo depois de ele sair do ar.
"""
import subprocess
from typing import Callable

TEMPO_LIMITE = 90


def _rodar(comando: list[str]) -> str:
    try:
        r = subprocess.run(
            comando, capture_output=True, encoding="utf-8",
            errors="replace", timeout=TEMPO_LIMITE,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return r.stdout or ""


RUIDO = ("WARNING", "ERROR", "[youtube", "[download", "Deleting", "NA")


def _linha_util(saida: str, serve) -> str:
    """A primeira linha que interessa. O yt-dlp fala muito antes de responder.

    Pegar so a primeira linha nao servia: um WARNING na frente viraria a
    resposta, e o canal seria dado como sem live nova.
    """
    for linha in (saida or "").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith(RUIDO):
            continue
        if serve(linha):
            return linha
    return ""


def url_do_canal(
    url_video: str, ytdlp: str, rodar: Callable[[list[str]], str] = _rodar
) -> str:
    """Endereco do canal dono do video. Funciona com a live ja encerrada."""
    saida = rodar([
        ytdlp, "--no-warnings", "--skip-download",
        "--print", "%(channel_url)s", url_video,
    ])
    return _linha_util(saida, lambda l: l.startswith("http"))


def live_do_canal(
    url_canal: str, ytdlp: str, rodar: Callable[[list[str]], str] = _rodar
) -> str:
    """Endereco da live que o canal esta transmitindo agora, ou vazio."""
    if not url_canal:
        return ""
    saida = rodar([
        ytdlp, "--no-warnings", "--skip-download",
        "--print", "%(id)s|%(live_status)s",
        url_canal.rstrip("/") + "/live",
    ])
    linha = _linha_util(saida, lambda l: "|" in l)
    if not linha:
        return ""
    identificador, estado = linha.rsplit("|", 1)
    if estado.strip() != "is_live" or not identificador.strip():
        return ""
    return f"https://www.youtube.com/watch?v={identificador.strip()}"


def procurar_substituta(
    url_atual: str,
    ytdlp: str,
    url_canal: str = "",
    rodar: Callable[[list[str]], str] = _rodar,
) -> tuple[str, str]:
    """Devolve (url da live nova, url do canal). Vazio quando nao ha o que trocar.

    O endereco do canal volta junto para virar cache: descobri-lo custa uma
    chamada de rede, e ele nunca muda.
    """
    canal = url_canal or url_do_canal(url_atual, ytdlp, rodar)
    if not canal:
        return "", ""
    nova = live_do_canal(canal, ytdlp, rodar)
    if not nova or nova == url_atual:
        return "", canal
    return nova, canal
