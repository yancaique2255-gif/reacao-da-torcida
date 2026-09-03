import json
import os
import time
from pathlib import Path

from nucleo import monitor


def _canal(pasta: Path, nome: str, sessoes: int, escrito_ha: float) -> Path:
    d = pasta / nome
    d.mkdir(parents=True)
    (d / "gravacao.json").write_text(
        json.dumps({"url": "u", "sessoes": [{"numero": n + 1, "t0": "2026-09-02T21:00:00"}
                                            for n in range(sessoes)]}),
        encoding="utf-8",
    )
    ts = d / "s01-parte-000.ts"
    ts.write_bytes(b"x" * 2_000_000)
    marca = time.time() - escrito_ha
    os.utime(ts, (marca, marca))
    return d


def test_canal_escrevendo_agora_aparece_como_gravando(tmp_path: Path):
    _canal(tmp_path, "diaxz", 1, escrito_ha=2)

    estado = monitor.estados(tmp_path, time.time())[0]

    assert estado["gravando"] and estado["sessoes"] == 1
    assert round(estado["mb"]) == 2


def test_canal_mudo_ha_tempo_aparece_como_parado(tmp_path: Path):
    """Live encerrada e o caso comum: o quadro tem que gritar, nao esconder."""
    _canal(tmp_path, "amici", 6, escrito_ha=300)

    estado = monitor.estados(tmp_path, time.time())[0]

    assert not estado["gravando"] and estado["silencio"] >= 300


def test_quadro_poe_quem_esta_gravando_em_cima(tmp_path: Path):
    _canal(tmp_path, "caiu", 6, escrito_ha=300)
    _canal(tmp_path, "firme", 1, escrito_ha=1)

    quadro = monitor.linhas(tmp_path, time.time())

    corpo = [l for l in quadro if l.startswith(("caiu", "firme"))]
    assert corpo[0].startswith("firme"), "canal vivo vem antes do que caiu"
    assert "PARADO" in corpo[1]
    assert "1 de 2 gravando" in quadro[-1]


def test_sem_pasta_nao_estoura(tmp_path: Path):
    assert monitor.linhas(tmp_path / "nao-existe", time.time())


def test_panorama_junta_os_dois_jogos_da_biblioteca(tmp_path: Path):
    """O painel mostra as duas partidas sem que ninguem lhe diga quais sao."""
    _canal(tmp_path / "2026-09-02 santos x palmeiras" / "bruto", "peixao", 1, 2)
    _canal(tmp_path / "2026-09-02 vitoria x vasco" / "bruto", "arena", 1, 2)
    _canal(tmp_path / "2026-09-02 vitoria x vasco" / "bruto", "canto", 3, 400)
    (tmp_path / "pasta-solta").mkdir()  # sem bruto: nao e jogo

    visao = monitor.panorama(tmp_path, time.time())

    assert [j["jogo"] for j in visao] == [
        "2026-09-02 vitoria x vasco",
        "2026-09-02 santos x palmeiras",
    ]
    assert visao[0]["total"] == 2 and visao[0]["gravando"] == 1
    assert visao[1]["total"] == 1 and visao[1]["gravando"] == 1


def test_panorama_sem_biblioteca_devolve_vazio(tmp_path: Path):
    assert monitor.panorama(tmp_path / "nao-existe", time.time()) == []
