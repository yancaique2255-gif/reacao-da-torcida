"""O molde do canal: uma declaracao so, dois renderizadores.

O desenho mora no navegador (HTML/CSS) e o video final sai do ffmpeg. Se cada
um tiver sua propria copia da geometria, os dois divergem - e divergem
justamente quando ninguem esta olhando, depois de alguem mexer num numero de um
lado so. Por isso a geometria vive aqui, em coordenadas de 0 a 1, e os dois
lados saem dela: `para_ffmpeg` e `para_pagina`. O teste compara as duas saidas
camada por camada; mexer num lado so reprova a bateria.

**O video nao leva letra nenhuma SOBRE A CENA.** Nem placar, nem cartela de
abertura, nem nome de canal escrito por cima do que foi gravado: quem identifica
o video e a capa e a legenda do post, que sao fora do mp4 e podem ser trocadas
sem refazer render nenhum. Foi escolha do dono em 05/09.

O que o desenho do palco (05/09) liberou e o CENARIO: os @s das redes e a
chamada, na faixa que sobra ao redor da janela, que nao tocam a cena e nao mudam
de jogo para jogo. Eles sao desenhados com PIL, num PNG, fora do ffmpeg - o
`drawtext` continua proibido, e e por isso que aqui nao ha nenhum.

A geometria mora em ARRANJOS nomeados, um por composicao, e cada formato tem os
seus. `quadro-cheio` e o de hoje e o padrao; os `palco-*` deixam sobra para a
marca do canal e poem a janela em 1280x720 cravado, que e o tamanho da fonte.
"""
from dataclasses import dataclass, replace

FPS = 30
COR_FUNDO = "#101418"  # o padrao ate a cor do time perdedor entrar


@dataclass(frozen=True)
class Camada:
    """Uma camada em coordenadas de 0 a 1, medidas na tela do formato.

    `cantos` e `borda` sao fracao da LARGURA: assim o mesmo numero vale nos dois
    formatos sem virar duas contas diferentes.
    """

    nome: str
    x: float
    y: float
    largura: float
    altura: float
    cantos: float = 0.0
    borda: float = 0.0


TAMANHOS = {"deitado": (1920, 1080), "em-pe": (1080, 1920)}

# Cantos de 24px e borda de 3px, medidos no deitado.
_CANTOS = 24 / 1920
_BORDA = 3 / 1920

ARRANJO_PADRAO = "quadro-cheio"

# A tabela de arranjos. Cada um e uma pilha de camadas de baixo para cima, e o
# `quadro-cheio` e o de hoje, numero por numero: e o que garante que ninguem
# acorda com o video diferente sem ter pedido.
#
# Nos arranjos de palco a janela e 1280x720 CRAVADO, que e o tamanho da fonte:
# os pixels caem 1:1 no video final, sem reamostrar. A imagem fica mais nitida
# PORQUE a janela e menor - e a sobra e onde a marca do canal aparece.
_ARRANJOS = {
    "deitado": {
        # Quadro de 1728x972 em 96,54 - a margem de 5% e o que deixa o fundo
        # aparecer. Sem ela, um clipe de webcam em tela cheia continua sendo um
        # clipe de webcam, e nao um produto.
        "quadro-cheio": [
            Camada("fundo", 0.0, 0.0, 1.0, 1.0),
            Camada("quadro", 0.05, 0.05, 0.90, 0.90, cantos=_CANTOS, borda=_BORDA),
        ],
        # 280px de sobra em cima: logo no alto a esquerda, redes no alto a
        # direita. 80px embaixo, so de respiro.
        "palco-alto": [
            Camada("fundo", 0.0, 0.0, 1.0, 1.0),
            Camada("logo", 64 / 1920, 48 / 1080, 192 / 1920, 192 / 1080),
            Camada("barra", 1136 / 1920, 88 / 1080, 720 / 1920, 112 / 1080),
            Camada(
                "quadro", 320 / 1920, 280 / 1080, 1280 / 1920, 720 / 1080,
                cantos=_CANTOS, borda=_BORDA,
            ),
        ],
        # O mais proximo da referencia: coluna de 576px a esquerda com a logo
        # centrada nela, barra atravessando o alto, 64px de respiro a direita.
        "palco-lateral": [
            Camada("fundo", 0.0, 0.0, 1.0, 1.0),
            Camada("logo", 128 / 1920, 380 / 1080, 320 / 1920, 320 / 1080),
            Camada("barra", 64 / 1920, 48 / 1080, 1792 / 1920, 96 / 1080),
            Camada(
                "quadro", 576 / 1920, 300 / 1080, 1280 / 1920, 720 / 1080,
                cantos=_CANTOS, borda=_BORDA,
            ),
        ],
    },
    # Em pe: quadro colado na largura, no terco de cima - a altura de 608/1920 e
    # o 16:9 do clipe deitado na tela em pe, sem esticar nada. Nesta rodada o
    # 9:16 nao ganha palco: precisa de outra arte e de outro lugar para a barra,
    # porque ali a faixa de cima e area nobre.
    "em-pe": {
        "quadro-cheio": [
            Camada("fundo", 0.0, 0.0, 1.0, 1.0),
            Camada("quadro", 0.0, 0.25, 1.0, 608 / 1920, cantos=_CANTOS, borda=_BORDA),
        ],
    },
}


