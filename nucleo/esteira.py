"""As quatro etapas da esteira; os .bat sao cascas em volta daqui."""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from nucleo import canais as mod_canais
from nucleo import catalogo, config, cortador, detector, gravador, importar, relogio


def listar_jogos(biblioteca: Path) -> list[str]:
    """Os jogos da biblioteca, do mais novo para o mais velho."""
    raiz = Path(biblioteca)
    if not raiz.is_dir():
        return []
    return [
        pasta.name
        for pasta in sorted(raiz.iterdir(), reverse=True)
        if (pasta / "bruto").is_dir()
    ]


def escolher_jogo(biblioteca: Path, ler=input, escrever=print) -> str | None:
    """Menu numerado dos jogos. Digitar o nome da pasta so gera erro de digitacao.

    Um jogo so: entra direto, sem perguntar nada.
    """
    jogos = listar_jogos(biblioteca)
    if not jogos:
        escrever(f"Nenhum jogo gravado em {biblioteca}")
        return None
    if len(jogos) == 1:
        escrever(f"Jogo: {jogos[0]}")
        return jogos[0]

    escrever("")
    for indice, jogo in enumerate(jogos, start=1):
        escrever(f"  {indice}) {jogo}")
    escrever("")
    try:
        escolha = int(ler("Numero do jogo: ").strip())
    except (ValueError, EOFError):
        escrever("Numero invalido.")
        return None
    if not 1 <= escolha <= len(jogos):
        escrever("Numero invalido.")
        return None
    return jogos[escolha - 1]


def nome_do_jogo(
    mandante: str, visitante: str, data: datetime | None = None
) -> str:
    data = data or datetime.now()
    return (
        f"{data:%Y-%m-%d} {gravador.apelido(mandante)} x "
        f"{gravador.apelido(visitante)}"
    )


def _cadastro() -> dict[str, list[mod_canais.Canal]]:
    return mod_canais.carregar(ARQUIVO_CANAIS)


ARQUIVO_CANAIS = Path(__file__).resolve().parent.parent / "dados" / "canais.json"


def etapa_canais(argv=None) -> int:
    p = argparse.ArgumentParser(description="Lista ou cadastra as lives escolhidas.")
    p.add_argument("time")
    p.add_argument(
        "--importar", nargs="+", metavar="URL",
        help="cola as URLs das lives; o nome do canal vem do proprio YouTube",
    )
    p.add_argument(
        "--torcida", default="",
        help="de que torcida e o lote, ex: santos. Vazio para narracao neutra.",
    )
    args = p.parse_args(argv)
    cfg = config.carregar()

    if args.importar:
        print(f"Lendo {len(args.importar)} endereco(s)...")
        novos = importar.importar(
            args.importar, cfg["caminho_ytdlp"], args.torcida.strip().lower()
        )
        if novos:
            cadastro = importar.juntar(
                importar.carregar_cru(ARQUIVO_CANAIS), args.time, novos
            )
            importar.salvar(ARQUIVO_CANAIS, cadastro)
            print(f'{len(novos)} canal(is) somado(s) a "{args.time}".\n')
        else:
            print("Nenhum canal novo.\n")

    escolhidos = mod_canais.selecionados_do_time(args.time, _cadastro())
    for canal, url in escolhidos:
        marca = f"[{canal.torcida}] " if canal.torcida else ""
        print(f"SELECIONADO  {marca}{canal.nome}  {url}")
    print(f"\n{len(escolhidos)} canal(is) selecionado(s).")
    if not escolhidos:
        print("Edite dados\\canais.json e cole as URLs das lives escolhidas.")
    aviso = gravador.avaliar_banda(len(escolhidos), cfg["teto_canais"])
    if aviso:
        print(f"AVISO: {aviso}")
    return 0


def etapa_gravar(argv=None) -> int:
    p = argparse.ArgumentParser(description="Grava as lives escolhidas manualmente.")
    p.add_argument("time")
    p.add_argument("mandante")
    p.add_argument("visitante")
    args = p.parse_args(argv)
    cfg = config.carregar()

    jogo = nome_do_jogo(args.mandante, args.visitante)
    escolhidos = mod_canais.selecionados_do_time(args.time, _cadastro())
    if not escolhidos:
        print("Nenhum canal escolhido. Edite dados\\canais.json antes de gravar.")
        return 1

    processos = gravador.iniciar(
        escolhidos, Path(cfg["biblioteca"]), jogo, cfg
    )
    # O botao PARAR do painel precisa saber quem derrubar. Se o processo ja
    # morreu, o taskkill falha calado e nada acontece - o arquivo velho e inofensivo.
    pasta_jogo = Path(cfg["biblioteca"]) / jogo
    pasta_jogo.mkdir(parents=True, exist_ok=True)
    (pasta_jogo / "supervisor.pid").write_text(str(os.getpid()), encoding="utf-8")
    print(f"Gravando {len(processos)} canal(is) em {cfg['biblioteca']}\\{jogo}", flush=True)
    print("Feche esta janela ou aperte PARAR no painel.", flush=True)
    gravador.supervisionar(processos, cfg)  # religa quem cair
    return 0


