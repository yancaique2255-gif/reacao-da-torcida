"""Painel de acompanhamento da gravacao: so le o disco, nunca mexe em nada.

O painel de curadoria (servidor.py) e outro: aquele e do depois do jogo. Este
serve para o durante, e por isso mora numa porta propria - os dois podem estar
abertos ao mesmo tempo.
"""
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from urllib.parse import parse_qs, urlparse

from nucleo import alinhamento, catalogo, config, cronometro, esteira
from nucleo import miniatura, monitor, placar, relogio

PAGINA = Path(__file__).resolve().parent / "gravacao.html"
PORTA_PADRAO = 8771
# Pasta de corte parada por mais que isto, com o catalogo ainda vazio, nao
# esta mais trabalhando: o corte morreu no meio. Cinco minutos folgam bem
# sobre o pior caso medido - onze canais recodificando em fila de tres.
CORTE_PARADO_APOS = 300.0


def estado(biblioteca: Path, agora: float) -> dict:
    """O que a pagina precisa: os jogos, com seus canais, e a hora da medicao."""
    jogos = monitor.panorama(biblioteca, agora)
    for j in jogos:
        j["gols"] = gols_do_jogo(biblioteca, j["jogo"], j["total"], agora)
        medidos = alinhamento.deslocamentos_do_jogo(
            Path(biblioteca) / j["jogo"] / "bruto"
        )
        for canal in j["canais"]:
            canal["deslocamento"] = medidos.get(canal["canal"])
        j["tem_clipes"] = pasta_dos_clipes(Path(biblioteca) / j["jogo"]).is_dir()
        try:
            j["espn"] = espn_do_jogo(biblioteca, j["jogo"], agora)
        except Exception:
            j["espn"] = None  # placar e um extra: nunca derruba o painel
    return {
        "hora": time.strftime("%H:%M:%S", time.localtime(agora)),
        "jogos": jogos,
        "gravando": sum(j["gravando"] for j in jogos),
        "total": sum(j["total"] for j in jogos),
        "mb": sum(j["mb"] for j in jogos),
    }


def _dentro(raiz: Path, nome: str) -> Path:
    """Junta os dois caminhos so se o resultado continuar dentro da raiz.

    Jogo e canal chegam pela pagina; nome nenhum pode virar caminho de fuga.
    """
    base = Path(raiz).resolve()
    destino = (base / nome).resolve()
    if base not in destino.parents:
        raise ValueError(f"caminho fora de {base}: {nome}")
    return destino


def _pasta_do_jogo(biblioteca: Path, jogo: str) -> Path:
    return _dentro(Path(biblioteca), jogo)


def marcar(biblioteca: Path, jogo: str, agora: datetime, atraso: float = 0.0) -> dict:
    """Grava o horario do gol no disco, na hora do clique.

    E o passo mais fragil da esteira: ate agora o operador anotava a hora no
    papel e digitava depois. `atraso` desconta a diferenca entre a tela dele e
    o ao vivo, para quem assiste por outra fonte.
    """
    pasta = _pasta_do_jogo(biblioteca, jogo)
    dados = catalogo.carregar(pasta)
    numero = catalogo.proximo_numero(dados)
    momento = agora - timedelta(seconds=atraso)
    dados = catalogo.registrar_gol(
        dados, numero, momento.isoformat(timespec="seconds"), ""
    )
    catalogo.salvar(pasta, dados)
    return {"numero": numero, "horario": momento.strftime("%H:%M:%S")}


def mover(biblioteca: Path, jogo: str, numero: int, segundos: float) -> dict:
    pasta = _pasta_do_jogo(biblioteca, jogo)
    dados = catalogo.mover_gol(catalogo.carregar(pasta), numero, segundos)
    catalogo.salvar(pasta, dados)
    return {"ok": True}


