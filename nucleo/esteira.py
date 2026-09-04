"""As quatro etapas da esteira; os .bat sao cascas em volta daqui."""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from nucleo import canais as mod_canais
from nucleo import alinhamento, catalogo, config, cortador, detector
from nucleo import estudio, ficha, gravador
from nucleo import receita
from nucleo import importar, relogio, torcidas, vigia


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
    return mod_canais.carregar(mod_canais.ARQUIVO)


def etapa_canais(argv=None) -> int:
    p = argparse.ArgumentParser(description="Lista ou cadastra as lives escolhidas.")
    p.add_argument("time")
    p.add_argument(
        "--importar", nargs="+", metavar="URL",
        help="cola as URLs das lives; o nome do canal vem do proprio YouTube",
    )
    p.add_argument(
        "--torcida", default="",
        help=f'de que torcida e o lote, ex: santos. Narracao sem lado: '
             f'"{mod_canais.NEUTRO}".',
    )
    args = p.parse_args(argv)
    cfg = config.carregar()

    if args.importar:
        # Recusar aqui e o barato. Canal cadastrado sem torcida nao da erro
        # nenhum: ele grava, corta, aparece no painel - e some do video la na
        # frente, quando o estudio filtrar pelo lado que perdeu.
        try:
            torcida = mod_canais.exigir_torcida(args.torcida)
        except ValueError as erro:
            print(f"Nao cadastrei nada: {erro}")
            return 2
        print(f"Lendo {len(args.importar)} endereco(s)...")
        novos = importar.importar(args.importar, cfg["caminho_ytdlp"], torcida)
        if novos:
            cadastro = importar.juntar(
                importar.carregar_cru(mod_canais.ARQUIVO), args.time, novos
            )
            importar.salvar(mod_canais.ARQUIVO, cadastro)
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
    p.add_argument(
        "--liga", default="",
        help="acompanha o placar e marca os gols sozinho, ex: copa-do-brasil",
    )
    p.add_argument(
        "--sem-cortar", action="store_true",
        help="com --liga, marca os gols mas nao corta sozinho",
    )
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
    catalogo.salvar(
        pasta_jogo,
        catalogo.registrar_partida(
            catalogo.carregar(pasta_jogo), args.liga, args.mandante, args.visitante
        ),
    )
    ficha.escrever(pasta_jogo)
    ficha.escrever_indice(Path(cfg["biblioteca"]))
    print(f"Gravando {len(processos)} canal(is) em {cfg['biblioteca']}\\{jogo}", flush=True)
    print("Feche esta janela ou aperte PARAR no painel.", flush=True)

    if args.liga:
        # Em thread separada: consultar o placar leva segundos, e nesse tempo
        # os canais nao podem ficar sem quem os supervisione.
        import threading

        espera = float(cfg.get("espera_para_cortar", 240))
        falar = lambda t: print(t, flush=True)  # noqa: E731

        def cortar_quando_der(numero: int, momento: datetime) -> None:
            """Corta o gol depois que o material dele tiver chegado ao disco.

            Cortar na hora nao daria certo: no instante em que o placar muda, os
            segundos DEPOIS do gol ainda estao sendo baixados - e sao eles que
            trazem a reacao.
            """
            def rodar():
                try:
                    cortar_gols(pasta_jogo, [(numero, momento)], cfg, falar)
                except Exception as erro:  # cortar nunca derruba a gravacao
                    falar(f"corte automatico do gol {numero} falhou: {erro}")

            falar(f"gol {numero}: corte automatico em {espera / 60:.0f} min")
            threading.Timer(espera, rodar).start()

        threading.Thread(
            target=vigia.vigiar,
            args=(args.liga, args.mandante, args.visitante, pasta_jogo),
            kwargs={
                "avisar": falar,
                "ao_marcar": cortar_quando_der if not args.sem_cortar else None,
            },
            daemon=True,
        ).start()
        print(f"Acompanhando o placar em {args.liga}.", flush=True)

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
class PlanoDoCanal:
    """Onde cortar e quanto, neste canal, para este gol."""
    nome: str
    recortes: list
    duracao: float
    largo: bool    # ganhou margem por nao ter alinhamento confirmado
    parcial: bool  # o gravado nao cobre a janela inteira pedida