def tamanho(formato: str) -> tuple[int, int]:
    _conferir(formato)
    return TAMANHOS[formato]


def arranjos(formato: str) -> list[str]:
    """Os arranjos daquele formato, na ordem em que a tela oferece."""
    _conferir(formato)
    return list(_ARRANJOS[formato])


def camadas(
    formato: str,
    arranjo: str = ARRANJO_PADRAO,
    escala: float = 1.0,
    deslocamento: float = 0.0,
) -> list[Camada]:
    """As camadas daquele arranjo, de baixo para cima, com o ajuste fino aplicado.

    `escala` multiplica a janela do arranjo escolhido e `deslocamento` a sobe ou
    desce; as duas so mexem no `quadro` - logo e barra ficam onde o arranjo
    disse. Quem confere os limites e o `nucleo/identidade.py`, na porta em que o
    numero e digitado.
    """
    _conferir(formato)
    if arranjo not in _ARRANJOS[formato]:
        raise ValueError(
            f"arranjo '{arranjo}' nao existe no {formato} - use "
            f"{' ou '.join(_ARRANJOS[formato])}"
        )
    base = _ARRANJOS[formato][arranjo]
    # Sem ajuste nenhum, devolve a declaracao INTACTA. Nao e economia de
    # processador: conta com float nao volta no mesmo numero (0,05 + 0,45 - 0,45
    # nao devolve 0,05), e o `quadro-cheio` sem ajuste tem que sair caractere
    # por caractere igual ao de hoje.
    if escala == 1.0 and deslocamento == 0.0:
        return list(base)
    return [
        _ajustada(c, escala, deslocamento) if c.nome == "quadro" else c for c in base
    ]


def _ajustada(quadro: Camada, escala: float, deslocamento: float) -> Camada:
    """A janela cresce e encolhe em torno do proprio centro, e sobe e desce inteira.

    Em torno do centro porque encolher empurrando para um canto nao e ajuste
    fino: e outra composicao, e ai o arranjo escolhido nao quer dizer mais nada.
    """
    centro_x = quadro.x + quadro.largura / 2
    centro_y = quadro.y + quadro.altura / 2
    largura = quadro.largura * escala
    altura = quadro.altura * escala
    return replace(
        quadro,
        x=centro_x - largura / 2,
        y=centro_y - altura / 2 + deslocamento,
        largura=largura,
        altura=altura,
    )


