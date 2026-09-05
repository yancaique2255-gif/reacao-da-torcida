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


@pytest.mark.parametrize(
    "formato,arranjo",
    [("deitado", "quadro-cheio"), ("deitado", "palco-alto"),
     ("deitado", "palco-lateral"), ("em-pe", "quadro-cheio")],
)
def test_ffmpeg_e_pagina_concordam_camada_por_camada(formato, arranjo):
    camadas = molde.camadas(formato, arranjo)

    filtro = molde.para_ffmpeg(camadas, formato)
    pagina = molde.para_pagina(camadas, formato)

    do_ffmpeg = _geometria_do_filtro(filtro)
    da_pagina = {c["nome"]: c for c in pagina["camadas"]}
    for nome, caixa in do_ffmpeg.items():
        for campo, valor in caixa.items():
            assert da_pagina[nome][campo] == valor, f"{formato}/{arranjo}/{nome}/{campo}"


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


def test_os_tres_arranjos_do_deitado_existem():
    assert molde.arranjos("deitado") == ["quadro-cheio", "palco-alto", "palco-lateral"]


def test_o_em_pe_tem_um_arranjo_so_nesta_rodada():
    """A spec e explicita: nesta rodada, so o deitado ganha palco."""
    assert molde.arranjos("em-pe") == ["quadro-cheio"]


@pytest.mark.parametrize("arranjo", ["palco-alto", "palco-lateral"])
def test_a_janela_do_palco_e_1280x720_cravado(arranjo):
    """A seccao 6: os pixels da fonte caem 1:1, sem reamostrar.

    Se alguem mexer num numero e quebrar o 1:1, a bateria reprova - e nao o olho
    de quem for assistir o proximo compilado.
    """
    quadro = molde.caixa("quadro", "deitado", arranjo)

    assert (quadro["largura"], quadro["altura"]) == (1280, 720)


def test_o_palco_alto_deixa_a_faixa_de_cima_livre():
    """280px em cima, que e onde a logo e a barra moram."""
    quadro = molde.caixa("quadro", "deitado", "palco-alto")

    assert (quadro["esquerda"], quadro["topo"]) == (320, 280)


def test_o_palco_lateral_deixa_a_coluna_da_esquerda_livre():
    quadro = molde.caixa("quadro", "deitado", "palco-lateral")

    assert quadro["esquerda"] == 576
    assert 1920 - (quadro["esquerda"] + quadro["largura"]) == 64


def test_o_quadro_cheio_nao_tem_logo_nem_barra():
    """Sem sobra, nao ha camada: o de hoje continua sendo o de hoje."""
    nomes = [c.nome for c in molde.camadas("deitado", "quadro-cheio")]

    assert nomes == ["fundo", "quadro"]


@pytest.mark.parametrize("arranjo", ["palco-alto", "palco-lateral"])
def test_o_palco_tem_logo_e_barra(arranjo):
    nomes = [c.nome for c in molde.camadas("deitado", arranjo)]

    assert nomes == ["fundo", "logo", "barra", "quadro"]


@pytest.mark.parametrize("arranjo", ["palco-alto", "palco-lateral"])
def test_a_logo_e_a_barra_nao_encostam_na_janela(arranjo):
    """O palco e o cenario ATRAS e AO REDOR: nada se sobrepoe a cena."""
    quadro = molde.caixa("quadro", "deitado", arranjo)
    for nome in ("logo", "barra"):
        caixa = molde.caixa(nome, "deitado", arranjo)
        ao_lado = (
            caixa["esquerda"] + caixa["largura"] <= quadro["esquerda"]
            or caixa["esquerda"] >= quadro["esquerda"] + quadro["largura"]
        )
        acima_ou_abaixo = (
            caixa["topo"] + caixa["altura"] <= quadro["topo"]
            or caixa["topo"] >= quadro["topo"] + quadro["altura"]
        )
        assert ao_lado or acima_ou_abaixo, f"{arranjo}/{nome} invade a janela"


@pytest.mark.parametrize("arranjo", ["palco-alto", "palco-lateral"])
def test_a_logo_e_a_barra_cabem_no_palco(arranjo):
    for nome in ("logo", "barra"):
        caixa = molde.caixa(nome, "deitado", arranjo)
        assert caixa["esquerda"] >= 0 and caixa["topo"] >= 0, f"{arranjo}/{nome}"
        assert caixa["esquerda"] + caixa["largura"] <= 1920, f"{arranjo}/{nome}"
        assert caixa["topo"] + caixa["altura"] <= 1080, f"{arranjo}/{nome}"


def test_a_escala_encolhe_a_janela_em_torno_do_centro():
    """Encolher tem que manter a janela onde estava, e nao empurra-la para um canto."""
    quadro = molde.caixa("quadro", "deitado", "palco-alto", escala=0.75)

    assert (quadro["largura"], quadro["altura"]) == (960, 540)
    assert (quadro["esquerda"], quadro["topo"]) == (480, 370)


def test_o_deslocamento_sobe_a_janela_inteira():
    """0,1 de 1080 = 108px, e so no eixo vertical."""
    quadro = molde.caixa("quadro", "deitado", "palco-alto", deslocamento=-0.1)

    assert (quadro["esquerda"], quadro["largura"]) == (320, 1280)
    assert quadro["topo"] == 172


def test_a_pagina_mostra_a_janela_JA_ajustada():
    """A previa le a mesma geometria; ler a tabela de novo divergiria do render."""
    camadas = molde.camadas("deitado", "palco-alto", escala=0.75)

    pagina = molde.para_pagina(camadas, "deitado")

    quadro = {c["nome"]: c for c in pagina["camadas"]}["quadro"]
    assert (quadro["largura"], quadro["altura"]) == (960, 540)


def test_o_ffmpeg_obedece_a_janela_ajustada():
    filtro = molde.para_ffmpeg(
        molde.camadas("deitado", "palco-alto", escala=0.75), "deitado"
    )

    assert "scale=960:540:force_original_aspect_ratio=increase" in filtro
    assert "overlay=480:370" in filtro


def test_arranjo_que_nao_existe_reclama_e_ensina_os_que_existem():
    with pytest.raises(ValueError) as erro:
        molde.camadas("deitado", "palco-do-mickey")

    assert "palco-alto" in str(erro.value) and "quadro-cheio" in str(erro.value)
