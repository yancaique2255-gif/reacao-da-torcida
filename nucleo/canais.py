"""Cadastro das lives escolhidas manualmente pelo operador."""
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "dados" / "canais.json"

# Canal de narracao, sem lado, se cadastra assim - por extenso. Vazio nao serve:
# vazio quer dizer "ninguem preencheu", que e outra coisa. Com a regra editorial
# do estudio ligada (publica-se so quem perdeu), campo vazio tira o canal do
# video sem avisar - foi o que quase aconteceu com o melhor material do
# primeiro jogo.
NEUTRO = "neutro"


@dataclass(frozen=True)
class Canal:
    nome: str
    url: str
    ativo: bool = True
    torcida: str = ""  # "santos", "palmeiras", "neutro" para narracao sem lado


def normalizar_torcida(texto: str | None) -> str:
    """"Grêmio " -> "gremio". Duas grafias nao podem virar duas torcidas."""
    sem_acento = (
        unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-").lower()


def exigir_torcida(texto: str | None) -> str:
    """A torcida normalizada. Vazio e recusado, e a recusa ensina a saida."""
    limpa = normalizar_torcida(texto)
    if not limpa:
        raise ValueError(
            "diga de que torcida e o canal (ex: inter, gremio). "
            f'Canal de narracao, sem lado, cadastre como "{NEUTRO}".'
        )
    return limpa


def carregar(caminho: Path) -> dict[str, list[Canal]]:
    arquivo = Path(caminho)
    if not arquivo.is_file():
        return {}
    bruto = json.loads(arquivo.read_text(encoding="utf-8"))
    return {
        time: [
            Canal(
                c["nome"], c["url"].strip(), c.get("ativo", True),
                normalizar_torcida(c.get("torcida")),
            )
            for c in lista
        ]
        for time, lista in bruto.items()
    }


def selecionados_do_time(
    time: str, cadastro: dict[str, list[Canal]]
) -> list[tuple[Canal, str]]:
    """Devolve os ativos na ordem manual, sem consultar ou alterar as URLs."""
    return [(canal, canal.url) for canal in cadastro.get(time, []) if canal.ativo]
