"""A biblioteca padrao nunca pode cair no Google Drive.

Gravar no `G:` dispara upload durante o jogo, e o upload disputa a mesma placa de
100 Mbps que baixa as lives - o gargalo do projeto inteiro. README e AGENTS.md
proibem desde sempre; o padrao do codigo apontava para la assim mesmo, e quem
instalasse sem `config.json` gravaria no Drive sem saber.
"""
import json
from pathlib import Path

from nucleo import config

RAIZ = Path(__file__).resolve().parent.parent


def test_a_biblioteca_padrao_nao_e_o_google_drive():
    assert not config.PADROES["biblioteca"].upper().startswith("G:")


def test_o_config_de_exemplo_nao_manda_gravar_no_drive():
    """O exemplo e o que o usuario novo copia: ele ensina o padrao."""
    exemplo = json.loads(
        (RAIZ / "dados" / "config.exemplo.json").read_text(encoding="utf-8")
    )
    assert not exemplo["biblioteca"].upper().startswith("G:")


def test_carregar_sem_arquivo_devolve_biblioteca_local():
    valores = config.carregar(RAIZ / "dados" / "nao-existe.json")
    assert not valores["biblioteca"].upper().startswith("G:")