def _completar_pedaco_final(
    sessao: relogio.Sessao, pasta: Path, cfg: dict, prefixo: str
) -> relogio.Sessao:
    """Acrescenta o pedaco que ficou de fora do CSV.

    O ffmpeg so escreve a linha do CSV quando o pedaco fecha. Fechar a janela da
    gravacao mata o processo no meio de um pedaco de 10 minutos: o .ts esta no
    disco, mas fora do manifesto — e um gol nos ultimos minutos, que e
    justamente o material bom, apareceria como "nao coberto".
    """
    conhecidos = {p.arquivo for p in sessao.pedacos}
    orfaos = sorted(
        a.name
        for a in pasta.glob(f"{prefixo}-parte-*.ts")
        if a.name not in conhecidos
    )
    pedacos = list(sessao.pedacos)
    fim = pedacos[-1].fim if pedacos else 0.0
    for nome in orfaos:
        medida = cortador.duracao(pasta / nome, cfg["caminho_ffprobe"])
        if medida <= 0:
            continue
        pedacos.append(relogio.Pedaco(nome, fim, fim + medida))
        fim += medida
    return relogio.Sessao(t0=sessao.t0, pedacos=pedacos)


def ancorar_t0(sessao: relogio.Sessao, pasta: Path) -> relogio.Sessao:
    """Refaz o t0 da sessao pelo relogio do disco, em vez do horario de lancamento.

    O t0 gravado e a hora em que o processo subiu. O primeiro frame chega bem
    depois: o yt-dlp leva alguns segundos para negociar e o ffmpeg ainda puxa
    acelerado o trecho velho que ja estava na playlist, ate alcancar o ao vivo.
    Medido nesta maquina, a diferenca passou de meio minuto - o bastante para o
    corte cair inteiro fora do lance.

    Cada pedaco fechado da um palpite: hora em que ele fechou menos a posicao em
    que ele termina. Fica o menor deles, que e o instante em que a gravacao
    esteve mais colada no ao vivo; assim um canal que atrasa la pelo fim do jogo
    nao empurra o horario de todos os gols anteriores.
    """
    palpites = []
    for pedaco in sessao.pedacos:
        arquivo = Path(pasta) / pedaco.arquivo
        if not arquivo.is_file():
            continue
        fechou = datetime.fromtimestamp(arquivo.stat().st_mtime)
        palpites.append(fechou - timedelta(seconds=pedaco.fim))
    if not palpites:
        return sessao
    return relogio.Sessao(t0=min(palpites), pedacos=sessao.pedacos)


def _sessoes_do_canal(pasta: Path, cfg: dict) -> list[relogio.Sessao]:
    import json

    dados = json.loads((pasta / "gravacao.json").read_text(encoding="utf-8"))
    sessoes = []
    for registro in dados["sessoes"]:
        prefixo = f"s{registro['numero']:02d}"
        csv = pasta / f"{prefixo}-segmentos.csv"
        t0 = datetime.fromisoformat(registro["t0"])
        sessao = (
            relogio.ler_segmentos(csv, t0)
            if csv.is_file()
            else relogio.Sessao(t0=t0, pedacos=[])
        )
        sessao = _completar_pedaco_final(sessao, pasta, cfg, prefixo)
        sessao = ancorar_t0(sessao, pasta)
        if sessao.pedacos:
            sessoes.append(sessao)
    return sessoes


def _torcida_do_canal(pasta: Path) -> str:
    """De que torcida e o canal, segundo o que ficou anotado na gravacao."""
    import json

    arquivo = Path(pasta) / "gravacao.json"
    if not arquivo.is_file():
        return ""
    return json.loads(arquivo.read_text(encoding="utf-8")).get("torcida", "")


def _data_da_pasta(jogo: str):
    try:
        return datetime.strptime(jogo[:10], "%Y-%m-%d").date()
    except ValueError:
        return datetime.now().date()


