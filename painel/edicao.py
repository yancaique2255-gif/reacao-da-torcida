"""O painel do estudio de edicao: porta 8772, arquivo novo, ao lado do de hoje.

Isso e deliberado. O estudio da 8770 e o que o operador usa para trabalhar, e
reforma grande nao se faz na ferramenta em uso: o novo nasce ao lado, prova que
funciona num jogo de verdade, e so entao o velho sai.

As rotas sao finas de proposito. Quem decide o que entra e o `perdedor`, quem
propoe o corte e o `melhor`, quem guarda a escolha e a `receita` e quem monta e
o `estudio`. Aqui so se traduz clique em chamada - e se grava em disco antes de
a tela mudar.
"""
import json
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nucleo import canais, capa, catalogo, cortador, estudio, molde
from nucleo import perdedor, publicacao, receita, torcidas

PAGINA = Path(__file__).resolve().parent / "edicao.html"
RAIZ = Path(__file__).resolve().parent.parent


def lancar_render(pasta_jogo: Path) -> int:
    """Sobe o render num processo proprio e devolve o PID dele.

    O painel pode ser fechado e reaberto sem matar o render; o progresso vive
    em `render.json`, do mesmo jeito que o supervisor da gravacao.

    Vai o CAMINHO INTEIRO, e nao o nome da pasta: o jogo aberto no painel pode
    nao estar dentro da biblioteca configurada, e ai o render montaria um jogo
    vazio sem ninguem entender por que.
    """
    processo = subprocess.Popen(
        [sys.executable, "-m", "nucleo.esteira", "render", str(Path(pasta_jogo))],
        cwd=str(RAIZ),
    )
    return processo.pid


def _clipes(dados: dict) -> dict:
    return {(c["gol"], c["canal"]): c for c in dados.get("clipes", [])}


def _torcidas_do_jogo(dados: dict) -> list[str]:
    """As torcidas que aparecem nos clipes - e o que o "rindo do" pode oferecer.

    `neutro` fica de fora: narracao sem lado nao tem frustracao para filmar.
    """
    vistas = {c.get("torcida") or "" for c in dados.get("clipes", [])}
    return sorted(t for t in vistas if t and t != canais.NEUTRO)


def tela(pasta_jogo: Path, dados: dict, edicao: dict, cfg: dict) -> dict:
    """Tudo o que a pagina precisa para se desenhar, numa resposta so.

    Uma chamada e nao cinco porque a tela e uma coisa so: o corte de um clipe
    muda quanto video vai sair, e os dois numeros nao podem discordar nem por um
    instante.
    """
    formato = edicao.get("formato", receita.FORMATO_PADRAO)
    clipes = _clipes(dados)
    alvo = perdedor.alvo(dados)

    gols = []
    for gol in dados.get("gols", []):
        itens = []
        for item in sorted(
            (i for i in edicao["itens"] if i["gol"] == gol["numero"]),
            key=lambda i: (not i["entra"], i["ordem"]),
        ):
            clipe = clipes.get((item["gol"], item["canal"]), {})
            itens.append({
                **item,
                "torcida": clipe.get("torcida", ""),
                "instante": clipe.get("instante", 0.0),
                "duracao": clipe.get("duracao", 0.0),
                "confianca_db": clipe.get("confianca_db", 0.0),
                "tem_pico": clipe.get("tem_pico", False),
                "parcial": clipe.get("parcial", False),
                "arquivo": "/midia/" + str(clipe.get("arquivo", "")).replace("\\", "/"),
            })
        gols.append({
            "numero": gol["numero"],
            "horario": gol.get("horario", ""),
            "placar": estudio.placar_do_gol(dados, gol["numero"]),
            # Os dois numeros crus, para os campos do placar daquele gol: a
            # tela precisa preencher os campos, e nao so mostrar a frase.
            "gols": list(gol.get("placar") or []),
            "itens": itens,
        })

    entram = receita.itens_do_video(edicao)
    quantos_gols = len({i["gol"] for i in entram})
    segundos = sum(i["ate"] - i["de"] for i in entram)
    segundos += quantos_gols * estudio.DURACAO_DA_CARTELA

    return {
        "jogo": Path(pasta_jogo).name,
        "partida": dados.get("partida") or {},
        "alvo": {
            "torcida": alvo.torcida, "time": alvo.time,
            "motivo": alvo.motivo, "decidido": alvo.decidido,
        },
        "torcidas": _torcidas_do_jogo(dados),
        "formato": formato,
        "duracao_por_clipe": (edicao.get("molde") or {}).get(
            "duracao_por_clipe", receita.DURACAO_POR_CLIPE
        ),
        "molde": molde.para_pagina(molde.camadas(formato), formato),
        "cor_fundo": estudio.cor_do_fundo(edicao),
        "gols": gols,
        "sem_torcida": perdedor.sem_torcida(dados),
        "quantos": len(entram),
        "segundos": round(segundos, 1),
        "textos": edicao.get("textos") or {},
        "render": estudio.estado(pasta_jogo),
        "cache_mb": round(estudio.tamanho_do_cache(pasta_jogo) / 1024**2, 1),
        "cache_no_teto": estudio.passou_do_teto(pasta_jogo, cfg),
    }