def em_pixels(camada: Camada, formato: str) -> dict:
    """Aquela camada em pixels daquele formato, arredondada uma vez so."""
    largura, altura = tamanho(formato)
    return {
        "nome": camada.nome,
        "esquerda": round(camada.x * largura),
        "topo": round(camada.y * altura),
        "largura": round(camada.largura * largura),
        "altura": round(camada.altura * altura),
        "cantos": round(camada.cantos * largura),
        "borda": round(camada.borda * largura),
    }


def caixa(
    nome: str,
    formato: str,
    arranjo: str = ARRANJO_PADRAO,
    escala: float = 1.0,
    deslocamento: float = 0.0,
) -> dict:
    for camada in camadas(formato, arranjo, escala, deslocamento):
        if camada.nome == nome:
            return em_pixels(camada, formato)
    raise KeyError(f"o arranjo '{arranjo}' do {formato} nao tem camada '{nome}'")


def para_pagina(camadas_: list[Camada], formato: str) -> dict:
    """O JSON que a previa usa para posicionar em CSS. Tudo ja em pixels.

    Sai das camadas RECEBIDAS, e nao da tabela: com escala e deslocamento, ler a
    tabela de novo devolveria a janela sem ajuste - a previa mostraria uma coisa
    e o ffmpeg faria outra, que e exatamente o que este modulo existe para
    impedir.
    """
    largura, altura = tamanho(formato)
    return {
        "formato": formato,
        "largura": largura,
        "altura": altura,
        "camadas": [em_pixels(c, formato) for c in camadas_],
    }


def para_ffmpeg(
    camadas_: list[Camada],
    formato: str,
    cor_fundo: str = COR_FUNDO,
    entrada: str = "0:v",
    mascara: str | None = None,
    moldura: str | None = None,
    fps: int = FPS,
) -> str:
    """O filter_complex de um item, montado das mesmas camadas.

    `mascara` e `moldura` sao entradas de imagem que o estudio gera com PIL: os
    cantos arredondados e a borda clara. Sem elas o filtro nao as menciona - e
    o que permite espiar um quadro parado sem PNG nenhum no disco.
    """
    largura, altura = tamanho(formato)
    # `em_pixels` e nao `caixa`: as camadas chegam aqui JA ajustadas, e reler a
    # tabela pelo nome desfaria a escala e o deslocamento em silencio.
    caixas = {c.nome: em_pixels(c, formato) for c in camadas_}
    quadro = caixas["quadro"]
    partes = [f"color=c={cor_fundo}:s={largura}x{altura}:r={fps},vignette=PI/4[fundo]"]

    corte = (
        # `setpts=PTS-STARTPTS` primeiro, e nao por capricho: com `-ss` no
        # clipe, o primeiro quadro dele chega com o relogio deslocado, DEPOIS
        # do primeiro quadro do fundo - e o `overlay` deixa passar o fundo
        # pelado. O ESPIAR, que e um quadro so, saia com a cor do time chapada.
        f"[{entrada}]setpts=PTS-STARTPTS,"
        f"scale={quadro['largura']}:{quadro['altura']}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={quadro['largura']}:{quadro['altura']},setsar=1"
    )
    if mascara:
        partes.append(f"{corte}[recortado]")
        partes.append(f"[{mascara}]scale={quadro['largura']}:{quadro['altura']}[cantos]")
        partes.append("[recortado][cantos]alphamerge[quadro]")
    else:
        partes.append(f"{corte}[quadro]")

    partes.append(
        f"[fundo][quadro]overlay={quadro['esquerda']}:{quadro['topo']}"
        f":shortest=1[com-quadro]"
    )
    ultimo = "com-quadro"
    if moldura:
        partes.append(
            f"[{ultimo}][{moldura}]overlay={quadro['esquerda']}:{quadro['topo']}"
            f"[com-moldura]"
        )
        ultimo = "com-moldura"

    partes.append(f"[{ultimo}]setsar=1[v]")
    return ";".join(partes)


def _conferir(formato: str) -> None:
    if formato not in TAMANHOS:
        raise ValueError(
            f"formato '{formato}' nao existe - use 'deitado' (16:9) ou 'em-pe' (9:16)"
        )
