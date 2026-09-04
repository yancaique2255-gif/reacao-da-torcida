"""A capa do video, composta com Pillow.

A capa e metade do clique no YouTube: um video bom com capa fraca rende menos
que um video medio com capa forte.

**Os rostos saem dos proprios clipes**, no instante do pico, que e onde a cara
esta mais expressiva - e e justamente o numero que o detector ja guardou. Cada
quadro extraido fica em disco: regerar a capa nao reextrai o que ja existe.

Pillow e nao `drawtext`: compor camadas com PIL e direto, e - o que decide - o
PIL sabe MEDIR texto. E por isso que a frase encolhe ate caber em vez de sair
cortada na borda, que e o que acontece no ffmpeg, e por isso as pilulas daqui
abracam o texto em vez de ter largura fixa.

**O desenho esta em `docs/DESIGN-DO-VIDEO.md`**: a mesma gramatica do video -
superficie chapada na cor do time, pilula branca com texto preto para toda
etiqueta, foto em `{rounded.lg}` com fio de cabelo, e nada de degrade.
"""
from pathlib import Path
from typing import Callable

from nucleo import cortador, estudio, molde, receita, times as mod_times

TAMANHO = (1280, 720)
ARQUIVO = "capa.jpg"
PASTA_SAIDA = "saida"
PASTA_ROSTOS = "rostos"
MAXIMO_DE_ROSTOS = 5

# x, y, largura, altura - onde os rostos moram na capa.
REGIAO = (40, 232, 1200, 384)
VAO = 12   # o ar entre dois rostos
RECUO = 40  # o mesmo recuo dos quatro lados, como no molde do video

# O cromado, traduzido do molde para o RGBA que o Pillow entende.
CANTOS = 24              # {rounded.lg}, o mesmo canto do quadro do video
FIO = 3                  # {colors.hairline} em 3 px, que a compressao nao come
COR_PILULA = (255, 255, 255)
COR_NA_PILULA = (0, 0, 0)
COR_TEXTO = (255, 255, 255)

# A anatomia do bloco de titulo, do placar e da frase.
CORPO_DO_SOBRETITULO = 40
CORPO_DO_TITULO = 92
CORPO_DO_PLACAR = 54
CORPO_DA_FRASE = 44
ALTURA_DA_PILULA = 76
RECHEIO_DA_PILULA = 26


def caixas(quantos: int, regiao=REGIAO) -> list[tuple[int, int, int, int]]:
    """Um layout que se adapta a 1, 2, 3, 4 ou 5 rostos, sem sobrar buraco.

    O layout era fixo em 1 rosto grande mais 4 pequenos, cinco canais. No jogo
    de 03/09 entraram tres: sobrou um quadrante vermelho vazio embaixo a
    direita, e a composicao saiu torta.

    Quantidade impar ganha um rosto grande a esquerda e os outros numa grade a
    direita - e a anatomia da capa de referencia, e e o que poe a cara mais
    forte no lugar maior. Quantidade par divide igual.
    """
    quantos = max(1, min(int(quantos), MAXIMO_DE_ROSTOS))
    if quantos == 1:
        return [tuple(regiao)]
    if quantos == 2:
        return _colunas(regiao, 2)
    if quantos == 4:
        return _grade(regiao, colunas=2, linhas=2)
    grande, resto = _partir(regiao, 0.5 if quantos == 3 else 0.4)
    if quantos == 3:
        return [grande] + _linhas(resto, 2)
    return [grande] + _grade(resto, colunas=2, linhas=2)


def caixa_da_frase() -> tuple[int, int, int, int]:
    """Onde a pilula da frase comeca. A largura dela abraca o texto.

    Abaixo da faixa de rostos, e nao por cima dela: era o degrade preto que
    dava legibilidade a frase sobre a foto, e o degrade saiu do sistema.
    """
    _, y, _, altura = REGIAO
    return (RECUO, y + altura + 24, TAMANHO[0] - 2 * RECUO, ALTURA_DA_PILULA)


def caixa_do_placar(texto: str, cfg: dict) -> tuple[int, int, int, int]:
    """A pilula do placar, encostada a direita e medida no texto de verdade."""
    largura = _largura_da_pilula(texto, CORPO_DO_PLACAR, fontes_de(cfg)["mono"])
    return (TAMANHO[0] - RECUO - largura, RECUO + 8, largura, ALTURA_DA_PILULA)


def fontes_de(cfg: dict) -> dict:
    """Os tres papeis de letra, os mesmos do video."""
    return estudio.fontes_de(cfg)


