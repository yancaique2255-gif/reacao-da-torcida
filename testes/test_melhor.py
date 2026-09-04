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
