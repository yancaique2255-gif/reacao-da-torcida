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
    RAIZ / "painel" / "recepcao.html",
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


def _css(caminho: Path) -> str:
    """So o que esta dentro do <style>: o corpo da pagina tem texto e emoji."""
    return "\n".join(re.findall(r"<style>(.*?)</style>", caminho.read_text(encoding="utf-8"), re.S))


def test_nenhuma_tela_tem_sombra():
    """O sistema da Ollama separa por fio, nao por profundidade. Nada levanta do papel."""
    for tela in TELAS:
        assert "box-shadow" not in _css(tela), f"{tela.name} voltou a ter sombra"


def test_nenhuma_tela_tem_gradiente_decorativo():
    for tela in TELAS:
        css = _css(tela)
        for enfeite in ("linear-gradient", "radial-gradient"):
            assert enfeite not in css, f"{tela.name} tem {enfeite}"


def test_so_os_raios_da_escala():
    """Escala de raio: 8 (midia interna, trilho) / 12 (cartao) / 999 (pilula), mais a bolinha."""
    permitidos = {"8px", "12px", "999px", "50%"}
    for tela in TELAS:
        usados = set(re.findall(r"border-radius:\s*([^;}]+)", _css(tela)))
        fora = {u.strip() for u in usados} - permitidos
        assert not fora, f"{tela.name} usa raio fora da escala: {sorted(fora)}"


def test_a_tinta_de_estado_e_12_por_cento():
    """A 16% o texto de --viva sobre a propria tinta dava 4,3:1 e reprovava na AA.

    O 40% e so de fio, que nao leva texto por cima.
    """
    for tela in TELAS:
        pcts = set(re.findall(r"color-mix\(in srgb, var\(--[a-z-]+\) (\d+)%", _css(tela)))
        assert pcts <= {"12", "40"}, f"{tela.name} mistura em {sorted(pcts)}%"


def test_nenhuma_cor_crua_fora_do_root():
    """Valor cru de cor e o erro mais chato de desfazer. Sobra o #000 de passe-partout.

    O preto atras de foto e video nao e superficie, e fundo para a imagem ter contra
    o que aparecer - por isso ele fica, e o texto sobre ele vai em var(--fundo).
    """
    for tela in TELAS:
        css = _css(tela)
        sem_root = re.sub(r":root\s*\{.*?\}", "", css, flags=re.S)
        crus = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{3,8}", sem_root)} - {"#000", "#000000"}
        assert not crus, f"{tela.name} tem cor crua fora do :root: {sorted(crus)}"


def test_a_acao_principal_e_a_pilula_preta():
    """Uma por tela: MARCAR GOL, MONTAR, RENDER FINAL. O ambar saiu na migracao."""
    principais = {
        "gravacao.html": ".marcar {",
        "pagina.html": "#montar {",
        "edicao.html": "button.render {",
        # A recepcao e a tela do jogo dividem o arquivo e nunca aparecem
        # juntas: uma pilula preta em cada uma, e nao duas na mesma dobra.
        "recepcao.html": "#continuar, #editar {",
    }
    for tela in TELAS:
        css = _css(tela)
        seletor = principais[tela.name]
        inicio = css.index(seletor)
        regra = css[inicio:css.index("}", inicio)]
        assert "background: var(--texto)" in regra, f"{tela.name}: {seletor} nao e a pilula preta"
        assert "color: var(--fundo)" in regra, f"{tela.name}: {seletor} sem tinta invertida"


def test_tudo_o_que_se_aperta_e_pilula():
    """Botao, select e campo de digitar: 999px. Era o que faltava em duas telas."""
    for tela in TELAS:
        css = _css(tela)
        base = re.search(r"(?m)^[ \t]*button\s*\{([^}]*)\}", css)
        assert base and "border-radius: 999px" in base.group(1), (
            f"{tela.name}: o botao base nao e pilula"
        )
        for seletor, corpo in re.findall(r"([^{}]+)\{([^}]*)\}", css):
            if "border-radius" not in corpo:
                continue
            if not re.search(r"\b(button|select|input)\b", seletor):
                continue
            if "checkbox" in seletor or "textarea" in seletor:
                continue
            assert "border-radius: 999px" in corpo, (
                f"{tela.name}: {seletor.strip()} se aperta e nao e pilula"
            )