def resolver_horario(
    texto: str, sessoes: list[relogio.Sessao], data_padrao
) -> datetime:
    """HH:MM:SS -> datetime, escolhendo o dia que cai dentro do que foi gravado.

    Jogo de Copa do Brasil comeca 21:30 e termina depois da meia-noite. Colar a
    hora do gol na data da pasta poria um gol de 00:15 doze horas antes do t0,
    e todo canal responderia "nao coberto".
    """
    hora = datetime.strptime(texto, "%H:%M:%S").time()
    intervalos = relogio.cobertura(sessoes)
    if not intervalos:
        return datetime.combine(data_padrao, hora)

    inicio = intervalos[0][0]
    for dia in (inicio.date(), inicio.date() + timedelta(days=1)):
        candidato = datetime.combine(dia, hora)
        if any(de <= candidato <= ate for de, ate in intervalos):
            return candidato
    return datetime.combine(data_padrao, hora)


@dataclass(frozen=True)
class ClipeCortado:
    canal: str
    arquivo: Path
    deslocamento: float
    forca_db: float   # quanto o audio subiu acima da linha de base
    tem_pico: bool


def medir_reacao(clipe: Path, cfg: dict, executar=None) -> tuple[float, bool]:
    """Quanto o audio explodiu acima da linha de base, em dB.

    Nao serve para achar o gol - o horario ja veio do operador. Serve para
    ordenar: com onze canais por gol, ver primeiro os mais explosivos poupa a
    maior parte do trabalho de curadoria. Falhar aqui nao pode custar o clipe,
    entao qualquer erro vira zero.
    """
    executar = executar or cortador.executar
    wav = clipe.with_suffix(".wav")
    try:
        executar(
            cortador.comando_audio(
                clipe, 0, cfg["segundos_antes"] + cfg["segundos_depois"],
                wav, cfg["caminho_ffmpeg"],
            )
        )
        achado = detector.analisar(wav, cfg["limiar_confianca_db"])
        return round(achado.confianca_db, 1), achado.tem_pico
    except Exception:
        return 0.0, False
    finally:
        wav.unlink(missing_ok=True)


def cortar_um_canal(
    nome: str, pasta_canal: Path, recortes, numero: int, destino: Path,
    tamanho: float, cfg: dict, executar=None,
) -> tuple[str, Path, float]:
    """Recorta o clipe de um canal. Nao toca no catalogo: quem grava e o laco.

    Separado justamente para poder rodar varios canais ao mesmo tempo - o
    corte recodifica, e recodificar onze canais em fila e o passo mais lento
    da esteira inteira.
    """
    executar = executar or cortador.executar
    temporaria = pasta_canal / f"janela-manual-{numero:02d}.ts"
    fonte, deslocamento = cortador.preparar_fonte(
        recortes, pasta_canal, temporaria, cfg["caminho_ffmpeg"], executar
    )
    saida = destino / f"{nome}.mp4"
    executar(
        cortador.comando_corte(
            fonte, deslocamento, tamanho, saida, cfg["caminho_ffmpeg"]
        )
    )
    temporaria.unlink(missing_ok=True)  # a juncao, quando houve
    temporaria.with_suffix(".txt").unlink(missing_ok=True)
    forca, tem_pico = medir_reacao(saida, cfg, executar)
    return ClipeCortado(nome, saida, deslocamento, forca, tem_pico)


def _gols_a_cortar(
    digitados, dados: dict, referencia, data_padrao
) -> list[tuple[int, datetime]]:
    """Os horarios da linha de comando; sem eles, o que o painel ja anotou.

    Anotar no botao durante o jogo e o caminho normal - o horario nasce certo,
    do relogio da maquina. Digitar continua valendo para quem foi de papel.
    """
    if digitados:
        return [
            (numero, resolver_horario(texto, referencia, data_padrao))
            for numero, texto in enumerate(digitados, start=1)
        ]
    return [
        (gol["numero"], datetime.fromisoformat(gol["horario"]))
        for gol in dados["gols"]
    ]


