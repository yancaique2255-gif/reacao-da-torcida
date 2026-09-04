"""A receita e tudo o que o operador escolheu, e mora na pasta do jogo.

Tres propriedades, e cada teste aqui trava uma delas:

1. Nasce sozinha - derivada do catalogo, com um video montavel ja na primeira
   vez que o painel abre.
2. A escolha do operador ganha - recortar o jogo de novo nao desfaz o que ele
   mexeu.
3. Grava na hora - cada clique escreve o arquivo antes de a tela mudar.

Apagar a receita e seguro: ela volta ao padrao. Nao se perde gravacao, so se
perde a edicao.
"""
from pathlib import Path

import pytest

from nucleo import catalogo, receita

CLIPES = [
    # canal, torcida, forca da reacao
    ("farid-germano-filho", "inter", 15.2),
    ("paulo-brito", "inter", 7.8),
    ("radio-imortal", "gremio", 11.4),
    ("baldasso-tv", "", 9.0),
]


def _jogo(placar=(3, 1), gols=(1,)) -> dict:
    """Gremio 3x1 Internacional: quem perdeu foi o Inter."""
    dados = catalogo.registrar_partida(
        catalogo.novo("2026-09-03 gremio x internacional"),
        "copa-do-brasil", "Grêmio", "Internacional",
    )
    for numero in gols:
        dados = catalogo.registrar_gol(dados, numero, f"2026-09-03T20:1{numero}:00", "")
        for canal, torcida, db in CLIPES:
            dados = catalogo.registrar_clipe(
                dados, numero, canal, f"clipes/gol-0{numero}/{canal}.mp4",
                100.0, db, True, torcida, 175.0,
            )
    return catalogo.registrar_placar(dados, *placar)


def _item(dados_receita: dict, gol: int, canal: str) -> dict:
    for item in dados_receita["itens"]:
        if item["gol"] == gol and item["canal"] == canal:
            return item
    raise AssertionError(f"a receita nao tem o gol {gol} do canal {canal}")


def test_a_receita_nasce_derivada_do_catalogo():
    """O operador abre o painel e ja tem um video montavel."""
    feita = receita.padrao(_jogo())

    assert feita["torcida_alvo"] == "inter"
    assert feita["formato"] == "deitado"
    assert _item(feita, 1, "farid-germano-filho")["entra"] is True
    # 100s de pico, 60s de janela: o pico cai a 35% do comeco.
    assert _item(feita, 1, "farid-germano-filho")["de"] == 79.0
    assert _item(feita, 1, "farid-germano-filho")["ate"] == 139.0


def test_a_ordem_comeca_pela_reacao_mais_forte():
    feita = receita.padrao(_jogo())

    entram = [i["canal"] for i in feita["itens"] if i["entra"]]
    assert entram == ["farid-germano-filho", "paulo-brito"]


def test_quem_nao_e_da_torcida_alvo_aparece_desmarcado():
    """Nunca sumir calado: o canal do vencedor fica na lista, so que sem marca."""
    feita = receita.padrao(_jogo())

    assert _item(feita, 1, "radio-imortal")["entra"] is False
    assert _item(feita, 1, "baldasso-tv")["entra"] is False


def test_a_janela_do_curto_e_mais_apertada():
    """Mesmo material, outro formato: 20s por clipe para caber em ~2 min."""
    feita = receita.padrao(_jogo(), formato="em-pe", duracao_por_clipe=20)

    item = _item(feita, 1, "paulo-brito")
    assert feita["formato"] == "em-pe"
    assert round(item["ate"] - item["de"], 1) == 20.0


def test_apagar_a_receita_volta_ao_padrao(tmp_path: Path):
    dados = _jogo()
    receita.salvar(tmp_path, receita.mexer(receita.padrao(dados), 1, "paulo-brito", entra=False))
    receita.caminho(tmp_path).unlink()

    voltou = receita.carregar(tmp_path, dados)

    assert _item(voltou, 1, "paulo-brito")["entra"] is True


def test_a_edicao_do_operador_sobrevive_a_um_corte_novo(tmp_path: Path):
    """Recortar o gol de novo nao pode desfazer o que ele mexeu."""
    dados = _jogo()
    feita = receita.mexer(receita.padrao(dados), 1, "paulo-brito", de=10.0, ate=70.0)
    receita.salvar(tmp_path, feita)

    # O detector rodou de novo e achou o pico noutro lugar.
    dados = catalogo.registrar_clipe(
        dados, 1, "paulo-brito", "clipes/gol-01/paulo-brito.mp4",
        20.0, 7.8, True, "inter", 175.0,
    )
    depois = receita.carregar(tmp_path, dados)

    assert (_item(depois, 1, "paulo-brito")["de"], _item(depois, 1, "paulo-brito")["ate"]) == (10.0, 70.0)


def test_clipe_que_o_operador_nao_tocou_acompanha_o_corte_novo(tmp_path: Path):
    dados = _jogo()
    receita.salvar(tmp_path, receita.padrao(dados))

    dados = catalogo.registrar_clipe(
        dados, 1, "paulo-brito", "clipes/gol-01/paulo-brito.mp4",
        20.0, 7.8, True, "inter", 175.0,
    )
    depois = receita.carregar(tmp_path, dados)

    assert _item(depois, 1, "paulo-brito")["de"] == 0.0  # 20 - 21 nao existe: prende no zero


def test_gol_cortado_depois_entra_sem_apagar_o_resto(tmp_path: Path):
    dados = _jogo(gols=(1,))
    receita.salvar(tmp_path, receita.mexer(receita.padrao(dados), 1, "paulo-brito", entra=False))

    depois = receita.carregar(tmp_path, _jogo(gols=(1, 2)))

    assert _item(depois, 2, "farid-germano-filho")["entra"] is True
    assert _item(depois, 1, "paulo-brito")["entra"] is False


def test_clipe_que_sumiu_do_catalogo_sai_da_receita(tmp_path: Path):
    """Gol marcado errado no calor do jogo: apagado, some tambem da edicao."""
    dados = _jogo(gols=(1, 2))
    receita.salvar(tmp_path, receita.padrao(dados))

    depois = receita.carregar(tmp_path, catalogo.remover_gol(dados, 2))

    assert [i for i in depois["itens"] if i["gol"] == 2] == []


def test_grava_na_hora_e_volta_igual_do_disco(tmp_path: Path):
    feita = receita.mexer(receita.padrao(_jogo()), 1, "paulo-brito", de=5.0, ate=65.0)

    receita.salvar(tmp_path, feita)

    assert receita.carregar(tmp_path, _jogo()) == feita


def test_mexer_marca_o_item_como_tocado():
    feita = receita.mexer(receita.padrao(_jogo()), 1, "paulo-brito", entra=False)

    assert _item(feita, 1, "paulo-brito")["tocado"] is True
    assert _item(feita, 1, "farid-germano-filho")["tocado"] is False


def test_mexer_em_clipe_que_nao_existe_reclama():
    with pytest.raises(KeyError):
        receita.mexer(receita.padrao(_jogo()), 9, "ninguem", entra=True)


def test_o_video_e_so_quem_entra_na_ordem_escolhida():
    feita = receita.mexer(receita.padrao(_jogo()), 1, "farid-germano-filho", ordem=9)

    assert [i["canal"] for i in receita.itens_do_video(feita)] == [
        "paulo-brito", "farid-germano-filho",
    ]
