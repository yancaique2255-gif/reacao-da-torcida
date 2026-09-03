"""Placar ao vivo pela API publica da ESPN.

Ela diz QUE houve gol, com placar oficial e sem falso positivo, e diz em que
SEGUNDO DE JOGO ele saiu. Esse segundo e o que vale: a hora em que a consulta
percebeu a mudanca chega com atraso proprio e variavel, mas "aos 4810 segundos
de jogo" e um fato do jogo, nao da consulta.

Cada live mostra o mesmo cronometro na tela, entao ele serve de referencia
comum entre a ESPN e todas elas - veja `nucleo/cronometro.py`.
"""
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from nucleo import cronometro

ENDERECO = "https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard"
# Sem User-Agent de navegador a ESPN recusa. Conferido em 02/09/2026.
CABECALHOS = {"User-Agent": "Mozilla/5.0"}
TEMPO_LIMITE = 25

# Copa do Brasil e com Z: `bra.copa_do_brasil` devolve HTTP 400.
LIGAS = {
    "copa-do-brasil": "bra.copa_do_brazil",
    "brasileirao": "bra.1",
    "supercopa": "bra.supercopa_do_brazil",
}

ACABOU = {"STATUS_FULL_TIME", "STATUS_FINAL", "STATUS_POSTPONED", "STATUS_CANCELED"}


@dataclass(frozen=True)
class Partida:
    identificador: str
    mandante: str
    visitante: str
    gols_mandante: int
    gols_visitante: int
    estado: str            # STATUS_SECOND_HALF, STATUS_FULL_TIME, ...
    relogio: str = ""      # "81'"
    # Segundo corrido de jogo. E o que permite comparar a ESPN com o cronometro
    # que cada live mostra na tela, e assim medir o atraso de cada uma.
    segundo_de_jogo: float | None = None
    lances: list = field(default_factory=list)

    @property
    def placar(self) -> tuple[int, int]:
        return self.gols_mandante, self.gols_visitante

    @property
    def acabou(self) -> bool:
        return self.estado in ACABOU

    def __str__(self) -> str:
        return (
            f"{self.mandante} {self.gols_mandante} x "
            f"{self.gols_visitante} {self.visitante}"
        )


def _buscar_cru(url: str) -> str:
    pedido = urllib.request.Request(url, headers=CABECALHOS)
    with urllib.request.urlopen(pedido, timeout=TEMPO_LIMITE) as resposta:
        return resposta.read().decode("utf-8", errors="replace")


def _inteiro(valor) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return 0


def interpretar(texto: str) -> list[Partida]:
    """Le a resposta da ESPN. Devolve lista vazia se vier lixo.

    A API as vezes responde HTML de erro no lugar do JSON; isso nao pode
    derrubar o laco que a consulta.
    """
    try:
        dados = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(dados, dict):
        return []

    partidas = []
    for evento in dados.get("events") or []:
        competicoes = evento.get("competitions") or []
        if not competicoes:
            continue
        c = competicoes[0]
        times = {t.get("homeAway"): t for t in c.get("competitors") or []}
        casa, fora = times.get("home"), times.get("away")
        if not casa or not fora:
            continue
        estado = ((c.get("status") or {}).get("type") or {}).get("name", "")
        lances = []
        for d in c.get("details") or []:
            if not d.get("scoringPlay"):
                continue
            relogio_do_lance = d.get("clock") or {}
            lances.append({
                "minuto": relogio_do_lance.get("displayValue", ""),
                "segundo_de_jogo": cronometro.segundos_da_espn(
                    relogio_do_lance.get("value"),
                    relogio_do_lance.get("displayValue", ""),
                ),
                "quem": (d.get("athletesInvolved") or [{}])[0].get("displayName", ""),
                "tipo": (d.get("type") or {}).get("text", ""),
            })
        partidas.append(Partida(
            identificador=str(evento.get("id", "")),
            mandante=(casa.get("team") or {}).get("displayName", "?"),
            visitante=(fora.get("team") or {}).get("displayName", "?"),
            gols_mandante=_inteiro(casa.get("score")),
            gols_visitante=_inteiro(fora.get("score")),
            estado=estado,
            relogio=(c.get("status") or {}).get("displayClock", ""),
            segundo_de_jogo=cronometro.segundos_da_espn(
                (c.get("status") or {}).get("clock"),
                (c.get("status") or {}).get("displayClock", ""),
            ),
            lances=lances,
        ))
    return partidas


def buscar(liga: str, buscar_cru: Callable[[str], str] = _buscar_cru) -> list[Partida]:
    """Partidas da liga hoje. Rede fora e resultado vazio, nunca excecao.

    Quem chama esta gravando um jogo: uma falha de rede aqui e um aviso, e nao
    pode subir e derrubar a gravacao.
    """
    slug = LIGAS.get(liga, liga)
    try:
        return interpretar(buscar_cru(ENDERECO.format(liga=slug)))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return []


def achar(partidas: list[Partida], mandante: str, visitante: str) -> Partida | None:
    """Acha a partida pelos nomes, sem exigir grafia exata.

    O operador escreve "vitoria" e a ESPN responde "Vitória"; o nome da pasta
    do jogo ja vem sem acento por causa de `gravador.apelido`.
    """
    import unicodedata

    def simples(texto: str) -> str:
        sem = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
        return sem.lower().strip()

    alvo_casa, alvo_fora = simples(mandante), simples(visitante)
    for p in partidas:
        casa, fora = simples(p.mandante), simples(p.visitante)
        if (alvo_casa in casa or casa in alvo_casa) and (
            alvo_fora in fora or fora in alvo_fora
        ):
            return p
    return None


def lances_novos(antes: Partida | None, agora: Partida | None) -> list[dict]:
    """Os gols que entraram entre uma consulta e a seguinte, com o minuto deles.

    O minuto e o que faz o corte automatico funcionar: ele diz onde o gol esta
    no RELOGIO DO JOGO, e nao na hora em que a ESPN avisou - que chega com
    atraso proprio e variavel.
    """
    quantos = gols_novos(antes, agora)
    if not quantos or agora is None:
        return []
    conhecidos = len(antes.lances) if antes else 0
    novos = agora.lances[conhecidos:]
    # A ESPN as vezes muda o placar antes de listar o lance; nesse caso o gol
    # existe mas ainda nao tem minuto, e quem acha o instante e o audio.
    return novos[-quantos:] if novos else [{} for _ in range(quantos)]


def gols_novos(antes: Partida | None, agora: Partida | None) -> int:
    """Quantos gols entraram entre uma consulta e a seguinte.

    Sem `antes` nao ha nada a comparar: a primeira leitura estabelece o ponto
    de partida, senao um jogo que ja estava 2x0 dispararia dois cortes.

    Placar que DIMINUI e gol anulado pelo VAR - devolve zero, nao negativo.
    """
    if antes is None or agora is None:
        return 0
    if antes.identificador != agora.identificador:
        return 0
    diferenca = (
        agora.gols_mandante + agora.gols_visitante
        - antes.gols_mandante - antes.gols_visitante
    )
    return max(0, diferenca)
