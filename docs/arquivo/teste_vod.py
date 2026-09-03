"""Modo teste: mede o erro do detector contra um gabarito conhecido.

E a regua do projeto. Sem essa medida nao existe base para dizer que funciona.
"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nucleo import config, cortador, detector

TOLERANCIA_S = 3.0
FRACAO_MINIMA = 0.8


@dataclass(frozen=True)
class Medida:
    gol: int
    esperado: float
    achado: float
    erro: float
    confianca_db: float
    tem_pico: bool


def medir(
    vod: Path,
    gabarito: list[float],
    cfg: dict,
    pasta_temp: Path,
    executar: Callable[[list[str]], None] = cortador.executar,
) -> list[Medida]:
    pasta_temp.mkdir(parents=True, exist_ok=True)
    medidas = []
    for numero, esperado in enumerate(gabarito, start=1):
        inicio = max(0.0, esperado - cfg["janela_antes"])
        duracao = cfg["janela_antes"] + cfg["janela_depois"]
        wav = pasta_temp / f"janela-{numero:02d}.wav"
        executar(cortador.comando_audio(vod, inicio, duracao, wav, cfg["caminho_ffmpeg"]))

        achado = detector.analisar(wav, limiar_db=cfg["limiar_confianca_db"])
        posicao = inicio + achado.instante
        medidas.append(
            Medida(
                gol=numero,
                esperado=esperado,
                achado=posicao,
                erro=abs(posicao - esperado),
                confianca_db=achado.confianca_db,
                tem_pico=achado.tem_pico,
            )
        )
    return medidas


def resumir(medidas: list[Medida], tolerancia: float = TOLERANCIA_S) -> dict:
    total = len(medidas)
    dentro = sum(1 for medida in medidas if medida.erro <= tolerancia)
    fracao = dentro / total if total else 0.0
    erros = [medida.erro for medida in medidas]
    return {
        "total": total,
        "dentro": dentro,
        "fracao": fracao,
        "aprovado": total > 0 and fracao >= FRACAO_MINIMA,
        "erro_medio": sum(erros) / total if total else 0.0,
    }


def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Mede o erro do detector sobre um VOD.")
    p.add_argument("vod", type=Path, help="arquivo de video ja baixado")
    p.add_argument(
        "--gols",
        type=float,
        nargs="+",
        required=True,
        help="posicao real de cada gol, em segundos do arquivo",
    )
    p.add_argument("--temp", type=Path, default=Path("temp-teste"))
    args = p.parse_args(argv)

    cfg = config.carregar()
    medidas = medir(args.vod, args.gols, cfg, args.temp)

    print(f"{'gol':>4} {'esperado':>10} {'achado':>10} {'erro':>7} {'conf dB':>8}  pico")
    for medida in medidas:
        marca = "sim" if medida.tem_pico else "NAO"
        print(
            f"{medida.gol:>4} {medida.esperado:>10.1f} {medida.achado:>10.1f} "
            f"{medida.erro:>7.1f} {medida.confianca_db:>8.1f}  {marca}"
        )

    resumo = resumir(medidas)
    print(
        f"\n{resumo['dentro']}/{resumo['total']} dentro de {TOLERANCIA_S:.0f}s "
        f"({resumo['fracao']:.0%}), erro medio {resumo['erro_medio']:.1f}s"
    )
    print(
        "APROVADO"
        if resumo["aprovado"]
        else "REPROVADO - nao siga para a gravacao ao vivo"
    )
    return 0 if resumo["aprovado"] else 1


if __name__ == "__main__":
    sys.exit(principal())
