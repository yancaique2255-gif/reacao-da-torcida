"""Acha o comeco da explosao de audio dentro de um trecho.

Nao sabe o que e futebol: recebe um wav, devolve um instante e uma confianca.
Aritmetica simples de proposito - a maquina nao tem GPU.
"""
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

QUADRO_S = 0.5
SUAVIZACAO_S = 3.0
FRACAO_DA_SUBIDA = 0.5


@dataclass(frozen=True)
class Achado:
    instante: float  # segundos desde o comeco do wav analisado
    confianca_db: float
    tem_pico: bool


def ler_wav(caminho: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(caminho), "rb") as w:
        taxa = w.getframerate()
        canais = w.getnchannels()
        bruto = w.readframes(w.getnframes())
    amostras = np.frombuffer(bruto, dtype="<i2").astype(np.float32) / 32768.0
    if canais > 1:
        amostras = amostras.reshape(-1, canais).mean(axis=1)
    return amostras, taxa


def curva_db(amostras: np.ndarray, taxa: int, quadro_s: float = QUADRO_S) -> np.ndarray:
    """Energia RMS por quadro, em decibeis."""
    por_quadro = max(1, int(taxa * quadro_s))
    inteiros = len(amostras) // por_quadro
    if inteiros == 0:
        return np.array([-120.0])
    blocos = amostras[: inteiros * por_quadro].reshape(inteiros, por_quadro)
    rms = np.sqrt(np.mean(blocos.astype(np.float64) ** 2, axis=1))
    return 20.0 * np.log10(rms + 1e-9)


def suavizar(curva: np.ndarray, quadros: int) -> np.ndarray:
    if quadros <= 1 or len(curva) < quadros:
        return curva
    nucleo = np.ones(quadros)
    soma = np.convolve(curva, nucleo, mode="same")
    quantidade = np.convolve(np.ones_like(curva), nucleo, mode="same")
    return soma / quantidade


def achar(curva: np.ndarray, quadro_s: float, limiar_db: float) -> Achado:
    """Pico, linha de base e o ponto em que a subida comeca."""
    base = float(np.median(curva))
    indice_pico = int(np.argmax(curva))
    pico = float(curva[indice_pico])
    altura = pico - base

    corte = base + FRACAO_DA_SUBIDA * altura
    indice_subida = indice_pico
    while indice_subida > 0 and curva[indice_subida - 1] >= corte:
        indice_subida -= 1

    return Achado(
        instante=indice_subida * quadro_s,
        confianca_db=altura,
        tem_pico=altura >= limiar_db,
    )


def analisar(caminho_wav: Path, limiar_db: float = 6.0) -> Achado:
    amostras, taxa = ler_wav(Path(caminho_wav))
    curva = curva_db(amostras, taxa)
    quadros = max(1, int(SUAVIZACAO_S / QUADRO_S))
    return achar(suavizar(curva, quadros), QUADRO_S, limiar_db)
