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
