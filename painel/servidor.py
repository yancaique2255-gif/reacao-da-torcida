"""Painel de curadoria: servidor local e rotas testaveis."""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nucleo import catalogo, montador

PAGINA = Path(__file__).resolve().parent / "pagina.html"


def montar_resposta(
    rota: str, corpo: dict, pasta_jogo: Path, cfg: dict
) -> tuple[int, dict]:
    if rota == "GET /api/catalogo":
        return 200, catalogo.carregar(pasta_jogo)

    if rota == "POST /api/escolha":
        dados = catalogo.carregar(pasta_jogo)
        try:
            dados = catalogo.marcar_escolha(
                dados, corpo["gol"], corpo["canal"], bool(corpo["escolhido"])
            )
        except KeyError as erro:
            return 404, {"erro": str(erro)}
        catalogo.salvar(pasta_jogo, dados)
        return 200, {"ok": True}

    if rota == "POST /api/montar":
        dados = catalogo.carregar(pasta_jogo)
        try:
            saida = montador.montar(catalogo.escolhidos(dados), pasta_jogo, cfg)
        except ValueError as erro:
            return 400, {"erro": str(erro)}
        return 200, {"ok": True, "arquivo": str(saida)}

    return 404, {"erro": f"rota desconhecida: {rota}"}


class _Manipulador(SimpleHTTPRequestHandler):
    def __init__(self, *args, pasta_jogo: Path, cfg: dict, **kwargs):
        self.pasta_jogo = pasta_jogo
        self.cfg = cfg
        super().__init__(*args, directory=str(pasta_jogo), **kwargs)

    def _responder(self, codigo: int, corpo: dict) -> None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            pagina = PAGINA.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(pagina)))
            self.end_headers()
            self.wfile.write(pagina)
            return
        if self.path.startswith("/api/"):
            codigo, corpo = montar_resposta(
                f"GET {self.path}", {}, self.pasta_jogo, self.cfg
            )
            self._responder(codigo, corpo)
            return
        if self.path.startswith("/midia/"):
            self.path = self.path[len("/midia") :]
        super().do_GET()

    def do_HEAD(self):
        if self.path.startswith("/midia/"):
            self.path = self.path[len("/midia") :]
        super().do_HEAD()

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        codigo, resposta = montar_resposta(
            f"POST {self.path}", corpo, self.pasta_jogo, self.cfg
        )
        self._responder(codigo, resposta)


def servir(pasta_jogo: Path, cfg: dict, porta: int = 8770) -> None:
    manipulador = partial(_Manipulador, pasta_jogo=Path(pasta_jogo), cfg=cfg)
    with ThreadingHTTPServer(("127.0.0.1", porta), manipulador) as servidor_http:
        print(f"Painel em http://127.0.0.1:{porta}  (Ctrl+C para parar)")
        servidor_http.serve_forever()
