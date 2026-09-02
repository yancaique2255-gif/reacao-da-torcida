"""Junta os clipes escolhidos numa compilacao, com o nome do canal na tela."""
from pathlib import Path
from typing import Callable

from nucleo import cortador

LARGURA, ALTURA, FPS = 1280, 720, 30
SEGUNDOS_DE_CARTELA = 3


def _escapar(texto: str) -> str:
    """Escapa os caracteres que drawtext trata como sintaxe."""
    for de, para in [("\\", "\\\\"), (":", "\\:"), ("'", "\\'"), ("%", "\\%")]:
        texto = texto.replace(de, para)
    return texto


def comando_cartela(
    clipe: Path, nome_canal: str, saida: Path, ffmpeg: str
) -> list[str]:
    filtro = (
        f"scale={LARGURA}:{ALTURA}:force_original_aspect_ratio=decrease,"
        f"pad={LARGURA}:{ALTURA}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},"
        f"drawtext=text='{_escapar(nome_canal)}':x=40:y=h-90:fontsize=42:"
        f"fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=12:"
        f"enable='lt(t,{SEGUNDOS_DE_CARTELA})'"
    )
    return [
        ffmpeg,
        "-y",
        "-i",
        str(clipe),
        "-vf",
        filtro,
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
        "-ar",
        "48000",
        str(saida),
    ]


def comando_concat(lista: Path, saida: Path, ffmpeg: str) -> list[str]:
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


def escrever_lista(arquivos: list[Path], destino: Path) -> Path:
    destino.write_text(
        "\n".join(f"file '{arquivo.as_posix()}'" for arquivo in arquivos) + "\n",
        encoding="utf-8",
    )
    return destino


def montar(
    escolhidos: list[dict],
    pasta_jogo: Path,
    cfg: dict,
    executar: Callable[[list[str]], None] = cortador.executar,
) -> Path:
    if not escolhidos:
        raise ValueError("nenhum clipe escolhido - marque as reacoes no painel primeiro")

    pasta_jogo = Path(pasta_jogo)
    temp = pasta_jogo / "temp-montagem"
    temp.mkdir(parents=True, exist_ok=True)
    pasta_saida = pasta_jogo / "saida"
    pasta_saida.mkdir(parents=True, exist_ok=True)

    intermediarios = []
    for indice, clipe in enumerate(escolhidos, start=1):
        origem = pasta_jogo / clipe["arquivo"]
        destino = temp / f"{indice:03d}.mp4"
        executar(
            comando_cartela(
                origem, clipe["canal"], destino, cfg["caminho_ffmpeg"]
            )
        )
        intermediarios.append(destino)

    lista = escrever_lista(intermediarios, temp / "lista.txt")
    saida = pasta_saida / "compilacao.mp4"
    executar(comando_concat(lista, saida, cfg["caminho_ffmpeg"]))
    return saida
