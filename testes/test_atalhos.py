"""Os .bat numerados sao a ordem de uso, e o README fala deles pelo numero.

Eles ja discordaram uma vez: o atalho da Area de Trabalho chamava "3 - CORTAR NA
MAO" e apontava para um arquivo chamado "2 - CORTAR.bat", enquanto o README
mandava clicar no "2". Quem seguia o texto abria a tela errada.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _passos() -> dict[int, str]:
    """Os .bat numerados, por numero."""
    achados = {}
    for arquivo in RAIZ.glob("*.bat"):
        casa = re.match(r"(\d+) - (.+)\.bat$", arquivo.name)
        if casa:
            achados[int(casa.group(1))] = casa.group(2)
    return achados


def test_os_passos_sao_uma_sequencia_sem_buraco():
    passos = _passos()
    assert passos, "nenhum .bat numerado encontrado"
    assert sorted(passos) == list(range(len(passos))), f"numeracao com buraco: {sorted(passos)}"


def test_o_readme_cita_cada_passo_pelo_nome():
    texto = RAIZ / "README.md"
    texto = texto.read_text(encoding="utf-8")
    for numero, nome in _passos().items():
        # O README escreve com acento; o nome do arquivo, sem.
        assert f"**{numero} - " in texto, f"o passo {numero} ({nome}) nao esta no README"
