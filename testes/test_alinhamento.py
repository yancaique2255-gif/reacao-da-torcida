from nucleo import alinhamento


def test_tres_canais_concordando_ficam_simetricos_em_torno_do_zero():
    picos = {"a": (100.0, 12.0), "b": (103.0, 9.0), "c": (106.0, 8.0)}

    c = alinhamento.medir(picos)

    assert c.referencia == 103.0, "a mediana"
    assert c.deslocamentos == {"a": -3.0, "b": 0.0, "c": 3.0}
    assert c.espalhamento == 6.0 and c.confiavel


def test_um_canal_sozinho_nao_gera_deslocamento_nenhum():
    """Sem com quem concordar, nao ha consenso - e nao se inventa."""
    assert alinhamento.medir({"a": (100.0, 20.0)}) is None
    assert alinhamento.medir({}) is None


def test_canal_muito_fora_nao_arrasta_a_referencia():
    """Caso real de 02/09/2026: um pico 56s fora dos outros dois.

    Com media, a referencia iria atras dele e os dois canais certos ficariam
    com deslocamento errado. Com mediana, ele e que fica marcado como o
    estranho - que e o que ele e.
    """
    picos = {
        "arena": (0.0, 15.9),    # 23:11:49
        "atencao": (56.0, 11.4),  # 23:12:45
        "fanatico": (58.0, 8.3),  # 23:12:47
    }

    c = alinhamento.medir(picos)

    assert c.referencia == 56.0, "a mediana fica com os dois que concordam"
    assert c.deslocamentos["atencao"] == 0.0
    assert c.deslocamentos["fanatico"] == 2.0
    assert c.deslocamentos["arena"] == -56.0
    assert not c.confiavel, "espalhamento de 58s pede olho humano"


def test_quem_nao_explodiu_nao_tem_voto():
    picos = {"a": (100.0, 12.0), "b": (103.0, 9.0), "mudo": (400.0, 1.2)}

    c = alinhamento.medir(picos, limiar_db=6.0)

    assert c.participantes == ["a", "b"]
    assert "mudo" not in c.deslocamentos, "canal que nao reagiu nao opina"


def test_todos_abaixo_do_limiar_e_o_mesmo_que_ninguem():
    picos = {"a": (100.0, 2.0), "b": (103.0, 1.0)}

    assert alinhamento.medir(picos, limiar_db=6.0) is None


def test_numero_par_de_canais_usa_o_meio_dos_dois_do_meio():
    picos = {"a": (10.0, 9.0), "b": (20.0, 9.0), "c": (30.0, 9.0), "d": (40.0, 9.0)}

    c = alinhamento.medir(picos)

    assert c.referencia == 25.0


def test_dois_canais_no_mesmo_instante_dao_deslocamento_zero():
    c = alinhamento.medir({"a": (77.0, 9.0), "b": (77.0, 8.0)})

    assert c.deslocamentos == {"a": 0.0, "b": 0.0}
    assert c.espalhamento == 0.0 and c.confiavel


def test_espalhamento_grande_marca_a_medida_como_frouxa():
    """O operador precisa saber que aquela medida merece conferencia."""
    apertado = alinhamento.medir({"a": (0.0, 9.0), "b": (5.0, 9.0)})
    frouxo = alinhamento.medir({"a": (0.0, 9.0), "b": (120.0, 9.0)})

    assert apertado.confiavel
    assert not frouxo.confiavel


def test_a_primeira_medida_de_um_canal_vale_inteira():
    assert alinhamento.combinar(None, 12.5) == 12.5


def test_cada_gol_novo_refina_a_estimativa():
    """Duas medidas parecidas convergem; uma medida solta nao manda sozinha."""
    assert alinhamento.combinar(10.0, 12.0) == 11.0
    assert alinhamento.combinar(11.0, 11.0, peso_do_antigo=2) == 11.0


def test_medida_antiga_com_mais_peso_se_move_menos():
    """Depois de tres gols, o quarto nao pode virar a estimativa de cabeca."""
    com_pouco = alinhamento.combinar(10.0, 40.0, peso_do_antigo=1)
    com_muito = alinhamento.combinar(10.0, 40.0, peso_do_antigo=5)

    assert com_pouco == 25.0
    assert com_muito == 15.0


def test_aplicar_soma_o_deslocamento_do_canal():
    d = {"atrasado": 25.0, "adiantado": -8.0}

    assert alinhamento.aplicar(d, "atrasado", 1000.0) == 1025.0
    assert alinhamento.aplicar(d, "adiantado", 1000.0) == 992.0


def test_canal_sem_medida_fica_no_horario_cru():
    """Nunca chutar: canal nao medido corta onde o operador marcou."""
    assert alinhamento.aplicar({"outro": 30.0}, "novo", 1000.0) == 1000.0