def apagar(biblioteca: Path, jogo: str, numero: int) -> dict:
    pasta = _pasta_do_jogo(biblioteca, jogo)
    dados = catalogo.remover_gol(catalogo.carregar(pasta), numero)
    catalogo.salvar(pasta, dados)
    return {"ok": True}


def pasta_do_corte(pasta_jogo: Path, numero: int) -> Path:
    return Path(pasta_jogo) / "clipes" / f"gol-{numero:02d}"


def estado_do_corte(
    pasta_jogo: Path, numero: int, total: int, agora: float, dados: dict | None = None
) -> dict:
    """Em que pe esta o corte de um gol, lido so do disco.

    O painel nao conversa com quem corta - o corte roda dentro do supervisor da
    gravacao, noutro processo. O que sobra sao dois rastros: a pasta do gol, que
    vai enchendo de .mp4, e o catalogo, que so e salvo quando o corte inteiro
    termina. Um da o andamento, o outro da o fim.
    """
    pasta_jogo = Path(pasta_jogo)
    destino = pasta_do_corte(pasta_jogo, numero)
    if dados is None:
        dados = catalogo.carregar(pasta_jogo)

    prontos = [c for c in dados.get("clipes", []) if c.get("gol") == numero]
    if prontos:
        # O catalogo fechou: acabou. Se veio menos que o total, canal ficou sem
        # material - o contador conta essa historia sozinho, sem travar o gol
        # em "cortando" para sempre.
        return {"situacao": "pronto", "feitos": len(prontos),
                "total": total, "pasta": True}

    if not destino.is_dir():
        return {"situacao": "aguardando", "feitos": 0, "total": total, "pasta": False}

    arquivos = list(destino.glob("*.mp4"))
    mexeu = max(
        [destino.stat().st_mtime] + [a.stat().st_mtime for a in arquivos]
    )
    situacao = "parou" if agora - mexeu > CORTE_PARADO_APOS else "cortando"
    return {"situacao": situacao, "feitos": len(arquivos),
            "total": total, "pasta": True}


def gols_do_jogo(
    biblioteca: Path, jogo: str, total: int = 0, agora: float | None = None
) -> list[dict]:
    pasta = _pasta_do_jogo(biblioteca, jogo)
    dados = catalogo.carregar(pasta)
    agora = time.time() if agora is None else agora
    return [
        {
            "numero": g["numero"],
            "horario": g["horario"][11:19],
            "corte": estado_do_corte(pasta, g["numero"], total, agora, dados),
        }
        for g in dados["gols"]
    ]


def _no_explorador(pasta: Path) -> None:
    os.startfile(str(pasta))  # so existe no Windows, que e onde isto roda


def pasta_dos_clipes(pasta_jogo: Path) -> Path:
    return Path(pasta_jogo) / "clipes"


def abrir_pasta(biblioteca: Path, jogo: str, abrir=None) -> dict:
    """Abre no Explorador a pasta de clipes do jogo, com um gol por subpasta.

    Um botao por jogo, e nao por gol: dentro de `clipes` o Explorador ja mostra
    gol-01, gol-02, e dali se navega mais rapido do que voltando ao painel.

    Conferir o corte e olhar o video, e olhar video e no player do sistema, nao
    no navegador: e por isso que o botao abre a pasta em vez de tocar aqui.
    """
    destino = pasta_dos_clipes(_pasta_do_jogo(biblioteca, jogo))
    if not destino.is_dir():
        return {"ok": False, "motivo": "este jogo ainda não tem clipe cortado"}
    (abrir or _no_explorador)(destino)
    return {"ok": True, "pasta": str(destino)}


def ajustar(biblioteca: Path, jogo: str, canal: str, segundos: float) -> dict:
    """O atrasador manual: quantos segundos este canal esta atras dos outros."""
    pasta = _dentro(_pasta_do_jogo(biblioteca, jogo) / "bruto", canal)
    valor = alinhamento.gravar_deslocamento(pasta, segundos, "manual")
    return {"ok": True, "canal": canal, "deslocamento": valor}


