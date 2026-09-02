"""Corta gols informados manualmente em um VOD.

Este modo nao tenta descobrir o gol. Recebe o instante exato no arquivo e usa
o mesmo corte preciso, com recodificacao, previsto para a esteira completa.
"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nucleo import config, cortador


@dataclass(frozen=True)
class PlanoCorte:
    numero: int
    momento: float
    inicio: float
    duracao: float
    saida: Path


def em_segundos(texto: str) -> float:
    """Aceita segundos ou um horario HH:MM:SS com fracao opcional."""
    original = texto
    texto = texto.replace(",", ".")
    try:
        if ":" not in texto:
            valor = float(texto)
        else:
            partes = texto.split(":")
            if len(partes) != 3:
                raise ValueError
            horas, minutos = int(partes[0]), int(partes[1])
            segundos = float(partes[2])
            if horas < 0 or not 0 <= minutos < 60 or not 0 <= segundos < 60:
                raise ValueError
            valor = horas * 3600 + minutos * 60 + segundos
        if valor < 0:
            raise ValueError
        return valor
    except ValueError as erro:
        raise ValueError(f"horario invalido: {original}") from erro


def planejar(
    momentos: list[float],
    pasta_saida: Path,
    segundos_antes: float,
    segundos_depois: float,
) -> list[PlanoCorte]:
    duracao = segundos_antes + segundos_depois
    return [
        PlanoCorte(
            numero=numero,
            momento=momento,
            inicio=max(0.0, momento - segundos_antes),
            duracao=duracao,
            saida=Path(pasta_saida) / f"gol-sofrido-{numero:02d}.mp4",
        )
        for numero, momento in enumerate(momentos, start=1)
    ]


def cortar(
    vod: Path,
    momentos: list[float],
    pasta_saida: Path,
    cfg: dict,
    executar: Callable[[list[str]], None] = cortador.executar,
) -> list[PlanoCorte]:
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    planos = planejar(
        momentos,
        pasta_saida,
        cfg["segundos_antes"],
        cfg["segundos_depois"],
    )
    for plano in planos:
        comando = cortador.comando_corte(
            Path(vod),
            plano.inicio,
            plano.duracao,
            plano.saida,
            cfg["caminho_ffmpeg"],
        )
        executar(comando)
    return planos


def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Corta um VOD nos horarios informados manualmente."
    )
    p.add_argument("vod", type=Path, help="arquivo de video ja baixado")
    p.add_argument(
        "--momentos",
        nargs="+",
        required=True,
        type=em_segundos,
        help="instantes no video, ex: 02:32:14.520",
    )
    p.add_argument("--saida", type=Path, required=True, help="pasta dos clipes")
    args = p.parse_args(argv)

    cfg = config.carregar()
    planos = cortar(args.vod, args.momentos, args.saida, cfg)
    for plano in planos:
        print(
            f"gol sofrido {plano.numero}: {plano.momento:.3f}s -> "
            f"{plano.saida} ({plano.duracao:g}s)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(principal())
