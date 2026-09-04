"""O molde do canal: uma declaracao so, dois renderizadores.

A previa mora no navegador (HTML/CSS) e o video final sai do ffmpeg. Se cada um
tiver sua propria copia da geometria, os dois divergem - e divergem justamente
quando ninguem esta olhando, depois de alguem mexer num numero de um lado so.
Uma previa que mente e pior do que nao ter previa.

Por isso a geometria vive aqui, em coordenadas de 0 a 1, e os dois lados saem
dela: `para_ffmpeg` e `para_pagina`. O teste compara as duas saidas camada por
camada; mexer num lado so reprova a bateria.

O molde e o formato do canal e nao muda de jogo para jogo. E o que faz os
videos parecerem da mesma casa.
"""
from dataclasses import dataclass
from pathlib import Path

FPS = 30
COR_FUNDO = "#101418"     # o padrao ate a cor do time perdedor entrar
COR_CAIXA = "black@0.55"  # atras dos textos, para ler por cima de qualquer cena
COR_TEXTO = "white"

# Quanto de largura ocupa, em media, um caractere da condensada pesada que o
# projeto usa, em fracao do tamanho da fonte. Medido no primeiro render: e o
# bastante para o molde garantir que o texto cabe antes de mandar para o ffmpeg,
# que nao sabe medir texto nenhum.
LARGURA_DO_CARACTERE = 0.58
MAXIMO_DO_CANAL = 22  # nome de canal maior que isso e cortado antes de desenhar


@dataclass(frozen=True)
class Camada:
    """Uma camada em coordenadas de 0 a 1, medidas na tela do formato.

    `cantos` e `borda` sao fracao da LARGURA e `fonte` e fracao da ALTURA: assim
    o mesmo numero vale nos dois formatos sem virar duas contas diferentes.
    """

    nome: str
    x: float
    y: float
    largura: float
    altura: float
    cantos: float = 0.0
    borda: float = 0.0
    fonte: float = 0.0


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
        Camada("etiqueta", 0.09, 0.72, 0.42, 0.12, fonte=0.045),
        Camada("placar", 0.74, 0.07, 0.20, 0.13, fonte=0.05),
        Camada("cartela", 0.0, 0.0, 1.0, 1.0, fonte=0.075),
    ],
    # Em pe: quadro colado na largura, no terco de cima; placar grande em cima e
    # etiqueta grande embaixo, onde o dedo nao tapa.
    "em-pe": [
        Camada("fundo", 0.0, 0.0, 1.0, 1.0),
        Camada("quadro", 0.0, 0.25, 1.0, 608 / 1920, cantos=_CANTOS, borda=_BORDA),
        Camada("etiqueta", 0.06, 0.62, 0.88, 0.10, fonte=0.032),
        Camada("placar", 0.05, 0.05, 0.90, 0.12, fonte=0.055),
        Camada("cartela", 0.0, 0.0, 1.0, 1.0, fonte=0.075),
    ],
}


def tamanho(formato: str) -> tuple[int, int]:
    _conferir(formato)
    return TAMANHOS[formato]


def camadas(formato: str) -> list[Camada]:
    """As camadas de baixo para cima: fundo, quadro, etiqueta, placar, cartela."""
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
                "fonte": round(camada.fonte * altura),
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
    canal: str = "",
    torcida: str = "",
    placar: str = "",
    fonte: Path | None = None,
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
        f"[{entrada}]scale={quadro['largura']}:{quadro['altura']}:"
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

    if canal:
        etiqueta = caixas["etiqueta"]
        recheio = round(etiqueta["altura"] * 0.18)
        desenhos = [
            _caixa_de_texto(etiqueta),
            _texto(
                canal,
                etiqueta["esquerda"] + recheio,
                etiqueta["topo"] + recheio,
                etiqueta["fonte"],
                fonte,
            ),
        ]
        if torcida:
            desenhos.append(
                _texto(
                    f"torcida do {torcida}",
                    etiqueta["esquerda"] + recheio,
                    etiqueta["topo"] + recheio * 2 + etiqueta["fonte"],
                    round(etiqueta["fonte"] * 0.62),
                    fonte,
                )
            )
        partes.append(f"[{ultimo}]" + ",".join(desenhos) + "[com-etiqueta]")
        ultimo = "com-etiqueta"

    if placar:
        caixa_placar = caixas["placar"]
        recheio = round(caixa_placar["altura"] * 0.2)
        desenhos = [
            _caixa_de_texto(caixa_placar),
            _texto(
                placar,
                caixa_placar["esquerda"] + recheio,
                caixa_placar["topo"] + recheio,
                caixa_placar["fonte"],
                fonte,
            ),
        ]
        partes.append(f"[{ultimo}]" + ",".join(desenhos) + "[com-placar]")
        ultimo = "com-placar"

    partes.append(f"[{ultimo}]setsar=1[v]")
    return ";".join(partes)


def filtro_cartela(
    formato: str,
    texto: str,
    cor_fundo: str = COR_FUNDO,
    fonte: Path | None = None,
    duracao: float = 2.0,
    fps: int = FPS,
) -> str:
    """A cartela que anuncia o gol antes da primeira reacao dele."""
    largura, altura = tamanho(formato)
    cartela = caixa("cartela", formato)
    return (
        f"color=c={cor_fundo}:s={largura}x{altura}:r={fps}:d={duracao},vignette=PI/4,"
        + _texto(texto, "(w-text_w)/2", "(h-text_h)/2", cartela["fonte"], fonte)
        + "[v]"
    )


def cabe(texto: str, caixa_: dict, recheio: float = 0.18) -> bool:
    """Se aquele texto cabe naquela caixa, no tamanho de fonte da camada.

    O drawtext do ffmpeg nao sabe encolher texto: o que nao cabe vaza por cima
    do video. Entao quem garante e o molde, e o teste cobra.
    """
    sobra = caixa_["largura"] - 2 * round(caixa_["altura"] * recheio)
    return len(texto) * caixa_["fonte"] * LARGURA_DO_CARACTERE <= sobra


def escapar(texto: str) -> str:
    """Escapa o que o drawtext trata como sintaxe. Nome de canal tem de tudo."""
    for de, para in [("\\", "\\\\"), (":", "\\:"), ("'", "\\'"), ("%", "\\%")]:
        texto = texto.replace(de, para)
    return texto


def caminho_de_fonte(arquivo: Path) -> str:
    """Converte o caminho da fonte para o que o filtro entende.

    O drawtext do ffmpeg no Windows exige `fontfile=` explicito, e o dois-pontos
    da unidade e sintaxe de filtro: sem escapar, falha com "Cannot find a valid
    font".
    """
    return str(arquivo).replace("\\", "/").replace(":", "\\:")


def _caixa_de_texto(caixa_: dict) -> str:
    return (
        f"drawbox=x={caixa_['esquerda']}:y={caixa_['topo']}:"
        f"w={caixa_['largura']}:h={caixa_['altura']}:color={COR_CAIXA}:t=fill"
    )


def _texto(texto: str, x, y, tamanho_fonte: int, fonte: Path | None) -> str:
    partes = ["drawtext="]
    if fonte:
        partes.append(f"fontfile='{caminho_de_fonte(Path(fonte))}':")
    partes.append(
        f"text='{escapar(texto)}':x={x}:y={y}:"
        f"fontsize={tamanho_fonte}:fontcolor={COR_TEXTO}"
    )
    return "".join(partes)


def _conferir(formato: str) -> None:
    if formato not in TAMANHOS:
        raise ValueError(
            f"formato '{formato}' nao existe - use 'deitado' (16:9) ou 'em-pe' (9:16)"
        )
