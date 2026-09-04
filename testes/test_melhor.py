"""A melhor janela de N segundos dentro de um clipe.

Os clipes saem com cerca de 175 segundos e o video longo tem que caber entre 12
e 20 minutos: cortar nao e enfeite do curto, e obrigatorio nos dois formatos.

Estes testes travam as duas estrategias - com pico, onde a reacao esta e a
sabemos; sem pico, o maior palpite disponivel - e, acima das duas, a regra que
vale sempre: a janela nunca sai do clipe.
"""
import numpy as np

from nucleo import melhor

QUADRO = 0.5


def curva(duracao_s: float, pico_s: float | None = None, altura_db: float = 20.0):
    """Curva plana em -40 dB, com um quadro bem alto no instante pedido."""
    linha = np.full(int(duracao_s / QUADRO), -40.0)
    if pico_s is not None:
        linha[int(pico_s / QUADRO)] += altura_db
    return linha


def test_pico_fica_a_35_por_cento_do_comeco_da_janela():
    """Um terco de subida, dois tercos de reacao.

    No meio ja e tarde e no comeco e pior: sem ver a cara do sujeito ANTES, a
    explosao nao tem graca.
    """
    assert melhor.janela(curva(175, pico_s=100), QUADRO, 60, True) == (79.0, 139.0)


def test_pico_no_comeco_nao_puxa_a_janela_para_antes_do_zero():
    assert melhor.janela(curva(175, pico_s=5), QUADRO, 60, True) == (0.0, 60.0)


def test_pico_no_fim_nao_empurra_a_janela_para_depois_do_clipe():
    assert melhor.janela(curva(175, pico_s=170), QUADRO, 60, True) == (115.0, 175.0)


def test_clipe_mais_curto_que_a_janela_sai_inteiro():
    assert melhor.janela(curva(15, pico_s=7), QUADRO, 60, True) == (0.0, 15.0)


def test_sem_pico_pega_o_trecho_de_maior_energia_media():
    linha = np.full(200, -40.0)  # 100 s de clipe
    linha[120:160] = -30.0       # de 60 s a 80 s, mais alto que o resto
    assert melhor.janela(linha, QUADRO, 20, False) == (60.0, 80.0)


def test_curva_plana_devolve_uma_janela_valida_do_tamanho_pedido():
    """Nada some calado: sem grito nenhum ainda sai um corte para o operador ver."""
    inicio, fim = melhor.janela(np.full(350, -40.0), QUADRO, 60, False)
    assert inicio >= 0.0 and fim <= 175.0
    assert round(fim - inicio, 3) == 60.0


def test_a_janela_nunca_sai_do_clipe_seja_onde_for_o_pico():
    for pico in range(0, 175, 5):
        inicio, fim = melhor.janela(curva(175, pico_s=pico), QUADRO, 60, True)
        assert inicio >= 0.0, f"pico em {pico}s comecou em {inicio}"
        assert fim <= 175.0, f"pico em {pico}s terminou em {fim}"
        assert round(fim - inicio, 3) == 60.0, f"pico em {pico}s mudou de tamanho"


def _clipe(instante=100.0, duracao=175.0, tem_pico=True) -> dict:
    return {"instante": instante, "duracao": duracao, "tem_pico": tem_pico}


def test_janela_do_clipe_usa_o_que_o_catalogo_ja_sabe():
    """O detector ja rodou e o numero esta gravado: abrir o audio de novo, para que?"""
    assert melhor.janela_do_clipe(_clipe(), 60) == (79.0, 139.0)


def test_janela_do_clipe_sem_pico_ainda_propoe_um_corte():
    """Sem a curva nao ha estrategia melhor; o painel marca o clipe como fraco."""
    assert melhor.janela_do_clipe(_clipe(tem_pico=False), 60) == (79.0, 139.0)


def test_janela_do_clipe_sem_duracao_conhecida_so_nao_comeca_antes_do_zero():
    """Clipe velho, cortado antes de o catalogo anotar duracao: nao da para prender o fim."""
    assert melhor.janela_do_clipe(_clipe(instante=200.0, duracao=0.0), 60) == (179.0, 239.0)


# ------------------------------------- o clipe que veio de outro momento do jogo

CFG_PICO = {
    "segundos_antes": 60,
    "segundos_depois": 60,
    "margem_sem_alinhamento": 60,
}


def _suspeito(instante: float, duracao: float = 240.0, largo=True, tem_pico=True) -> dict:
    return {
        "instante": instante, "duracao": duracao,
        "largo": largo, "tem_pico": tem_pico,
    }


def test_pico_na_hora_do_gol_nao_e_suspeito():
    """Clipe largo tem o gol no segundo 120: 60 pedidos mais 60 de margem."""
    assert melhor.fora_de_hora(_suspeito(119.0), CFG_PICO) is False


def test_pico_a_quarenta_e_cinco_minutos_do_gol_e_suspeito():
    """O `farid-germano-filho` religou 55x e caiu no primeiro tempo nos gols 3 e 4.

    Isto e defeito da esteira de corte, e nao do estudio - mas o estudio pode
    marcar em vermelho em vez de deixar o operador descobrir no video pronto.
    """
    assert melhor.fora_de_hora(_suspeito(11.0), CFG_PICO) is True
    assert melhor.fora_de_hora(_suspeito(34.5), CFG_PICO) is True


def test_clipe_sem_pico_nao_e_acusado():
    """Sem grito nao ha o que comparar, e o painel ja marca esse clipe como fraco."""
    assert melhor.fora_de_hora(_suspeito(3.0, tem_pico=False), CFG_PICO) is False


def test_clipe_sem_margem_espera_o_gol_no_segundo_sessenta():
    assert melhor.fora_de_hora(_suspeito(58.0, duracao=120.0, largo=False), CFG_PICO) is False
    assert melhor.fora_de_hora(_suspeito(5.0, duracao=120.0, largo=False), CFG_PICO) is True


def test_cobertura_parcial_aceita_o_gol_nos_dois_lugares_possiveis():
    """Faltou gravado de um dos lados, e nao se sabe de qual - nao da para acusar.

    O gol 1 de 03/09 saiu com clipes de ~174s numa janela de 240s: se o que
    faltou foi o comeco, o gol esta em 54s; se foi o fim, em 120s.
    """
    assert melhor.fora_de_hora(_suspeito(80.0, duracao=170.4), CFG_PICO) is False
    assert melhor.fora_de_hora(_suspeito(119.0, duracao=170.4), CFG_PICO) is False
    assert melhor.fora_de_hora(_suspeito(158.0, duracao=170.4), CFG_PICO) is True


def test_a_tolerancia_sai_da_configuracao():
    assert melhor.fora_de_hora(_suspeito(60.0), {**CFG_PICO, "tolerancia_do_pico": 5}) is True
    assert melhor.fora_de_hora(_suspeito(60.0), {**CFG_PICO, "tolerancia_do_pico": 90}) is False