def planejar_corte(
    nome: str, sessoes: list, momento: datetime, cfg: dict,
    deslocamento: float | None = None,
) -> PlanoDoCanal:
    """Canal sem alinhamento confirmado ganha margem dos dois lados.

    Nao se sabe exatamente onde a reacao esta naquele canal, e as duas falhas
    nao custam a mesma coisa: clipe longo demais o operador apara no estudio,
    clipe que corta o lance ao meio nao tem conserto.

    A margem some sozinha conforme o alinhamento do canal vai sendo confirmado
    pelos gols - entao os clipes apertam com o tempo, sem ninguem mexer.
    """
    margem = 0.0 if deslocamento is not None else float(
        cfg.get("margem_sem_alinhamento", 60)
    )
    antes = cfg["segundos_antes"] + margem
    depois = cfg["segundos_depois"] + margem
    alvo_momento = momento + timedelta(seconds=deslocamento or 0.0)
    inicio, fim = relogio.janela(alvo_momento, antes, depois)

    recortes = relogio.trechos(sessoes, inicio, fim)
    coberto = sum(t.fim - t.inicio for t in recortes)
    return PlanoDoCanal(
        nome=nome,
        recortes=recortes,
        duracao=round(coberto, 2),
        largo=margem > 0,
        parcial=coberto < (antes + depois) - 0.05,
    )


@dataclass(frozen=True)
class ClipeCortado:
    canal: str
    arquivo: Path
    deslocamento: float
    forca_db: float   # quanto o audio subiu acima da linha de base
    tem_pico: bool
    duracao: float = 0.0
    largo: bool = False
    parcial: bool = False


def medir_reacao(
    clipe: Path, cfg: dict, executar=None, duracao: float | None = None
) -> tuple[float, bool]:
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
                # O clipe nem sempre tem o tamanho da janela pedida: canal sem
                # alinhamento sai maior, canal com cobertura parcial sai menor.
                clipe, 0,
                duracao or (cfg["segundos_antes"] + cfg["segundos_depois"]),
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
    plano: PlanoDoCanal, pasta_canal: Path, numero: int, destino: Path,
    cfg: dict, executar=None,
) -> ClipeCortado:
    """Recorta o clipe de um canal. Nao toca no catalogo: quem grava e o laco.

    Separado justamente para poder rodar varios canais ao mesmo tempo - o
    corte recodifica, e recodificar onze canais em fila e o passo mais lento
    da esteira inteira.
    """
    executar = executar or cortador.executar
    temporaria = pasta_canal / f"janela-manual-{numero:02d}.ts"
    fonte, deslocamento = cortador.preparar_fonte(
        plano.recortes, pasta_canal, temporaria, cfg["caminho_ffmpeg"], executar
    )
    saida = destino / f"{plano.nome}.mp4"
    executar(
        cortador.comando_corte(
            fonte, deslocamento, plano.duracao, saida, cfg["caminho_ffmpeg"]
        )
    )
    temporaria.unlink(missing_ok=True)  # a juncao, quando houve
    temporaria.with_suffix(".txt").unlink(missing_ok=True)
    forca, tem_pico = medir_reacao(saida, cfg, executar, plano.duracao)
    return ClipeCortado(
        plano.nome, saida, deslocamento, forca, tem_pico,
        plano.duracao, plano.largo, plano.parcial,
    )


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
    deslocamentos = alinhamento.deslocamentos_do_jogo(pasta_bruto)
    if deslocamentos:
        print(
            "alinhamento em uso: "
            + ", ".join(f"{c} {v:+.1f}s" for c, v in sorted(deslocamentos.items())),
            flush=True,
        )

    marcados = _gols_a_cortar(args.gols, dados, referencia, data_jogo)
    if not marcados:
        print(
            "Nenhum gol para cortar. Aperte MARCAR GOL no painel da gravacao "
            "durante o jogo, ou passe --gols 21:37:00 22:05:30"
        )
        return 1

    cortar_gols(pasta_jogo, marcados, cfg, avisar=lambda t: print(t, flush=True))
    return 0