def medir_alinhamento(
    biblioteca: Path, jogo: str, numero: int, cfg: dict, forcar: bool = False
) -> dict:
    """Roda o consenso sobre um gol ja marcado e guarda o que achou.

    E o caminho automatico do que `ajustar` faz na mao: em vez de o operador
    cronometrar canal por canal, o proprio grito do gol revela o atraso.
    """
    pasta_jogo = _pasta_do_jogo(biblioteca, jogo)
    bruto = pasta_jogo / "bruto"
    dados = catalogo.carregar(pasta_jogo)
    gol = next((g for g in dados["gols"] if g["numero"] == numero), None)
    if gol is None:
        raise KeyError(f"gol {numero} nao existe")

    por_canal = {
        pasta.name: esteira._sessoes_do_canal(pasta, cfg)
        for pasta in sorted(bruto.iterdir())
        if (pasta / "gravacao.json").is_file()
    }
    momento = datetime.fromisoformat(gol["horario"])
    picos = alinhamento.picos_do_gol(por_canal, bruto, momento, cfg)
    consenso = alinhamento.medir(picos, cfg["limiar_confianca_db"])
    if consenso is None:
        return {
            "ok": False,
            "motivo": "menos de dois canais acusaram: sem consenso, nada e gravado",
            "picos": {c: round(f, 1) for c, (_, f) in picos.items()},
        }

    gravados = alinhamento.guardar_consenso(bruto, consenso, forcar)
    return {
        "ok": True,
        "gravado": bool(gravados),
        "deslocamentos": gravados,
        "espalhamento": consenso.espalhamento,
        "confiavel": consenso.confiavel,
        "participantes": consenso.participantes,
    }


_ESPN_EM_CACHE: dict[str, tuple[float, object]] = {}
SEGUNDOS_DE_CACHE_DA_ESPN = 15  # a pagina atualiza a cada 3s; a API nao e nossa


def espn_do_jogo(biblioteca: Path, jogo: str, agora: float | None = None) -> dict | None:
    """O que a ESPN diz desta partida agora, com o instante da consulta.

    O instante importa tanto quanto o placar: o cronometro anda um segundo por
    segundo, entao saber QUANDO se leu permite calcular o minuto do jogo em
    qualquer outro momento.
    """
    agora = time.time() if agora is None else agora
    dados = catalogo.carregar(_pasta_do_jogo(biblioteca, jogo))
    partida_de = dados.get("partida") or {}
    liga = partida_de.get("liga")
    if not liga:
        return None

    quando, guardado = _ESPN_EM_CACHE.get(jogo, (0.0, None))
    if agora - quando > SEGUNDOS_DE_CACHE_DA_ESPN:
        guardado = placar.achar(
            placar.buscar(liga), partida_de["mandante"], partida_de["visitante"]
        )
        _ESPN_EM_CACHE[jogo] = (agora, guardado)
        quando = agora
    if guardado is None:
        return None
    return {
        "placar": str(guardado),
        "relogio": guardado.relogio,
        "segundo_de_jogo": guardado.segundo_de_jogo,
        "estado": guardado.estado,
        "lido_em": datetime.fromtimestamp(quando).isoformat(timespec="seconds"),
        "acabou": guardado.acabou,
    }


def instante_do_quadro(
    biblioteca: Path, jogo: str, canal: str, cfg: dict
) -> datetime | None:
    """Hora de relogio do quadro que a miniatura mostra.

    O quadro sai de seis segundos antes do fim do arquivo, entao ele mostra o
    fim da cobertura menos esse recuo. Sem esta hora nao da para comparar o
    cronometro da tela com o da ESPN: os dois andam.
    """
    pasta = _dentro(_pasta_do_jogo(biblioteca, jogo) / "bruto", canal)
    if not (pasta / "gravacao.json").is_file():
        return None
    intervalos = relogio.cobertura(esteira._sessoes_do_canal(pasta, cfg))
    if not intervalos:
        return None
    return intervalos[-1][1] - timedelta(seconds=miniatura.RECUO)


