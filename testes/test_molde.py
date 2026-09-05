"""O molde e declarado uma vez e sai nos dois renderizadores.

O desenho mora no navegador (HTML/CSS) e o video final sai do ffmpeg. Se cada um
tiver sua propria copia da geometria, eles divergem - e divergem justamente
quando ninguem esta olhando, depois de alguem mexer num numero de um lado so.

Por isso o teste que importa aqui e o `test_ffmpeg_e_pagina_concordam`: ele le a
geometria de volta do filter_complex, como o ffmpeg leria, e compara com o que a
pagina recebe para posicionar em CSS.

E o outro que importa e o `test_o_video_nao_leva_letra_nenhuma`: o dono pediu o
video limpo, e essa e a promessa mais facil de quebrar sem querer - basta
alguem devolver um `drawtext` ao molde para todo render passar a escrever.
"""
import re

import pytest

from nucleo import molde


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

    filtro = molde.para_ffmpeg(camadas, formato)
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
    """A ordem e a pilha: o fundo primeiro, o quadro por cima dele. Fim."""
    nomes = [c.nome for c in molde.camadas("deitado")]

    assert nomes == ["fundo", "quadro"]


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_o_fundo_cobre_a_tela_inteira(formato):
    caixa = molde.caixa("fundo", formato)

    assert (caixa["esquerda"], caixa["topo"]) == (0, 0)
    assert (caixa["largura"], caixa["altura"]) == molde.tamanho(formato)


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


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_o_video_nao_leva_letra_nenhuma(formato):
    """O dono pediu o video limpo em 05/09: nem canal, nem placar, nem cartela.

    Quem identifica o video e a capa e a legenda do post, fora do mp4. Este
    teste e o portao: qualquer `drawtext` que volte ao molde reprova aqui antes
    de virar render, que e onde custa 20 minutos para descobrir.
    """
    filtro = molde.para_ffmpeg(molde.camadas(formato), formato)

    assert "drawtext" not in filtro
    assert "drawbox" not in filtro
    assert not hasattr(molde, "filtro_cartela"), "a cartela saiu junto"


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


@pytest.mark.parametrize("formato", ["deitado", "em-pe"])
def test_o_clipe_entra_no_filtro_com_o_relogio_zerado(formato):
    """Sem zerar o relogio do clipe, o overlay nao acha o primeiro quadro dele.

    Achado na prova no jogo de verdade, depois do conserto do `instante`: com
    `-ss 80` no clipe, o primeiro quadro dele chega DEPOIS do primeiro quadro
    do fundo, e o `overlay` deixa passar o fundo pelado. O ESPIAR, que e um
    quadro so, saia com a cor do time chapada; no video inteiro era um piscar
    de cor no comeco de cada clipe. Antes do conserto do `instante` isto nao
    aparecia porque o ESPIAR sempre pedia o segundo zero.
    """
    filtro = molde.para_ffmpeg(molde.camadas(formato), formato)

    assert "setpts=PTS-STARTPTS" in filtro
    assert filtro.index("setpts=PTS-STARTPTS") < filtro.index("overlay=")




FILTRO_DE_HOJE_DEITADO = (
    "color=c=#101418:s=1920x1080:r=30,vignette=PI/4[fundo];"
    "[0:v]setpts=PTS-STARTPTS,scale=1728:972:force_original_aspect_ratio=increase,"
    "crop=1728:972,setsar=1[recortado];"
    "[1:v]scale=1728:972[cantos];"
    "[recortado][cantos]alphamerge[quadro];"
    "[fundo][quadro]overlay=96:54:shortest=1[com-quadro];"
    "[com-quadro][2:v]overlay=96:54[com-moldura];"
    "[com-moldura]setsar=1[v]"
)


def test_o_quadro_cheio_sai_caractere_por_caractere_igual_ao_de_hoje():
    """A nao-regressao da seccao 7 da spec do palco.

    O palco e a identidade do canal entram por cima de um sistema que ja monta
    video de verdade. O teto do risco e este teste: identidade vazia com
    `quadro-cheio` produz o MESMO filter_complex de antes, caractere por
    caractere. Se ele reprovar, o video mudou sem ninguem ter pedido.
    """
    filtro = molde.para_ffmpeg(
        molde.camadas("deitado"), "deitado", mascara="1:v", moldura="2:v"
    )

    assert filtro == FILTRO_DE_HOJE_DEITADO
