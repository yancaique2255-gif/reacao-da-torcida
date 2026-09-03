import json
from datetime import datetime
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


def test_marcar_grava_o_gol_em_disco_na_hora_do_clique(tmp_path: Path):
    """O passo mais fragil era anotar no papel e digitar depois."""
    jogo = "2026-09-02 santos x palmeiras"
    _canal(tmp_path / jogo / "bruto", "peixao", 1)

    r = gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 47, 13))

    assert r == {"numero": 1, "horario": "21:47:13"}
    salvo = json.loads((tmp_path / jogo / "catalogo.json").read_text(encoding="utf-8"))
    assert salvo["gols"][0]["horario"] == "2026-09-02T21:47:13"


def test_marcar_desconta_o_atraso_da_tela_de_quem_assiste(tmp_path: Path):
    """Quem assiste pela TV esta adiantado em relacao ao que o YouTube entrega."""
    jogo = "j"
    (tmp_path / jogo).mkdir()

    r = gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 47, 13), atraso=25)

    assert r["horario"] == "21:46:48"


def test_marcas_seguidas_recebem_numeros_diferentes(tmp_path: Path):
    jogo = "j"
    (tmp_path / jogo).mkdir()

    gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 40, 0))
    segundo = gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 22, 10, 0))

    assert segundo["numero"] == 2
    assert len(gravacao.gols_do_jogo(tmp_path, jogo)) == 2


def test_mover_e_apagar_a_marca(tmp_path: Path):
    jogo = "j"
    (tmp_path / jogo).mkdir()
    gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 40, 0))

    gravacao.mover(tmp_path, jogo, 1, -8)
    assert gravacao.gols_do_jogo(tmp_path, jogo)[0]["horario"] == "21:39:52"

    gravacao.apagar(tmp_path, jogo, 1)
    assert gravacao.gols_do_jogo(tmp_path, jogo) == []


def test_nome_de_jogo_nao_pode_escapar_da_biblioteca(tmp_path: Path):
    """A pagina manda o nome do jogo; nome nenhum pode virar caminho de fuga."""
    for nome in ("../fora", r"..\fora", r"C:\Windows"):
        try:
            gravacao.marcar(tmp_path, nome, datetime(2026, 9, 2, 21, 40, 0))
        except (ValueError, OSError):
            continue
        raise AssertionError(f"deveria ter recusado: {nome}")


def test_estado_traz_as_marcas_de_cada_jogo(tmp_path: Path):
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 55, 0))

    d = gravacao.estado(tmp_path, time.time())

    assert d["jogos"][0]["gols"] == [{"numero": 1, "horario": "21:55:00"}]


def test_pagina_avisa_e_apita_quando_um_canal_cai():
    """Canal caido tem que gritar: o painel fica aberto de canto de olho."""
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "apitar" in html and "AudioContext" in html
    assert "pararam de gravar" in html
    assert "document.title" in html, "o aviso tem que aparecer na aba tambem"


def test_pagina_mostra_o_quadro_de_cada_canal():
    """Saber que grava nao basta: o que importa e se tem cara na camera."""
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "/api/quadro?jogo=" in html
    assert "encodeURIComponent" in html, "nome de canal tem espaco e acento"


def test_canal_de_outro_jogo_nao_pode_ser_alcancado_por_caminho(tmp_path: Path):
    jogo = "2026-09-02 santos x palmeiras"
    _canal(tmp_path / jogo / "bruto", "peixao", 1)
    cfg = {"caminho_ffmpeg": "ffmpeg"}

    for canal in ("../../fora", r"..\..\fora"):
        try:
            gravacao.quadro_do_canal(tmp_path, jogo, canal, cfg)
        except (ValueError, OSError):
            continue
        raise AssertionError(f"deveria ter recusado: {canal}")
