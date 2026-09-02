import wave
from pathlib import Path

import numpy as np

from nucleo import detector

TAXA = 16000


def gravar_wav(caminho: Path, amostras: np.ndarray, taxa: int = TAXA) -> Path:
    inteiros = np.clip(amostras, -1.0, 1.0)
    inteiros = (inteiros * 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(inteiros.tobytes())
    return caminho


def audio_com_grito(duracao_s: int = 60, comeco_do_grito: float = 40.0) -> np.ndarray:
    """Ruido baixo constante e, a partir do comeco, um trecho bem mais alto."""
    gerador = np.random.default_rng(42)
    sinal = gerador.normal(0.0, 0.02, duracao_s * TAXA)
    de = int(comeco_do_grito * TAXA)
    ate = int((comeco_do_grito + 8) * TAXA)
    subida = np.linspace(0.0, 1.0, int(0.5 * TAXA))
    sinal[de : de + len(subida)] += gerador.normal(0.0, 0.5, len(subida)) * subida
    sinal[de + len(subida) : ate] += gerador.normal(0.0, 0.5, ate - de - len(subida))
    return sinal


def test_acha_o_comeco_da_subida_e_nao_o_auge(tmp_path: Path):
    arquivo = gravar_wav(tmp_path / "grito.wav", audio_com_grito())

    achado = detector.analisar(arquivo, limiar_db=6.0)

    assert achado.tem_pico
    assert abs(achado.instante - 40.0) <= 1.5, f"achou em {achado.instante}"
    assert achado.confianca_db > 10


def test_ruido_constante_nao_tem_pico(tmp_path: Path):
    gerador = np.random.default_rng(7)
    arquivo = gravar_wav(tmp_path / "plano.wav", gerador.normal(0.0, 0.05, 60 * TAXA))

    achado = detector.analisar(arquivo, limiar_db=6.0)

    assert not achado.tem_pico


def test_sem_pico_ainda_devolve_um_instante_utilizavel(tmp_path: Path):
    """Nada some calado: mesmo sem pico, ha um instante para cortar e conferir."""
    gerador = np.random.default_rng(7)
    arquivo = gravar_wav(tmp_path / "plano.wav", gerador.normal(0.0, 0.05, 60 * TAXA))

    achado = detector.analisar(arquivo, limiar_db=6.0)

    assert 0.0 <= achado.instante <= 60.0


def test_grito_no_comeco_do_trecho_nao_estoura(tmp_path: Path):
    arquivo = gravar_wav(tmp_path / "cedo.wav", audio_com_grito(comeco_do_grito=0.5))
    achado = detector.analisar(arquivo, limiar_db=6.0)
    assert achado.instante >= 0.0


def test_curva_em_db_tem_um_valor_por_quadro():
    amostras = np.zeros(TAXA * 10) + 0.1
    curva = detector.curva_db(amostras, TAXA, quadro_s=0.5)
    assert len(curva) == 20
    assert np.all(np.isfinite(curva))