def cronometrar(
    biblioteca: Path, jogo: str, canal: str, texto: str, tempo: int,
    instante: str, cfg: dict,
) -> dict:
    """Compara o cronometro que a tela mostrava com o da ESPN naquele instante.

    E o alinhamento que nao depende de gol nenhum: qualquer quadro da partida
    serve, porque os dois relogios marcam a mesma coisa.
    """
    do_canal = cronometro.segundos_do_texto(texto, tempo)
    if do_canal is None:
        raise ValueError(f"nao entendi o cronometro: {texto!r}")

    espn = espn_do_jogo(biblioteca, jogo)
    if espn is None or espn.get("segundo_de_jogo") is None:
        raise ValueError(
            "a ESPN nao esta dando o cronometro desta partida agora - "
            "use o campo de atraso na mao"
        )

    visto_em = datetime.fromisoformat(instante)
    lido_em = datetime.fromisoformat(espn["lido_em"])
    # O cronometro anda junto com o relogio: leva-se o minuto da ESPN de volta
    # ao instante do quadro para comparar as duas leituras no mesmo momento.
    espn_no_quadro = espn["segundo_de_jogo"] - (lido_em - visto_em).total_seconds()

    if not cronometro.mesma_metade(espn_no_quadro, do_canal):
        raise ValueError(
            "o cronometro digitado esta na outra metade do jogo - confira o tempo"
        )

    segundos = cronometro.atraso(espn_no_quadro, do_canal)
    pasta = _dentro(_pasta_do_jogo(biblioteca, jogo) / "bruto", canal)
    valor = alinhamento.gravar_deslocamento(pasta, segundos, "cronometro")
    return {
        "ok": True, "canal": canal, "deslocamento": valor,
        "espn_no_quadro": round(espn_no_quadro, 1), "no_canal": do_canal,
    }


def _taskkill(pid: int) -> None:
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)


