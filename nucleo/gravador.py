"""Sobe gravacoes ao vivo, uma por canal escolhido.

O comando e um cano: yt-dlp entrega o stream, ffmpeg fatia em pedacos de
MPEG-TS sem recodificar. TS sobrevive a processo morto; mp4 nao.

Um yt-dlp velho derruba a gravacao em meio minuto: o YouTube passa a responder
403 em todo pedaco e o processo continua de pe, mudo. Manter o yt-dlp em dia
nao e higiene, e requisito.
"""
import json
import re
import shutil
import subprocess
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from concurrent.futures import ThreadPoolExecutor

from nucleo import canais as mod_canais
from nucleo import cortador, religador


MAX_TENTATIVAS = 5  # padrao; cfg["max_tentativas"] manda
QUEDAS_ATE_PROCURAR = 2  # a primeira queda pode ser solucao; a segunda, nao
MINIMO_PRODUTIVO = 15  # segundos gravados que provam que a live continua de pe


@dataclass
class Processo:
    canal: mod_canais.Canal
    url: str
    pasta: Path
    sessao: int
    processo: object
    tentativas: int = 0
    inicio: float = field(default_factory=time.time)  # epoch do comeco da sessao
    inicio_sessao: float = field(default_factory=time.time)  # t0 real da sessao
    canal_url: str = ""   # descoberto na primeira busca e guardado: nunca muda
    busca: object = None  # procura por live nova em andamento, fora do laco


