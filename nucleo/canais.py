"""Cadastro das lives escolhidas manualmente pelo operador."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Canal:
    nome: str
    url: str
    ativo: bool = True
    torcida: str = ""  # "santos", "palmeiras", "" para neutro/narracao


def carregar(caminho: Path) -> dict[str, list[Canal]]:
    arquivo = Path(caminho)
    if not arquivo.is_file():
        return {}
    bruto = json.loads(arquivo.read_text(encoding="utf-8"))
    return {
        time: [
            Canal(
                c["nome"], c["url"].strip(), c.get("ativo", True),
                (c.get("torcida") or "").strip().lower(),
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
