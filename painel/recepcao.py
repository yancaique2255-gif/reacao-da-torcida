"""A recepção do estúdio: a biblioteca inteira numa porta só (8773).

O estúdio de hoje serve UM jogo, escolhido no terminal na largada: trocar de
jogo é fechar a janela e abrir de novo, e a tela não diz de que jogo se trata.
Com dois jogos no disco isso já não se sustenta.

Aqui o jogo vai na rota (`/api/jogo/<pasta>/...`), então trocar de jogo é
clicar - nada reinicia. O nome vem da URL e a URL é coisa que se digita, então
ele é casado com a lista de jogos do disco antes de virar caminho: é o que
impede um `..` de virar leitura de qualquer pasta da máquina.

Esta tela nasce ao lado da 8770, e não no lugar dela - reforma grande não se faz
na ferramenta em uso.
"""
import atexit
import json
import socket
import subprocess
import sys
import time
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nucleo import acervo, canais, catalogo, ficha, torcidas

PAGINA = Path(__file__).resolve().parent / "recepcao.html"
RAIZ = Path(__file__).resolve().parent.parent

# As portas dos estúdios de edição que esta recepção subiu. 8780 para cima
# porque 8770/8771/8772 são os painéis que o operador abre pelos atalhos.
PRIMEIRA_PORTA = 8780
PORTAS_DE_EDICAO = 20
SEGUNDOS_PARA_SUBIR = 8.0

_abertas: dict[str, int] = {}
_filhos: list[subprocess.Popen] = []


def _ocupada(porta: int) -> bool:
    with socket.socket() as tomada:
        tomada.settimeout(0.2)
        return tomada.connect_ex(("127.0.0.1", porta)) == 0


def porta_livre(primeira: int = PRIMEIRA_PORTA) -> int:
    for porta in range(primeira, primeira + PORTAS_DE_EDICAO):
        if not _ocupada(porta):
            return porta
    raise RuntimeError("nenhuma porta livre para o estúdio de edição")


def subir_edicao(
    pasta_jogo: Path, abertas: dict[str, int] | None = None, esperar=time.sleep
) -> int:
    """Sobe o estúdio de edição daquele jogo e devolve a porta dele.

    Um por jogo, e o mesmo se ele já estiver no ar: clicar duas vezes não pode
    render dois servidores disputando o mesmo `receita.json`.

    Vai o CAMINHO INTEIRO e não o nome da pasta, pelo mesmo motivo do render: o
    jogo pode não estar dentro da biblioteca configurada, e aí a edição abriria
    um jogo vazio sem ninguém entender por quê.
    """
    abertas = _abertas if abertas is None else abertas
    nome = Path(pasta_jogo).name
    porta = abertas.get(nome)
    if porta and _ocupada(porta):
        return porta

    porta = porta_livre()
    _filhos.append(subprocess.Popen(
        [sys.executable, "-m", "nucleo.esteira", "edicao",
         str(Path(pasta_jogo)), "--porta", str(porta)],
        cwd=str(RAIZ),
    ))
    abertas[nome] = porta

    # Devolver a porta antes de o servidor atender abriria uma aba morta, e o
    # operador aprenderia a clicar duas vezes em tudo.
    limite = time.monotonic() + SEGUNDOS_PARA_SUBIR
    while time.monotonic() < limite and not _ocupada(porta):
        esperar(0.15)
    return porta


@atexit.register
def _fechar_edicoes() -> None:
    """Fechar a recepção fecha as edições que ela subiu.

    Sem isto, uma tarde de trabalho deixa meia dúzia de servidores pendurados
    em portas que ninguém mais lembra.
    """
    for filho in _filhos:
        if filho.poll() is None:
            filho.terminate()


def _abrir_no_windows(caminho: Path) -> None:
    """Abre pasta no Explorador ou arquivo no programa de sempre."""
    import os

    os.startfile(str(caminho))  # noqa: S606 - caminho vem do disco, não da URL


def resolver(biblioteca: Path, nome: str) -> Path | None:
    """A pasta daquele jogo, e só se ela for um jogo desta biblioteca."""
    for pasta in ficha.jogos(biblioteca):
        if pasta.name == nome:
            return pasta
    return None


def _tela_do_jogo(pasta_jogo: Path, agora: float, cfg: dict) -> dict:
    """Tudo o que a tela do jogo precisa, numa resposta só.

    Uma chamada e não três porque os números não podem discordar entre si nem
    por um instante: escolher um clipe muda a contagem, a duração e a etapa.
    """
    dados = catalogo.carregar(pasta_jogo)
    resumo = acervo.resumo(pasta_jogo, agora, cfg)
    vistas = {c.get("torcida") or "" for c in dados.get("clipes") or []}
    return {
        "resumo": resumo,
        "gols": sorted(dados.get("gols") or [], key=lambda g: g["numero"]),
        "clipes": dados.get("clipes") or [],
        # Canal que gravou e não tem clipe daquele gol aparece marcado na tela.
        "faltas": acervo.faltas(dados, [c["canal"] for c in resumo["canais"]]),
        # As torcidas que ESTE jogo conhece: no jogo do Grêmio não faz sentido
        # oferecer "santos".
        "torcidas": sorted({t for t in vistas if t} | {canais.NEUTRO}),
    }


