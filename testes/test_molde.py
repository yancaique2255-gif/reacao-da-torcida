"""O molde e declarado uma vez e sai nos dois renderizadores.

A previa mora no navegador (HTML/CSS) e o video final sai do ffmpeg. Se cada um
tiver sua propria copia da geometria, eles divergem - e divergem justamente
quando ninguem esta olhando, depois de alguem mexer num numero de um lado so.
Uma previa que mente e pior do que nao ter previa.

Por isso o teste que importa aqui e o `test_ffmpeg_e_pagina_concordam`: ele le a
geometria de volta do filter_complex, como o ffmpeg leria, e compara com o que a
pagina recebe para posicionar em CSS.
"""
import re
from pathlib import Path

import pytest

from nucleo import molde


# ------------------------------------------------ o design do produto publicado

FONTES = {
    "display": Path(r"C:\Windows\Fonts\bahnschrift.ttf"),
    "sans": Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    "mono": Path(r"C:\Windows\Fonts\consolab.ttf"),
}
IMAGENS = {
    "mascara": "1:v", "moldura": "2:v",
    "etiqueta": "3:v", "torcida": "4:v", "placar": "5:v",
}
TITULO = "GREMIO 3 x 0 INTER"
META = "COPA DO BRASIL - 03/09/2026"


def _filtro_cheio(formato: str) -> str:
    return molde.para_ffmpeg(
        molde.camadas(formato), formato,
        canal="BALDASSO TV", torcida="TORCIDA DO INTER", placar="3 x 0",
        fontes=FONTES, imagens=IMAGENS,
    )


def _da_forma(filtro: str, nome: str) -> dict:
    """Le a geometria de uma camada de pilula de volta do filter_complex."""
    marca = nome.replace("-", "_")
    tamanho = re.search(rf"scale=(\d+):(\d+)\[forma_{marca}\]", filtro)
    posicao = re.search(rf"\[forma_{marca}\]overlay=(\d+):(\d+)", filtro)
    corpo = re.search(rf"\[fundo_{marca}\]drawtext=[^;]*?fontsize=(\d+)", filtro)
    assert tamanho and posicao and corpo, f"{nome} nao esta no filtro"
    return {
        "largura": int(tamanho.group(1)), "altura": int(tamanho.group(2)),
        "esquerda": int(posicao.group(1)), "topo": int(posicao.group(2)),
        "fonte": int(corpo.group(1)),
    }


def _do_texto(filtro: str, nome: str) -> dict:
    marca = nome.replace("-", "_")
    achado = re.search(
        rf"drawtext=[^;]*?:x=(\d+):y=(\d+):fontsize=(\d+)[^;]*\[posto_{marca}\]",
        filtro,
    )
    assert achado, f"{nome} nao esta no filtro"
    return {
        "esquerda": int(achado.group(1)), "topo": int(achado.group(2)),
        "fonte": int(achado.group(3)),
    }


def _da_pagina(formato: str) -> dict:
    return {
        c["nome"]: c
        for c in molde.para_pagina(molde.camadas(formato), formato)["camadas"]
    }


def _geometria_do_filtro(filtro: str) -> dict:
    """Le de volta o que o ffmpeg vai obedecer, e nao o que quisemos dizer."""
    escala = re.search(r"scale=(\d+):(\d+):force_original_aspect_ratio", filtro)
    posicao = re.search(r"\]overlay=(\d+):(\d+)", filtro)
    return {
        "quadro": {
            "esquerda": int(posicao.group(1)), "topo": int(posicao.group(2)),
            "largura": int(escala.group(1)), "altura": int(escala.group(2)),
        }
    }


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_ffmpeg_e_pagina_concordam_camada_por_camada(formato):
    camadas = molde.camadas(formato)

    filtro = _filtro_cheio(formato)
    pagina = molde.para_pagina(camadas, formato)

    da_pagina = {c["nome"]: c for c in pagina["camadas"]}
    lido = _geometria_do_filtro(filtro)
    for nome in molde.CROMADO:
        lido[nome] = _da_forma(filtro, nome)
    for nome, caixa in lido.items():
        for campo, valor in caixa.items():
            assert da_pagina[nome][campo] == valor, f"{formato}/{nome}/{campo}"


