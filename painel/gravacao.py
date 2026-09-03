"""Painel de acompanhamento da gravacao: so le o disco, nunca mexe em nada.

O painel de curadoria (servidor.py) e outro: aquele e do depois do jogo. Este
serve para o durante, e por isso mora numa porta propria - os dois podem estar
abertos ao mesmo tempo.
"""
import json
import subprocess
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from urllib.parse import parse_qs, urlparse

from nucleo import alinhamento, catalogo, config, esteira, miniatura, monitor

PAGINA = Path(__file__).resolve().parent / "gravacao.html"
PORTA_PADRAO = 8771


def estado(biblioteca: Path, agora: float) -> dict:
    """O que a pagina precisa: os jogos, com seus canais, e a hora da medicao."""
    jogos = monitor.panorama(biblioteca, agora)
    for j in jogos:
        j["gols"] = gols_do_jogo(biblioteca, j["jogo"])
        medidos = alinhamento.deslocamentos_do_jogo(
            Path(biblioteca) / j["jogo"] / "bruto"
        )
        for canal in j["canais"]:
            canal["deslocamento"] = medidos.get(canal["canal"])
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


def gols_do_jogo(biblioteca: Path, jogo: str) -> list[dict]:
    dados = catalogo.carregar(_pasta_do_jogo(biblioteca, jogo))
    return [
        {"numero": g["numero"], "horario": g["horario"][11:19]}
        for g in dados["gols"]
    ]


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
            "/api/ajustar": lambda c: ajustar(
                self.biblioteca, c["jogo"], c["canal"], float(c["segundos"])
            ),
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
