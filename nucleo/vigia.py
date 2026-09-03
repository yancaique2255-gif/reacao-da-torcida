"""Fica de olho no placar e marca o gol sozinho quando ele sai.

Divisao de trabalho, e ela e o ponto todo deste modulo:

  a ESPN sabe QUE houve gol - placar oficial, sem falso positivo
  o audio sabe QUANDO cada canal reagiu - o consenso de picos

Uma cobre exatamente o buraco da outra. A ESPN tem atraso proprio e variavel,
entao ela nunca serve de relogio: o horario que ela dispara e so um ponto de
partida, e quem o corrige e o alinhamento.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from nucleo import catalogo, placar

SEGUNDOS_ENTRE_CONSULTAS = 20  # educado: a API nao e nossa


def marcar_gol(pasta_jogo: Path, momento: datetime, origem: str = "espn") -> int:
    """Anota o gol no catalogo e devolve o numero dele."""
    dados = catalogo.carregar(pasta_jogo)
    numero = catalogo.proximo_numero(dados)
    dados = catalogo.registrar_gol(
        dados, numero, momento.isoformat(timespec="seconds"), ""
    )
    for gol in dados["gols"]:
        if gol["numero"] == numero:
            gol["origem"] = origem
            gol["confirmado"] = False  # so o alinhamento acha o instante certo
    catalogo.salvar(pasta_jogo, dados)
    return numero


def vigiar(
    liga: str,
    mandante: str,
    visitante: str,
    pasta_jogo: Path,
    voltas: int | None = None,
    buscar: Callable[[str], list] = placar.buscar,
    agora: Callable[[], datetime] = datetime.now,
    dormir: Callable[[float], None] = time.sleep,
    avisar: Callable[[str], None] = print,
    intervalo: float = SEGUNDOS_ENTRE_CONSULTAS,
) -> list[int]:
    """Consulta o placar ate o jogo acabar. Devolve os numeros dos gols marcados.

    `voltas` existe para o teste rodar um numero finito de consultas.
    """
    anterior = None
    marcados = []
    feitas = 0

    while voltas is None or feitas < voltas:
        if feitas:
            dormir(intervalo)
        feitas += 1

        partida = placar.achar(buscar(liga), mandante, visitante)
        if partida is None:
            # Jogo ainda nao no ar, ou nome que nao bate: nao e erro, e espera.
            continue

        novos = placar.gols_novos(anterior, partida)
        for _ in range(novos):
            numero = marcar_gol(pasta_jogo, agora())
            marcados.append(numero)
            avisar(f"GOL detectado pelo placar: {partida} - anotado como #{numero}")

        if anterior is None:
            avisar(f"acompanhando {partida} ({partida.estado})")
        anterior = partida

        if partida.acabou:
            avisar(f"fim de jogo: {partida}")
            break

    return marcados
