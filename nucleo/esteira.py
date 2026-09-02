"""As quatro etapas da esteira; os .bat sao cascas em volta daqui."""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from nucleo import canais as mod_canais
from nucleo import catalogo, config, cortador, gravador, relogio


def nome_do_jogo(
    mandante: str, visitante: str, data: datetime | None = None
) -> str:
    data = data or datetime.now()
    return (
        f"{data:%Y-%m-%d} {gravador.apelido(mandante)} x "
        f"{gravador.apelido(visitante)}"
    )


def _cadastro() -> dict[str, list[mod_canais.Canal]]:
    arquivo = Path(__file__).resolve().parent.parent / "dados" / "canais.json"
    return mod_canais.carregar(arquivo)


def etapa_canais(argv=None) -> int:
    p = argparse.ArgumentParser(description="Lista as lives escolhidas manualmente.")
    p.add_argument("time")
    args = p.parse_args(argv)
    cfg = config.carregar()

    escolhidos = mod_canais.selecionados_do_time(args.time, _cadastro())
    for canal, url in escolhidos:
        print(f"SELECIONADO  {canal.nome}  {url}")
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
    print(f"Gravando {len(processos)} canal(is) em {cfg['biblioteca']}\\{jogo}")
    print("Feche esta janela para parar.")
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


def etapa_cortar(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Gera clipes nos horarios exatos informados manualmente."
    )
    p.add_argument("jogo", help="nome da pasta do jogo")
    p.add_argument(
        "--gols",
        nargs="+",
        required=True,
        help="horarios exatos na gravacao, ex: 21:37:00 22:05:30",
    )
    args = p.parse_args(argv)
    cfg = config.carregar()

    pasta_jogo = Path(cfg["biblioteca"]) / args.jogo
    pasta_bruto = pasta_jogo / "bruto"
    if not pasta_bruto.is_dir():
        print(f"Pasta de gravacoes nao encontrada: {pasta_bruto}")
        return 1

    dados = catalogo.carregar(pasta_jogo)
    data_jogo = _data_da_pasta(args.jogo)
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
    referencia = next(iter(por_canal.values()))

    for numero, texto in enumerate(args.gols, start=1):
        momento = resolver_horario(texto, referencia, data_jogo)
        dados = catalogo.registrar_gol(dados, numero, momento.isoformat(), "")
        inicio, fim = relogio.janela(
            momento, cfg["segundos_antes"], cfg["segundos_depois"]
        )
        destino = pasta_jogo / "clipes" / f"gol-{numero:02d}"
        destino.mkdir(parents=True, exist_ok=True)

        for nome, sessoes in por_canal.items():
            pasta_canal = pasta_bruto / nome
            recortes = relogio.trechos(sessoes, inicio, fim)
            duracao_coberta = sum(t.fim - t.inicio for t in recortes)
            if not recortes or duracao_coberta < tamanho - 0.05:
                gravado = ", ".join(
                    f"{de:%H:%M:%S}-{ate:%H:%M:%S}"
                    for de, ate in relogio.cobertura(sessoes)
                ) or "nada"
                print(
                    f"gol {numero}: {nome} nao cobre todo o corte em "
                    f"{momento:%H:%M:%S} - gravado: {gravado}"
                )
                continue

            temporaria = pasta_canal / f"janela-manual-{numero:02d}.ts"
            fonte, deslocamento = cortador.preparar_fonte(
                recortes, pasta_canal, temporaria, cfg["caminho_ffmpeg"]
            )
            saida = destino / f"{nome}.mp4"
            cortador.executar(
                cortador.comando_corte(
                    fonte,
                    deslocamento,
                    tamanho,
                    saida,
                    cfg["caminho_ffmpeg"],
                )
            )
            dados = catalogo.registrar_clipe(
                dados,
                numero,
                nome,
                str(saida.relative_to(pasta_jogo)).replace("\\", "/"),
                deslocamento,
                0.0,
                False,
            )
            print(f"gol {numero}: {nome} -> {saida.name}  (CORTE MANUAL)")
            temporaria.unlink(missing_ok=True)  # a juncao, quando houve
            temporaria.with_suffix(".txt").unlink(missing_ok=True)

    catalogo.salvar(pasta_jogo, dados)
    return 0


def etapa_estudio(argv=None) -> int:
    from painel import servidor

    p = argparse.ArgumentParser()
    p.add_argument("jogo")
    p.add_argument("--porta", type=int, default=8770)
    args = p.parse_args(argv)
    cfg = config.carregar()
    servidor.servir(Path(cfg["biblioteca"]) / args.jogo, cfg, args.porta)
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