def montar_resposta(
    rota: str,
    corpo: dict,
    biblioteca: Path,
    cfg: dict,
    agora: float | None = None,
    abrir=None,
    subir=None,
) -> tuple[int, dict]:
    agora = time.time() if agora is None else agora
    abrir = abrir or _abrir_no_windows
    subir = subir or subir_edicao
    biblioteca = Path(biblioteca)

    metodo, _, caminho = rota.partition(" ")
    partes = [urllib.parse.unquote(p) for p in caminho.strip("/").split("/") if p]

    if metodo == "GET" and partes == ["api", "panorama"]:
        return 200, acervo.panorama(biblioteca, agora, cfg)

    if partes[:2] != ["api", "jogo"] or len(partes) < 3:
        return 404, {"erro": f"rota desconhecida: {rota}"}

    pasta_jogo = resolver(biblioteca, partes[2])
    if pasta_jogo is None:
        return 404, {"erro": f"jogo desconhecido: {partes[2]}"}
    acao = partes[3] if len(partes) > 3 else ""

    if metodo == "GET" and not acao:
        return 200, _tela_do_jogo(pasta_jogo, agora, cfg)

    if metodo == "POST" and acao == "escolha":
        dados = catalogo.carregar(pasta_jogo)
        try:
            dados = catalogo.marcar_escolha(
                dados, corpo["gol"], corpo["canal"], bool(corpo["escolhido"])
            )
        except KeyError as erro:
            return 404, {"erro": str(erro)}
        catalogo.salvar(pasta_jogo, dados)
        return 200, _tela_do_jogo(pasta_jogo, agora, cfg)

    if metodo == "POST" and acao == "torcida":
        # O canal sem torcida aparece marcado na tela e o conserto é ali mesmo.
        # Mandar o operador abrir um json no meio da curadoria é o jeito
        # garantido de o campo continuar vazio - e campo vazio tira o canal do
        # vídeo sem ninguém perceber.
        try:
            torcidas.aplicar(
                pasta_jogo, {corpo.get("canal", ""): corpo.get("torcida", "")}
            )
        except KeyError as erro:
            return 404, {"erro": erro.args[0]}
        except ValueError as erro:
            return 400, {"erro": str(erro)}
        # O cadastro é a origem: sem consertar lá, o buraco volta no próximo jogo.
        torcidas.definir_no_cadastro(canais.ARQUIVO, {corpo["canal"]: corpo["torcida"]})
        return 200, _tela_do_jogo(pasta_jogo, agora, cfg)

    if metodo == "POST" and acao == "abrir":
        # `Path("")` e a pasta atual, e ela existe: sem este `or None`, pedir o
        # video de um jogo que ainda nao renderizou abria a pasta do servidor.
        pronto = acervo.video(pasta_jogo).get("arquivo") or ""
        onde = {
            "pasta": pasta_jogo,
            "saida": pasta_jogo / "saida",
            "video": Path(pronto) if pronto else None,
        }.get(corpo.get("o_que") or "pasta")
        if onde is None or not onde.exists():
            return 404, {"erro": "isso ainda não existe no disco"}
        abrir(onde)
        return 200, {"ok": True, "caminho": str(onde)}

    if metodo == "POST" and acao == "edicao":
        porta = subir(pasta_jogo)
        return 200, {"ok": True, "porta": porta, "url": f"http://127.0.0.1:{porta}/"}

    return 404, {"erro": f"rota desconhecida: {rota}"}


class _Manipulador(SimpleHTTPRequestHandler):
    def __init__(self, *args, biblioteca: Path, cfg: dict, **kwargs):
        self.biblioteca = biblioteca
        self.cfg = cfg
        super().__init__(*args, directory=str(biblioteca), **kwargs)

    def _responder(self, codigo: int, corpo: dict) -> None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path in ("/", "/index.html") or self.path.startswith("/#"):
            pagina = PAGINA.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(pagina)))
            self.end_headers()
            self.wfile.write(pagina)
            return
        if self.path.startswith("/api/"):
            codigo, corpo = montar_resposta(
                f"GET {self.path}", {}, self.biblioteca, self.cfg
            )
            self._responder(codigo, corpo)
            return
        if self.path.startswith("/midia/"):
            self.path = self.path[len("/midia"):]
        super().do_GET()

    def do_HEAD(self):
        if self.path.startswith("/midia/"):
            self.path = self.path[len("/midia"):]
        super().do_HEAD()

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        codigo, resposta = montar_resposta(
            f"POST {self.path}", corpo, self.biblioteca, self.cfg
        )
        self._responder(codigo, resposta)


def servir(biblioteca: Path, cfg: dict, porta: int = 8773) -> None:
    manipulador = partial(_Manipulador, biblioteca=Path(biblioteca), cfg=cfg)
    with ThreadingHTTPServer(("127.0.0.1", porta), manipulador) as servidor_http:
        print(f"Recepção do estúdio em http://127.0.0.1:{porta}  (Ctrl+C para parar)")
        print(f"Biblioteca: {biblioteca}")
        servidor_http.serve_forever()
