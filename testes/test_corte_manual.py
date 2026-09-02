from pathlib import Path

import pytest

from nucleo import corte_manual


def test_converte_horario_do_video_em_segundos():
    assert corte_manual.em_segundos("02:32:14.520") == pytest.approx(9134.52)
    assert corte_manual.em_segundos("10367.68") == pytest.approx(10367.68)


def test_rejeita_horario_invalido():
    with pytest.raises(ValueError, match="horario invalido"):
        corte_manual.em_segundos("02:75:00")


def test_planeja_oito_segundos_antes_e_doze_depois(tmp_path: Path):
    planos = corte_manual.planejar(
        [9134.52, 10367.68], tmp_path, segundos_antes=8, segundos_depois=12
    )

    assert planos[0].inicio == pytest.approx(9126.52)
    assert planos[0].duracao == 20
    assert planos[0].saida == tmp_path / "gol-sofrido-01.mp4"
    assert planos[1].saida == tmp_path / "gol-sofrido-02.mp4"


def test_executa_o_mesmo_corte_preciso_do_cortador(tmp_path: Path):
    chamadas = []
    cfg = {
        "segundos_antes": 8,
        "segundos_depois": 12,
        "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
    }

    planos = corte_manual.cortar(
        Path("vod.mp4"), [9134.52], tmp_path / "clipes", cfg, executar=chamadas.append
    )

    assert len(planos) == 1
    assert len(chamadas) == 1
    comando = chamadas[0]
    assert "9126.52" in comando
    assert "20" in comando
    assert "libx264" in comando
    assert comando[-1].endswith("gol-sofrido-01.mp4")
