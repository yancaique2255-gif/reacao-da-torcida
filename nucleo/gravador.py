"""Sobe gravacoes ao vivo, uma por canal escolhido.

O comando e um cano: yt-dlp entrega o stream, ffmpeg fatia em pedacos de
MPEG-TS sem recodificar. TS sobrevive a processo morto; mp4 nao.

Quem baixa o HLS e o proprio yt-dlp (m3u8:native). Deixar o ffmpeg baixar,
que e o padrao para live, derruba a gravacao em meio minuto com 403 em todo
pedaco - e sem matar o processo, o que engana qualquer supervisor.
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

from nucleo import canais as mod_canais


MAX_TENTATIVAS = 5


@dataclass
class Processo:
    canal: mod_canais.Canal
    url: str
    pasta: Path
    sessao: int
    processo: object
    tentativas: int = 0
    inicio: float = field(default_factory=time.time)  # epoch do comeco da sessao


def apelido(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-")
    return limpo.lower()


def pasta_do_canal(biblioteca: Path, jogo: str, canal: mod_canais.Canal) -> Path:
    return Path(biblioteca) / jogo / "bruto" / apelido(canal.nome)


def comando(url: str, pasta: Path, sessao: int, cfg: dict) -> str:
    # Formato unico, ja com video e audio: juntar duas faixas na saida padrao
    # nao da, e para live o YouTube sempre oferece um combinado ate 720p.
    formato = f'b[height<={cfg["altura_maxima"]}]'
    # _abrir roda com cwd=pasta; nomes relativos mantem nomes simples no CSV.
    saida = f"s{sessao:02d}-parte-%03d.ts"
    lista = f"s{sessao:02d}-segmentos.csv"
    return (
        f'"{cfg["caminho_ytdlp"]}" --downloader m3u8:native --hls-use-mpegts'
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


def escrever_gravacao(pasta: Path, url: str, sessao: int, t0: datetime) -> Path:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "gravacao.json"
    if arquivo.is_file():
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    else:
        dados = {"url": url, "sessoes": []}
    dados["sessoes"].append({"numero": sessao, "t0": t0.isoformat()})
    arquivo.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return arquivo


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

    aviso = avaliar_banda(len(escolhidos), cfg["teto_canais"])
    if aviso:
        print(f"AVISO: {aviso}")

    processos = []
    for canal, url in escolhidos:
        pasta = pasta_do_canal(biblioteca, jogo, canal)
        pasta.mkdir(parents=True, exist_ok=True)
        sessao = 1
        escrever_gravacao(pasta, url, sessao, datetime.now())
        processo = abrir(comando(url, pasta, sessao, cfg), pasta)
        processos.append(Processo(canal, url, pasta, sessao, processo))
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


def supervisionar(
    processos: list[Processo],
    cfg: dict,
    abrir: Callable[[str, Path], object] = _abrir,
    dormir: Callable[[float], None] = time.sleep,
    agora: Callable[[], datetime] = datetime.now,
    matar: Callable[[object], None] = _matar,
    voltas: int | None = None,
) -> None:
    """Fica de olho nas gravacoes: quem cair volta em nova sessao.

    Sem isto, uma queda de conexao aos 20 minutos perde o resto do jogo naquele
    canal, calada. Quem cai varias vezes seguidas teve a live encerrada de
    verdade — ai desiste, em vez de religar para sempre.

    `voltas` existe para o teste rodar um numero finito de conferencias.
    """
    feitas = 0
    while processos and (voltas is None or feitas < voltas):
        dormir(cfg["segundos_entre_conferencias"])
        feitas += 1
        limite = cfg.get("segundos_sem_crescer", 120)
        for pr in list(processos):
            vivo = pr.processo.poll() is None
            emperrado = vivo and travou(pr, limite, agora().timestamp())
            if vivo and not emperrado:
                continue
            if emperrado:
                print(f"{pr.canal.nome}: parou de gravar sem morrer - derrubando")
                matar(pr.processo)

            pr.tentativas += 1
            if pr.tentativas > MAX_TENTATIVAS:
                print(f"{pr.canal.nome}: caiu {MAX_TENTATIVAS}x seguidas - desistindo")
                processos.remove(pr)
                continue

            pr.sessao += 1
            pr.inicio = agora().timestamp()
            escrever_gravacao(pr.pasta, pr.url, pr.sessao, agora())
            pr.processo = abrir(comando(pr.url, pr.pasta, pr.sessao, cfg), pr.pasta)
            print(f"{pr.canal.nome}: caiu, religando na sessao {pr.sessao}")
