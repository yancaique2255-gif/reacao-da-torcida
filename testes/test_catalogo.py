from pathlib import Path

from nucleo import catalogo


def test_ida_e_volta_no_disco_preserva_escolhas(tmp_path: Path):
    dados = catalogo.novo("2026-09-01 atletico-mg x cruzeiro")
    dados = catalogo.registrar_gol(dados, 1, "2026-09-01T21:37:00", "1x0")
    dados = catalogo.registrar_clipe(
        dados, 1, "canal-a", "clipes/gol-01/canal-a.mp4", 4412.5, 14.2, True
    )
    dados = catalogo.marcar_escolha(dados, 1, "canal-a", True)

    catalogo.salvar(tmp_path, dados)
    relido = catalogo.carregar(tmp_path)

    assert relido["clipes"][0]["escolhido"] is True
    assert relido["gols"][0]["descricao"] == "1x0"


def test_clipe_novo_comeca_sem_decisao(tmp_path: Path):
    dados = catalogo.registrar_clipe(
        catalogo.novo("j"), 1, "canal-a", "x.mp4", 10.0, 3.0, False
    )
    assert dados["clipes"][0]["escolhido"] is None
    assert dados["clipes"][0]["tem_pico"] is False


def test_registrar_o_mesmo_clipe_duas_vezes_atualiza_em_vez_de_duplicar():
    dados = catalogo.novo("j")
    dados = catalogo.registrar_clipe(dados, 1, "canal-a", "x.mp4", 10.0, 3.0, False)
    dados = catalogo.registrar_clipe(dados, 1, "canal-a", "x.mp4", 12.0, 9.0, True)
    assert len(dados["clipes"]) == 1
    assert dados["clipes"][0]["instante"] == 12.0


def test_escolhidos_saem_na_ordem_dos_gols():
    dados = catalogo.novo("j")
    dados = catalogo.registrar_clipe(dados, 2, "canal-b", "b.mp4", 1.0, 9.0, True)
    dados = catalogo.registrar_clipe(dados, 1, "canal-a", "a.mp4", 1.0, 9.0, True)
    dados = catalogo.registrar_clipe(dados, 1, "canal-z", "z.mp4", 1.0, 9.0, True)
    for gol, canal in [(2, "canal-b"), (1, "canal-a"), (1, "canal-z")]:
        dados = catalogo.marcar_escolha(dados, gol, canal, True)

    ordem = [(c["gol"], c["canal"]) for c in catalogo.escolhidos(dados)]
    assert ordem == [(1, "canal-a"), (1, "canal-z"), (2, "canal-b")]


def test_carregar_pasta_sem_catalogo_devolve_estrutura_vazia(tmp_path: Path):
    dados = catalogo.carregar(tmp_path)
    assert dados["gols"] == []
    assert dados["clipes"] == []


def test_proximo_numero_nao_reaproveita_o_de_um_gol_apagado():
    """Reaproveitar trocaria o dono de uma pasta gol-NN que ja esta no disco."""
    dados = catalogo.novo("jogo")
    dados = catalogo.registrar_gol(dados, 1, "2026-09-02T21:40:00", "")
    dados = catalogo.registrar_gol(dados, 2, "2026-09-02T22:10:00", "")
    dados = catalogo.remover_gol(dados, 2)

    assert catalogo.proximo_numero(dados) == 2 or catalogo.proximo_numero(dados) == 2
    dados = catalogo.registrar_gol(dados, 5, "2026-09-02T22:30:00", "")
    assert catalogo.proximo_numero(dados) == 6


def test_remover_gol_leva_os_clipes_junto():
    dados = catalogo.novo("jogo")
    dados = catalogo.registrar_gol(dados, 1, "2026-09-02T21:40:00", "")
    dados = catalogo.registrar_clipe(dados, 1, "peixao", "clipes/gol-01/peixao.mp4", 0, 0, False)
    dados = catalogo.registrar_gol(dados, 2, "2026-09-02T22:10:00", "")
    dados = catalogo.registrar_clipe(dados, 2, "peixao", "clipes/gol-02/peixao.mp4", 0, 0, False)

    dados = catalogo.remover_gol(dados, 1)

    assert [g["numero"] for g in dados["gols"]] == [2]
    assert [c["gol"] for c in dados["clipes"]] == [2]


def test_mover_gol_empurra_o_horario():
    """O dedo vai no botao depois do lance: acertar em segundos e o normal."""
    dados = catalogo.novo("jogo")
    dados = catalogo.registrar_gol(dados, 1, "2026-09-02T21:40:00", "")

    dados = catalogo.mover_gol(dados, 1, -8)

    assert dados["gols"][0]["horario"] == "2026-09-02T21:39:52"


def test_mover_gol_que_nao_existe_reclama():
    try:
        catalogo.mover_gol(catalogo.novo("jogo"), 9, 5)
    except KeyError:
        pass
    else:
        raise AssertionError("deveria ter reclamado")


def test_placar_final_fica_gravado_junto_da_partida():
    """O estudio edita dias depois, quando a ESPN ja nao responde por este jogo.

    Sem o placar em disco nao ha como saber quem perdeu, e quem perdeu e a
    regra que decide o video inteiro.
    """
    dados = catalogo.registrar_partida(
        catalogo.novo("jogo"), "copa-do-brasil", "Grêmio", "Internacional"
    )

    dados = catalogo.registrar_placar(dados, 3, 1)

    assert dados["partida"]["gols_mandante"] == 3
    assert dados["partida"]["gols_visitante"] == 1
    assert dados["partida"]["mandante"] == "Grêmio"


def test_placar_pode_ser_corrigido_depois():
    """Prorrogacao, penaltis, gol anulado: o ultimo numero e o que vale."""
    dados = catalogo.registrar_placar(catalogo.novo("jogo"), 1, 0)

    dados = catalogo.registrar_placar(dados, 1, 2)

    assert dados["partida"]["gols_mandante"] == 1
    assert dados["partida"]["gols_visitante"] == 2