def rostos(
    pasta_jogo: Path,
    dados: dict,
    dados_receita: dict,
    cfg: dict,
    executar: Callable[[list[str]], None] | None = None,
    quantos: int = MAXIMO_DE_ROSTOS,
) -> list[Path]:
    """Um quadro por canal que entra no video, no instante do pico.

    Na ordem da receita, que ja vem do mais explosivo para o mais morno: a cara
    mais forte fica no lugar maior.
    """
    executar = executar or cortador.executar
    pasta_jogo = Path(pasta_jogo)
    clipes = {(c["gol"], c["canal"]): c for c in dados.get("clipes", [])}
    pasta = pasta_jogo / estudio.PASTA_CACHE / PASTA_ROSTOS
    pasta.mkdir(parents=True, exist_ok=True)

    achados = []
    vistos = set()
    for item in receita.itens_do_video(dados_receita):
        if item["canal"] in vistos or len(achados) >= quantos:
            continue
        clipe = clipes.get((item["gol"], item["canal"]))
        if clipe is None:
            continue
        vistos.add(item["canal"])
        instante = estudio.instante_de_espiar(clipe, item)
        destino = pasta / f"{item['canal']}-{item['gol']}.jpg"
        if not destino.is_file():
            executar([
                cfg["caminho_ffmpeg"], "-y",
                "-ss", str(instante), "-i", str(pasta_jogo / clipe["arquivo"]),
                "-frames:v", "1", "-update", "1", str(destino),
            ])
        if destino.is_file():
            achados.append(destino)
    return achados


def fonte_que_cabe(texto: str, largura: int, tamanho: int, arquivo: Path | None) -> int:
    """O maior tamanho de fonte em que aquele texto cabe naquela largura.

    O PIL mede o texto de verdade, entao aqui nao ha chute: a frase da capa
    encolhe ate caber em vez de sair cortada.
    """
    from PIL import ImageDraw

    if not texto:
        return tamanho
    medidor = ImageDraw.Draw(_tela((10, 10), (0, 0, 0)))
    for corpo in range(tamanho, 11, -2):
        if medidor.textlength(texto, font=_fonte(arquivo, corpo)) <= largura:
            return corpo
    return 12


def gerar(
    pasta_jogo: Path,
    dados: dict,
    dados_receita: dict,
    cfg: dict,
    cadastrados: dict | None = None,
    executar: Callable[[list[str]], None] | None = None,
) -> Path:
    """Compoe a `capa.jpg` na pasta de saida do jogo."""
    cadastrados = mod_times.carregar() if cadastrados is None else cadastrados
    pasta_jogo = Path(pasta_jogo)
    partida = dados.get("partida") or {}
    alvo = mod_times.achar(dados_receita.get("torcida_alvo", ""), cadastrados)
    letras = fontes_de(cfg)

    # Superficie chapada: nada de degrade, nada de vinheta, nada de atmosfera.
    tela = _tela(TAMANHO, _rgb(alvo["cor"]))

    quadros = rostos(pasta_jogo, dados, dados_receita, cfg, executar)
    for imagem, caixa in zip(quadros, caixas(len(quadros))):
        _colar(tela, imagem, caixa)

    textos = dados_receita.get("textos") or {}
    _titulo(tela, alvo, letras)
    _placar(tela, partida, letras, cfg)
    _frase(tela, textos.get("frase_da_capa") or "", letras)

    pasta = pasta_jogo / PASTA_SAIDA
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / ARQUIVO
    tela.convert("RGB").save(destino, quality=92)
    return destino


# --------------------------------------------------------------- as camadas

def _tela(tamanho, cor):
    from PIL import Image

    return Image.new("RGB", tamanho, cor)


def _fonte(arquivo: Path | None, tamanho: int):
    from PIL import ImageFont

    if arquivo and Path(arquivo).is_file():
        return ImageFont.truetype(str(arquivo), tamanho)
    # Fonte que nao carrega deixa a capa em letra de sistema: feia, mas legivel.
    return ImageFont.load_default()


def _rgb(cor: str) -> tuple[int, int, int]:
    cor = (cor or molde.COR_FUNDO).lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_do_molde(cor: str) -> tuple[int, int, int]:
    """`#d4d4d4` do molde no RGB que o Pillow desenha."""
    limpa = cor.lstrip("#")
    return tuple(int(limpa[i:i + 2], 16) for i in (0, 2, 4))


def _fio_rgba() -> tuple[int, int, int, int]:
    """O `white@0.22` do molde, para a foto ter o mesmo fio que o quadro."""
    alfa = float(molde.COR_FIO.split("@")[1]) if "@" in molde.COR_FIO else 1.0
    return (255, 255, 255, round(255 * alfa))