def cortar_gols(
    pasta_jogo: Path, marcados: list, cfg: dict, avisar=print
) -> dict:
    """Corta uma lista de (numero, momento) em todos os canais do jogo.

    Separado de `etapa_cortar` para o corte automatico poder chamar o mesmo
    caminho: um gol marcado durante o jogo corta exatamente como um gol
    digitado depois.
    """
    pasta_jogo = Path(pasta_jogo)
    pasta_bruto = pasta_jogo / "bruto"
    dados = catalogo.carregar(pasta_jogo)
    por_canal = {
        pasta.name: _sessoes_do_canal(pasta, cfg)
        for pasta in sorted(pasta_bruto.iterdir())
        if (pasta / "gravacao.json").is_file()
    }
    torcidas = {nome: _torcida_do_canal(pasta_bruto / nome) for nome in por_canal}
    deslocamentos = alinhamento.deslocamentos_do_jogo(pasta_bruto)
    if deslocamentos:
        avisar(
            "alinhamento em uso: "
            + ", ".join(f"{c} {v:+.1f}s" for c, v in sorted(deslocamentos.items()))
        )

    for numero, momento in marcados:
        dados = catalogo.registrar_gol(dados, numero, momento.isoformat(), "")
        destino = pasta_jogo / "clipes" / f"gol-{numero:02d}"
        destino.mkdir(parents=True, exist_ok=True)

        minimo = float(cfg.get("minimo_do_clipe", 15))
        a_cortar = []
        for nome, sessoes in por_canal.items():
            # Cada canal procura no relogio dele: a mesma jogada aparece em
            # instantes diferentes conforme o atraso da transmissao.
            plano = planejar_corte(
                nome, sessoes, momento, cfg, deslocamentos.get(nome)
            )
            if plano.duracao < minimo:
                # So aqui se desiste, e por falta de material mesmo: o trecho
                # nao chegou a ser baixado. Nunca sumir calado.
                gravado = ", ".join(
                    f"{de:%H:%M:%S}-{ate:%H:%M:%S}"
                    for de, ate in relogio.cobertura(sessoes)
                ) or "nada"
                avisar(
                    f"gol {numero}: {nome} SEM MATERIAL em {momento:%H:%M:%S} "
                    f"({plano.duracao:.0f}s no disco) - gravado: {gravado}"
                )
                continue
            a_cortar.append(plano)

        # Em paralelo porque o corte recodifica: onze canais em fila deixavam o
        # operador esperando o dobro do que a maquina precisa.
        trabalhadores = max(1, min(cfg.get("cortes_em_paralelo", 3), len(a_cortar) or 1))
        with ThreadPoolExecutor(max_workers=trabalhadores) as equipe:
            futuros = {
                equipe.submit(
                    cortar_um_canal, plano, pasta_bruto / plano.nome,
                    numero, destino, cfg,
                ): plano.nome
                for plano in a_cortar
            }
            prontos = {}
            for futuro in as_completed(futuros):
                nome = futuros[futuro]
                try:
                    prontos[nome] = futuro.result()
                except Exception as erro:
                    avisar(f"gol {numero}: {nome} falhou no corte - {erro}")

        for plano in a_cortar:
            if plano.nome not in prontos:
                continue
            clipe = prontos[plano.nome]
            dados = catalogo.registrar_clipe(
                dados, numero, plano.nome,
                str(clipe.arquivo.relative_to(pasta_jogo)).replace("\\", "/"),
                clipe.deslocamento, clipe.forca_db, clipe.tem_pico,
                torcidas.get(plano.nome, ""),
                duracao=clipe.duracao, largo=clipe.largo, parcial=clipe.parcial,
            )
            marcas = []
            if clipe.largo:
                marcas.append("janela larga: apare no estudio")
            if clipe.parcial:
                marcas.append("PARCIAL")
            recado = f"  [{', '.join(marcas)}]" if marcas else ""
            avisar(
                f"gol {numero}: {plano.nome} -> {clipe.arquivo.name}  "
                f"({clipe.duracao:.0f}s, reacao {clipe.forca_db:+.1f} dB){recado}"
            )

    catalogo.salvar(pasta_jogo, dados)
    # A ficha e derivada: refazer e barato e a deixa sempre igual ao disco.
    # Falhar aqui nao pode custar o corte, que ja esta gravado.
    try:
        ficha.escrever(pasta_jogo)
        ficha.escrever_indice(pasta_jogo.parent)
    except Exception as erro:
        avisar(f"nao deu para atualizar a ficha do jogo: {erro}")
    return dados


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


