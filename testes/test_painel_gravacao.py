import json
import os
import time
from pathlib import Path

from painel import gravacao


def _canal(pasta: Path, nome: str, escrito_ha: float) -> None:
    d = pasta / nome
    d.mkdir(parents=True)
    (d / "gravacao.json").write_text(
        json.dumps({"url": "u", "sessoes": [{"numero": 1, "t0": "2026-09-02T21:00:00"}]}),
        encoding="utf-8",
    )
    ts = d / "s01-parte-000.ts"
    ts.write_bytes(b"x" * 1_000_000)
    marca = time.time() - escrito_ha
    os.utime(ts, (marca, marca))


def test_estado_soma_os_dois_jogos(tmp_path: Path):
    _canal(tmp_path / "2026-09-02 santos x palmeiras" / "bruto", "peixao", 1)
    _canal(tmp_path / "2026-09-02 vitoria x vasco" / "bruto", "arena", 1)
    _canal(tmp_path / "2026-09-02 vitoria x vasco" / "bruto", "canto", 500)

    d = gravacao.estado(tmp_path, time.time())

    assert d["total"] == 3 and d["gravando"] == 2
    assert round(d["mb"]) == 3
    assert len(d["jogos"]) == 2
    assert ":" in d["hora"]


def test_estado_de_biblioteca_vazia_nao_estoura(tmp_path: Path):
    d = gravacao.estado(tmp_path, time.time())
    assert d["jogos"] == [] and d["total"] == 0


def test_pagina_existe_e_pede_o_estado(tmp_path: Path):
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "/api/estado" in html
    assert "não para a gravação" in html, "o aviso e o que impede o usuario de fechar errado"
