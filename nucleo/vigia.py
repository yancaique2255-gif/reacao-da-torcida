"""Fica de olho no placar e marca o gol sozinho quando ele sai.

O que a ESPN entrega, e o que ela nao entrega:

  ela sabe QUE houve gol, e EM QUE SEGUNDO DE JOGO ele saiu
  ela nao sabe em que instante aquilo aparece em cada live

A hora em que a consulta percebeu a mudanca nao serve de nada - chega com o
intervalo entre consultas somado ao atraso da propria ESPN. Mas "aos 4810
segundos de jogo" e um fato do jogo, e nao da consulta: sabendo em que minuto
o jogo estava quando se leu, volta-se ao instante em que a bola entrou.

De ali para dentro de cada live, quem leva e o deslocamento do canal - medido
pelo cronometro na tela (`nucleo/cronometro.py`) ou pelo consenso de audio.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from nucleo import catalogo, cronometro, placar

SEGUNDOS_ENTRE_CONSULTAS = 20  # educado: a API nao e nossa
# Em jogo de mata-mata, o apito do tempo normal pode nao ser o fim: vem
# prorrogacao ou penaltis, que sao o melhor material da noite. Sair na hora
# perderia justamente isso.
MINUTOS_DEPOIS_DO_APITO = 25


def hora_do_lance(
    partida: placar.Partida, lance: dict, lido_em: datetime
) -> tuple[datetime, float | None]:
    """Traduz o minuto do gol em hora de relogio, e diz qual minuto era.

    A consulta so percebe o gol depois - vinte segundos de intervalo, mais o
    atraso da propria ESPN. Mas "aos 4810 segundos de jogo" e um fato do jogo,
    nao da consulta: sabendo em que minuto o jogo estava quando se leu, da para
    voltar ao instante exato em que a bola entrou.
    """
    do_gol = lance.get("segundo_de_jogo")
    agora_no_jogo = partida.segundo_de_jogo
    if do_gol is None or agora_no_jogo is None:
        return lido_em, do_gol
    if not cronometro.mesma_metade(do_gol, agora_no_jogo):
        # Gol do primeiro tempo percebido no segundo: o intervalo entraria na
        # conta como se fosse jogo. Melhor a hora da leitura do que uma errada.
        return lido_em, do_gol
    ancora = cronometro.ancora_da_espn(lido_em, agora_no_jogo)
    return cronometro.momento_do_minuto(ancora, do_gol), do_gol


def marcar_gol(
    pasta_jogo: Path, momento: datetime, origem: str = "espn",
    minuto_do_jogo: float | None = None,
    placar_agora: tuple[int, int] | None = None,
) -> int:
    """Anota o gol no catalogo e devolve o numero dele.

    `placar_agora` e o placar NAQUELE gol, e nao o final: o quadro do gol 1 diz
    1x0. E o unico momento em que da para saber - depois do apito a ESPN nao
    responde mais por este jogo.
    """
    dados = catalogo.carregar(pasta_jogo)
    numero = catalogo.proximo_numero(dados)
    dados = catalogo.registrar_gol(
        dados, numero, momento.isoformat(timespec="seconds"), ""
    )
    for gol in dados["gols"]:
        if gol["numero"] == numero:
            gol["origem"] = origem
            gol["minuto_do_jogo"] = minuto_do_jogo
            # Com o minuto do jogo a hora ja nasce boa; sem ele, e a hora em
            # que a consulta percebeu, e quem acerta o instante e o audio.
            gol["confirmado"] = minuto_do_jogo is not None
            if placar_agora is not None:
                gol["placar"] = list(placar_agora)
    catalogo.salvar(pasta_jogo, dados)
    return numero


def anotar_placar(pasta_jogo: Path, partida: placar.Partida) -> None:
    """Guarda no catalogo o placar visto agora, se ele mudou.

    O estudio de edicao edita dias depois e precisa saber quem perdeu - e a
    ESPN so responde enquanto o jogo esta no ar. Gravar a cada consulta seria
    escrever de vinte em vinte segundos por nada; o que importa e o ultimo
    placar visto sobreviver ao apito.
    """
    dados = catalogo.carregar(pasta_jogo)
    antes = dados.get("partida") or {}
    if (antes.get("gols_mandante"), antes.get("gols_visitante")) == partida.placar:
        return
    catalogo.salvar(pasta_jogo, catalogo.registrar_placar(dados, *partida.placar))


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
    ao_marcar: Callable[[int, datetime], None] | None = None,
) -> list[int]:
    """Consulta o placar ate o jogo acabar. Devolve os numeros dos gols marcados.

    `voltas` existe para o teste rodar um numero finito de consultas.
    """
    anterior = None
    marcados = []
    feitas = 0
    fim_visto_em = None

    while voltas is None or feitas < voltas:
        if feitas:
            dormir(intervalo)
        feitas += 1

        partida = placar.achar(buscar(liga), mandante, visitante)
        if partida is None:
            # Jogo ainda nao no ar, ou nome que nao bate: nao e erro, e espera.
            continue

        lido_em = agora()
        anotar_placar(pasta_jogo, partida)
        for lance in placar.lances_novos(anterior, partida):
            momento, minuto = hora_do_lance(partida, lance, lido_em)
            numero = marcar_gol(pasta_jogo, momento, "espn", minuto, partida.placar)
            marcados.append(numero)
            quem = lance.get("quem") or ""
            de_quando = (
                f"aos {lance['minuto']}" if lance.get("minuto") else "sem minuto"
            )
            avisar(
                f"GOL pelo placar: {partida} ({de_quando}{', ' + quem if quem else ''})"
                f" - anotado como #{numero} as {momento:%H:%M:%S}"
            )
            if ao_marcar is not None:
                ao_marcar(numero, momento)

        if anterior is None:
            avisar(f"acompanhando {partida} ({partida.estado})")
        anterior = partida

        if partida.acabou:
            if fim_visto_em is None:
                fim_visto_em = lido_em
                avisar(
                    f"fim do tempo normal: {partida} - seguindo de olho por "
                    f"{MINUTOS_DEPOIS_DO_APITO} min, caso venha prorrogacao ou penaltis"
                )
            elif (lido_em - fim_visto_em).total_seconds() > MINUTOS_DEPOIS_DO_APITO * 60:
                avisar(f"encerrado: {partida}")
                break
        else:
            fim_visto_em = None  # voltou a rolar: prorrogacao

    return marcados
