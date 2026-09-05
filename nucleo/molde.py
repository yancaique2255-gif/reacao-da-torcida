"""O molde do canal: uma declaracao so, dois renderizadores.

O desenho mora no navegador (HTML/CSS) e o video final sai do ffmpeg. Se cada
um tiver sua propria copia da geometria, os dois divergem - e divergem
justamente quando ninguem esta olhando, depois de alguem mexer num numero de um
lado so. Por isso a geometria vive aqui, em coordenadas de 0 a 1, e os dois
lados saem dela: `para_ffmpeg` e `para_pagina`. O teste compara as duas saidas
camada por camada; mexer num lado so reprova a bateria.

**O video nao leva letra nenhuma.** Nem nome de canal, nem placar, nem cartela
de abertura: so a cena, no quadro, sobre a cor do time que perdeu. Quem
identifica o video e a capa e a legenda do post, que sao fora do mp4 e podem
ser trocadas sem refazer render nenhum. Foi escolha do dono em 05/09, e e por
isso que aqui nao ha `drawtext`.

O molde e o formato do canal e nao muda de jogo para jogo. E o que faz os
videos parecerem da mesma casa.
"""
from dataclasses import dataclass

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

_MOLDE = {
    # Deitado: quadro de 1728x972 em 96,54 - a margem de 5% e o que deixa o
    # fundo aparecer. Sem ela, um clipe de webcam em tela cheia continua sendo
    # um clipe de webcam, e nao um produto.
    "deitado": [
        Camada("fundo", 0.0, 0.0, 1.0, 1.0),
        Camada("quadro", 0.05, 0.05, 0.90, 0.90, cantos=_CANTOS, borda=_BORDA),
    ],
    # Em pe: quadro colado na largura, no terco de cima - a altura de 608/1920 e
    # o 16:9 do clipe deitado na tela em pe, sem esticar nada.
    "em-pe": [
        Camada("fundo", 0.0, 0.0, 1.0, 1.0),
        Camada("quadro", 0.0, 0.25, 1.0, 608 / 1920, cantos=_CANTOS, borda=_BORDA),
    ],
}


def tamanho(formato: str) -> tuple[int, int]:
    _conferir(formato)
    return TAMANHOS[formato]


def camadas(formato: str) -> list[Camada]:
    """As camadas de baixo para cima: fundo e quadro. E so isso - ver o docstring."""
    _conferir(formato)
    return list(_MOLDE[formato])


def caixa(nome: str, formato: str) -> dict:
    """A camada em pixels daquele formato, arredondada uma vez so."""
    largura, altura = tamanho(formato)
    for camada in _MOLDE[formato]:
        if camada.nome == nome:
            return {
                "nome": camada.nome,
                "esquerda": round(camada.x * largura),
                "topo": round(camada.y * altura),
                "largura": round(camada.largura * largura),
                "altura": round(camada.altura * altura),
                "cantos": round(camada.cantos * largura),
                "borda": round(camada.borda * largura),
            }
    raise KeyError(f"o molde nao tem camada '{nome}'")


def para_pagina(camadas_: list[Camada], formato: str) -> dict:
    """O JSON que a previa usa para posicionar em CSS. Tudo ja em pixels."""
    largura, altura = tamanho(formato)
    return {
        "formato": formato,
        "largura": largura,
        "altura": altura,
        "camadas": [caixa(c.nome, formato) for c in camadas_],
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
    caixas = {c.nome: caixa(c.nome, formato) for c in camadas_}
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
