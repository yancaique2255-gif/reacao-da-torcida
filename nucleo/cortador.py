"""Monta e executa os comandos ffmpeg de extracao de audio e corte de clipe.

Nao sabe o que e gol: recebe inicio e duracao.
"""
import subprocess
from pathlib import Path
from typing import Callable

from nucleo import relogio


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


def executar(comando: list[str]) -> None:
    subprocess.run(comando, check=True, capture_output=True)


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