def _colar(tela, arquivo: Path, caixa) -> None:
    """A foto em `{rounded.lg}` com fio de cabelo. Nada de caixilho branco."""
    from PIL import Image, ImageDraw

    x, y, largura, altura = caixa
    rosto = Image.open(arquivo).convert("RGB")
    proporcao = max(largura / rosto.width, altura / rosto.height)
    rosto = rosto.resize(
        (max(1, round(rosto.width * proporcao)), max(1, round(rosto.height * proporcao)))
    )
    esquerda = (rosto.width - largura) // 2
    topo = (rosto.height - altura) // 2
    rosto = rosto.crop((esquerda, topo, esquerda + largura, topo + altura))

    mascara = Image.new("L", (largura, altura), 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, largura - 1, altura - 1), radius=CANTOS, fill=255
    )
    tela.paste(rosto, (x, y), mascara)

    fio = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    ImageDraw.Draw(fio).rounded_rectangle(
        (0, 0, largura - 1, altura - 1), radius=CANTOS, outline=_fio_rgba(), width=FIO
    )
    tela.paste(
        Image.alpha_composite(
            tela.crop((x, y, x + largura, y + altura)).convert("RGBA"), fio
        ).convert("RGB"),
        (x, y),
    )


def _largura_da_pilula(texto: str, corpo: int, arquivo: Path | None) -> int:
    """A pilula abraca o texto: o PIL mede, e por isso nao ha largura fixa."""
    from PIL import ImageDraw

    medidor = ImageDraw.Draw(_tela((10, 10), (0, 0, 0)))
    largura = medidor.textlength(texto, font=_fonte(arquivo, corpo))
    return round(largura) + 2 * RECHEIO_DA_PILULA


def _pilula(tela, texto: str, caixa, corpo: int, arquivo: Path | None) -> None:
    """Pilula branca com texto preto - o unico cromado do sistema."""
    from PIL import ImageDraw

    if not texto:
        return
    x, y, _, altura = caixa
    largura = _largura_da_pilula(texto, corpo, arquivo)
    desenho = ImageDraw.Draw(tela)
    # O fio de contorno pelo mesmo motivo do video: a capa vai aparecer sobre
    # miniatura clara e escura, e pilula branca sem fio se dissolve na clara.
    desenho.rounded_rectangle(
        (x, y, x + largura - 1, y + altura - 1),
        radius=altura // 2, fill=COR_PILULA,
        outline=_rgb_do_molde(molde.COR_FIO_FORTE), width=FIO,
    )
    desenho.text(
        (x + RECHEIO_DA_PILULA, y + altura // 2), texto,
        font=_fonte(arquivo, corpo), fill=COR_NA_PILULA, anchor="lm",
    )


def _texto(tela, texto: str, posicao, corpo: int, arquivo: Path | None, ancora="la"):
    from PIL import ImageDraw

    if not texto:
        return
    ImageDraw.Draw(tela).text(
        posicao, texto, font=_fonte(arquivo, corpo), fill=COR_TEXTO, anchor=ancora
    )


def _titulo(tela, alvo: dict, letras: dict) -> None:
    """"REAÇÕES" na sans do sistema; o adjetivo da torcida no display."""
    _texto(tela, "REAÇÕES", (RECUO, RECUO), CORPO_DO_SOBRETITULO, letras["sans"])
    _texto(
        tela,
        alvo["adjetivo"] or alvo["curto"] or alvo["nome"].upper(),
        (RECUO, RECUO + CORPO_DO_SOBRETITULO + 18),
        CORPO_DO_TITULO,
        letras["display"],
    )


def _placar(tela, partida: dict, letras: dict, cfg: dict) -> None:
    if "gols_mandante" not in partida:
        return
    texto = f"{partida['gols_mandante']} x {partida['gols_visitante']}"
    _pilula(tela, texto, caixa_do_placar(texto, cfg), CORPO_DO_PLACAR, letras["mono"])


def _frase(tela, frase: str, letras: dict) -> None:
    if not frase:
        return
    caixa = caixa_da_frase()
    corpo = fonte_que_cabe(
        frase, caixa[2] - 2 * RECHEIO_DA_PILULA, CORPO_DA_FRASE, letras["sans"]
    )
    _pilula(tela, frase, caixa, corpo, letras["sans"])


def _partir(regiao, fracao: float):
    """Corta a regiao em duas colunas, a primeira com `fracao` da largura util."""
    x, y, largura, altura = regiao
    esquerda = round((largura - VAO) * fracao)
    return (
        (x, y, esquerda, altura),
        (x + esquerda + VAO, y, largura - esquerda - VAO, altura),
    )


def _colunas(regiao, quantas: int):
    x, y, largura, altura = regiao
    passo = (largura - VAO * (quantas - 1)) / quantas
    return [
        (x + round(indice * (passo + VAO)), y, round(passo), altura)
        for indice in range(quantas)
    ]


def _linhas(regiao, quantas: int):
    x, y, largura, altura = regiao
    passo = (altura - VAO * (quantas - 1)) / quantas
    return [
        (x, y + round(indice * (passo + VAO)), largura, round(passo))
        for indice in range(quantas)
    ]


def _grade(regiao, colunas: int, linhas: int):
    """Na ordem de leitura: a cara mais forte primeiro, em cima e a esquerda."""
    saida = []
    for faixa in _linhas(regiao, linhas):
        saida.extend(_colunas(faixa, colunas))
    return saida