def test_o_quadro_deitado_e_o_que_o_desenho_diz():
    """1728x972 em 96,54 - margem de 5% para o fundo aparecer."""
    quadro = molde.caixa("quadro", "deitado")

    assert (quadro["esquerda"], quadro["topo"]) == (96, 54)
    assert (quadro["largura"], quadro["altura"]) == (1728, 972)


def test_o_quadro_em_pe_e_o_que_o_desenho_diz():
    """1080x608 colado na largura, no terco de cima."""
    quadro = molde.caixa("quadro", "em-pe")

    assert (quadro["esquerda"], quadro["largura"]) == (0, 1080)
    assert quadro["altura"] == 608


def test_as_camadas_saem_de_baixo_para_cima():
    """A ordem e a pilha: o fundo primeiro, a cartela por cima de tudo."""
    nomes = [c.nome for c in molde.camadas("deitado")]

    assert nomes == [
        "fundo", "quadro", "etiqueta", "torcida", "placar",
        "cartela", "cartela-marca", "cartela-titulo", "cartela-regra", "cartela-meta",
    ]


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_o_fundo_e_a_cartela_cobrem_a_tela_inteira(formato):
    tamanho = molde.tamanho(formato)

    for nome in ("fundo", "cartela"):
        caixa = molde.caixa(nome, formato)
        assert (caixa["esquerda"], caixa["topo"]) == (0, 0), nome
        assert (caixa["largura"], caixa["altura"]) == tamanho, nome


def test_o_quadro_nunca_encosta_na_borda_da_tela():
    """Sem margem, um clipe de webcam em tela cheia e um clipe de webcam."""
    for formato in ("deitado", "em-pe"):
        quadro = molde.caixa("quadro", formato)
        largura, altura = molde.tamanho(formato)
        assert quadro["topo"] > 0, formato
        assert quadro["topo"] + quadro["altura"] < altura, formato
        assert quadro["largura"] <= largura, formato


def test_a_pagina_recebe_cantos_e_borda_em_pixels():
    """O CSS precisa de px; o molde guarda fracao para os dois formatos baterem."""
    pagina = molde.para_pagina(molde.camadas("deitado"), "deitado")
    quadro = {c["nome"]: c for c in pagina["camadas"]}

    assert quadro["quadro"]["cantos"] == 24
    assert quadro["quadro"]["borda"] == 3


def test_formato_desconhecido_reclama_e_ensina_a_saida():
    with pytest.raises(ValueError) as erro:
        molde.camadas("quadrado")

    assert "deitado" in str(erro.value) and "em-pe" in str(erro.value)


def test_texto_do_canal_vai_escapado_para_o_ffmpeg():
    """Nome de canal com dois-pontos ou apostrofo quebraria o filter_complex."""
    filtro = molde.para_ffmpeg(
        molde.camadas("deitado"), "deitado", canal="O'Bar: 100% Gol", torcida="inter"
    )

    assert r"O\'Bar\: 100\%" in filtro


def test_sem_mascara_o_filtro_nao_inventa_uma_entrada():
    """Espiar um quadro parado nao tem PNG de cantos: o filtro nao pode pedir um."""
    filtro = molde.para_ffmpeg(molde.camadas("deitado"), "deitado", imagens=None)

    assert "alphamerge" not in filtro
    assert "[1:v]" not in filtro


def test_com_mascara_os_cantos_do_quadro_sao_recortados():
    filtro = molde.para_ffmpeg(
        molde.camadas("deitado"), "deitado",
        imagens={"mascara": "1:v", "moldura": "2:v"},
    )

    assert "alphamerge" in filtro
    assert filtro.count("overlay=96:54") == 2  # o quadro e a moldura dele


