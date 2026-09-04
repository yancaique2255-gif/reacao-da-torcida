"""Monta e executa os comandos ffmpeg de extracao de audio e corte de clipe.

Nao sabe o que e gol: recebe inicio e duracao.
"""
import subprocess
from pathlib import Path
from typing import Callable

from nucleo import relogio

# Quinze minutos por comando. O item mais caro do render final levou 23 s
# nesta maquina; um pedaco que passe disto nao esta trabalhando, esta travado -
# medido em 03/09, com 0% de CPU e ~1,4 GB presos por 11 minutos. Sem
# `timeout=`, o render espera para sempre e o painel fica "rodando" para sempre.
TEMPO_LIMITE = 900
LINHAS_DO_ERRO = 8
# Travar e falhar doem igual para quem chamou: um `except` so serve aos dois.
FALHAS = (subprocess.CalledProcessError, subprocess.TimeoutExpired)


def _rodar_texto(comando: list[str]) -> str:
    return subprocess.run(comando, capture_output=True, text=True).stdout


def duracao(
    arquivo: Path, ffprobe: str, rodar: Callable[[list[str]], str] = _rodar_texto
) -> float:
    """Duracao em segundos. Devolve 0.0 se o arquivo estiver truncado ou ilegivel.

    Serve para medir o pedaco final de uma gravacao interrompida, que por isso
    nao chegou a entrar no CSV de segmentos.
    """
    saida = rodar([
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(arquivo),
    ])
    try:
        return float(saida.strip())
    except (TypeError, ValueError):
        return 0.0


def executar(comando: list[str], timeout: float | None = TEMPO_LIMITE) -> None:
    subprocess.run(comando, check=True, capture_output=True, timeout=timeout)


def motivo(erro: BaseException, linhas: int = LINHAS_DO_ERRO) -> str:
    """As ultimas linhas do stderr do ffmpeg, em uma frase para o operador.

    O `capture_output=True` engole o stderr, e quando o comando enfim quebrava o
    console mostrava um traceback de Python - o operador nunca via o motivo. As
    ultimas linhas sao onde o ffmpeg escreve o que deu errado; as primeiras sao
    a lista de codecs.
    """
    bruto = getattr(erro, "stderr", None) or b""
    if isinstance(bruto, bytes):
        bruto = bruto.decode("utf-8", "replace")
    cauda = "\n".join(bruto.strip().splitlines()[-linhas:]).strip()
    if isinstance(erro, subprocess.TimeoutExpired):
        cabeca = f"o ffmpeg travou: passou de {erro.timeout:g}s sem terminar"
    else:
        codigo = getattr(erro, "returncode", "?")
        cabeca = f"o ffmpeg saiu com codigo {codigo}"
    return f"{cabeca}\n{cauda}".strip() if cauda else cabeca


def comando_audio(
    fonte: Path, inicio: float, duracao: float, saida: Path, ffmpeg: str
) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-ss",
        str(inicio),
        "-i",
        str(fonte),
        "-t",
        str(duracao),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(saida),
    ]


def comando_corte(
    fonte: Path, inicio: float, duracao: float, saida: Path, ffmpeg: str
) -> list[str]:
    # Recodifica de proposito: com -c copy o corte pula para o keyframe anterior
    # e a reacao comeca fora de hora. Sao 20 segundos, custa quase nada.
    return [
        ffmpeg,
        "-y",
        "-ss",
        str(inicio),
        "-i",
        str(fonte),
        "-t",
        str(duracao),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(saida),
    ]


def comando_juntar(lista: Path, saida: Path, ffmpeg: str) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(lista),
        "-c",
        "copy",
        str(saida),
    ]


def escrever_lista_concat(
    trechos: list[relogio.Trecho], pasta: Path, destino: Path
) -> Path:
    linhas = []
    for trecho in trechos:
        linhas.extend(
            [
                f"file '{(pasta / trecho.arquivo).as_posix()}'",
                f"inpoint {trecho.inicio}",
                f"outpoint {trecho.fim}",
            ]
        )
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


def preparar_fonte(
    trechos: list[relogio.Trecho],
    pasta: Path,
    temporaria: Path,
    ffmpeg: str,
    executar: Callable[[list[str]], None] = executar,
) -> tuple[Path, float]:
    """Devolve (arquivo de onde cortar, deslocamento a somar ao instante)."""
    if not trechos:
        raise ValueError("sem trecho gravado para esse intervalo")
    if len(trechos) == 1:
        return pasta / trechos[0].arquivo, trechos[0].inicio

    lista = escrever_lista_concat(trechos, pasta, temporaria.with_suffix(".txt"))
    executar(comando_juntar(lista, temporaria, ffmpeg))
    return temporaria, 0.0
