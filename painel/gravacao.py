"""Painel de acompanhamento da gravacao: so le o disco, nunca mexe em nada.

O painel de curadoria (servidor.py) e outro: aquele e do depois do jogo. Este
serve para o durante, e por isso mora numa porta propria - os dois podem estar
abertos ao mesmo tempo.
"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nucleo import config, monitor

PAGINA = Path(__file__).resolve().parent / "gravacao.html"
PORTA_PADRAO = 8771


def estado(biblioteca: Path, agora: float) -> dict:
    """O que a pagina precisa: os jogos, com seus canais, e a hora da medicao."""
    jogos = monitor.panorama(biblioteca, agora)
    return {
        "hora": time.strftime("%H:%M:%S", time.localtime(agora)),
        "jogos": jogos,
        "gravando": sum(j["gravando"] for j in jogos),
        "total": sum(j["total"] for j in jogos),
        "mb": sum(j["mb"] for j in jogos),
    }


class _Manipulador(BaseHTTPRequestHandler):
    biblioteca = Path(".")

    def log_message(self, *args):  # silencio: a janela e do usuario
        pass

    def do_GET(self):
        if self.path.startswith("/api/estado"):
            corpo = json.dumps(
                estado(self.biblioteca, time.time()), ensure_ascii=False
            ).encode("utf-8")
            tipo = "application/json; charset=utf-8"
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
