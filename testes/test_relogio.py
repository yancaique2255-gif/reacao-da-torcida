from datetime import datetime, timedelta
from pathlib import Path

from nucleo import relogio

T0 = datetime(2026, 9, 1, 21, 0, 0)


def sessao_simples() -> relogio.Sessao:
    """Tres pedacos: 0-600, 600-1200, 1200-1500 (o ultimo mais curto)."""
    return relogio.Sessao(
        t0=T0,
        pedacos=[
            relogio.Pedaco("parte-000.ts", 0.0, 600.0),
            relogio.Pedaco("parte-001.ts", 600.0, 1200.0),
            relogio.Pedaco("parte-002.ts", 1200.0, 1500.0),
        ],
    )


def test_localiza_dentro_do_primeiro_pedaco():
    achado = relogio.localizar([sessao_simples()], T0 + timedelta(seconds=125))
    assert achado.arquivo == "parte-000.ts"
    assert achado.segundo == 125.0


def test_localiza_no_pedaco_do_meio_descontando_o_offset():
    achado = relogio.localizar([sessao_simples()], T0 + timedelta(seconds=725))
    assert achado.arquivo == "parte-001.ts"
    assert achado.segundo == 125.0


def test_pedaco_final_mais_curto_e_respeitado():
    achado = relogio.localizar([sessao_simples()], T0 + timedelta(seconds=1499))
    assert achado.arquivo == "parte-002.ts"
    assert achado.segundo == 299.0


def test_momento_depois_do_fim_nao_e_coberto():
    assert relogio.localizar([sessao_simples()], T0 + timedelta(seconds=1600)) is None


def test_momento_antes_do_inicio_nao_e_coberto():
    assert relogio.localizar([sessao_simples()], T0 - timedelta(seconds=5)) is None


def test_buraco_entre_sessoes_nao_e_coberto():
    """A gravacao caiu aos 1500s e so religou 120s depois."""
    primeira = sessao_simples()
    segunda = relogio.Sessao(
        t0=T0 + timedelta(seconds=1620),
        pedacos=[relogio.Pedaco("parte-100.ts", 0.0, 600.0)],
    )
    sessoes = [primeira, segunda]

    assert relogio.localizar(sessoes, T0 + timedelta(seconds=1550)) is None

    depois = relogio.localizar(sessoes, T0 + timedelta(seconds=1700))
    assert depois.arquivo == "parte-100.ts"
    assert depois.segundo == 80.0


def test_trechos_dentro_de_um_pedaco_so():
    recortes = relogio.trechos(
        [sessao_simples()],
        T0 + timedelta(seconds=100),
        T0 + timedelta(seconds=120),
    )
    assert recortes == [relogio.Trecho("parte-000.ts", 100.0, 120.0)]


def test_trechos_atravessando_dois_pedacos():
    recortes = relogio.trechos(
        [sessao_simples()],
        T0 + timedelta(seconds=595),
        T0 + timedelta(seconds=615),
    )
    assert recortes == [
        relogio.Trecho("parte-000.ts", 595.0, 600.0),
        relogio.Trecho("parte-001.ts", 0.0, 15.0),
    ]


def test_trechos_pulam_o_buraco_entre_sessoes():
    segunda = relogio.Sessao(
        t0=T0 + timedelta(seconds=1620),
        pedacos=[relogio.Pedaco("parte-100.ts", 0.0, 600.0)],
    )
    recortes = relogio.trechos(
        [sessao_simples(), segunda],
        T0 + timedelta(seconds=1490),
        T0 + timedelta(seconds=1630),
    )
    assert recortes == [
        relogio.Trecho("parte-002.ts", 290.0, 300.0),
        relogio.Trecho("parte-100.ts", 0.0, 10.0),
    ]


def test_le_o_csv_que_o_ffmpeg_escreve(tmp_path: Path):
    csv = tmp_path / "segmentos.csv"
    csv.write_text(
        "parte-000.ts,0.000000,600.000000\n"
        "parte-001.ts,600.000000,1200.000000\n",
        encoding="utf-8",
    )

    sessao = relogio.ler_segmentos(csv, T0)

    assert sessao.t0 == T0
    assert len(sessao.pedacos) == 2
    assert sessao.pedacos[1] == relogio.Pedaco("parte-001.ts", 600.0, 1200.0)


def test_cobertura_lista_os_intervalos_realmente_gravados():
    segunda = relogio.Sessao(
        t0=T0 + timedelta(seconds=1620),
        pedacos=[relogio.Pedaco("parte-100.ts", 0.0, 600.0)],
    )
    intervalos = relogio.cobertura([sessao_simples(), segunda])
    assert intervalos == [
        (T0, T0 + timedelta(seconds=1500)),
        (T0 + timedelta(seconds=1620), T0 + timedelta(seconds=2220)),
    ]
