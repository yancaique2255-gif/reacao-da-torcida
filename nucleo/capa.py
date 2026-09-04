"""A capa do video, composta com Pillow.

A capa e metade do clique no YouTube: um video bom com capa fraca rende menos
que um video medio com capa forte. A anatomia foi tirada da capa do video de
referencia - bloco de titulo, um rosto grande, uma grade de rostos menores,
placar em cima e a frase embaixo.

**Os rostos saem dos proprios clipes**, no instante do pico, que e onde a cara
esta mais expressiva - e e justamente o numero que o detector ja guardou. Cada
quadro extraido fica em disco: regerar a capa nao reextrai o que ja existe.

Pillow e nao `drawtext`: compor camadas com PIL e direto, e - o que decide - o
PIL sabe MEDIR texto. E por isso que a frase encolhe ate caber em vez de sair
cortada na borda, que e o que acontece no ffmpeg.
"""
from pathlib import Path
from typing import Callable

from nucleo import cortador, estudio, receita, times as mod_times

TAMANHO = (1280, 720)
ARQUIVO = "capa.jpg"
PASTA_SAIDA = "saida"
PASTA_ROSTOS = "rostos"
MAXIMO_DE_ROSTOS = 5

# x, y, largura, altura - onde os rostos moram na capa.
REGIAO = (40, 232, 1200, 384)
VAO = 12  # o ar entre dois rostos
COR_TEXTO = (255, 255, 255)
COR_SOMBRA = (0, 0, 0)


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
    from PIL import ImageDraw, ImageFont

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
    from PIL import Image

    cadastrados = mod_times.carregar() if cadastrados is None else cadastrados
    pasta_jogo = Path(pasta_jogo)
    partida = dados.get("partida") or {}
    alvo = mod_times.achar(dados_receita.get("torcida_alvo", ""), cadastrados)
    fonte = estudio.fonte_de(cfg)

    tela = _tela(TAMANHO, _rgb(alvo["cor"]))
    _escurecer_bordas(tela)

    quadros = rostos(pasta_jogo, dados, dados_receita, cfg, executar)
    for imagem, caixa in zip(quadros, caixas(len(quadros))):
        _colar(tela, imagem, caixa)

    textos = dados_receita.get("textos") or {}
    _titulo(tela, alvo, fonte)
    _placar(tela, partida, fonte)
    _frase(tela, textos.get("frase_da_capa") or "", fonte)

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
    cor = (cor or "#101418").lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))


def _escurecer_bordas(tela) -> None:
    """Degrade escuro de baixo para cima: e o que faz a frase ser legivel."""
    from PIL import Image, ImageDraw

    largura, altura = tela.size
    escuro = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    desenho = ImageDraw.Draw(escuro)
    for y in range(altura):
        # Preto quase nada em cima, preto forte embaixo.
        alfa = int(210 * (y / altura) ** 2)
        desenho.line([(0, y), (largura, y)], fill=(0, 0, 0, alfa))
    tela.paste(Image.alpha_composite(tela.convert("RGBA"), escuro).convert("RGB"), (0, 0))


def _colar(tela, arquivo: Path, caixa) -> None:
    from PIL import Image, ImageDraw

    x, y, largura, altura = caixa
    rosto = Image.open(arquivo).convert("RGB")
    proporcao = max(largura / rosto.width, altura / rosto.height)
    rosto = rosto.resize(
        (max(1, round(rosto.width * proporcao)), max(1, round(rosto.height * proporcao)))
    )
    esquerda = (rosto.width - largura) // 2
    topo = (rosto.height - altura) // 2
    tela.paste(rosto.crop((esquerda, topo, esquerda + largura, topo + altura)), (x, y))
    ImageDraw.Draw(tela).rectangle(
        (x, y, x + largura - 1, y + altura - 1), outline=(255, 255, 255), width=4
    )


def _texto(tela, texto: str, posicao, tamanho: int, fonte, ancora="la") -> None:
    from PIL import ImageDraw

    if not texto:
        return
    desenho = ImageDraw.Draw(tela)
    letra = _fonte(fonte, tamanho)
    x, y = posicao
    # Sombra dura atras: a capa vai aparecer sobre miniatura clara e escura.
    desenho.text((x + 3, y + 3), texto, font=letra, fill=COR_SOMBRA, anchor=ancora)
    desenho.text((x, y), texto, font=letra, fill=COR_TEXTO, anchor=ancora)


def _titulo(tela, alvo: dict, fonte) -> None:
    _texto(tela, "REAÇÕES", (44, 40), 58, fonte)
    _texto(tela, alvo["adjetivo"] or alvo["curto"] or alvo["nome"].upper(),
           (44, 104), 92, fonte)


def _placar(tela, partida: dict, fonte) -> None:
    if "gols_mandante" not in partida:
        return
    _texto(
        tela,
        f"{partida['gols_mandante']} x {partida['gols_visitante']}",
        (TAMANHO[0] - 44, 48), 84, fonte, ancora="ra",
    )


def _frase(tela, frase: str, fonte) -> None:
    if not frase:
        return
    corpo = fonte_que_cabe(frase, TAMANHO[0] - 88, 64, fonte)
    _texto(tela, frase, (TAMANHO[0] // 2, TAMANHO[1] - 48), corpo, fonte, ancora="ms")
