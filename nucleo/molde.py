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

**O desenho esta escrito em `docs/DESIGN-DO-VIDEO.md`**, que traduz o sistema da
Ollama (https://getdesign.md/ollama/design-md) para esta superficie: superficie
chapada sem degrade nenhum, estrutura por fio de cabelo, pilula para tudo o que
e etiqueta, e a tipografia do sistema em tres papeis. A unica inversao de
superficie e a propria tela - o fundo e a cor do time que perdeu, e o cromado
por cima dele e pilula branca com texto preto. O `test_design_do_video.py`
cobra que aquele documento e este arquivo digam o mesmo numero.
"""
from dataclasses import dataclass
from pathlib import Path

FPS = 30
COR_FUNDO = "#101418"       # o padrao ate a cor do time perdedor entrar

# O cromado, e so ele. A cor de marca e a do time, e ela e o FUNDO.
COR_PILULA = "#ffffff"      # {colors.canvas}
COR_NA_PILULA = "black"     # {colors.ink}
COR_TEXTO = "white"         # {colors.on-dark}
COR_TEXTO_FRACO = "white@0.72"  # {colors.on-dark-mute}
COR_FIO = "white@0.22"      # {colors.hairline}
# A pilula e branca e a transmissao tem cromado branco proprio: sem um fio de
# contorno, a pilula do placar some em cima da barra de patrocinadores do canal.
# O sistema de origem ja resolve isso - o `button-secondary` dele e branco com
# fio de `{colors.hairline-strong}`, que e uma superficie branca que precisa se
# destacar de outra branca.
COR_FIO_FORTE = "#d4d4d4"   # {colors.hairline-strong}

# Os tres papeis de letra. Nenhum deles e fonte de marca: e a decisao de nao
# ter uma decisao de tipografia, que e o que faz o sistema parecer nativo.
LETRAS = ("display", "sans", "mono")

# Quanto de largura ocupa, em media, um caractere, em fracao do tamanho da
# fonte. Medido no primeiro render: e o bastante para o molde garantir que o
# texto cabe antes de mandar para o ffmpeg, que nao sabe medir texto nenhum.
LARGURA_DO_CARACTERE = 0.58
# Quanto de altura ocupa a caixa de texto do drawtext, em fracao do corpo. Serve
# para centrar o texto na pilula em vez de encosta-lo no topo.
ALTURA_DO_TEXTO = 1.2
MAXIMO_DO_CANAL = 22    # nome de canal maior que isso e cortado antes de desenhar
MAXIMO_DA_TORCIDA = 12  # "TORCIDA DO " mais isto e o que cabe na pilula

# O recuo de toda pilula para dentro da borda do quadro, nos quatro lados, e o
# trilho esquerdo da cartela. Um numero so, aplicado em tudo - o equivalente ao
# `{spacing.section}` de 88 px que a Ollama usa liberalmente.
RECUO = 0.04
# `{rounded.lg}`: 24 px no deitado. A outra forma do sistema e a pilula, cujo
# canto e sempre metade da altura da propria camada (`{rounded.full}`).
CANTOS_DO_QUADRO = 24 / 1920
# O fio tem 3 px, e nao 1: 1 px desaparece na compressao H.264 do YouTube. E a
# unica medida do sistema que nao e a da origem, e o motivo e o meio.
FIO = 3 / 1920
# Recheio horizontal da pilula, em fracao da altura dela. Menos que isso e o
# texto encosta na curva da ponta.
RECHEIO_DA_PILULA = 0.34


@dataclass(frozen=True)
class Camada:
    """Uma camada em coordenadas de 0 a 1, medidas na tela do formato.

    `cantos` e `borda` sao fracao da LARGURA e `fonte` e fracao da ALTURA: assim
    o mesmo numero vale nos dois formatos sem virar duas contas diferentes.

    `pilula` faz o canto ser metade da altura da camada, que e o `{rounded.full}`
    do sistema - o unico jeito de o mesmo numero dar uma pilula de verdade nos
    dois formatos. `letra` diz de que dos tres papeis o texto sai.
    """

    nome: str
    x: float
    y: float
    largura: float
    altura: float
    cantos: float = 0.0
    borda: float = 0.0
    fonte: float = 0.0
    letra: str = ""
    pilula: bool = False


TAMANHOS = {"deitado": (1920, 1080), "em-pe": (1080, 1920)}

_MOLDE = {
    # Deitado: quadro de 1728x972 em 96,54 - a margem de 5% e o que deixa o
    # fundo aparecer. Sem ela, um clipe de webcam em tela cheia continua sendo
    # um clipe de webcam, e nao um produto. As pilulas ficam dentro do quadro,
    # a um recuo da borda dele: nome do canal e torcida embaixo a esquerda,
    # placar em cima a direita.
    "deitado": [
        Camada("fundo", 0.0, 0.0, 1.0, 1.0),
        Camada("quadro", 0.05, 0.05, 0.90, 0.90, cantos=CANTOS_DO_QUADRO, borda=FIO),
        Camada("etiqueta", 0.09, 0.804, 0.34, 0.075,
               fonte=0.042, letra="sans", pilula=True),
        Camada("torcida", 0.442, 0.804, 0.24, 0.075,
               fonte=0.026, letra="mono", pilula=True),
        Camada("placar", 0.76, 0.121, 0.15, 0.075,
               fonte=0.05, letra="mono", pilula=True),
        # A cartela e um bloco alinhado a esquerda, no mesmo trilho da etiqueta,
        # lido de cima para baixo como uma secao de documento: onde estamos, o
        # que mudou, a regua, e de que jogo se trata.
        Camada("cartela", 0.0, 0.0, 1.0, 1.0),
        Camada("cartela-marca", 0.09, 0.315, 0.125, 0.075,
               fonte=0.038, letra="mono", pilula=True),
        Camada("cartela-titulo", 0.09, 0.425, 0.82, 0.13,
               fonte=0.09, letra="display"),
        Camada("cartela-regra", 0.09, 0.60, 0.50, 3 / 1080, borda=FIO),
        Camada("cartela-meta", 0.09, 0.635, 0.82, 0.05, fonte=0.028, letra="mono"),
    ],
    # Em pe: quadro colado na largura, no terco de cima; placar grande em cima e
    # as duas pilulas EMPILHADAS embaixo do quadro, onde o dedo nao tapa - 1080
    # px de largura nao comportam as duas em linha.
    "em-pe": [
        Camada("fundo", 0.0, 0.0, 1.0, 1.0),
        Camada("quadro", 0.0, 0.25, 1.0, 608 / 1920,
               cantos=CANTOS_DO_QUADRO, borda=FIO),
        Camada("etiqueta", 0.06, 0.60, 0.62, 0.048,
               fonte=0.024, letra="sans", pilula=True),
        Camada("torcida", 0.06, 0.658, 0.50, 0.038,
               fonte=0.016, letra="mono", pilula=True),
        Camada("placar", 0.06, 0.075, 0.42, 0.048,
               fonte=0.032, letra="mono", pilula=True),
        Camada("cartela", 0.0, 0.0, 1.0, 1.0),
        Camada("cartela-marca", 0.06, 0.36, 0.24, 0.042,
               fonte=0.021, letra="mono", pilula=True),
        Camada("cartela-titulo", 0.06, 0.425, 0.88, 0.05,
               fonte=0.028, letra="display"),
        Camada("cartela-regra", 0.06, 0.50, 0.50, 3 / 1920, borda=FIO),
        Camada("cartela-meta", 0.06, 0.525, 0.88, 0.03, fonte=0.016, letra="mono"),
    ],
}

# As camadas de cromado do clipe, na ordem em que sao desenhadas.
CROMADO = ("etiqueta", "torcida", "placar")


def tamanho(formato: str) -> tuple[int, int]:
    _conferir(formato)
    return TAMANHOS[formato]


def camadas(formato: str) -> list[Camada]:
    """As camadas de baixo para cima: o fundo primeiro, a cartela por cima."""
    _conferir(formato)
    return list(_MOLDE[formato])


def caixa(nome: str, formato: str) -> dict:
    """A camada em pixels daquele formato, arredondada uma vez so."""
    largura, altura = tamanho(formato)
    for camada in _MOLDE[formato]:
        if camada.nome != nome:
            continue
        alta = round(camada.altura * altura)
        return {
            "nome": camada.nome,
            "esquerda": round(camada.x * largura),
            "topo": round(camada.y * altura),
            "largura": round(camada.largura * largura),
            "altura": alta,
            # `{rounded.full}` por construcao: pilula tem canto de metade da
            # altura dela, em qualquer formato, sem segundo numero para manter.
            "cantos": alta // 2 if camada.pilula else round(camada.cantos * largura),
            "borda": round(camada.borda * largura),
            "fonte": round(camada.fonte * altura),
            "letra": camada.letra,
            "recheio": round(alta * RECHEIO_DA_PILULA) if camada.pilula else 0,
            "pilula": camada.pilula,
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
    fontes: dict | None = None,
    entrada: str = "0:v",
    imagens: dict | None = None,
    fps: int = FPS,
) -> str:
    """O filter_complex de um item, montado das mesmas camadas.

    `imagens` mapeia nome de camada para entrada de imagem do ffmpeg - os PNGs
    de forma que o estudio gera com PIL: `mascara` e `moldura` (os cantos e o
    fio do quadro) e uma pilula por camada de cromado. Camada sem imagem cai
    para um retangulo de canto reto: e o caminho degradado, para espiar um
    quadro parado sem PNG nenhum no disco.

    Nao ha degrade nem vinheta em lugar nenhum: a cor do time cobre a tela
    chapada. E a primeira regra do sistema.
    """
    imagens = imagens or {}
    largura, altura = tamanho(formato)
    caixas = {c.nome: caixa(c.nome, formato) for c in camadas_}
    quadro = caixas["quadro"]
    partes = [f"color=c={cor_fundo}:s={largura}x{altura}:r={fps}[fundo]"]

    corte = (
        # `setpts=PTS-STARTPTS` primeiro, e nao por capricho: com `-ss` no
        # clipe, o primeiro quadro dele chega com o relogio deslocado, DEPOIS
        # do primeiro quadro do fundo - e o `overlay` deixa passar o fundo
        # pelado. O ESPIAR, que e um quadro so, saia vermelho chapado; no video
        # inteiro era um piscar de cor no comeco de cada clipe.
        f"[{entrada}]setpts=PTS-STARTPTS,"
        f"scale={quadro['largura']}:{quadro['altura']}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={quadro['largura']}:{quadro['altura']},setsar=1"
    )
    if imagens.get("mascara"):
        partes.append(f"{corte}[recortado]")
        partes.append(
            f"[{imagens['mascara']}]scale={quadro['largura']}:{quadro['altura']}[cantos]"
        )
        partes.append("[recortado][cantos]alphamerge[quadro]")
    else:
        partes.append(f"{corte}[quadro]")

    partes.append(
        f"[fundo][quadro]overlay={quadro['esquerda']}:{quadro['topo']}"
        f":shortest=1[com_quadro]"
    )
    ultimo = "com_quadro"
    if imagens.get("moldura"):
        partes.append(
            f"[{ultimo}][{imagens['moldura']}]"
            f"overlay={quadro['esquerda']}:{quadro['topo']}[com_moldura]"
        )
        ultimo = "com_moldura"

    textos = {"etiqueta": canal, "torcida": torcida, "placar": placar}
    for nome in CROMADO:
        if not textos.get(nome) or nome not in caixas:
            continue
        ultimo = _pilula(
            partes, ultimo, caixas[nome], textos[nome], fontes,
            imagens.get(nome), COR_NA_PILULA,
        )

    partes.append(f"[{ultimo}]setsar=1[v]")
    return ";".join(partes)


def filtro_cartela(
    formato: str,
    marca: str,
    titulo: str,
    meta: str = "",
    cor_fundo: str = COR_FUNDO,
    fontes: dict | None = None,
    duracao: float = 2.0,
    fps: int = FPS,
    imagens: dict | None = None,
) -> str:
    """A cartela que anuncia o gol antes da primeira reacao dele.

    Saia `GOL 3` centralizado no meio da tela. Sao quatro camadas alinhadas a
    esquerda, no trilho do recuo: a marca do gol numa pilula, o placar por
    extenso no unico display do sistema, uma regua de fio, e a linha de meta.
    """
    imagens = imagens or {}
    largura, altura = tamanho(formato)
    partes = [
        f"color=c={cor_fundo}:s={largura}x{altura}:r={fps}:d={duracao}[fundo_cartela]"
    ]
    ultimo = "fundo_cartela"

    if marca:
        ultimo = _pilula(
            partes, ultimo, caixa("cartela-marca", formato), marca, fontes,
            imagens.get("cartela-marca"), COR_NA_PILULA,
        )
    if titulo:
        ultimo = _linha_de_texto(
            partes, ultimo, caixa("cartela-titulo", formato), titulo, fontes, COR_TEXTO
        )

    regua = caixa("cartela-regra", formato)
    partes.append(
        f"[{ultimo}]{_fio(regua)}[posto_cartela_regra]"
    )
    ultimo = "posto_cartela_regra"

    if meta:
        ultimo = _linha_de_texto(
            partes, ultimo, caixa("cartela-meta", formato), meta, fontes,
            COR_TEXTO_FRACO,
        )

    partes.append(f"[{ultimo}]setsar=1[v]")
    return ";".join(partes)


def cabe(texto: str, caixa_: dict) -> bool:
    """Se aquele texto cabe naquela caixa, no tamanho de fonte da camada.

    O drawtext do ffmpeg nao sabe encolher texto: o que nao cabe vaza por cima
    do video. Entao quem garante e o molde, e o teste cobra - com o pior texto
    possivel de cada camada, em cada formato.
    """
    sobra = caixa_["largura"] - 2 * caixa_.get("recheio", 0)
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


# ------------------------------------------------------------------- as camadas

def _pilula(
    partes: list, ultimo: str, caixa_: dict, texto: str, fontes, imagem, cor: str
) -> str:
    """Uma pilula de forma com o texto por cima, e devolve o rotulo novo.

    A forma vem de um PNG do Pillow - canto arredondado no ffmpeg puro daria um
    `geq` caro e ilegivel. O `scale` carrega o tamanho e o `overlay` carrega a
    posicao, e por isso da para ler a geometria de volta do filtro, como o
    ffmpeg leria, e cobrar que ela bate com a da pagina.
    """
    nome = caixa_["nome"].replace("-", "_")
    if imagem:
        partes.append(
            f"[{imagem}]scale={caixa_['largura']}:{caixa_['altura']}[forma_{nome}]"
        )
        partes.append(
            f"[{ultimo}][forma_{nome}]"
            f"overlay={caixa_['esquerda']}:{caixa_['topo']}[fundo_{nome}]"
        )
    else:
        # Caminho degradado: sem o PNG, um retangulo de canto reto. Serve para
        # espiar um quadro parado sem forma nenhuma no disco.
        partes.append(
            f"[{ultimo}]drawbox=x={caixa_['esquerda']}:y={caixa_['topo']}:"
            f"w={caixa_['largura']}:h={caixa_['altura']}:color={COR_PILULA}:t=fill"
            f"[fundo_{nome}]"
        )
    partes.append(
        f"[fundo_{nome}]"
        + _texto(
            texto,
            caixa_["esquerda"] + caixa_["recheio"],
            _meio_do_texto(caixa_),
            caixa_["fonte"],
            _letra(fontes, caixa_["letra"]),
            cor,
        )
        + f"[posto_{nome}]"
    )
    return f"posto_{nome}"


def _linha_de_texto(
    partes: list, ultimo: str, caixa_: dict, texto: str, fontes, cor: str
) -> str:
    """Texto solto sobre a cor do time, sem caixa nenhuma atras. O ar e o fundo."""
    nome = caixa_["nome"].replace("-", "_")
    partes.append(
        f"[{ultimo}]"
        + _texto(
            texto, caixa_["esquerda"], caixa_["topo"], caixa_["fonte"],
            _letra(fontes, caixa_["letra"]), cor,
        )
        + f"[posto_{nome}]"
    )
    return f"posto_{nome}"


def _fio(caixa_: dict) -> str:
    """A regua de fio de cabelo. Separar sem divisoria decorativa nenhuma."""
    return (
        f"drawbox=x={caixa_['esquerda']}:y={caixa_['topo']}:"
        f"w={caixa_['largura']}:h={caixa_['altura']}:color={COR_FIO}:t=fill"
    )


def _meio_do_texto(caixa_: dict) -> int:
    """O `y` que centra o texto na pilula, e nao o que o encosta no topo."""
    return caixa_["topo"] + max(
        0, round((caixa_["altura"] - caixa_["fonte"] * ALTURA_DO_TEXTO) / 2)
    )


def _letra(fontes, papel: str) -> Path | None:
    """O arquivo do papel pedido. Sem os tres, o que houver; sem nada, o sistema."""
    if not fontes:
        return None
    if isinstance(fontes, (str, Path)):
        return Path(fontes)
    return fontes.get(papel) or fontes.get("sans") or None


def _texto(texto: str, x, y, tamanho_fonte: int, fonte: Path | None, cor: str) -> str:
    partes = ["drawtext="]
    if fonte:
        partes.append(f"fontfile='{caminho_de_fonte(Path(fonte))}':")
    partes.append(
        f"text='{escapar(texto)}':x={x}:y={y}:"
        f"fontsize={tamanho_fonte}:fontcolor={cor}"
    )
    return "".join(partes)


def _conferir(formato: str) -> None:
    if formato not in TAMANHOS:
        raise ValueError(
            f"formato '{formato}' nao existe - use 'deitado' (16:9) ou 'em-pe' (9:16)"
        )