def test_a_cartela_anuncia_o_gol_na_tela_inteira():
    filtro = molde.filtro_cartela(
        "deitado", marca="GOL 01", titulo="GREMIO 1 x 0 INTER", meta="COPA DO BRASIL"
    )

    assert "1920x1080" in filtro
    assert "GOL 01" in filtro and "GREMIO 1 x 0 INTER" in filtro
    assert "COPA DO BRASIL" in filtro


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_o_nome_mais_longo_de_canal_cabe_na_etiqueta(formato):
    """Texto que estoura a caixa vaza por cima do video, e ficou feio no render.

    Medido no primeiro render de verdade: "FARID GERMANO FILHO" passou da borda
    direita da tarja. O molde e quem tem que garantir que cabe - a fonte e a
    largura da tarja saem daqui, e o operador nao tem como consertar isso.
    """
    etiqueta = molde.caixa("etiqueta", formato)

    assert molde.cabe("X" * molde.MAXIMO_DO_CANAL, etiqueta), formato


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_o_placar_cabe_na_caixa_dele(formato):
    assert molde.cabe("10 x 10", molde.caixa("placar", formato)), formato


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_a_pilula_do_ffmpeg_e_a_da_pagina_camada_por_camada(formato):
    """As pilulas sao imagem do Pillow, e a posicao delas sai do molde.

    O `scale` no filtro carrega o tamanho e o `overlay` carrega a posicao: da
    para ler os dois de volta, como o ffmpeg leria, e cobrar que batem com o
    que a pagina recebe para posicionar em CSS.
    """
    filtro = _filtro_cheio(formato)
    pagina = _da_pagina(formato)

    for nome in ("etiqueta", "torcida", "placar"):
        for campo, valor in _da_forma(filtro, nome).items():
            assert pagina[nome][campo] == valor, f"{formato}/{nome}/{campo}"


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_a_cartela_do_ffmpeg_e_a_da_pagina_camada_por_camada(formato):
    filtro = molde.filtro_cartela(
        formato, marca="GOL 03", titulo=TITULO, meta=META,
        fontes=FONTES, imagens={"cartela-marca": "1:v"},
    )
    pagina = _da_pagina(formato)

    for campo, valor in _da_forma(filtro, "cartela-marca").items():
        assert pagina["cartela-marca"][campo] == valor, f"{formato}/marca/{campo}"
    for nome in ("cartela-titulo", "cartela-meta"):
        for campo, valor in _do_texto(filtro, nome).items():
            assert pagina[nome][campo] == valor, f"{formato}/{nome}/{campo}"

    regua = re.search(
        r"drawbox=x=(\d+):y=(\d+):w=(\d+):h=(\d+)[^;]*\[posto_cartela_regra\]", filtro
    )
    assert regua, "a regua de fio nao esta no filtro"
    esperada = pagina["cartela-regra"]
    assert [int(regua.group(n)) for n in (1, 2, 3, 4)] == [
        esperada["esquerda"], esperada["topo"],
        esperada["largura"], esperada["altura"],
    ]


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_nao_sobrou_degrade_nem_vinheta_em_lugar_nenhum(formato):
    """A regra numero um do sistema: superficie chapada, sem atmosfera."""
    cartela = molde.filtro_cartela(formato, "GOL 03", TITULO, META)

    for filtro in (_filtro_cheio(formato), cartela):
        assert "vignette" not in filtro
        assert "gradient" not in filtro


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_nao_sobrou_tarja_translucida_atras_de_texto(formato):
    """Se precisa de fundo, e pilula branca - e nao caixa preta a 55%."""
    assert "black@" not in _filtro_cheio(formato)


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_a_pilula_e_redonda_de_verdade_nos_dois_formatos(formato):
    """`rounded.full`: o canto e metade da altura, e nao um raio qualquer."""
    for nome in ("etiqueta", "torcida", "placar", "cartela-marca"):
        caixa = molde.caixa(nome, formato)
        assert caixa["cantos"] == caixa["altura"] // 2, f"{formato}/{nome}"


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_o_quadro_fica_em_canto_medio_e_nao_de_pilula(formato):
    quadro = molde.caixa("quadro", formato)

    assert 0 < quadro["cantos"] < quadro["altura"] // 4


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_cada_camada_de_texto_declara_a_letra_que_usa(formato):
    """Tres papeis, e nenhuma camada de texto sem papel declarado."""
    for camada in molde.camadas(formato):
        if camada.fonte:
            assert camada.letra in molde.LETRAS, f"{formato}/{camada.nome}"


