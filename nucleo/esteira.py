"""As quatro etapas da esteira; os .bat sao cascas em volta daqui."""
import argparse
import sys
from datetime import datetime
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
    for processo in processos:
        processo.processo.wait()
    return 0


def _sessoes_do_canal(pasta: Path) -> list[relogio.Sessao]:
    import json

    dados = json.loads((pasta / "gravacao.json").read_text(encoding="utf-8"))
    sessoes = []
    for sessao in dados["sessoes"]:
        csv = pasta / f"s{sessao['numero']:02d}-segmentos.csv"
        if csv.is_file():
            sessoes.append(
                relogio.ler_segmentos(csv, datetime.fromisoformat(sessao["t0"]))
            )
    return sessoes


def _data_da_pasta(jogo: str):
    try:
        return datetime.strptime(jogo[:10], "%Y-%m-%d").date()
    except ValueError:
        return datetime.now().date()


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

    for numero, texto in enumerate(args.gols, start=1):
        momento = datetime.combine(
            data_jogo, datetime.strptime(texto, "%H:%M:%S").time()
        )
        dados = catalogo.registrar_gol(dados, numero, momento.isoformat(), "")
        inicio, fim = relogio.janela(
            momento, cfg["segundos_antes"], cfg["segundos_depois"]
        )
        destino = pasta_jogo / "clipes" / f"gol-{numero:02d}"
        destino.mkdir(parents=True, exist_ok=True)

        for pasta_canal in sorted(pasta_bruto.iterdir()):
            if not (pasta_canal / "gravacao.json").is_file():
                continue
            nome = pasta_canal.name
            sessoes = _sessoes_do_canal(pasta_canal)
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
