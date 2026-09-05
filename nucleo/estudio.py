"""Executa a receita: espiar, previa, final, cache e fila.

A maquina e modesta - Ryzen 5 5600G, seis nucleos, sem placa de video dedicada.
Um video de 20 minutos em 1080p com sobreposicoes leva MINUTOS de CPU. Fingir
que e instantaneo seria mentir para o operador, entao sao tres velocidades
declaradas:

- **espiar**: um quadro parado, ja com fundo e quadro. Instantaneo. Serve para
  ver como a cena fica dentro do molde.
- **previa**: o trecho escolhido, cru e com 640 de largura. Segundos.
- **final**: o video inteiro, `libx264`, em fila com progresso. Minutos.

O que torna isso usavel e o **cache por item**: cada peca vira um arquivo com
nome de hash de tudo o que afeta a imagem dela - origem, corte, molde, textos,
formato. Mexer no item 5 refaz o item 5, e mais nada. A emenda e copia de
fluxo, e por isso e instantanea.

O `montador.py` foi a versao anterior disto e continua servindo o painel da
8770 enquanto o novo nao prova que funciona num jogo de verdade. O que ele
tinha de bom veio junto: o `loudnorm` em -16 LUFS e a emenda por `concat`.
"""
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

from nucleo import cortador, identidade, molde, receita, times as mod_times

PASTA_CACHE = "intermediarios"
# As pecas prontas moram numa pasta propria, e chegar la e o batismo: um arquivo
# so recebe o nome final depois de o ffmpeg sair com codigo zero. Antes disso o
# render escrevia direto no nome final, e um ffmpeg morto no meio deixava um
# .mp4 de 48 bytes que o render seguinte reaproveitava como peca boa - a
# compilacao de 03/09 saiu 60s mais curta sem uma linha de aviso.
PASTA_PECAS = "pecas"
# O cenario do canal mora numa prateleira propria do cache: e forma, e nao peca
# de video, e da para abrir no visualizador e conferir antes de gastar treze
# minutos de render.
PASTA_FORMAS = "formas"
# O ar entre a arte e a marca, medido no palco de 1920x1080.
VAO_DO_PALCO = 16
# Os icones das redes vao versionados no repositorio, em PNG branco com
# transparencia, com o nome da chave em `identidade.redes`.
PASTA_DOS_ICONES = Path(__file__).resolve().parent.parent / "dados" / "icones"
PASTA_SAIDA = "saida"
NOME_ESTADO = "render.json"
FORMATO_PADRAO = "deitado"
TETO_CACHE_GB = 5

# Cada canal grava com o volume que quer: um berra, o outro mal se ouve. Numa
# compilacao que corta de um para o outro isso e insuportavel, entao todo clipe
# passa pelo mesmo alvo (a recomendacao de streaming, -16 LUFS).
VOLUME_ALVO = "loudnorm=I=-16:TP=-1.5:LRA=11"
# So a largura: a altura sai da proporcao do clipe, para a previa nunca
# entortar uma imagem que no render final seria recortada.
LARGURA_DA_PREVIA = 640
# O travamento do ffmpeg e intermitente: o mesmo item, dez vezes, travou em ~2
# de cada 3. Tres tentativas e o que faz um travamento virar um recado em vez
# de um render morto.
TENTATIVAS = 3
# Quanto tempo depois de nascer um PID ainda conta como vivo sem o tasklist
# confirmar. Medido: o `tasklist` demora alguns segundos para enxergar um
# processo recem-criado.
CARENCIA_DO_PID = 15.0

_VIDEO_FINAL = [
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
    "-pix_fmt", "yuv420p", "-r", str(molde.FPS),
]
_AUDIO = ["-c:a", "aac", "-b:a", "128k", "-ar", "48000"]


# ---------------------------------------------------------------- os caminhos

def pasta_cache(pasta_jogo: Path) -> Path:
    return Path(pasta_jogo) / PASTA_CACHE


def pasta_das_pecas(pasta_jogo: Path) -> Path:
    """Onde vivem as pecas que o ffmpeg terminou. Nada mais entra aqui."""
    return pasta_cache(pasta_jogo) / PASTA_PECAS