def montar_resposta(
    rota: str,
    corpo: dict,
    pasta_jogo: Path,
    cfg: dict,
    executar=None,
    lancar=None,
) -> tuple[int, dict]:
    pasta_jogo = Path(pasta_jogo)
    dados = catalogo.carregar(pasta_jogo)

    if rota == "GET /api/estado":
        return 200, estudio.estado(pasta_jogo)

    if rota == "GET /api/edicao":
        edicao = receita.carregar(pasta_jogo, dados)
        receita.salvar(pasta_jogo, edicao)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota == "POST /api/item":
        edicao = receita.carregar(pasta_jogo, dados)
        campos = {
            campo: corpo[campo]
            for campo in receita.CAMPOS_DO_OPERADOR
            if campo in corpo
        }
        clipe = _clipes(dados).get((corpo.get("gol"), corpo.get("canal")))
        erro = _conferir_corte(campos, clipe)
        if erro:
            return 400, {"erro": erro}
        try:
            edicao = receita.mexer(edicao, corpo["gol"], corpo["canal"], **campos)
        except KeyError as erro:
            return 404, {"erro": erro.args[0]}
        receita.salvar(pasta_jogo, edicao)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota in ("POST /api/placar", "POST /api/placar-do-gol"):
        # O placar e fato do jogo: mora no catalogo, e a receita se re-deriva
        # dele. Sem este campo o estudio de 03/09 abriu com "sem placar", nada
        # marcado, as cartelas escritas so "GOL 3" e o titulo sem o 3x1 - a
        # `vigia` so escreve placar enquanto a partida esta no ar.
        try:
            casa = int(corpo["gols_mandante"])
            fora = int(corpo["gols_visitante"])
        except (KeyError, TypeError, ValueError):
            return 400, {
                "erro": "placar precisa de gols_mandante e gols_visitante "
                        "em numeros inteiros"
            }
        if rota.endswith("placar-do-gol"):
            try:
                dados = catalogo.registrar_placar_do_gol(
                    dados, int(corpo.get("gol", 0)), casa, fora
                )
            except (KeyError, TypeError, ValueError) as erro:
                return 404, {"erro": str(erro.args[0] if erro.args else erro)}
        else:
            dados = catalogo.registrar_placar(dados, casa, fora)
        catalogo.salvar(pasta_jogo, dados)
        dados = catalogo.carregar(pasta_jogo)
        edicao = receita.carregar(pasta_jogo, dados)
        receita.salvar(pasta_jogo, edicao)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota == "POST /api/alvo":
        # A escolha do lado mora no catalogo, e nao na receita: ela e um fato do
        # jogo, e a receita se re-deriva dela.
        catalogo.salvar(pasta_jogo, perdedor.escolher(dados, corpo.get("torcida", "")))
        dados = catalogo.carregar(pasta_jogo)
        edicao = receita.carregar(pasta_jogo, dados)
        receita.salvar(pasta_jogo, edicao)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota == "POST /api/molde":
        formato = corpo.get("formato")
        if formato and formato not in molde.TAMANHOS:
            return 400, {
                "erro": f"formato '{formato}' nao existe - use "
                        f"{' ou '.join(molde.TAMANHOS)}"
            }
        edicao = receita.ajustar(
            receita.carregar(pasta_jogo, dados), dados,
            formato=formato, duracao_por_clipe=corpo.get("duracao_por_clipe"),
        )
        receita.salvar(pasta_jogo, edicao)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota == "POST /api/torcida":
        try:
            torcidas.aplicar(
                pasta_jogo, {corpo.get("canal", ""): corpo.get("torcida", "")}
            )
        except KeyError as erro:
            return 404, {"erro": erro.args[0]}
        except ValueError as erro:
            return 400, {"erro": str(erro)}
        # O cadastro e a origem: sem consertar la, o buraco volta no proximo jogo.
        torcidas.definir_no_cadastro(canais.ARQUIVO, {corpo["canal"]: corpo["torcida"]})
        dados = catalogo.carregar(pasta_jogo)
        edicao = receita.carregar(pasta_jogo, dados)
        receita.salvar(pasta_jogo, edicao)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota in ("POST /api/espiar", "POST /api/previa"):
        edicao = receita.carregar(pasta_jogo, dados)
        fazer = estudio.espiar if rota.endswith("espiar") else estudio.previa
        try:
            saida = fazer(
                pasta_jogo, dados, edicao, corpo["gol"], corpo["canal"], cfg,
                executar=executar or cortador.executar,
            )
        except KeyError as erro:
            return 404, {"erro": erro.args[0]}
        except subprocess.CalledProcessError as erro:
            return 500, {"erro": f"o ffmpeg recusou: {erro}"}
        relativo = saida.relative_to(pasta_jogo).as_posix()
        # A tela troca a imagem sem recarregar a pagina; sem o contador, o
        # navegador mostra a espiada anterior e o operador acha que nao mudou.
        return 200, {"arquivo": f"/midia/{relativo}?v={saida.stat().st_mtime_ns}"}

    if rota == "POST /api/textos":
        edicao = receita.carregar(pasta_jogo, dados)
        try:
            edicao = receita.definir_textos(
                edicao,
                **{c: corpo[c] for c in receita.TEXTOS_DO_OPERADOR if c in corpo},
            )
        except KeyError as erro:
            return 400, {"erro": erro.args[0]}
        receita.salvar(pasta_jogo, edicao)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota == "POST /api/capa":
        edicao = receita.carregar(pasta_jogo, dados)
        try:
            saida = capa.gerar(
                pasta_jogo, dados, edicao, cfg, executar=executar or cortador.executar
            )
        except subprocess.CalledProcessError as erro:
            return 500, {"erro": f"o ffmpeg recusou o quadro do rosto: {erro}"}
        relativo = saida.relative_to(pasta_jogo).as_posix()
        return 200, {"arquivo": f"/midia/{relativo}?v={saida.stat().st_mtime_ns}"}

    if rota == "POST /api/publicar":
        edicao = receita.carregar(pasta_jogo, dados)
        saida = publicacao.escrever(pasta_jogo, dados, edicao)
        return 200, {
            "arquivo": f"/midia/{saida.relative_to(pasta_jogo).as_posix()}",
            "texto": saida.read_text(encoding="utf-8"),
        }

    if rota == "POST /api/render":
        estado = estudio.estado(pasta_jogo)
        if estado.get("rodando"):
            return 409, {"erro": "ja tem um render rodando neste jogo", **estado}
        edicao = receita.carregar(pasta_jogo, dados)
        if not receita.itens_do_video(edicao):
            return 400, {
                "erro": "nenhuma reacao marcada - marque as que entram antes de montar"
            }
        receita.salvar(pasta_jogo, edicao)
        estudio.anotar(
            pasta_jogo, rodando=True, feito=0,
            total=len(receita.itens_do_video(edicao)), saida="",
            mensagem="na fila",
        )
        # O PID entra antes de a tela voltar: e por ele que o painel sabe
        # diferenciar "ainda trabalhando" de "morreu no meio".
        estudio.anotar(pasta_jogo, pid=(lancar or lancar_render)(pasta_jogo) or 0)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota == "POST /api/limpar":
        liberado = estudio.limpar(pasta_jogo)
        return 200, {
            "liberado": liberado, "liberado_mb": round(liberado / 1024**2, 1)
        }

    return 404, {"erro": f"rota desconhecida: {rota}"}