def apelido(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-")
    return limpo.lower()


def pasta_do_canal(biblioteca: Path, jogo: str, canal: mod_canais.Canal) -> Path:
    return Path(biblioteca) / jogo / "bruto" / apelido(canal.nome)


def comando(url: str, pasta: Path, sessao: int, cfg: dict) -> str:
    formato = (
        f'bv*[height<={cfg["altura_maxima"]}]+ba/'
        f'b[height<={cfg["altura_maxima"]}]'
    )
    # _abrir roda com cwd=pasta; nomes relativos mantem nomes simples no CSV.
    saida = f"s{sessao:02d}-parte-%03d.ts"
    lista = f"s{sessao:02d}-segmentos.csv"
    return (
        f'"{cfg["caminho_ytdlp"]}" --js-runtimes node --hls-use-mpegts'
        f' --retries infinite --fragment-retries infinite'
        f' --retry-sleep 2 --socket-timeout 20'
        f' -f "{formato}" --no-part -o - "{url}"'
        f' | "{cfg["caminho_ffmpeg"]}" -y -i pipe: -c copy'
        f' -f segment -segment_time {cfg["duracao_pedaco"]}'
        f" -segment_format mpegts -reset_timestamps 1"
        f' -segment_list "{lista}" -segment_list_type csv'
        f' "{saida}"'
    )


def espaco_livre_gb(caminho: Path) -> float:
    return shutil.disk_usage(Path(caminho)).free / (1024**3)


def verificar_espaco(caminho: Path, minimo_gb: float) -> None:
    livre = espaco_livre_gb(caminho)
    if livre < minimo_gb:
        raise RuntimeError(
            f"disco com {livre:.0f} GB livres, minimo exigido {minimo_gb:.0f} GB. "
            "Libere espaco antes de comecar - nao no meio do jogo."
        )


def avaliar_banda(quantidade: int, teto: int) -> str | None:
    if quantidade <= teto:
        return None
    return (
        f"{quantidade} canais passa do teto de {teto} da placa de 100 Mbps. "
        "Gravacao pode cair no meio do jogo."
    )


def gravando_em_outros_jogos(
    biblioteca: Path, jogo: str, agora: float, limite: float
) -> int:
    """Quantos canais de OUTROS jogos estao gravando agora nesta biblioteca.

    Cada jogo roda no seu proprio supervisor, e cada um so enxergava os
    proprios canais. Com duas partidas ao mesmo tempo, o teto da placa de
    100 Mbps era conferido pela metade - o aviso nunca aparecia.
    """
    raiz = Path(biblioteca)
    if not raiz.is_dir():
        return 0
    total = 0
    for pasta_jogo in raiz.iterdir():
        if pasta_jogo.name == jogo or not (pasta_jogo / "bruto").is_dir():
            continue
        for canal in (pasta_jogo / "bruto").iterdir():
            if canal.is_dir() and esta_gravando(canal, agora, limite):
                total += 1
    return total


def escrever_gravacao(
    pasta: Path, url: str, sessao: int, t0: datetime, pid: int | None = None,
    torcida: str = "",
) -> Path:
    """Anota a sessao no disco, com o pid de quem a esta gravando.

    O pid e o que permite trocar o codigo do supervisor sem derrubar a
    gravacao: quem sobe depois precisa saber a quem obedece cada pasta.
    """
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "gravacao.json"
    if arquivo.is_file():
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    else:
        dados = {"url": url, "sessoes": []}
    dados["url"] = url
    if torcida:
        dados["torcida"] = torcida  # o religador pode ter trocado o endereco no meio do jogo
    dados["sessoes"].append({"numero": sessao, "t0": t0.isoformat(), "pid": pid})
    arquivo.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return arquivo


def derrubar_arvore(pid: int | None, rodar=None) -> None:
    """Mata o cmd e tudo que ele abriu. Sem o /T, o ffmpeg fica orfao gravando."""
    if not pid:
        return
    rodar = rodar or (lambda c: subprocess.run(c, capture_output=True))
    rodar(["taskkill", "/T", "/F", "/PID", str(pid)])


class Adotado:
    """Gravacao que ja rodava quando este supervisor subiu.

    Nao ha handle de processo para consultar - o dono era outro Python, que
    ja morreu. Quem responde se esta viva e o disco, pelo mesmo criterio que
    o supervisor ja usa para qualquer canal: o pedaco cresceu ou nao cresceu.
    """

    def __init__(self, pid: int | None):
        self.pid = pid

    def poll(self):
        return None  # quem decide e `travou`, olhando o disco

    def kill(self):
        derrubar_arvore(self.pid)


def ultima_sessao(pasta: Path) -> tuple[int, str, int | None]:
    """(numero, url, pid) da ultima sessao anotada. Zeros quando nao ha nada."""
    arquivo = Path(pasta) / "gravacao.json"
    if not arquivo.is_file():
        return 0, "", None
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    sessoes = dados.get("sessoes") or []
    if not sessoes:
        return 0, dados.get("url", ""), None
    ultima = sessoes[-1]
    return ultima["numero"], dados.get("url", ""), ultima.get("pid")


def conteudo_da_sessao(pasta: Path, sessao: int, ffprobe: str) -> float:
    """Quantos segundos de video a sessao ja tem no disco.

    O CSV so ganha linha quando um pedaco fecha, entao o pedaco aberto - que
    pode ter varios minutos - precisa ser medido a parte.
    """
    pasta = Path(pasta)
    prefixo = f"s{sessao:02d}"
    csv = pasta / f"{prefixo}-segmentos.csv"
    fechados, nomes = 0.0, set()
    if csv.is_file():
        for linha in csv.read_text(encoding="utf-8").splitlines():
            partes = linha.split(",")
            if len(partes) >= 3:
                nomes.add(partes[0])
                try:
                    fechados = float(partes[2])
                except ValueError:
                    pass
    abertos = sum(
        cortador.duracao(a, ffprobe)
        for a in pasta.glob(f"{prefixo}-parte-*.ts")
        if a.name not in nomes
    )
    return fechados + abertos


def atraso_do_ao_vivo(pr: Processo, cfg: dict, agora: float) -> float:
    """Quanto o canal esta atras do ao vivo, em segundos.

    O ffmpeg pode entrar na playlist bem atras da ponta e baixar mais devagar
    do que o jogo acontece. O canal escreve bytes o tempo todo - entao passa
    por saudavel em qualquer teste de crescimento - e mesmo assim, quando sai
    o gol, o trecho simplesmente ainda nao existe no disco.

    Medido em jogo: tres canais de seis chegaram a trinta minutos de conteudo
    depois de noventa minutos gravando.
    """
    passado = agora - pr.inicio_sessao
    if passado <= 0:
        return 0.0
    return passado - conteudo_da_sessao(pr.pasta, pr.sessao, cfg["caminho_ffprobe"])


def ficou_para_tras(pr: Processo, cfg: dict, agora: float) -> bool:
    """So julga depois de a sessao ter idade suficiente para o arranque passar."""
    carencia = cfg.get("carencia_do_arranque", 120)
    if agora - pr.inicio_sessao < carencia:
        return False
    return atraso_do_ao_vivo(pr, cfg, agora) > cfg.get("atraso_maximo", 300)


def esta_gravando(pasta: Path, agora: float, limite: float) -> bool:
    """Pasta que recebeu byte novo ha pouco esta sendo gravada por alguem."""
    ultimo = _ultimo_crescimento(pasta)
    return bool(ultimo) and (agora - ultimo) < limite


def adotar(
    canal: mod_canais.Canal, pasta: Path, cfg: dict, agora: float
) -> Processo | None:
    """Assume uma gravacao em andamento em vez de abrir outra por cima.

    Sem isto, trocar o codigo do supervisor custava o jogo inteiro: era preciso
    derrubar a arvore e recomecar, e todo canal perdia o intervalo da troca.
    """
    limite = cfg.get("segundos_sem_crescer", 120)
    if not esta_gravando(pasta, agora, limite):
        return None
    sessao, url, pid = ultima_sessao(pasta)
    if not sessao:
        return None
    return Processo(
        canal=canal, url=url or canal.url, pasta=Path(pasta), sessao=sessao,
        processo=Adotado(pid), inicio=agora,
        inicio_sessao=_t0_da_sessao(pasta, agora),
    )


def _t0_da_sessao(pasta: Path, padrao: float) -> float:
    """Epoch do comeco da sessao que esta rodando, para medir o atraso direito."""
    arquivo = Path(pasta) / "gravacao.json"
    if not arquivo.is_file():
        return padrao
    sessoes = json.loads(arquivo.read_text(encoding="utf-8")).get("sessoes") or []
    if not sessoes:
        return padrao
    try:
        return datetime.fromisoformat(sessoes[-1]["t0"]).timestamp()
    except (KeyError, ValueError):
        return padrao


def _abrir(comando_shell: str, pasta: Path):
    return subprocess.Popen(comando_shell, shell=True, cwd=str(pasta))


def iniciar(
    escolhidos: list[tuple[mod_canais.Canal, str]],
    biblioteca: Path,
    jogo: str,
    cfg: dict,
    abrir: Callable[[str, Path], object] = _abrir,
) -> list[Processo]:
    Path(biblioteca).mkdir(parents=True, exist_ok=True)
    verificar_espaco(biblioteca, cfg["disco_minimo_gb"])

    agora_epoch = time.time()
    limite = cfg.get("segundos_sem_crescer", 120)
    ja_no_ar = gravando_em_outros_jogos(biblioteca, jogo, agora_epoch, limite)
    aviso = avaliar_banda(len(escolhidos) + ja_no_ar, cfg["teto_canais"])
    if aviso:
        print(f"AVISO: {aviso}", flush=True)
    if ja_no_ar:
        print(f"({ja_no_ar} canal(is) de outro jogo ja estao no ar)", flush=True)

    processos = []
    for canal, url in escolhidos:
        pasta = pasta_do_canal(biblioteca, jogo, canal)
        pasta.mkdir(parents=True, exist_ok=True)

        adotado = adotar(canal, pasta, cfg, agora_epoch)
        if adotado is not None:
            print(
                f"{canal.nome}: ja estava gravando na sessao {adotado.sessao} "
                "- adotado sem interromper",
                flush=True,
            )
            processos.append(adotado)
            continue

        sessao = ultima_sessao(pasta)[0] + 1
        processo = abrir(comando(url, pasta, sessao, cfg), pasta)
        escrever_gravacao(
            pasta, url, sessao, datetime.now(), getattr(processo, "pid", None),
            canal.torcida,
        )
        agora_novo = time.time()
        processos.append(
            Processo(canal, url, pasta, sessao, processo,
                     inicio=agora_novo, inicio_sessao=agora_novo)
        )
    return processos


def _ultimo_crescimento(pasta: Path) -> float:
    marcas = [arquivo.stat().st_mtime for arquivo in Path(pasta).glob("*.ts")]
    return max(marcas, default=0.0)


def travou(pr: Processo, limite: float, agora_epoch: float) -> bool:
    """Processo vivo que parou de escrever ha tempo demais.

    Morrer e o caso facil. O caso que engana e a gravacao que emperra com o
    processo de pe: nenhum byte novo entra e o poll() continua respondendo que
    esta tudo bem. Sem esta conferencia, o canal fica mudo o jogo inteiro.
    """
    ultimo = max(_ultimo_crescimento(pr.pasta), pr.inicio)
    return agora_epoch - ultimo > limite


def _matar(processo) -> None:
    processo.kill()


VOLTAS_ENTRE_CONFERIR_DISCO = 30
VOLTAS_ENTRE_MEDIR_ATRASO = 6  # medir custa um ffprobe por canal; nao e de graca


def conferir_disco(processos: list[Processo], cfg: dict, avisar=print) -> bool:
    """Avisa se o disco esta acabando NO MEIO do jogo.

    Conferir so ao comecar nao bastava: duas partidas de duas horas gravando
    juntas comem dezenas de GB, e o disco enche depois da largada.
    """
    if not processos:
        return True
    livre = espaco_livre_gb(processos[0].pasta)
    if livre >= cfg["disco_minimo_gb"]:
        return True
    avisar(
        f"AVISO: restam {livre:.0f} GB no disco, abaixo do minimo de "
        f"{cfg['disco_minimo_gb']:.0f} GB. Libere espaco AGORA - a gravacao "
        "para sozinha quando acabar."
    )
    return False


def _colher_buscas(processos: list[Processo]) -> None:
    """Aplica as procuras que ja terminaram, sem esperar por nenhuma.

    Live encerrada nao volta na mesma URL: o canal abre outra. Trocar o
    endereco e o que transforma um canal abandonado em canal de volta.
    """
    for pr in processos:
        if pr.busca is None or not pr.busca.done():
            continue
        try:
            nova, canal = pr.busca.result()
        except Exception:  # procurar nunca pode derrubar a gravacao
            nova, canal = "", ""
        pr.busca = None
        if canal:
            pr.canal_url = canal
        if nova:
            print(f"{pr.canal.nome}: live nova encontrada - {nova}", flush=True)
            pr.url = nova
            pr.tentativas = 0


def supervisionar(
    processos: list[Processo],
    cfg: dict,
    abrir: Callable[[str, Path], object] = _abrir,
    dormir: Callable[[float], None] = time.sleep,
    agora: Callable[[], datetime] = datetime.now,
    matar: Callable[[object], None] = _matar,
    procurar: Callable[[str, str, str], tuple[str, str]] = religador.procurar_substituta,
    tarefas=None,
    voltas: int | None = None,
) -> None:
    """Fica de olho nas gravacoes: quem cair volta em nova sessao.

    Sem isto, uma queda de conexao aos 20 minutos perde o resto do jogo naquele
    canal, calada. Quem cai varias vezes seguidas teve a live encerrada de
    verdade — ai desiste, em vez de religar para sempre.

    `voltas` existe para o teste rodar um numero finito de conferencias.
    """
    proprias = tarefas is None
    tarefas = tarefas or ThreadPoolExecutor(max_workers=4)
    feitas = 0
    while processos and (voltas is None or feitas < voltas):
        dormir(cfg["segundos_entre_conferencias"])
        feitas += 1
        _colher_buscas(processos)
        if feitas % VOLTAS_ENTRE_CONFERIR_DISCO == 1:
            conferir_disco(processos, cfg, lambda t: print(t, flush=True))
        limite = cfg.get("segundos_sem_crescer", 120)
        teto = cfg.get("max_tentativas", MAX_TENTATIVAS)
        confere_atraso = feitas % VOLTAS_ENTRE_MEDIR_ATRASO == 1
        for pr in list(processos):
            agora_epoch = agora().timestamp()
            vivo = pr.processo.poll() is None
            emperrado = vivo and travou(pr, limite, agora_epoch)
            atrasado = (
                vivo and not emperrado and confere_atraso
                and ficou_para_tras(pr, cfg, agora_epoch)
            )
            if vivo and not emperrado and not atrasado:
                continue
            if emperrado:
                print(f"{pr.canal.nome}: parou de gravar sem morrer - derrubando", flush=True)
                matar(pr.processo)
            elif atrasado:
                # Recomecar e o unico jeito de voltar para a ponta: o yt-dlp
                # entra no ao vivo, e o que ja foi gravado continua no disco.
                atras = atraso_do_ao_vivo(pr, cfg, agora_epoch)
                print(
                    f"{pr.canal.nome}: {atras / 60:.0f} min atras do ao vivo - "
                    "recomecando na ponta",
                    flush=True,
                )
                matar(pr.processo)

            if atrasado:
                # Correcao de rumo nao e queda: o canal esta vivo e saudavel,
                # so estava longe da ponta. Gastar tentativa por isso acabaria
                # abandonando justamente quem a rede castiga.
                pr.tentativas = 0
            else:
                # Sessao que chegou a gravar de verdade tambem nao conta: o que
                # o contador procura e a live encerrada, que morre toda vez.
                if _ultimo_crescimento(pr.pasta) - pr.inicio > MINIMO_PRODUTIVO:
                    pr.tentativas = 0
                pr.tentativas += 1
            if pr.tentativas > teto:
                print(f"{pr.canal.nome}: caiu {teto}x seguidas - desistindo", flush=True)
                processos.remove(pr)
                continue

            if pr.tentativas >= QUEDAS_ATE_PROCURAR and pr.busca is None:
                # Fora do laco: procurar leva ate um minuto e meio, e nesse
                # tempo os outros canais nao podem ficar sem quem os olhe.
                pr.busca = tarefas.submit(
                    procurar, pr.url, cfg["caminho_ytdlp"], pr.canal_url
                )

            pr.sessao += 1
            pr.inicio = pr.inicio_sessao = agora().timestamp()
            pr.processo = abrir(comando(pr.url, pr.pasta, pr.sessao, cfg), pr.pasta)
            escrever_gravacao(
                pr.pasta, pr.url, pr.sessao, agora(),
                getattr(pr.processo, "pid", None), pr.canal.torcida,
            )
            print(f"{pr.canal.nome}: caiu, religando na sessao {pr.sessao}", flush=True)

    if proprias:
        tarefas.shutdown(wait=False)