def parar_gravacao(biblioteca: Path, jogo: str, matar=_taskkill) -> dict:
    """Derruba a gravacao de UM jogo: primeiro o supervisor, depois as arvores.

    A ordem importa. Derrubar os canais antes deixaria o supervisor vivo para
    religar tudo em seguida - e com max_tentativas em 60 ele insistiria muito.

    Pid de processo ja morto e inofensivo: o taskkill falha calado.
    """
    pasta = _pasta_do_jogo(biblioteca, jogo)
    derrubados = []

    arquivo_pid = pasta / "supervisor.pid"
    if arquivo_pid.is_file():
        try:
            pid = int(arquivo_pid.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = 0
        if pid:
            matar(pid)
            derrubados.append(pid)
        # Sai do disco para o proximo PARAR nao mirar num pid ja reciclado.
        arquivo_pid.unlink(missing_ok=True)

    bruto = pasta / "bruto"
    if bruto.is_dir():
        for canal in sorted(bruto.iterdir()):
            arquivo = canal / "gravacao.json"
            if not arquivo.is_file():
                continue
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            for sessao in dados.get("sessoes") or []:
                pid = sessao.get("pid")
                if pid:
                    matar(pid)
                    derrubados.append(pid)
    return {"ok": True, "derrubados": len(set(derrubados))}


def quadro_do_canal(biblioteca: Path, jogo: str, canal: str, cfg: dict) -> Path | None:
    """Quadro recente do canal. Guardado fora de `bruto` para nao virar gravacao."""
    pasta_jogo = _pasta_do_jogo(biblioteca, jogo)
    pasta_canal = _dentro(pasta_jogo / "bruto", canal)
    if not pasta_canal.is_dir():
        return None
    return miniatura.gerar(
        pasta_canal,
        pasta_jogo / "miniaturas" / f"{canal}.jpg",
        cfg["caminho_ffmpeg"],
    )


class _Manipulador(BaseHTTPRequestHandler):
    biblioteca = Path(".")
    cfg: dict = {}

    def log_message(self, *args):  # silencio: a janela e do usuario
        pass

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        acoes = {
            "/api/marcar": lambda c: marcar(
                self.biblioteca, c["jogo"], datetime.now(), float(c.get("atraso", 0))
            ),
            "/api/mover": lambda c: mover(
                self.biblioteca, c["jogo"], int(c["numero"]), float(c["segundos"])
            ),
            "/api/apagar": lambda c: apagar(
                self.biblioteca, c["jogo"], int(c["numero"])
            ),
            "/api/parar": lambda c: parar_gravacao(self.biblioteca, c["jogo"]),
            "/api/cronometrar": lambda c: cronometrar(
                self.biblioteca, c["jogo"], c["canal"], c["relogio"],
                int(c.get("tempo", 0)), c["instante"], self.cfg,
            ),
            "/api/ajustar": lambda c: ajustar(
                self.biblioteca, c["jogo"], c["canal"], float(c["segundos"])
            ),
            "/api/abrir": lambda c: abrir_pasta(self.biblioteca, c["jogo"]),
            "/api/alinhar": lambda c: medir_alinhamento(
                self.biblioteca, c["jogo"], int(c["numero"]), self.cfg,
                bool(c.get("forcar")),
            ),
        }
        acao = acoes.get(self.path)
        if acao is None:
            self.send_error(404)
            return
        try:
            resposta, codigo = acao(corpo), 200
        except (KeyError, ValueError) as erro:
            resposta, codigo = {"erro": str(erro)}, 400
        dados = json.dumps(resposta, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        extras: dict[str, str] = {}
        if self.path.startswith("/api/estado"):
            corpo = json.dumps(
                estado(self.biblioteca, time.time()), ensure_ascii=False
            ).encode("utf-8")
            tipo = "application/json; charset=utf-8"
        elif self.path.startswith("/api/quadro"):
            campos = parse_qs(urlparse(self.path).query)
            try:
                arquivo = quadro_do_canal(
                    self.biblioteca,
                    campos.get("jogo", [""])[0],
                    campos.get("canal", [""])[0],
                    self.cfg,
                )
            except ValueError:
                self.send_error(400)
                return
            if arquivo is None or not arquivo.is_file():
                self.send_error(404)
                return
            corpo, tipo = arquivo.read_bytes(), "image/jpeg"
            try:
                quando = instante_do_quadro(
                    self.biblioteca, campos.get("jogo", [""])[0],
                    campos.get("canal", [""])[0], self.cfg,
                )
            except Exception:
                quando = None
            if quando:
                # A pagina precisa saber de QUE momento e o quadro que ela
                # esta mostrando: e contra esse instante que o cronometro da
                # tela vai ser comparado com o da ESPN.
                extras["X-Instante"] = quando.isoformat()
        elif self.path in ("/", "/index.html"):
            corpo = PAGINA.read_bytes()
            tipo = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        for nome, valor in extras.items():
            self.send_header(nome, valor)
        self.end_headers()
        self.wfile.write(corpo)


def servir(biblioteca: Path, porta: int = PORTA_PADRAO) -> None:
    _Manipulador.biblioteca = Path(biblioteca)
    _Manipulador.cfg = config.carregar()
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), _Manipulador)
    print(f"Painel da gravacao em http://127.0.0.1:{porta}")
    print("Fechar esta janela NAO para a gravacao.")
    servidor.serve_forever()


def main(argv=None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Painel de acompanhamento da gravacao.")
    p.add_argument("--porta", type=int, default=PORTA_PADRAO)
    args = p.parse_args(argv)
    servir(Path(config.carregar()["biblioteca"]), args.porta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