def etapa_edicao(argv=None) -> int:
    """Abre o estudio de EDICAO, na 8772 - o novo, ao lado do de sempre.

    O da 8770 continua onde esta: reforma grande nao se faz na ferramenta em
    uso. Os dois podem rodar ao mesmo tempo, cada um na sua porta.
    """
    from painel import edicao

    p = argparse.ArgumentParser(description="Abre o estudio de edicao (porta 8772).")
    p.add_argument("jogo", nargs="?")
    p.add_argument("--porta", type=int, default=8772)
    args = p.parse_args(argv)
    cfg = config.carregar()
    jogo = args.jogo or escolher_jogo(Path(cfg["biblioteca"]))
    if not jogo:
        return 1
    edicao.servir(Path(cfg["biblioteca"]) / jogo, cfg, args.porta)
    return 0


def _par_canal_torcida(texto: str) -> tuple[str, str]:
    if "=" not in texto:
        raise argparse.ArgumentTypeError(f'use CANAL=TORCIDA, nao "{texto}"')
    canal, torcida = texto.split("=", 1)
    return canal.strip(), torcida.strip()


def etapa_torcida(argv=None) -> int:
    """Mostra e conserta a torcida dos canais de um jogo ja gravado.

    O campo virou obrigatorio no cadastro, mas os jogos gravados antes disso
    ficaram com buracos - e buraco desses tira o canal do video sem avisar.
    """
    p = argparse.ArgumentParser(
        description="Mostra e preenche a torcida dos canais de um jogo gravado."
    )
    p.add_argument("jogo", nargs="?", help="nome da pasta; sem isto, menu")
    p.add_argument(
        "--definir", nargs="+", default=[], metavar="CANAL=TORCIDA",
        type=_par_canal_torcida,
        help="ex: --definir baldasso-tv=inter gaucha-esportes=neutro",
    )
    args = p.parse_args(argv)
    cfg = config.carregar()

    jogo = args.jogo or escolher_jogo(Path(cfg["biblioteca"]))
    if not jogo:
        return 1
    pasta_jogo = Path(cfg["biblioteca"]) / jogo

    anotadas = torcidas.gravadas(pasta_jogo)
    if not anotadas:
        print(f"Nenhuma gravacao em {pasta_jogo}\\bruto")
        return 1

    # O que o cadastro ja sabe entra sozinho; digitar de novo o que ja esta
    # escrito e trabalho repetido, e e onde nasce a divergencia entre os dois.
    sabidas = torcidas.do_cadastro(_cadastro())
    definicoes = {
        canal: sabidas[canal]
        for canal, torcida in anotadas.items()
        if not torcida and canal in sabidas
    }
    definicoes.update(dict(args.definir))

    if definicoes:
        try:
            mexidos = torcidas.aplicar(pasta_jogo, definicoes)
        except (KeyError, ValueError) as erro:
            print(f"Nao mudei nada: {erro.args[0]}")
            return 2
        for canal in mexidos:
            print(f"  {canal} -> {definicoes[canal]}")
        no_cadastro = torcidas.definir_no_cadastro(mod_canais.ARQUIVO, definicoes)
        if no_cadastro:
            print(f"cadastro tambem atualizado: {', '.join(no_cadastro)}")
        print("")

    anotadas = torcidas.gravadas(pasta_jogo)
    for canal, torcida in anotadas.items():
        print(f"  {canal:<24} {torcida or 'SEM TORCIDA'}")

    faltam = [canal for canal, torcida in anotadas.items() if not torcida]
    if faltam:
        # Nunca sumir calado: o comando pronto vai junto do aviso.
        exemplo = " ".join(f"{canal}=inter" for canal in faltam)
        print(
            f"\nAVISO: {len(faltam)} canal(is) sem torcida. Com a regra do "
            f"perdedor ligada, eles ficam de fora do video.\n"
            f'  python -m nucleo.esteira torcida "{jogo}" --definir {exemplo}'
        )
    return 0