def _conferir_corte(campos: dict, clipe: dict | None) -> str:
    """A alca nao pode sair do clipe: fora dele o render vira tela preta.

    O navegador ja prende o arrasto, mas quem garante e este lado - a pagina
    pode ser recarregada, adulterada ou simplesmente estar desatualizada.
    """
    if clipe is None or ("de" not in campos and "ate" not in campos):
        return ""
    de = float(campos.get("de", 0.0))
    ate = float(campos.get("ate", 0.0))
    duracao = float(clipe.get("duracao") or 0.0)
    if de < 0 or ate <= de:
        return f"corte invertido ou negativo: de {de} ate {ate}"
    if duracao and ate > duracao:
        return f"o clipe tem {duracao:g}s e o corte pede ate {ate:g}s"
    return ""


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
            f"POST {self.path}", corpo, self.pasta_jogo, self.cfg
        )
        self._responder(codigo, resposta)


def servir(pasta_jogo: Path, cfg: dict, porta: int = 8772) -> None:
    manipulador = partial(_Manipulador, pasta_jogo=Path(pasta_jogo), cfg=cfg)
    with ThreadingHTTPServer(("127.0.0.1", porta), manipulador) as servidor_http:
        print(f"Estudio de edicao em http://127.0.0.1:{porta}  (Ctrl+C para parar)")
        servidor_http.serve_forever()
