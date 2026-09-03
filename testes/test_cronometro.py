from datetime import datetime

from nucleo import cronometro


def test_le_o_cronometro_do_primeiro_tempo():
    assert cronometro.segundos_do_texto("12:43", tempo=1) == 763.0
    assert cronometro.segundos_do_texto("44:52", tempo=1) == 2692.0


def test_o_segundo_tempo_conta_a_partir_de_quarenta_e_cinco():
    """A tela do canal zera no intervalo; a ESPN nao zera."""
    assert cronometro.segundos_do_texto("35:22", tempo=2) == 4822.0
    assert cronometro.segundos_do_texto("00:00", tempo=2) == 2700.0


def test_o_prefixo_na_tela_manda_no_argumento():
    """Se o canal escreve '2T 35:22', nao ha por que perguntar a metade."""
    assert cronometro.segundos_do_texto("2T 35:22", tempo=1) == 4822.0
    assert cronometro.segundos_do_texto("1T 12:43", tempo=2) == 763.0
    assert cronometro.segundos_do_texto("2t 35:22") == 4822.0


def test_le_o_formato_da_espn():
    assert cronometro.segundos_do_texto("81'") == 4860.0
    assert cronometro.segundos_do_texto("90'+7'") == 5820.0
    assert cronometro.segundos_do_texto("45'+2'") == 2820.0


def test_texto_que_nao_e_cronometro_devolve_nada():
    for lixo in ("", "  ", "abc", "35:99", "12", None):
        assert cronometro.segundos_do_texto(lixo) is None


def test_o_numero_da_espn_e_mais_preciso_que_o_texto():
    """value=4810 e 80:10 exatos; displayValue arredonda para 81'."""
    assert cronometro.segundos_da_espn(4810.0, "81'") == 4810.0


def test_no_acrescimo_a_espn_trava_o_numero_e_so_o_texto_anda():
    """Gol aos 90'+7' veio com value=5400, que e o teto - o texto e que vale."""
    assert cronometro.segundos_da_espn(5400.0, "90'+7'") == 5820.0


def test_sem_numero_a_espn_ainda_da_para_ler_pelo_texto():
    assert cronometro.segundos_da_espn(None, "81'") == 4860.0
    assert cronometro.segundos_da_espn(None, "") is None


def test_live_adiantada_da_atraso_negativo():
    """O caso que o operador descreveu: ESPN em 12:53 e a live em 12:59."""
    espn = cronometro.segundos_do_texto("12:53", tempo=1)
    live = cronometro.segundos_do_texto("12:59", tempo=1)

    assert cronometro.atraso(espn, live) == -6.0


def test_live_atrasada_da_atraso_positivo():
    """Positivo e o valor a somar ao horario do gol: a reacao vem depois."""
    espn = cronometro.segundos_do_texto("12:53", tempo=1)
    live = cronometro.segundos_do_texto("12:32", tempo=1)

    assert cronometro.atraso(espn, live) == 21.0


def test_canal_no_mesmo_segundo_da_espn_nao_tem_atraso():
    assert cronometro.atraso(4822.0, 4822.0) == 0.0


def test_acha_a_hora_de_relogio_de_um_minuto_do_jogo():
    """Medido em 02/09/2026: a tela mostrava 2T 35:22 as 23:12:34."""
    ancora = cronometro.Ancora(datetime(2026, 9, 2, 23, 12, 34), 4822.0)

    # o gol da ESPN foi aos 4810s, doze segundos antes do que a tela mostrava
    assert cronometro.momento_do_minuto(ancora, 4810.0) == datetime(
        2026, 9, 2, 23, 12, 22
    )


def test_minuto_adiante_da_ancora_cai_adiante_no_relogio():
    ancora = cronometro.Ancora(datetime(2026, 9, 2, 23, 0, 0), 3600.0)

    assert cronometro.momento_do_minuto(ancora, 3660.0) == datetime(
        2026, 9, 2, 23, 1, 0
    )


def test_o_intervalo_separa_as_metades():
    """Ancora de um tempo nao serve para o outro: os quinze minutos de descanso
    entrariam na conta como se fossem jogo."""
    primeiro = cronometro.segundos_do_texto("40:00", tempo=1)
    segundo = cronometro.segundos_do_texto("35:00", tempo=2)

    assert not cronometro.mesma_metade(primeiro, segundo)
    assert cronometro.mesma_metade(primeiro, 100.0)
    assert cronometro.mesma_metade(segundo, 5000.0)
