"""Um quadro recente de cada canal, para o painel mostrar o que esta entrando.

Sem isto, o operador so sabe que um canal esta gravando - nao o que ele grava.
E a diferenca entre uma cara de torcedor na webcam e um placar parado importa
mais do que o tamanho do arquivo: e a materia-prima do projeto.
"""
import subprocess
import time
from pathlib import Path
from typing import Callable

SEGUNDOS_DE_VALIDADE = 15  # dentro disso, reaproveita o quadro ja tirado
RECUO = 6                  # segundos antes do fim: o fim do arquivo esta sendo escrito
LARGURA = 320


def _rodar(comando: list[str]) -> None:
    subprocess.run(comando, capture_output=True, timeout=30)


def pedaco_mais_novo(pasta_canal: Path) -> Path | None:
    pedacos = list(Path(pasta_canal).glob("*.ts"))
    if not pedacos:
        return None
    return max(pedacos, key=lambda p: p.stat().st_mtime)


def comando(fonte: Path, saida: Path, ffmpeg: str) -> list[str]:
    """Le so o finalzinho do arquivo: o pedaco inteiro tem centenas de MB."""
    return [
        ffmpeg, "-y", "-v", "error",
        "-sseof", f"-{RECUO}",
        "-i", str(fonte),
        "-frames:v", "1",
        "-vf", f"scale={LARGURA}:-2",
        "-q:v", "6",
        str(saida),
    ]


def esta_fresca(arquivo: Path, agora: float) -> bool:
    return arquivo.is_file() and (agora - arquivo.stat().st_mtime) < SEGUNDOS_DE_VALIDADE


def gerar(
    pasta_canal: Path,
    destino: Path,
    ffmpeg: str,
    agora: float | None = None,
    rodar: Callable[[list[str]], None] = _rodar,
) -> Path | None:
    """Devolve o quadro do canal, tirando um novo so quando o de antes envelheceu."""
    agora = time.time() if agora is None else agora
    destino = Path(destino)
    if esta_fresca(destino, agora):
        return destino

    fonte = pedaco_mais_novo(pasta_canal)
    if fonte is None:
        return None

    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        rodar(comando(fonte, destino, ffmpeg))
    except (subprocess.SubprocessError, OSError):
        return destino if destino.is_file() else None
    return destino if destino.is_file() else None
