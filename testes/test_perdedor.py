"""Gravamos os dois lados; publicamos so o lado que perdeu.

E a regra editorial que organiza o estudio inteiro: a graca e a reacao de quem
se frustrou, e reacao de vencedor nao rende. O placar decide sozinho, o
operador discorda quando quiser, e nada disso pode sumir calado.
"""
from pathlib import Path

from nucleo import catalogo, perdedor

CANAIS = [
    ("paulo-brito", "inter"),
    ("radio-imortal", "gremio"),
    ("gaucha-esportes", "neutro"),
    ("baldasso-tv", ""),
]


def _jogo(placar: tuple[int, int] | None = None) -> dict:
    """Gremio x Internacional com os quatro casos de torcida que existem."""
    dados = catalogo.registrar_partida(
        catalogo.novo("2026-09-03 gremio x internacional"),
        "copa-do-brasil", "Grêmio", "Internacional",
    )
    dados = catalogo.registrar_gol(dados, 1, "2026-09-03T20:13:32", "")
    for canal, torcida in CANAIS:
        dados = catalogo.registrar_clipe(
            dados, 1, canal, f"clipes/gol-01/{canal}.mp4",
            10.0, 9.0, True, torcida, 175.0,
        )
    if placar is not None:
        dados = catalogo.registrar_placar(dados, *placar)
    return dados


def test_vitoria_do_mandante_poe_a_torcida_do_visitante_no_video():
    alvo = perdedor.alvo(_jogo(placar=(3, 1)))

    assert alvo.torcida == "inter"
    assert alvo.time == "Internacional"
    assert alvo.motivo == "perdeu"


def test_vitoria_do_visitante_poe_a_torcida_do_mandante_no_video():
    alvo = perdedor.alvo(_jogo(placar=(0, 2)))

    assert alvo.torcida == "gremio"
    assert alvo.time == "Grêmio"


def test_empate_nao_tem_perdedor_e_espera_o_operador():
    alvo = perdedor.alvo(_jogo(placar=(1, 1)))

    assert not alvo.decidido
    assert alvo.motivo == "empate"


def test_sem_placar_nao_chuta_um_lado():
    alvo = perdedor.alvo(_jogo())

    assert not alvo.decidido
    assert alvo.motivo == "sem placar"


def test_escolha_do_operador_vence_o_placar():
    """Ele troca no painel e pronto: e sugestao, nao trava."""
    dados = perdedor.escolher(_jogo(placar=(3, 1)), "Grêmio")

    alvo = perdedor.alvo(dados)

    assert alvo.torcida == "gremio"
    assert alvo.time == "Grêmio"
    assert alvo.motivo == "escolha do operador"


def test_a_escolha_do_operador_sobrevive_ao_disco(tmp_path: Path):
    """Nada so na memoria da pagina aberta: recarregar nao pode perder trabalho."""
    catalogo.salvar(tmp_path, perdedor.escolher(_jogo(placar=(3, 1)), "gremio"))

    assert perdedor.alvo(catalogo.carregar(tmp_path)).torcida == "gremio"


def test_apagar_a_escolha_volta_ao_perdedor():
    dados = perdedor.escolher(_jogo(placar=(3, 1)), "gremio")

    dados = perdedor.escolher(dados, "")

    assert perdedor.alvo(dados).torcida == "inter"


def test_entram_so_os_clipes_da_torcida_que_perdeu():
    entram = perdedor.entram(_jogo(placar=(3, 1)))

    assert [c["canal"] for c in entram] == ["paulo-brito"]


def test_canal_neutro_nao_entra_nem_quando_e_o_alvo():
    """Narracao sem lado nao e reacao de torcida: nao ha frustracao para filmar."""
    dados = perdedor.escolher(_jogo(placar=(3, 1)), "neutro")

    assert perdedor.entram(dados) == []


def test_canal_sem_torcida_nao_entra_mas_aparece_marcado():
    """O `baldasso-tv` de 03/09: o melhor material da noite, perdido por um campo vazio."""
    dados = _jogo(placar=(3, 1))

    assert "baldasso-tv" not in [c["canal"] for c in perdedor.entram(dados)]
    assert perdedor.sem_torcida(dados) == ["baldasso-tv"]


def test_a_lista_vem_do_mais_explosivo_para_o_mais_morno():
    """A forca da reacao ordena a lista sozinha; o operador comeca pelo melhor."""
    dados = _jogo(placar=(3, 1))
    for canal, db in [("farid-germano-filho", 15.2), ("paulo-brito", 7.8)]:
        dados = catalogo.registrar_clipe(
            dados, 1, canal, f"clipes/gol-01/{canal}.mp4", 10.0, db, True, "inter", 175.0
        )

    assert [c["canal"] for c in perdedor.entram(dados)] == [
        "farid-germano-filho", "paulo-brito",
    ]


def test_apelido_da_torcida_casa_com_o_nome_do_time():
    """"inter" e "Internacional" sao a mesma gente; "Grêmio" e "gremio" tambem."""
    assert perdedor.combina("inter", "Internacional")
    assert perdedor.combina("gremio", "Grêmio")
    assert not perdedor.combina("gremio", "Internacional")


def test_perdedor_sem_canal_gravado_ainda_diz_de_quem_era_a_vez():
    """Ninguem gravou o lado que perdeu: dizer isso, e nao promover o vencedor."""
    dados = _jogo(placar=(0, 2))
    dados["clipes"] = [c for c in dados["clipes"] if c["torcida"] != "gremio"]

    assert perdedor.alvo(dados).torcida == "gremio"
    assert perdedor.entram(dados) == []


def test_jogo_sem_partida_anotada_nao_quebra():
    """Catalogo velho, de antes de a partida ser registrada."""
    alvo = perdedor.alvo(catalogo.novo("jogo"))

    assert not alvo.decidido
    assert perdedor.entram(catalogo.novo("jogo")) == []
