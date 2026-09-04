"""O `docs/DESIGN-DO-VIDEO.md` nao pode mentir.

O painel ja aprendeu isso: o `test_design.py` cobra que o `DESIGN.md` descreva
os tokens que as telas realmente usam. Aqui e a mesma trava para o produto
publicado - o bloco de metadados do topo do documento e comparado com o que o
`molde.py` e o `capa.py` declaram, numero por numero.

Documento de design que diverge do codigo e pior do que documento nenhum: ele
ensina errado, e ninguem descobre ate o video sair torto.
"""
from pathlib import Path

import pytest

from nucleo import capa, config, molde

DOCUMENTO = Path(__file__).resolve().parent.parent / "docs" / "DESIGN-DO-VIDEO.md"


def _metadados(caminho: Path = DOCUMENTO) -> dict:
    """Le o bloco entre as duas linhas de `---` no topo. Subconjunto de YAML.

    Nada de dependencia nova para ler quatro niveis de dois espacos: o
    `test_design.py` ja le CSS com expressao regular, e a regra do projeto e
    nao somar biblioteca por conveniencia de teste.
    """
    bruto = caminho.read_text(encoding="utf-8").split("---")[1]
    raiz: dict = {}
    ramos = {0: raiz}
    pular_acima_de = None
    for linha in bruto.splitlines():
        if not linha.strip() or linha.lstrip().startswith("#"):
            continue
        recuo = len(linha) - len(linha.lstrip())
        if pular_acima_de is not None:
            if recuo > pular_acima_de:
                continue
            pular_acima_de = None
        chave, _, valor = linha.strip().partition(":")
        valor = valor.strip().strip('"')
        if valor == "|":  # bloco de texto livre: nao interessa ao teste
            pular_acima_de = recuo
            continue
        if valor:
            ramos[recuo][chave] = valor
        else:
            ramos[recuo][chave] = {}
            ramos[recuo + 2] = ramos[recuo][chave]
    return raiz


META = _metadados()


def test_o_documento_diz_de_onde_o_sistema_veio():
    """Sistema emprestado se credita, e o link tem de estar no documento."""
    assert META["base"] == "https://getdesign.md/ollama/design-md"
    assert "getdesign.md/ollama/design-md" in DOCUMENTO.read_text(encoding="utf-8")


def test_as_cores_do_documento_sao_as_do_molde():
    cores = META["colors"]

    assert cores["canvas"] == molde.COR_PILULA
    assert cores["ink"] == molde.COR_NA_PILULA
    assert cores["on-dark"] == molde.COR_TEXTO
    assert cores["on-dark-mute"] == molde.COR_TEXTO_FRACO
    assert cores["hairline"] == molde.COR_FIO


def test_as_fontes_do_documento_sao_as_que_a_configuracao_usa():
    """Tres papeis, tres arquivos. Nenhum deles e a Arial de antes."""
    letras = META["typography"]

    for papel, arquivo in letras.items():
        caminho = config.PADROES[f"fonte_{papel}"]
        assert Path(caminho).name.lower() == arquivo.lower(), papel
    assert set(letras) == set(molde.LETRAS)


def test_o_recuo_e_os_cantos_do_documento_sao_os_do_molde():
    assert float(META["spacing"]["recuo"]) == molde.RECUO
    assert float(META["rounded"]["lg"]) == pytest.approx(molde.CANTOS_DO_QUADRO)


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_a_geometria_do_documento_e_a_do_molde_camada_por_camada(formato):
    escritas = META["molde"][formato]
    declaradas = {c.nome: c for c in molde.camadas(formato)}

    assert set(escritas) == set(declaradas), formato
    for nome, linha in escritas.items():
        do_documento = [round(float(n), 6) for n in linha.split()]
        camada = declaradas[nome]
        do_codigo = [
            round(v, 6)
            for v in (camada.x, camada.y, camada.largura, camada.altura)
        ]
        assert do_documento == do_codigo, f"{formato}/{nome}"


def test_a_capa_do_documento_e_a_do_codigo():
    assert [int(n) for n in META["capa"]["tamanho"].split()] == list(capa.TAMANHO)
    assert [int(n) for n in META["capa"]["regiao"].split()] == list(capa.REGIAO)
    assert int(META["capa"]["vao"]) == capa.VAO


def test_o_documento_esta_apontado_no_agents_md():
    """A trinca do combinado: AGENTS.md como escrever, DESIGN.md como a tela
    parece, DESIGN-DO-VIDEO.md como o produto publicado parece."""
    raiz = DOCUMENTO.parent.parent
    assert "DESIGN-DO-VIDEO.md" in (raiz / "AGENTS.md").read_text(encoding="utf-8")