def fazer_peca(
    destino: Path, comando_de, executar, avisar, qual: str,
    tentativas: int = TENTATIVAS,
) -> None:
    """Renderiza para um nome temporario e batiza a peca so no fim.

    Arquivo truncado tem nome, tamanho e data de arquivo bom - nao ha como
    olhar um .mp4 no cache e saber se ele saiu inteiro. O que da para saber e
    quem passou pelo ffmpeg com codigo zero, e e disso que o nome final vira
    prova. Foi o que faltou em 03/09: o `baldasso-tv` do gol 4 morreu no meio,
    e os dois renders seguintes reaproveitaram os 48 bytes que ele deixou.

    Tenta de novo porque o travamento e intermitente: o mesmo item, repetido
    dez vezes, travou em ~2 de cada 3. Refazer transforma "painel morto" em
    "item X falhou, refazendo" - e quando nem assim volta, o que sobe para a
    tela sao as ultimas linhas do ffmpeg, e nao um traceback de Python.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    meio = destino.parent.parent / f"parcial-{destino.name}"
    for tentativa in range(1, max(1, tentativas) + 1):
        try:
            executar(comando_de(meio))
        except cortador.FALHAS as erro:
            meio.unlink(missing_ok=True)
            recado = cortador.motivo(erro)
            if tentativa >= max(1, tentativas):
                avisar(f"FALHOU: {qual} - {recado}")
                raise
            avisar(f"{qual}: {recado}\nrefazendo ({tentativa + 1} de {tentativas})")
            continue
        except BaseException:
            meio.unlink(missing_ok=True)
            raise
        os.replace(meio, destino)
        avisar(f"pronto: {qual}")
        return


def chave_da_peca(
    origem: str, de: float, ate: float, filtro: str, palco: str = ""
) -> str:
    """Hash de tudo o que afeta a imagem daquela peca.

    O filtro ja carrega molde, formato, textos e cores: mudar qualquer um deles
    muda o nome do arquivo, e o cache percebe sozinho. Nao ha versao para
    lembrar de incrementar.

    O nome era `identidade`, e virou `chave_da_peca` quando a identidade DO
    CANAL passou a ser um modulo: duas coisas com o mesmo nome no mesmo arquivo
    e defeito esperando hora.

    O `palco` e a assinatura do cenario, e entra na chave SO QUANDO EXISTE: o
    filtro nomeia a entrada do palco ([3:v]), mas nao diz qual PNG e - trocar a
    arte mudaria a imagem sem mudar a chave. Acrescentar o campo sempre, mesmo
    vazio, renomearia de uma vez todo o cache que ja esta no disco.
    """
    crua = json.dumps(
        [origem, round(float(de), 3), round(float(ate), 3), filtro]
        + ([palco] if palco else []),
        ensure_ascii=False,
    )
    return hashlib.sha1(crua.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ os textos

def placar_do_gol(dados: dict, numero: int) -> str:
    """"Grêmio 1 x 0 Internacional" - o placar DAQUELE gol, nao o final.

    Vazio quando o gol foi anotado antes de o placar do momento existir: dizer
    o que se sabe, e nunca inventar um numero na tela.
    """
    partida = dados.get("partida") or {}
    for gol in dados.get("gols", []):
        if gol["numero"] == numero and gol.get("placar"):
            casa, fora = gol["placar"]
            return (
                f"{partida.get('mandante', '')} {casa} x "
                f"{fora} {partida.get('visitante', '')}"
            ).strip()
    return ""


# ------------------------------------------------------------------- as pecas

def mascaras(
    pasta_jogo: Path, formato: str, moldagem: dict | None = None
) -> tuple[Path, Path]:
    """Os dois PNGs do quadro: o recorte dos cantos e a borda clara.

    Cantos arredondados no ffmpeg puro dariam um `geq` caro e ilegivel; com o
    Pillow sai uma imagem so, feita uma vez por formato e reaproveitada. A
    geometria vem do molde - o mesmo numero que a tela usa em CSS.
    """
    from PIL import Image, ImageDraw

    quadro = molde.caixa("quadro", formato, **(moldagem or {}))
    largura, altura = quadro["largura"], quadro["altura"]
    canto, borda = quadro["cantos"], quadro["borda"]
    pasta = pasta_cache(pasta_jogo)
    pasta.mkdir(parents=True, exist_ok=True)

    alvo_mascara = pasta / f"mascara-{formato}-{largura}x{altura}-{canto}.png"
    alvo_moldura = pasta / f"moldura-{formato}-{largura}x{altura}-{canto}-{borda}.png"

    if not alvo_mascara.is_file():
        imagem = Image.new("L", (largura, altura), 0)
        ImageDraw.Draw(imagem).rounded_rectangle(
            (0, 0, largura - 1, altura - 1), radius=canto, fill=255
        )
        imagem.save(alvo_mascara)

    if not alvo_moldura.is_file():
        imagem = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
        ImageDraw.Draw(imagem).rounded_rectangle(
            (0, 0, largura - 1, altura - 1),
            radius=canto, outline=(255, 255, 255, 230), width=max(1, borda),
        )
        imagem.save(alvo_moldura)

    return alvo_mascara, alvo_moldura


# -------------------------------------------------------------------- o palco

def camadas_do_palco(ident: dict, formato: str, moldagem: dict) -> list[str]:
    """Quais camadas de marca este palco desenha, na ordem em que vao ao PNG.

    E a regra central da identidade num lugar so: **campo vazio e camada que NAO
    EXISTE** - nao e camada transparente, nao e espaco reservado. Arranjo sem
    sobra tambem nao tem onde por logo nem barra, e ai elas nao entram nem com
    os campos preenchidos.
    """
    tem = {c.nome for c in molde.camadas(formato, **moldagem)}
    desenhar = []
    if _arquivo_de(ident.get("arte_de_fundo")):
        desenhar.append("arte_de_fundo")
    if "logo" in tem and _arquivo_de(ident.get("logo")):
        desenhar.append("logo")
    if "barra" in tem and arrobas(ident):
        desenhar.append("barra")
    return desenhar


def arrobas(ident: dict) -> list[tuple[str, str]]:
    """As redes preenchidas, na ordem do arquivo. Rede vazia nao ocupa espaco."""
    return [
        (rede, str(arroba).strip())
        for rede, arroba in (ident.get("redes") or {}).items()
        if str(arroba).strip()
    ]


def icone(rede: str, corpo: int):
    """O PNG branco de `dados/icones/<rede>.png`, no tamanho da letra.

    Sem icone no disco, a barra sai so com texto: o dono ainda vai por os
    arquivos la, e esperar por eles nao pode travar o palco.
    """
    arquivo = PASTA_DOS_ICONES / f"{rede}.png"
    if not arquivo.is_file():
        return None
    from PIL import Image

    desenhado = Image.open(arquivo).convert("RGBA")
    desenhado.thumbnail((corpo, corpo))
    return desenhado


def tem_o_que_desenhar(ident: dict, formato: str, moldagem: dict) -> bool:
    """Sem nada de marca, o palco nem existe - e o filtro e o de sempre."""
    return bool(camadas_do_palco(ident, formato, moldagem))


def assinatura_do_palco(
    formato: str, ident: dict, moldagem: dict, cor_fundo: str,
    fonte: Path | None = None,
) -> str:
    """Impressao digital do cenario: identidade, moldagem e cor do time.

    Mudou qualquer um, gera outro arquivo; nao mudou nada, reaproveita - o mesmo
    mecanismo do `mascaras()`. O relogio e o tamanho dos arquivos de arte vao
    junto: trocar o PNG por outro com o MESMO nome tem que gerar outro palco,
    senao o cache serve o cenario velho para sempre.
    """
    crua = json.dumps(
        [
            formato,
            {c: ident.get(c, "") for c in ("arte_de_fundo", "logo", "chamada")},
            ident.get("redes") or {},
            moldagem,
            cor_fundo,
            [_relogio_do_arquivo(ident.get(c)) for c in ("arte_de_fundo", "logo")],
            str(fonte or ""),
        ],
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha1(crua.encode("utf-8")).hexdigest()[:16]


def palco(
    pasta_jogo: Path,
    formato: str,
    ident: dict,
    moldagem: dict,
    cor_fundo: str,
    fonte: Path | None = None,
    avisar: Callable[[str], None] | None = None,
) -> Path | None:
    """O PNG do cenario do canal: arte de fundo, logo e barra ja compostos.

    `None` quando nao ha nada de marca para desenhar, e ai o render segue com a
    cor do time e a vinheta do ffmpeg, como antes de o palco existir.

    Um PNG so, e nao tres entradas de imagem: o filtro nao cresce, o numero de
    entradas do ffmpeg nao muda, e o palco vira um arquivo que se abre no
    visualizador e se confere antes de gastar treze minutos de render.
    """
    if not tem_o_que_desenhar(ident, formato, moldagem):
        return None
    marca = assinatura_do_palco(formato, ident, moldagem, cor_fundo, fonte)
    destino = pasta_cache(pasta_jogo) / PASTA_FORMAS / f"palco-{formato}-{marca}.png"
    if destino.is_file():
        return destino

    destino.parent.mkdir(parents=True, exist_ok=True)
    tela = _fundo_do_palco(ident, molde.tamanho(formato), cor_fundo, avisar)
    _desenhar_logo(tela, ident, formato, moldagem)
    _desenhar_barra(tela, ident, formato, moldagem, fonte)
    # Nome provisorio ate o arquivo estar inteiro, como as pecas de video: PNG
    # truncado tem nome, tamanho e data de arquivo bom, e o render seguinte o
    # reaproveitaria como cenario pronto.
    meio = destino.with_name(f"parcial-{destino.name}")
    tela.convert("RGB").save(meio)
    os.replace(meio, destino)
    return destino


def _arquivo_de(caminho) -> Path | None:
    """O caminho que existe no disco, ou `None`. Campo vazio nao desenha."""
    if not caminho:
        return None
    arquivo = Path(str(caminho))
    return arquivo if arquivo.is_file() else None


def _relogio_do_arquivo(caminho) -> list:
    arquivo = _arquivo_de(caminho)
    if arquivo is None:
        return []
    ficha = arquivo.stat()
    return [ficha.st_mtime_ns, ficha.st_size]


def _fundo_do_palco(ident: dict, tamanho: tuple[int, int], cor_fundo: str, avisar):
    from PIL import Image

    arte = _arquivo_de(ident.get("arte_de_fundo"))
    if arte:
        try:
            return _cobrindo(Image.open(arte).convert("RGB"), tamanho)
        except OSError as erro:
            # Arte que nao abre nao para um render de treze minutos: avisa e cai
            # na cor do time. Nunca sumir calado vale aqui tambem.
            if avisar:
                avisar(f"a arte de fundo nao abriu ({erro}) - fica a cor do time")
    return _vinheta(Image.new("RGB", tamanho, _rgb_do_palco(cor_fundo)))


def _cobrindo(imagem, tamanho: tuple[int, int]):
    """Redimensiona cobrindo o palco, sem deformar, e corta o excesso."""
    largura, altura = tamanho
    proporcao = max(largura / imagem.width, altura / imagem.height)
    imagem = imagem.resize((
        max(1, round(imagem.width * proporcao)),
        max(1, round(imagem.height * proporcao)),
    ))
    esquerda = (imagem.width - largura) // 2
    topo = (imagem.height - altura) // 2
    return imagem.crop((esquerda, topo, esquerda + largura, topo + altura))


def _vinheta(tela):
    """Escurece as pontas, como o `vignette=PI/4` fazia no fundo chapado.

    E aproximacao, e nao a mesma conta: o filtro do ffmpeg e otica de lente. O
    que importa e o efeito - meio claro, pontas escuras, para a janela ter
    contra o que aparecer. Sem marca nenhuma o palco nem existe, e ai o render
    continua usando a vinheta do proprio ffmpeg.
    """
    from PIL import Image

    escuro = Image.radial_gradient("L").resize(tela.size)
    escuro = escuro.point(lambda valor: int(210 * (valor / 255) ** 2))
    tela.paste(Image.new("RGB", tela.size, (0, 0, 0)), (0, 0), escuro)
    return tela


def _desenhar_logo(tela, ident: dict, formato: str, moldagem: dict) -> None:
    arquivo = _arquivo_de(ident.get("logo"))
    caixa = _caixa_ou_nada("logo", formato, moldagem)
    if not (arquivo and caixa):
        return
    from PIL import Image

    desenhada = Image.open(arquivo).convert("RGBA")
    # `thumbnail` e nao `resize`: a logo cabe INTEIRA na caixa, sem deformar e
    # sem ser cortada. Logo cortada nao e logo.
    desenhada.thumbnail((caixa["largura"], caixa["altura"]))
    tela.paste(
        desenhada,
        (
            caixa["esquerda"] + (caixa["largura"] - desenhada.width) // 2,
            caixa["topo"] + (caixa["altura"] - desenhada.height) // 2,
        ),
        desenhada,
    )


def _desenhar_barra(
    tela, ident: dict, formato: str, moldagem: dict, fonte: Path | None
) -> None:
    """A faixa de redes: um par icone + arroba por rede que existir.

    Monta da DIREITA para a esquerda, com o que existir: rede vazia nao deixa
    buraco. A chamada entra no que sobrar a esquerda, e so se couber - o PIL
    sabe medir texto, e texto cortado na borda e pior do que texto ausente.
    """
    caixa = _caixa_ou_nada("barra", formato, moldagem)
    escritas = arrobas(ident)
    if not (caixa and escritas):
        return
    from PIL import ImageDraw

    desenho = ImageDraw.Draw(tela)
    corpo = max(14, caixa["altura"] // 3)
    letra = _letra_do_palco(fonte, corpo)
    meio = caixa["topo"] + caixa["altura"] // 2
    direita = caixa["esquerda"] + caixa["largura"]

    for rede, arroba in reversed(escritas):
        _texto_do_palco(desenho, arroba, (direita, meio), letra, "rm")
        direita -= round(desenho.textlength(arroba, font=letra)) + VAO_DO_PALCO
        marca = icone(rede, corpo)
        if marca:
            tela.paste(marca, (direita - marca.width, meio - marca.height // 2), marca)
            direita -= marca.width + VAO_DO_PALCO

    chamada = str(ident.get("chamada") or "").strip()
    livre = direita - caixa["esquerda"] - VAO_DO_PALCO
    if chamada and desenho.textlength(chamada, font=letra) <= livre:
        _texto_do_palco(desenho, chamada, (caixa["esquerda"], meio), letra, "lm")


def _caixa_ou_nada(nome: str, formato: str, moldagem: dict) -> dict | None:
    """A caixa daquela camada, ou `None` se o arranjo nao tiver onde por."""
    try:
        return molde.caixa(nome, formato, **moldagem)
    except KeyError:
        return None


def _letra_do_palco(fonte: Path | None, corpo: int):
    """A fonte da barra. Sem arquivo, a letra do sistema: feia, mas legivel.

    Nao se importa do `capa.py` porque o `capa` importa o estudio - importar de
    volta fecharia o ciclo. Sao seis linhas; o ciclo custaria mais.
    """
    from PIL import ImageFont

    if fonte and Path(fonte).is_file():
        return ImageFont.truetype(str(fonte), corpo)
    return ImageFont.load_default()


def _texto_do_palco(desenho, texto: str, posicao, letra, ancora: str) -> None:
    """Letra branca com sombra dura atras: a barra vai sobre arte clara e escura."""
    x, y = posicao
    desenho.text((x + 2, y + 2), texto, font=letra, fill=(0, 0, 0), anchor=ancora)
    desenho.text((x, y), texto, font=letra, fill=(255, 255, 255), anchor=ancora)


def _rgb_do_palco(cor: str) -> tuple[int, int, int]:
    cor = (cor or molde.COR_FUNDO).lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))


def fonte_de(cfg: dict) -> Path | None:
    """A fonte pesada da CAPA. O video em si nao escreve nada."""
    caminho = cfg.get("fonte_cartela") or ""
    return Path(caminho) if caminho else None


def cor_do_fundo(dados_receita: dict, cadastrados: dict | None = None) -> str:
    """A cor da torcida que perdeu, que e o fundo do video inteiro.

    Sem esse fundo com a cara do time, um clipe de webcam em tela cheia continua
    sendo um clipe de webcam. A receita pode fixar outra cor; sem isso, vale a
    do `dados/times.json`, e sem o time cadastrado vale o cinza do molde.
    """
    escolhida = (dados_receita.get("molde") or {}).get("cor_fundo")
    if escolhida:
        return escolhida
    ficha = mod_times.achar(dados_receita.get("torcida_alvo", ""), cadastrados)
    return ficha.get("cor") or molde.COR_FUNDO


def filtro_do_item(
    dados_receita: dict, ident: dict | None = None, com_mascaras: bool = True
) -> tuple[str, str]:
    """O filter_complex do item e o rotulo da saida dele.

    Nao depende do clipe nem do jogo porque nao ha nada de individual para
    desenhar: o mesmo filtro serve a todos os itens daquela receita. O que muda
    de um para o outro e o corte, que mora no comando.

    A moldagem vem RESOLVIDA - padrao do canal com o desvio do jogo por cima - e
    e ela que decide o tamanho e a posicao da janela.
    """
    ident = identidade.carregar() if ident is None else ident
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    moldagem = identidade.moldagem(ident, dados_receita)
    filtro = molde.para_ffmpeg(
        molde.camadas(formato, **moldagem),
        formato,
        cor_fundo=cor_do_fundo(dados_receita),
        mascara="1:v" if com_mascaras else None,
        moldura="2:v" if com_mascaras else None,
        palco="3:v" if (
            com_mascaras and tem_o_que_desenhar(ident, formato, moldagem)
        ) else None,
    )
    return filtro, "v"


def comando_item(
    origem: Path,
    item: dict,
    filtro: str,
    rotulo: str,
    mascara: Path,
    moldura: Path,
    destino: Path,
    ffmpeg: str,
    video=None,
    palco: Path | None = None,
) -> list[str]:
    duracao = round(float(item["ate"]) - float(item["de"]), 3)
    return [
        ffmpeg, "-y",
        "-ss", str(item["de"]), "-t", str(duracao), "-i", str(origem),
        # `-t` na ENTRADA de imagem, e nao so na saida. Medido em 03/09:
        # limitar as entradas fez 3 de 4 renders passarem, contra 1 de 3 sem
        # isso; trocar o `-shortest` da saida por `-t` piorou (0 de 3).
        "-loop", "1", "-t", str(duracao), "-i", str(mascara),
        "-loop", "1", "-t", str(duracao), "-i", str(moldura),
        # O palco e a QUARTA entrada, depois da mascara e da moldura: assim 1:v
        # e 2:v continuam sendo elas, e o filtro de hoje nao se mexe.
        *(["-loop", "1", "-t", str(duracao), "-i", str(palco)] if palco else []),
        "-filter_complex", filtro,
        "-map", f"[{rotulo}]",
        # O `?` deixa passar clipe sem faixa de audio: acontece, e nao pode
        # derrubar a montagem inteira por causa de um canal.
        "-map", "0:a?",
        "-af", VOLUME_ALVO,
        *(video or _VIDEO_FINAL), *_AUDIO, "-shortest",
        str(destino),
    ]


def comando_concat(lista: Path, saida: Path, ffmpeg: str) -> list[str]:
    return [
        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
        "-c", "copy", str(saida),
    ]


def escrever_lista(arquivos: list[Path], destino: Path) -> Path:
    destino.write_text(
        "\n".join(f"file '{arquivo.as_posix()}'" for arquivo in arquivos) + "\n",
        encoding="utf-8",
    )
    return destino


# --------------------------------------------------------------- as tres saidas

def _clipes_por_chave(dados: dict) -> dict:
    return {(c["gol"], c["canal"]): c for c in dados.get("clipes", [])}


def _clipe_de(dados: dict, gol: int, canal: str) -> dict:
    clipe = _clipes_por_chave(dados).get((gol, canal))
    if clipe is None:
        raise KeyError(f"o catalogo nao tem o gol {gol} do canal {canal}")
    return clipe


def _item_de(dados_receita: dict, gol: int, canal: str) -> dict:
    for item in dados_receita.get("itens", []):
        if item["gol"] == gol and item["canal"] == canal:
            return item
    raise KeyError(f"a receita nao tem o gol {gol} do canal {canal}")


def planejar(
    dados: dict,
    dados_receita: dict,
    avisar: Callable[[str], None] | None = None,
    ident: dict | None = None,
    fonte: Path | None = None,
) -> list[dict]:
    """As pecas deste video, na ordem, cada uma com o nome que tem no cache.

    So contas: nao escreve arquivo nenhum e nao chama ffmpeg. Quem monta usa
    esta lista para saber o que fazer, e a recepcao usa a MESMA lista para
    saber se o mp4 que esta no disco ainda e o video que a edicao pede.
    """
    ident = identidade.carregar() if ident is None else ident
    clipes = _clipes_por_chave(dados)
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    moldagem = identidade.moldagem(ident, dados_receita)
    # A assinatura do palco entra na chave das pecas: o filtro nomeia a entrada
    # ([3:v]) mas nao diz qual PNG e. Sem isto, trocar a arte deixaria o cache
    # servindo pecas com o cenario velho.
    marca = (
        assinatura_do_palco(
            formato, ident, moldagem, cor_do_fundo(dados_receita), fonte
        )
        if tem_o_que_desenhar(ident, formato, moldagem) else ""
    )
    # Um filtro so para todas as pecas: sem texto, o molde nao tem nada de
    # individual para desenhar. O que separa uma peca da outra e o corte.
    filtro, rotulo = filtro_do_item(dados_receita, ident)
    plano = []
    for item in receita.itens_do_video(dados_receita):
        clipe = clipes.get((item["gol"], item["canal"]))
        if clipe is None:
            if avisar:
                avisar(
                    f"o gol {item['gol']} do canal {item['canal']} "
                    "nao esta no catalogo"
                )
            continue
        plano.append({
            "nome": chave_da_peca(
                clipe["arquivo"], item["de"], item["ate"], filtro, marca
            ),
            "qual": f"{item['canal']} no gol {item['gol']}",
            "clipe": clipe,
            "item": item,
            "filtro": filtro,
            "rotulo": rotulo,
        })
    return plano


def assinatura(
    dados: dict, dados_receita: dict, ident: dict | None = None,
    fonte: Path | None = None,
) -> str:
    """Impressao digital do video que esta edicao geraria.

    E a lista de pecas do plano, que ja carrega corte, molde, formato e cor - o
    mesmo truque de `identidade`, um degrau acima. O render
    guarda esta assinatura no `render.json`; a recepcao compara com a de agora
    e sabe se o mp4 do disco envelheceu.

    O mtime do arquivo nao serve para isso: a tela de edicao regrava a receita
    cada vez que abre, e ai todo video parecia velho um minuto depois de sair.
    """
    nomes = [
        peca["nome"]
        for peca in planejar(dados, dados_receita, ident=ident, fonte=fonte)
    ]
    return hashlib.sha1("|".join(nomes).encode("utf-8")).hexdigest()[:12]


def montar(
    pasta_jogo: Path,
    dados: dict,
    dados_receita: dict,
    cfg: dict,
    executar: Callable[[list[str]], None] | None = None,
    avisar: Callable[[str], None] = print,
    tentativas: int = TENTATIVAS,
    ident: dict | None = None,
) -> Path:
    """O video final. Roda peca por peca, reaproveitando o que nao mudou."""
    executar = executar or cortador.executar
    itens = receita.itens_do_video(dados_receita)
    if not itens:
        raise ValueError(
            "nenhuma reacao marcada - marque as que entram no painel antes de montar"
        )

    pasta_jogo = Path(pasta_jogo)
    ident = identidade.carregar() if ident is None else ident
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    moldagem = identidade.moldagem(ident, dados_receita)
    mascara, moldura = mascaras(pasta_jogo, formato, moldagem)
    fonte = fonte_de(cfg)
    cenario = palco(
        pasta_jogo, formato, ident, moldagem, cor_do_fundo(dados_receita),
        fonte, avisar,
    )
    cache = pasta_das_pecas(pasta_jogo)

    tarefas = []
    for peca in planejar(dados, dados_receita, avisar, ident, fonte):
        destino = cache / f"{peca['nome']}.mp4"
        comando_de = (
            lambda destino, p=peca: comando_item(
                pasta_jogo / p["clipe"]["arquivo"], p["item"], p["filtro"],
                p["rotulo"], mascara, moldura, destino, cfg["caminho_ffmpeg"],
                palco=cenario,
            )
        )
        tarefas.append((destino, comando_de, peca["qual"]))

    total = len(tarefas)
    # O PID e de quem esta montando de verdade: e por ele que o painel sabe
    # diferenciar "ainda trabalhando" de "morreu no meio".
    anotar(pasta_jogo, rodando=True, feito=0, total=total, saida="",
           pid=os.getpid(), mensagem=f"montando {total} peca(s)")

    pecas = []
    pasta_saida = pasta_jogo / PASTA_SAIDA
    pasta_saida.mkdir(parents=True, exist_ok=True)
    saida = pasta_saida / f"compilacao-{formato}.mp4"
    try:
        for feito, (destino, comando_de, qual) in enumerate(tarefas, start=1):
            if destino.is_file():
                avisar(f"reaproveitado: {qual}")
            else:
                fazer_peca(destino, comando_de, executar, avisar, qual, tentativas)
            pecas.append(destino)
            anotar(pasta_jogo, feito=feito, total=total,
                   mensagem=f"{feito} de {total}: {qual}")

        executar(comando_concat(
            escrever_lista(pecas, pasta_cache(pasta_jogo) / "lista.txt"), saida,
            cfg["caminho_ffmpeg"],
        ))
    except cortador.FALHAS as erro:
        # Estado travado que nunca resolve e pior do que erro: o operador fica
        # esperando um arquivo que nunca vem. Quem corrigia isso era so a
        # LEITURA do estado, e o disco continuava dizendo "rodando: true".
        anotar(pasta_jogo, rodando=False, mensagem=cortador.motivo(erro))
        raise

    anotar(pasta_jogo, rodando=False, feito=total, total=total,
           saida=str(saida), mensagem="pronto",
           assinatura=assinatura(dados, dados_receita, ident, fonte))
    return saida


def espiar(
    pasta_jogo: Path,
    dados: dict,
    dados_receita: dict,
    gol: int,
    canal: str,
    cfg: dict,
    executar: Callable[[list[str]], None] | None = None,
    ident: dict | None = None,
) -> Path:
    """Um quadro parado, ja no molde. E o mais barato dos dois."""
    executar = executar or cortador.executar
    pasta_jogo = Path(pasta_jogo)
    clipe = _clipe_de(dados, gol, canal)
    item = _item_de(dados_receita, gol, canal)
    ident = identidade.carregar() if ident is None else ident
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    mascara, moldura = mascaras(
        pasta_jogo, formato, identidade.moldagem(ident, dados_receita)
    )
    cenario = palco(
        pasta_jogo, formato, ident, identidade.moldagem(ident, dados_receita),
        cor_do_fundo(dados_receita), fonte_de(cfg),
    )
    filtro, rotulo = filtro_do_item(dados_receita, ident)

    destino = pasta_cache(pasta_jogo) / f"espiada-{gol}-{canal}.png"
    executar([
        cfg["caminho_ffmpeg"], "-y",
        "-ss", str(instante_de_espiar(clipe, item)), "-i", str(pasta_jogo / clipe["arquivo"]),
        "-loop", "1", "-i", str(mascara),
        "-loop", "1", "-i", str(moldura),
        *(["-loop", "1", "-i", str(cenario)] if cenario else []),
        "-filter_complex", filtro,
        "-map", f"[{rotulo}]", "-frames:v", "1", "-update", "1",
        str(destino),
    ])
    return destino


def instante_de_espiar(clipe: dict, item: dict) -> float:
    """O quadro do pico, que e onde a cara esta mais expressiva.

    Fora da janela escolhida, o pico nao serve de amostra do que vai sair - ai
    vale o meio do trecho.
    """
    pico = float(clipe.get("instante") or 0.0)
    if float(item["de"]) <= pico <= float(item["ate"]):
        return pico
    return round((float(item["de"]) + float(item["ate"])) / 2, 3)


def previa(
    pasta_jogo: Path,
    dados: dict,
    dados_receita: dict,
    gol: int,
    canal: str,
    cfg: dict,
    executar: Callable[[list[str]], None] | None = None,
) -> Path:
    """So o trecho escolhido, cru e pequeno - para conferir O CORTE.

    A previa nao leva fundo, quadro, etiqueta nem placar de proposito. Ela
    responde uma pergunta so: o corte pegou o que tinha que pegar? Quem confere
    as camadas e o ESPIAR, que sai num quadro parado e e instantaneo.

    Compor tudo em 1080p para so entao encolher para 640 era o preco que se
    pagava por essa resposta: 25 s no trecho de 60 s do gol 1 (medido em
    05/09), 48 s no laudo do jogo real. Cortando cru, 2,2 s - e o que aparece
    na tela e o mesmo corte.
    """
    executar = executar or cortador.executar
    pasta_jogo = Path(pasta_jogo)
    clipe = _clipe_de(dados, gol, canal)
    item = _item_de(dados_receita, gol, canal)

    # A previa nao tem filtro para carregar o resto no hash, e nao precisa: sem
    # camadas, o que muda a imagem dela e so o clipe de origem e o trecho.
    chave = chave_da_peca(clipe["arquivo"], item["de"], item["ate"], "crua")
    destino = pasta_cache(pasta_jogo) / f"previa-{gol}-{canal}-{chave}.mp4"
    if destino.is_file():
        return destino

    # Nome provisorio ate o ffmpeg sair com codigo zero. Com cache, um render
    # morto no meio nao estraga uma previa - estraga TODAS as proximas, porque
    # o arquivo quebrado passa a ser servido sem nunca mais chamar o ffmpeg.
    destino.parent.mkdir(parents=True, exist_ok=True)
    meio = destino.with_name(f"parcial-{destino.name}")
    try:
        executar(comando_previa(
            pasta_jogo / clipe["arquivo"], item, meio, cfg["caminho_ffmpeg"]
        ))
    except BaseException:
        meio.unlink(missing_ok=True)
        raise
    os.replace(meio, destino)
    return destino


def comando_previa(origem: Path, item: dict, destino: Path, ffmpeg: str) -> list[str]:
    """O corte cru, encolhido. Sem filter_complex, sem loudnorm, sem etiqueta.

    Tres coisas fazem a diferenca de tempo:

    - **`-ss` antes do `-i`**: o ffmpeg pula pelo indice do arquivo em vez de
      decodificar o clipe inteiro ate o ponto do corte.
    - **encolher na entrada**: um `scale` sobre o clipe e barato; compor em
      1080p e so entao encolher e que era caro.
    - **`+faststart`**: o indice vai para o comeco do arquivo, e o navegador
      comeca a tocar sem baixar o resto. Metade da espera na tela era isto.
    """
    duracao = round(float(item["ate"]) - float(item["de"]), 3)
    return [
        ffmpeg, "-y",
        "-ss", str(item["de"]), "-t", str(duracao), "-i", str(origem),
        "-map", "0:v:0",
        # O `?` deixa passar clipe sem faixa de audio, do mesmo jeito que o
        # render: acontece, e nao pode derrubar a previa por causa disso.
        "-map", "0:a?",
        "-vf", f"scale={LARGURA_DA_PREVIA}:-2",
        # `ultrafast` porque aqui o que importa e o relogio, nao o arquivo: a
        # previa e descartavel e mora no cache do jogo.
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
        "-movflags", "+faststart",
        str(destino),
    ]


# ------------------------------------------------------------ a fila e o disco

def processo_vivo(pid: int, perguntar=None) -> bool:
    """Se aquele PID ainda existe nesta maquina.

    `os.kill(pid, 0)` NAO serve aqui: no Windows ele chama TerminateProcess e
    mata o processo em vez de perguntar por ele.
    """
    if not pid:
        return False
    perguntar = perguntar or _tasklist
    return str(pid) in perguntar(int(pid))


def _tasklist(pid: int) -> str:
    try:
        return subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        # Sem conseguir perguntar, o menos errado e dar o processo por vivo:
        # dizer que morreu liberaria um segundo render por cima do primeiro.
        return str(pid)


def estado(pasta_jogo: Path, vivo=None) -> dict:
    """O que o render esta fazendo, lido do disco.

    Mora em disco e nao na pagina: o painel pode ser fechado e reaberto sem
    matar o render, do mesmo jeito que o supervisor da gravacao ja funciona.

    Se o processo que se disse dono do render sumiu, isto aqui para de repetir
    que ele esta rodando. Estado travado que nunca resolve e pior do que erro:
    o operador fica esperando um arquivo que nunca vem.
    """
    atual = _ler_cru(pasta_jogo)
    if not (atual["rodando"] and atual["pid"]):
        return atual
    # Carencia: o `tasklist` nao enxerga na hora um PID recem-criado, e sem
    # isto a resposta imediata ao clique no RENDER dizia "o render parou
    # sozinho" - a primeira coisa que o operador lia. Sumia no refresh
    # seguinte, o que e pior: ensina a ignorar o aviso que um dia sera verdade.
    if time.time() - float(atual.get("pid_em") or 0.0) < CARENCIA_DO_PID:
        return atual
    if (vivo or processo_vivo)(atual["pid"]):
        return atual

    morto = {
        **atual, "rodando": False,
        "mensagem": "o render parou sozinho antes de terminar - "
                    "veja a janela dele e mande de novo",
    }
    # Grava a correcao: antes disso quem corrigia era so a leitura, e o disco
    # continuava dizendo "rodando: true" depois de o processo morrer.
    _gravar(pasta_jogo, morto)
    return morto


def _ler_cru(pasta_jogo: Path) -> dict:
    """O que esta no arquivo, sem julgar se o processo ainda vive."""
    padrao = {"rodando": False, "feito": 0, "total": 0, "mensagem": "",
              "saida": "", "pid": 0, "pid_em": 0.0, "assinatura": ""}
    arquivo = Path(pasta_jogo) / NOME_ESTADO
    if not arquivo.is_file():
        return padrao
    try:
        return {**padrao, **json.loads(arquivo.read_text(encoding="utf-8"))}
    except json.JSONDecodeError:
        return padrao


def _gravar(pasta_jogo: Path, estado_novo: dict) -> None:
    Path(pasta_jogo).mkdir(parents=True, exist_ok=True)
    (Path(pasta_jogo) / NOME_ESTADO).write_text(
        json.dumps(estado_novo, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def anotar(pasta_jogo: Path, **campos) -> dict:
    # Le o arquivo CRU, e nao o `estado`: a leitura do estado corrige render
    # morto, e anotar o PID novo por cima dessa correcao gravava um render que
    # acabou de nascer como render que ja morreu. Era o aviso falso que o
    # operador lia ao clicar RENDER.
    atual = _ler_cru(pasta_jogo)
    atual.update(campos)
    # Quem anota um PID esta anotando um processo que acabou de nascer: a hora
    # vem junto, e e dela que sai a carencia da leitura.
    if "pid" in campos and "pid_em" not in campos:
        atual["pid_em"] = time.time()
    _gravar(pasta_jogo, atual)
    return atual


def tamanho_do_cache(pasta_jogo: Path) -> int:
    pasta = pasta_cache(pasta_jogo)
    if not pasta.is_dir():
        return 0
    return sum(a.stat().st_size for a in pasta.rglob("*") if a.is_file())


def passou_do_teto(pasta_jogo: Path, cfg: dict) -> bool:
    teto = float(cfg.get("teto_cache_gb", TETO_CACHE_GB))
    return tamanho_do_cache(pasta_jogo) > teto * 1024**3


def limpar(pasta_jogo: Path) -> int:
    """Apaga os intermediarios e devolve quantos bytes liberou.

    Eles sao uma copia inteira do video - 1 a 2 GB por jogo - e a biblioteca e
    disco local. Perder o cache custa um render; nao perder custa o disco.
    """
    liberado = tamanho_do_cache(pasta_jogo)
    shutil.rmtree(pasta_cache(pasta_jogo), ignore_errors=True)
    return liberado