def etapa_cortar(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Gera clipes nos horarios exatos informados manualmente."
    )
    p.add_argument("jogo", nargs="?", help="nome da pasta; sem isto, menu")
    p.add_argument(
        "--gols",
        nargs="+",
        help="horarios exatos, ex: 21:37:00 22:05:30. Sem isto, usa o que foi "
             "anotado no botao MARCAR GOL do painel da gravacao.",
    )
    args = p.parse_args(argv)
    cfg = config.carregar()

    jogo = args.jogo or escolher_jogo(Path(cfg["biblioteca"]))
    if not jogo:
        return 1
    pasta_jogo = Path(cfg["biblioteca"]) / jogo
    pasta_bruto = pasta_jogo / "bruto"
    if not pasta_bruto.is_dir():
        print(f"Pasta de gravacoes nao encontrada: {pasta_bruto}")
        return 1

    dados = catalogo.carregar(pasta_jogo)
    data_jogo = _data_da_pasta(jogo)
    tamanho = float(cfg["segundos_antes"] + cfg["segundos_depois"])

    # Le as sessoes de todos os canais uma vez so: alem de evitar reler o disco
    # por gol, e o que permite resolver a data do horario informado.
    por_canal = {
        pasta.name: _sessoes_do_canal(pasta, cfg)
        for pasta in sorted(pasta_bruto.iterdir())
        if (pasta / "gravacao.json").is_file()
    }
    if not por_canal:
        print(f"Nenhuma gravacao em {pasta_bruto}")
        return 1
    # A cobertura de todos os canais junta, e nao a do primeiro da pasta: se o
    # primeiro por ordem alfabetica for justamente o que caiu cedo, resolver a
    # data do horario por ele jogaria todos os gols para fora do gravado.
    referencia = [sessao for sessoes in por_canal.values() for sessao in sessoes]
    torcidas = {nome: _torcida_do_canal(pasta_bruto / nome) for nome in por_canal}

    marcados = _gols_a_cortar(args.gols, dados, referencia, data_jogo)
    if not marcados:
        print(
            "Nenhum gol para cortar. Aperte MARCAR GOL no painel da gravacao "
            "durante o jogo, ou passe --gols 21:37:00 22:05:30"
        )
        return 1

    for numero, momento in marcados:
        dados = catalogo.registrar_gol(dados, numero, momento.isoformat(), "")
        inicio, fim = relogio.janela(
            momento, cfg["segundos_antes"], cfg["segundos_depois"]
        )
        destino = pasta_jogo / "clipes" / f"gol-{numero:02d}"
        destino.mkdir(parents=True, exist_ok=True)

        a_cortar = []
        for nome, sessoes in por_canal.items():
            recortes = relogio.trechos(sessoes, inicio, fim)
            duracao_coberta = sum(t.fim - t.inicio for t in recortes)
            if not recortes or duracao_coberta < tamanho - 0.05:
                gravado = ", ".join(
                    f"{de:%H:%M:%S}-{ate:%H:%M:%S}"
                    for de, ate in relogio.cobertura(sessoes)
                ) or "nada"
                print(
                    f"gol {numero}: {nome} nao cobre todo o corte em "
                    f"{momento:%H:%M:%S} - gravado: {gravado}",
                    flush=True,
                )
                continue
            a_cortar.append((nome, recortes))

        # Em paralelo porque o corte recodifica: onze canais em fila deixavam o
        # operador esperando o dobro do que a maquina precisa.
        trabalhadores = max(1, min(cfg.get("cortes_em_paralelo", 3), len(a_cortar) or 1))
        with ThreadPoolExecutor(max_workers=trabalhadores) as equipe:
            futuros = {
                equipe.submit(
                    cortar_um_canal, nome, pasta_bruto / nome, recortes,
                    numero, destino, tamanho, cfg,
                ): nome
                for nome, recortes in a_cortar
            }
            prontos = {}
            for futuro in as_completed(futuros):
                nome = futuros[futuro]
                try:
                    prontos[nome] = futuro.result()
                except Exception as erro:
                    print(f"gol {numero}: {nome} falhou no corte - {erro}", flush=True)

        for nome, _ in a_cortar:
            if nome not in prontos:
                continue
            clipe = prontos[nome]
            dados = catalogo.registrar_clipe(
                dados, numero, nome,
                str(clipe.arquivo.relative_to(pasta_jogo)).replace("\\", "/"),
                clipe.deslocamento, clipe.forca_db, clipe.tem_pico,
                torcidas.get(nome, ""),
            )
            print(
                f"gol {numero}: {nome} -> {clipe.arquivo.name}  "
                f"(reacao {clipe.forca_db:+.1f} dB)",
                flush=True,
            )

    catalogo.salvar(pasta_jogo, dados)
    return 0


def etapa_estudio(argv=None) -> int:
    from painel import servidor

    p = argparse.ArgumentParser()
    p.add_argument("jogo", nargs="?")
    p.add_argument("--porta", type=int, default=8770)
    args = p.parse_args(argv)
    cfg = config.carregar()
    jogo = args.jogo or escolher_jogo(Path(cfg["biblioteca"]))
    if not jogo:
        return 1
    servidor.servir(Path(cfg["biblioteca"]) / jogo, cfg, args.porta)
    return 0


if __name__ == "__main__":
    etapas = {
        "canais": etapa_canais,
        "gravar": etapa_gravar,
        "cortar": etapa_cortar,
        "estudio": etapa_estudio,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in etapas:
        print("Uso: python -m nucleo.esteira canais|gravar|cortar|estudio ...")
        sys.exit(2)
    sys.exit(etapas[sys.argv[1]](sys.argv[2:]))