def test_o_texto_de_cada_camada_vai_na_fonte_do_papel_dela():
    """Display so no titulo da cartela; o resto e sans do sistema e mono."""
    cartela = molde.filtro_cartela(
        "deitado", marca="GOL 03", titulo=TITULO, meta=META,
        fontes=FONTES, imagens={"cartela-marca": "1:v"},
    )
    item = _filtro_cheio("deitado")

    assert cartela.count("bahnschrift") == 1, "o display e um por peca"
    assert "consolab" in cartela  # a marca e a meta
    assert "segoeuib" in item and "consolab" in item
    assert "bahnschrift" not in item, "o clipe nao tem display nenhum"
    assert "arialbd" not in item and "arialbd" not in cartela


# --- o drawtext nao encolhe nada: o molde e quem garante que cabe -------------

PIOR_CANAL = "X" * molde.MAXIMO_DO_CANAL
PIOR_TORCIDA = "TORCIDA DO " + "X" * molde.MAXIMO_DA_TORCIDA
PIOR_TITULO = "PALMEIRAS 10 x 10 PALMEIRAS"
PIOR_META = "COPA DO BRASIL - 03/09/2026 - 2o TEMPO"


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
@pytest.mark.parametrize(
    "camada,texto",
    [
        ("etiqueta", PIOR_CANAL),
        ("torcida", PIOR_TORCIDA),
        ("placar", "10 x 10"),
        ("cartela-marca", "GOL 99"),
        ("cartela-titulo", PIOR_TITULO),
        ("cartela-meta", PIOR_META),
    ],
)
def test_o_pior_texto_de_cada_camada_cabe_na_caixa_dela(formato, camada, texto):
    assert molde.cabe(texto, molde.caixa(camada, formato)), f"{formato}/{camada}"


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_as_duas_pilulas_de_baixo_nao_se_encostam(formato):
    """Etiqueta e torcida sao duas pilulas: encostadas viram uma tarja so."""
    etiqueta = molde.caixa("etiqueta", formato)
    torcida = molde.caixa("torcida", formato)

    cruzam_na_horizontal = (
        etiqueta["esquerda"] + etiqueta["largura"] > torcida["esquerda"]
        and torcida["esquerda"] + torcida["largura"] > etiqueta["esquerda"]
    )
    if cruzam_na_horizontal:
        # No em pe elas empilham; ai o que nao pode e cruzar na vertical.
        assert (
            etiqueta["topo"] + etiqueta["altura"] <= torcida["topo"]
            or torcida["topo"] + torcida["altura"] <= etiqueta["topo"]
        ), formato


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_toda_pilula_do_clipe_respeita_o_recuo_dentro_do_quadro(formato):
    """Um recuo so, nos quatro lados - o equivalente ao `{spacing.section}`."""
    largura, _ = molde.tamanho(formato)
    quadro = molde.caixa("quadro", formato)
    recuo = round(molde.RECUO * largura)

    for nome in ("etiqueta", "torcida", "placar"):
        caixa = molde.caixa(nome, formato)
        assert caixa["esquerda"] >= quadro["esquerda"] + recuo - 1, f"{formato}/{nome}"
        assert (
            caixa["esquerda"] + caixa["largura"]
            <= quadro["esquerda"] + quadro["largura"] - recuo + 1
        ), f"{formato}/{nome}"


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_o_clipe_entra_no_filtro_com_o_relogio_zerado(formato):
    """Sem zerar o relogio do clipe, o overlay nao acha o primeiro quadro dele.

    Achado na primeira prova depois do conserto do `instante`: com `-ss 80` no
    clipe, o primeiro quadro dele chega DEPOIS do primeiro quadro do fundo, e o
    `overlay` deixa passar o fundo pelado. O ESPIAR, que e um quadro so, saia
    vermelho chapado; no video inteiro era um piscar de cor no comeco de cada
    clipe. Antes do conserto do `instante` isto nao aparecia porque o ESPIAR
    sempre pedia o segundo zero.
    """
    filtro = _filtro_cheio(formato)

    assert "setpts=PTS-STARTPTS" in filtro
    assert filtro.index("setpts=PTS-STARTPTS") < filtro.index("overlay=")


def test_sem_placar_anotado_a_cartela_nao_inventa_numero():
    filtro = molde.filtro_cartela("deitado", "GOL 03", "GREMIO x INTER", "COPA")

    assert "GREMIO x INTER" in filtro
    assert "0 x 0" not in filtro
