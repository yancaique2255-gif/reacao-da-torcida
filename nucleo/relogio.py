"""Traduz horario de relogio em posicao dentro dos arquivos gravados.

Uma sessao e um trecho continuo de gravacao. Se a gravacao cai e religa, abre
uma nova sessao com seu proprio t0 - e o buraco entre elas fica visivel, porque
nenhum momento dentro dele e coberto.
"""
import csv as _csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Pedaco:
    arquivo: str
    inicio: float  # segundos desde o comeco da sessao
    fim: float


@dataclass(frozen=True)
class Sessao:
    t0: datetime  # horario de relogio do primeiro frame da sessao
    pedacos: list[Pedaco]


@dataclass(frozen=True)
class Localizacao:
    arquivo: str
    segundo: float  # segundos desde o comeco daquele arquivo


@dataclass(frozen=True)
class Trecho:
    arquivo: str
    inicio: float
    fim: float


def ler_segmentos(csv: Path, t0: datetime) -> Sessao:
    """Le o CSV que o ffmpeg escreve com -segment_list_type csv."""
    pedacos = []
    with Path(csv).open(encoding="utf-8", newline="") as f:
        for linha in _csv.reader(f):
            if len(linha) < 3:
                continue
            pedacos.append(Pedaco(linha[0], float(linha[1]), float(linha[2])))
    return Sessao(t0=t0, pedacos=pedacos)


def _decorridos(sessao: Sessao, momento: datetime) -> float:
    return (momento - sessao.t0).total_seconds()


def localizar(sessoes: list[Sessao], momento: datetime) -> Localizacao | None:
    """Devolve o arquivo e o segundo correspondentes, ou None se nao foi gravado."""
    for sessao in sessoes:
        decorridos = _decorridos(sessao, momento)
        if decorridos < 0:
            continue
        for pedaco in sessao.pedacos:
            if pedaco.inicio <= decorridos < pedaco.fim:
                return Localizacao(pedaco.arquivo, decorridos - pedaco.inicio)
    return None


def trechos(sessoes: list[Sessao], inicio: datetime, fim: datetime) -> list[Trecho]:
    """Recortes que cobrem o intervalo pedido, na ordem, pulando o que nao foi gravado."""
    recortes: list[Trecho] = []
    for sessao in sessoes:
        de = _decorridos(sessao, inicio)
        ate = _decorridos(sessao, fim)
        for pedaco in sessao.pedacos:
            comeco = max(de, pedaco.inicio)
            termino = min(ate, pedaco.fim)
            if termino > comeco:
                recortes.append(
                    Trecho(pedaco.arquivo, comeco - pedaco.inicio, termino - pedaco.inicio)
                )
    return recortes


def cobertura(sessoes: list[Sessao]) -> list[tuple[datetime, datetime]]:
    """Intervalos de relogio realmente gravados. Serve para explicar um nao coberto."""
    intervalos = []
    for sessao in sessoes:
        if not sessao.pedacos:
            continue
        comeco = sessao.t0 + timedelta(seconds=sessao.pedacos[0].inicio)
        termino = sessao.t0 + timedelta(seconds=sessao.pedacos[-1].fim)
        intervalos.append((comeco, termino))
    return intervalos


def janela(momento: datetime, antes: int, depois: int) -> tuple[datetime, datetime]:
    """Janela larga de busca em volta do horario informado do gol."""
    return momento - timedelta(seconds=antes), momento + timedelta(seconds=depois)
