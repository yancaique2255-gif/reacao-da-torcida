"""As duas telas falam o mesmo vocabulario visual.

Elas divergiram uma vez: mesmo conceito com nome diferente E valor diferente nos
dois arquivos - `--viva: #35d07f` de um lado, `--verde: #39d98a` do outro. Mudar
"o verde" virava editar dois arquivos com dois verdes. Este teste e a trava para
nao acontecer de novo; o vocabulario esta escrito no DESIGN.md.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TELAS = [
    RAIZ / "painel" / "gravacao.html",
    RAIZ / "painel" / "pagina.html",
    RAIZ / "painel" / "edicao.html",
]
DESIGN = RAIZ / "DESIGN.md"


def _tokens(caminho: Path) -> dict[str, str]:
    texto = caminho.read_text(encoding="utf-8")
    bloco = re.search(r":root\s*\{(.*?)\}", texto, re.S)
    assert bloco, f"{caminho.name} nao tem :root"
    return dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]+)", bloco.group(1)))


def test_as_telas_definem_os_mesmos_tokens():
    primeira, *outras = [(t.name, _tokens(t)) for t in TELAS]
    for nome, tokens in outras:
        assert tokens == primeira[1], (
            f"{nome} divergiu de {primeira[0]}: "
            f"so na primeira {sorted(set(primeira[1]) - set(tokens))}, "
            f"so nela {sorted(set(tokens) - set(primeira[1]))}, "
            "valores diferentes "
            f"{sorted(k for k in set(tokens) & set(primeira[1]) if tokens[k] != primeira[1][k])}"
        )


def test_nenhuma_tela_usa_token_que_nao_definiu():
    for tela in TELAS:
        texto = tela.read_text(encoding="utf-8")
        definidos = set(_tokens(tela))
        usados = set(re.findall(r"var\((--[a-z0-9-]+)\)", texto))
        assert not usados - definidos, f"{tela.name} usa {sorted(usados - definidos)}"


def test_o_design_md_descreve_os_tokens_que_existem():
    """Documento que mente e pior que documento que falta."""
    texto = DESIGN.read_text(encoding="utf-8")
    for token, valor in _tokens(TELAS[0]).items():
        assert f"`{token}`" in texto, f"{token} nao esta no DESIGN.md"
        assert valor in texto, f"o valor de {token} ({valor}) nao confere com o DESIGN.md"


def test_o_design_md_esta_do_lado_do_agents_md():
    """A dupla e o combinado: AGENTS.md como escrever, DESIGN.md como parece."""
    assert DESIGN.is_file()
    assert "DESIGN.md" in (RAIZ / "AGENTS.md").read_text(encoding="utf-8")
