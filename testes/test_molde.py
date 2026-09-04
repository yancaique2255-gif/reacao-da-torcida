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

import pytest

from nucleo import molde


def _geometria_do_filtro(filtro: str) -> dict:
    """Le de volta o que o ffmpeg vai obedecer, e nao o que quisemos dizer."""
    escala = re.search(r"scale=(\d+):(\d+):force_original_aspect_ratio", filtro)
    posicao = re.search(r"\]overlay=(\d+):(\d+)", filtro)
    caixas = re.findall(r"drawbox=x=(\d+):y=(\d+):w=(\d+):h=(\d+)", filtro)
    lido = {
        "quadro": {
            "esquerda": int(posicao.group(1)), "topo": int(posicao.group(2)),
            "largura": int(escala.group(1)), "altura": int(escala.group(2)),
        }
    }
    # Na ordem em que as camadas sao desenhadas: etiqueta e depois placar.
    for nome, (x, y, w, h) in zip(("etiqueta", "placar"), caixas):
        lido[nome] = {
            "esquerda": int(x), "topo": int(y), "largura": int(w), "altura": int(h)
        }
    return lido


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_ffmpeg_e_pagina_concordam_camada_por_camada(formato):
    camadas = molde.camadas(formato)

    filtro = molde.para_ffmpeg(
        camadas, formato, canal="BALDASSO TV", torcida="inter", placar="GREMIO 1 x 0 INTER"
    )
    pagina = molde.para_pagina(camadas, formato)

    do_ffmpeg = _geometria_do_filtro(filtro)
    da_pagina = {c["nome"]: c for c in pagina["camadas"]}
    for nome, caixa in do_ffmpeg.items():
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

    assert nomes == ["fundo", "quadro", "etiqueta", "placar", "cartela"]


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
    filtro = molde.para_ffmpeg(molde.camadas("deitado"), "deitado", mascara=None)

    assert "alphamerge" not in filtro
    assert "[1:v]" not in filtro


def test_com_mascara_os_cantos_do_quadro_sao_recortados():
    filtro = molde.para_ffmpeg(
        molde.camadas("deitado"), "deitado", mascara="1:v", moldura="2:v"
    )

    assert "alphamerge" in filtro
    assert filtro.count("overlay=96:54") == 2  # o quadro e a moldura dele


def test_a_cartela_anuncia_o_gol_na_tela_inteira():
    filtro = molde.filtro_cartela("deitado", "GOL 1 - GREMIO 1 x 0 INTER")

    assert "1920x1080" in filtro
    assert "GOL 1 - GREMIO 1 x 0 INTER" in filtro


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
