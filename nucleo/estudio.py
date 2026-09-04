"""Executa a receita: espiar, previa, final, cache e fila.

A maquina e modesta - Ryzen 5 5600G, seis nucleos, sem placa de video dedicada.
Um video de 20 minutos em 1080p com sobreposicoes leva MINUTOS de CPU. Fingir
que e instantaneo seria mentir para o operador, entao sao tres velocidades
declaradas:

- **espiar**: um quadro parado, com todas as camadas. Instantaneo. Serve para
  ver se a etiqueta cobriu o rosto.
- **previa**: 640x360, so o trecho que ele esta olhando. Segundos.
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

from nucleo import cortador, molde, receita, times as mod_times

PASTA_CACHE = "intermediarios"
# As pecas prontas moram numa pasta propria, e chegar la e o batismo: um arquivo
# so recebe o nome final depois de o ffmpeg sair com codigo zero. Antes disso o
# render escrevia direto no nome final, e um ffmpeg morto no meio deixava um
# .mp4 de 48 bytes que o render seguinte reaproveitava como peca boa - a
# compilacao de 03/09 saiu 60s mais curta sem uma linha de aviso.
PASTA_PECAS = "pecas"
PASTA_SAIDA = "saida"
NOME_ESTADO = "render.json"
FORMATO_PADRAO = "deitado"
TETO_CACHE_GB = 5

# Cada canal grava com o volume que quer: um berra, o outro mal se ouve. Numa
# compilacao que corta de um para o outro isso e insuportavel, entao todo clipe
# passa pelo mesmo alvo (a recomendacao de streaming, -16 LUFS).
VOLUME_ALVO = "loudnorm=I=-16:TP=-1.5:LRA=11"
DURACAO_DA_CARTELA = 2.0
PREVIA = (640, 360)
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


def identidade(origem: str, de: float, ate: float, filtro: str) -> str:
    """Hash de tudo o que afeta a imagem daquela peca.

    O filtro ja carrega molde, formato, textos e cores: mudar qualquer um deles
    muda o nome do arquivo, e o cache percebe sozinho. Nao ha versao para
    lembrar de incrementar.
    """
    crua = json.dumps(
        [origem, round(float(de), 3), round(float(ate), 3), filtro], ensure_ascii=False
    )
    return hashlib.sha1(crua.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ os textos

def titulo_do_canal(canal: str) -> str:
    """"baldasso-tv" -> "BALDASSO TV", cortado no que cabe na tarja.

    Cortar o nome e feio; deixar vazar por cima do video e pior, e foi o que
    aconteceu no primeiro render com "FARID GERMANO FILHO".
    """
    nome = canal.replace("-", " ").upper()
    if len(nome) <= molde.MAXIMO_DO_CANAL:
        return nome
    return nome[: molde.MAXIMO_DO_CANAL - 1].rstrip() + "."


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


def numeros_do_gol(dados: dict, numero: int) -> str:
    """"1 x 0" - so os numeros, que e o que cabe na caixa do quadro.

    Nome de time por extenso transborda: medido no primeiro render de verdade,
    "Grêmio 1 x 0 Internacional" saiu cortado pela borda direita da tela. Quem
    identifica os times ali e o escudo; por extenso, so na cartela, que e tela
    cheia e tem espaco.
    """
    for gol in dados.get("gols", []):
        if gol["numero"] == numero and gol.get("placar"):
            casa, fora = gol["placar"]
            return f"{casa} x {fora}"
    return ""


def texto_da_cartela(dados: dict, numero: int) -> str:
    placar = placar_do_gol(dados, numero)
    return f"GOL {numero} - {placar}" if placar else f"GOL {numero}"


# ------------------------------------------------------------------- as pecas

def mascaras(pasta_jogo: Path, formato: str) -> tuple[Path, Path]:
    """Os dois PNGs do quadro: o recorte dos cantos e a borda clara.

    Cantos arredondados no ffmpeg puro dariam um `geq` caro e ilegivel; com o
    Pillow sai uma imagem so, feita uma vez por formato e reaproveitada. A
    geometria vem do molde - o mesmo numero que a previa usa em CSS.
    """
    from PIL import Image, ImageDraw

    quadro = molde.caixa("quadro", formato)
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


def fonte_de(cfg: dict) -> Path | None:
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
    clipe: dict,
    dados: dict,
    dados_receita: dict,
    cfg: dict,
    com_mascaras: bool = True,
    escala: tuple[int, int] | None = None,
) -> tuple[str, str]:
    """O filter_complex do item e o rotulo da saida dele."""
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    filtro = molde.para_ffmpeg(
        molde.camadas(formato),
        formato,
        cor_fundo=cor_do_fundo(dados_receita),
        canal=titulo_do_canal(clipe["canal"]),
        torcida=clipe.get("torcida", ""),
        placar=numeros_do_gol(dados, clipe["gol"]),
        fonte=fonte_de(cfg),
        mascara="1:v" if com_mascaras else None,
        moldura="2:v" if com_mascaras else None,
    )
    if escala:
        filtro += f";[v]scale={escala[0]}:{escala[1]}[menor]"
        return filtro, "menor"
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
) -> list[str]:
    duracao = round(float(item["ate"]) - float(item["de"]), 3)
    return [
        ffmpeg, "-y",
        "-ss", str(item["de"]), "-t", str(duracao), "-i", str(origem),
        "-loop", "1", "-i", str(mascara),
        "-loop", "1", "-i", str(moldura),
        "-filter_complex", filtro,
        "-map", f"[{rotulo}]",
        # O `?` deixa passar clipe sem faixa de audio: acontece, e nao pode
        # derrubar a montagem inteira por causa de um canal.
        "-map", "0:a?",
        "-af", VOLUME_ALVO,
        *(video or _VIDEO_FINAL), *_AUDIO, "-shortest",
        str(destino),
    ]


def comando_cartela(
    texto: str, formato: str, cfg: dict, destino: Path, cor_fundo: str
) -> list[str]:
    """A cartela tem audio mudo de proposito.

    A emenda e `concat` com copia de fluxo, e o concat exige as MESMAS faixas em
    todas as pecas. Cartela sem audio derrubaria a emenda inteira.
    """
    filtro = molde.filtro_cartela(
        formato, texto, cor_fundo=cor_fundo, fonte=fonte_de(cfg),
        duracao=DURACAO_DA_CARTELA,
    )
    return [
        cfg["caminho_ffmpeg"], "-y",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-filter_complex", filtro,
        "-map", "[v]", "-map", "0:a",
        "-t", str(DURACAO_DA_CARTELA),
        *_VIDEO_FINAL, *_AUDIO,
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


def montar(
    pasta_jogo: Path,
    dados: dict,
    dados_receita: dict,
    cfg: dict,
    executar: Callable[[list[str]], None] | None = None,
    avisar: Callable[[str], None] = print,
    tentativas: int = TENTATIVAS,
) -> Path:
    """O video final. Roda peca por peca, reaproveitando o que nao mudou."""
    executar = executar or cortador.executar
    itens = receita.itens_do_video(dados_receita)
    if not itens:
        raise ValueError(
            "nenhuma reacao marcada - marque as que entram no painel antes de montar"
        )

    pasta_jogo = Path(pasta_jogo)
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    mascara, moldura = mascaras(pasta_jogo, formato)
    cache = pasta_das_pecas(pasta_jogo)
    clipes = _clipes_por_chave(dados)

    tarefas = []
    gol_anterior = None
    for item in itens:
        if item["gol"] != gol_anterior:
            gol_anterior = item["gol"]
            texto = texto_da_cartela(dados, item["gol"])
            filtro = molde.filtro_cartela(
                formato, texto, cor_fundo=cor_do_fundo(dados_receita),
                fonte=fonte_de(cfg), duracao=DURACAO_DA_CARTELA,
            )
            nome = identidade(f"cartela-{item['gol']}", 0, DURACAO_DA_CARTELA, filtro)
            tarefas.append((
                cache / f"{nome}.mp4",
                lambda destino, texto=texto: comando_cartela(
                    texto, formato, cfg, destino, cor_do_fundo(dados_receita)
                ),
                f"cartela do gol {item['gol']}",
            ))

        clipe = clipes.get((item["gol"], item["canal"]))
        if clipe is None:
            avisar(f"o gol {item['gol']} do canal {item['canal']} nao esta no catalogo")
            continue
        filtro, rotulo = filtro_do_item(clipe, dados, dados_receita, cfg)
        nome = identidade(clipe["arquivo"], item["de"], item["ate"], filtro)
        tarefas.append((
            cache / f"{nome}.mp4",
            lambda destino, clipe=clipe, item=item, filtro=filtro, rotulo=rotulo:
                comando_item(
                    pasta_jogo / clipe["arquivo"], item, filtro, rotulo,
                    mascara, moldura, destino, cfg["caminho_ffmpeg"],
                ),
            f"{item['canal']} no gol {item['gol']}",
        ))

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
           saida=str(saida), mensagem="pronto")
    return saida


def espiar(
    pasta_jogo: Path,
    dados: dict,
    dados_receita: dict,
    gol: int,
    canal: str,
    cfg: dict,
    executar: Callable[[list[str]], None] | None = None,
) -> Path:
    """Um quadro parado, com todas as camadas. E o mais barato dos tres."""
    executar = executar or cortador.executar
    pasta_jogo = Path(pasta_jogo)
    clipe = _clipe_de(dados, gol, canal)
    item = _item_de(dados_receita, gol, canal)
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    mascara, moldura = mascaras(pasta_jogo, formato)
    filtro, rotulo = filtro_do_item(clipe, dados, dados_receita, cfg)

    destino = pasta_cache(pasta_jogo) / f"espiada-{gol}-{canal}.png"
    executar([
        cfg["caminho_ffmpeg"], "-y",
        "-ss", str(instante_de_espiar(clipe, item)), "-i", str(pasta_jogo / clipe["arquivo"]),
        "-loop", "1", "-i", str(mascara),
        "-loop", "1", "-i", str(moldura),
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
    """So o trecho que ele esta olhando, pequeno e rapido - para conferir som e movimento."""
    executar = executar or cortador.executar
    pasta_jogo = Path(pasta_jogo)
    clipe = _clipe_de(dados, gol, canal)
    item = _item_de(dados_receita, gol, canal)
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    mascara, moldura = mascaras(pasta_jogo, formato)
    filtro, rotulo = filtro_do_item(clipe, dados, dados_receita, cfg, escala=PREVIA)

    destino = pasta_cache(pasta_jogo) / f"previa-{gol}-{canal}.mp4"
    codec = cfg.get("codec_previa", "libx264")
    fazer = lambda qual: comando_item(  # noqa: E731
        pasta_jogo / clipe["arquivo"], item, filtro, rotulo, mascara, moldura,
        destino, cfg["caminho_ffmpeg"], video=_video_da_previa(qual),
    )
    try:
        executar(fazer(codec))
    except cortador.FALHAS:
        # A APU pode estar ocupada, o ffmpeg da maquina pode nem ter o encoder
        # dela, e ela tambem TRAVA - nao falha so com codigo de erro. Ficar sem
        # previa por isso seria bobagem: o libx264 sempre existe, e em 640x360
        # ele da conta.
        if codec == "libx264":
            raise
        executar(fazer("libx264"))
    return destino


def _video_da_previa(codec: str) -> list[str]:
    """As opcoes de video da previa, que mudam com o codec.

    Medido nesta maquina: o `h264_amf` recusa `-preset veryfast` ("Unable to
    parse preset option value") e nao tem `-crf`. Taxa de bits fixa serve aos
    dois, e a previa nao precisa de mais do que isso.
    """
    comum = ["-c:v", codec, "-b:v", "900k", "-pix_fmt", "yuv420p", "-r", str(molde.FPS)]
    return comum + (["-preset", "veryfast"] if codec == "libx264" else ["-quality", "speed"])


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
    padrao = {"rodando": False, "feito": 0, "total": 0, "mensagem": "",
              "saida": "", "pid": 0, "pid_em": 0.0}
    arquivo = Path(pasta_jogo) / NOME_ESTADO
    if not arquivo.is_file():
        return padrao
    try:
        atual = {**padrao, **json.loads(arquivo.read_text(encoding="utf-8"))}
    except json.JSONDecodeError:
        return padrao
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


def _gravar(pasta_jogo: Path, estado_novo: dict) -> None:
    Path(pasta_jogo).mkdir(parents=True, exist_ok=True)
    (Path(pasta_jogo) / NOME_ESTADO).write_text(
        json.dumps(estado_novo, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def anotar(pasta_jogo: Path, **campos) -> dict:
    atual = estado(pasta_jogo)
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