def etapa_render(argv=None) -> int:
    """Monta o video do jogo a partir da receita. Casca fina: quem monta e o estudio.

    Roda em processo proprio de proposito. O render final leva minutos nesta
    maquina, e o painel precisa poder ser fechado e reaberto sem matar o
    trabalho - o progresso mora em disco, como o do supervisor de gravacao.
    """
    p = argparse.ArgumentParser(description="Monta o video do jogo.")
    p.add_argument("jogo", nargs="?", help="nome da pasta; sem isto, menu")
    p.add_argument("--formato", default=None, choices=["deitado", "em-pe"])
    args = p.parse_args(argv)
    cfg = config.carregar()

    jogo = args.jogo or escolher_jogo(Path(cfg["biblioteca"]))
    if not jogo:
        return 1
    pasta_jogo = Path(cfg["biblioteca"]) / jogo

    dados = catalogo.carregar(pasta_jogo)
    edicao = receita.carregar(pasta_jogo, dados)
    if args.formato and args.formato != edicao.get("formato"):
        edicao["formato"] = args.formato
    receita.salvar(pasta_jogo, edicao)

    falar = lambda t: print(t, flush=True)  # noqa: E731
    try:
        saida = estudio.montar(pasta_jogo, dados, edicao, cfg, avisar=falar)
    except ValueError as erro:
        print(f"Nao montei: {erro}")
        estudio.anotar(pasta_jogo, rodando=False, mensagem=str(erro))
        return 2
    print(f"Pronto: {saida}")
    if estudio.passou_do_teto(pasta_jogo, cfg):
        tamanho = estudio.tamanho_do_cache(pasta_jogo) / 1024**3
        print(
            f"AVISO: os intermediarios ja somam {tamanho:.1f} GB neste jogo.\n"
            f'  python -m nucleo.esteira limpar "{jogo}"'
        )
    return 0


def etapa_limpar(argv=None) -> int:
    """Apaga os intermediarios de um jogo. Perder o cache custa um render."""
    p = argparse.ArgumentParser(description="Apaga os intermediarios do render.")
    p.add_argument("jogo", nargs="?", help="nome da pasta; sem isto, menu")
    args = p.parse_args(argv)
    cfg = config.carregar()

    jogo = args.jogo or escolher_jogo(Path(cfg["biblioteca"]))
    if not jogo:
        return 1
    liberado = estudio.limpar(Path(cfg["biblioteca"]) / jogo)
    print(f"Liberado: {liberado / 1024**2:.1f} MB")
    return 0


def etapa_ficha(argv=None) -> int:
    """Refaz a ficha de um jogo e o indice da biblioteca, lendo tudo do disco."""
    p = argparse.ArgumentParser(description="Refaz JOGO.md e JOGOS.md.")
    p.add_argument("jogo", nargs="?", help="nome da pasta; sem isto, todos")
    args = p.parse_args(argv)
    cfg = config.carregar()
    biblioteca = Path(cfg["biblioteca"])

    alvos = [biblioteca / args.jogo] if args.jogo else ficha.jogos(biblioteca)
    for pasta in alvos:
        print(f"ficha: {ficha.escrever(pasta)}")
    print(f"indice: {ficha.escrever_indice(biblioteca)}")
    return 0


if __name__ == "__main__":
    etapas = {
        "canais": etapa_canais,
        "gravar": etapa_gravar,
        "cortar": etapa_cortar,
        "estudio": etapa_estudio,
        "edicao": etapa_edicao,
        "render": etapa_render,
        "limpar": etapa_limpar,
        "ficha": etapa_ficha,
        "torcida": etapa_torcida,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in etapas:
        print(
            "Uso: python -m nucleo.esteira "
            "canais|gravar|cortar|estudio|edicao|render|limpar|ficha|torcida ..."
        )
        sys.exit(2)
    sys.exit(etapas[sys.argv[1]](sys.argv[2:]))
