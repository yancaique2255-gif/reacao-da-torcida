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


import os
from datetime import datetime
from pathlib import Path

from nucleo import relogio


def _sessao_falsa(pasta: Path, nome: str, t0: datetime, duracao: float) -> list:
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_bytes(b"x")
    return [relogio.Sessao(t0=t0, pedacos=[relogio.Pedaco(nome, 0.0, duracao)])]


def test_pico_do_canal_devolve_o_instante_relativo_ao_horario_marcado(
    tmp_path: Path, monkeypatch
):
    """O consenso compara canais; para isso o instante tem que ser relativo."""
    sessoes = _sessao_falsa(tmp_path, "s01-parte-000.ts", datetime(2026, 9, 2, 23, 0, 0), 3600)
    monkeypatch.setattr(
        alinhamento.detector, "analisar",
        lambda wav, limiar: alinhamento.detector.Achado(100.0, 12.0, True),
    )

    medida = alinhamento.pico_do_canal(
        tmp_path, sessoes, datetime(2026, 9, 2, 23, 12, 36),
        {"caminho_ffmpeg": "ffmpeg", "limiar_confianca_db": 6.0},
        executar=lambda c: None,
    )

    # o pico caiu aos 100s de uma janela que comeca 90s antes do horario:
    # entao ele esta 10s DEPOIS do que o operador marcou.
    assert medida == (10.0, 12.0)


def test_canal_sem_o_trecho_gravado_nao_devolve_pico(tmp_path: Path):
    sessoes = _sessao_falsa(tmp_path, "s01-parte-000.ts", datetime(2026, 9, 2, 21, 0, 0), 60)

    medida = alinhamento.pico_do_canal(
        tmp_path, sessoes, datetime(2026, 9, 2, 23, 12, 36),
        {"caminho_ffmpeg": "ffmpeg", "limiar_confianca_db": 6.0},
        executar=lambda c: None,
    )

    assert medida is None


def test_a_busca_e_bem_mais_larga_que_o_corte():
    """Ela precisa conter o pico mesmo com o canal dessincronizado."""
    assert alinhamento.BUSCA_ANTES >= 60 and alinhamento.BUSCA_DEPOIS >= 60


def test_o_wav_de_busca_nao_fica_para_tras(tmp_path: Path, monkeypatch):
    """Sao dezenas de MB por canal por gol; deixar isso no disco enche o HD."""
    sessoes = _sessao_falsa(tmp_path, "s01-parte-000.ts", datetime(2026, 9, 2, 23, 0, 0), 3600)
    monkeypatch.setattr(
        alinhamento.detector, "analisar",
        lambda wav, limiar: alinhamento.detector.Achado(50.0, 9.0, True),
    )

    alinhamento.pico_do_canal(
        tmp_path, sessoes, datetime(2026, 9, 2, 23, 12, 36),
        {"caminho_ffmpeg": "ffmpeg", "limiar_confianca_db": 6.0},
        executar=lambda c: None,
    )

    assert not (tmp_path / "busca-alinhamento.wav").exists()
    assert not (tmp_path / "busca-alinhamento.ts").exists()


def test_ffmpeg_que_estoura_num_canal_nao_derruba_a_medicao(tmp_path: Path):
    sessoes = _sessao_falsa(tmp_path, "s01-parte-000.ts", datetime(2026, 9, 2, 23, 0, 0), 3600)

    def explode(comando):
        raise RuntimeError("ffmpeg morreu")

    assert alinhamento.pico_do_canal(
        tmp_path, sessoes, datetime(2026, 9, 2, 23, 12, 36),
        {"caminho_ffmpeg": "ffmpeg", "limiar_confianca_db": 6.0}, executar=explode,
    ) is None


def test_picos_do_gol_pula_quem_falhou_e_devolve_o_resto(tmp_path: Path, monkeypatch):
    bom = _sessao_falsa(tmp_path / "bom", "s01-parte-000.ts", datetime(2026, 9, 2, 23, 0, 0), 3600)
    sem_trecho = _sessao_falsa(tmp_path / "sem", "s01-parte-000.ts", datetime(2026, 9, 2, 20, 0, 0), 60)
    monkeypatch.setattr(
        alinhamento.detector, "analisar",
        lambda wav, limiar: alinhamento.detector.Achado(95.0, 11.0, True),
    )

    picos = alinhamento.picos_do_gol(
        {"bom": bom, "sem": sem_trecho}, tmp_path, datetime(2026, 9, 2, 23, 12, 36),
        {"caminho_ffmpeg": "ffmpeg", "limiar_confianca_db": 6.0, "cortes_em_paralelo": 2},
        executar=lambda c: None,
    )

    assert set(picos) == {"bom"}
    assert picos["bom"] == (5.0, 11.0)


# Picos medidos de verdade em 02/09/2026, Vitoria x Vasco, com o detector
# rodando sobre a gravacao. Ficam aqui como gabarito: se o consenso mudar de
# comportamento, e sobre estes numeros que a mudanca tem que ser justificada.
PICOS_GOL_1 = {
    "arena-rubro-negra": (-54.5, 18.0),
    "fantico-vascano": (12.5, 7.4),
    "ateno-vascanos": (8.5, 7.2),
}
PICOS_GOL_2 = {
    "arena-rubro-negra": (29.5, 11.2),
    "ateno-vascanos": (10.0, 8.5),
    "fantico-vascano": (11.5, 6.6),
    "complexo-vascano": (13.5, 5.8),   # abaixo do limiar: sem voto
    "canto-rubro-negro": (-64.5, 5.2), # abaixo do limiar: sem voto
}


def test_gabarito_o_gol_1_da_consenso_mas_avisa_que_e_frouxo():
    """O canal mais alto do gol 1 foi o que estava mais fora - 54s antes."""
    c = alinhamento.medir(PICOS_GOL_1, limiar_db=6.0)

    assert c is not None
    assert c.referencia == 8.5, "a mediana ficou com os dois que concordam"
    assert not c.confiavel, "67s de espalhamento tem que acender a luz amarela"


def test_gabarito_o_gol_2_da_consenso_confiavel():
    """Tres canais dentro de 20s: e a medida boa das duas."""
    c = alinhamento.medir(PICOS_GOL_2, limiar_db=6.0)

    assert c.referencia == 11.5
    assert c.confiavel and c.espalhamento <= 20.0
    assert set(c.participantes) == {
        "arena-rubro-negra", "ateno-vascanos", "fantico-vascano"
    }, "quem ficou abaixo de 6 dB nao vota"


def test_gabarito_a_referencia_bate_com_o_que_se_ve_no_video():
    """No clipe do gol 1 a reacao aparece por volta de +2s do horario marcado.

    A regua da spec pede menos de 10s de erro; medido, deu 6,5s.
    """
    c = alinhamento.medir(PICOS_GOL_1, limiar_db=6.0)
    visto_no_video = 2.0

    assert abs(c.referencia - visto_no_video) < 10.0


def _canal_no_disco(pasta: Path, **extra) -> Path:
    import json as _json
    pasta.mkdir(parents=True, exist_ok=True)
    dados = {"url": "https://y/1", "sessoes": [{"numero": 1, "t0": "2026-09-02T21:30:00"}]}
    dados.update(extra)
    (pasta / "gravacao.json").write_text(_json.dumps(dados), encoding="utf-8")
    return pasta


def test_deslocamento_gravado_volta_na_leitura(tmp_path: Path):
    _canal_no_disco(tmp_path / "peixao")

    alinhamento.gravar_deslocamento(tmp_path / "peixao", 12.5, "consenso")

    valor, origem, medidas = alinhamento.ler_deslocamento(tmp_path / "peixao")
    assert valor == 12.5 and origem == "consenso" and medidas == 1


def test_gravar_nao_apaga_o_resto_do_arquivo(tmp_path: Path):
    """O gravacao.json e lido por _sessoes_do_canal: perder as sessoes seria fatal."""
    import json as _json
    _canal_no_disco(tmp_path / "peixao", torcida="santos")

    alinhamento.gravar_deslocamento(tmp_path / "peixao", 8.0)

    dados = _json.loads((tmp_path / "peixao" / "gravacao.json").read_text(encoding="utf-8"))
    assert dados["sessoes"] == [{"numero": 1, "t0": "2026-09-02T21:30:00"}]
    assert dados["torcida"] == "santos"
    assert dados["url"] == "https://y/1"


def test_o_que_o_operador_digitou_nao_e_sobrescrito_pelo_algoritmo(tmp_path: Path):
    """Ele viu; o algoritmo estimou. Manual vence consenso, sempre."""
    _canal_no_disco(tmp_path / "peixao")
    alinhamento.gravar_deslocamento(tmp_path / "peixao", 30.0, "manual")

    alinhamento.gravar_deslocamento(tmp_path / "peixao", 5.0, "consenso")

    valor, origem, _ = alinhamento.ler_deslocamento(tmp_path / "peixao")
    assert valor == 30.0 and origem == "manual"


def test_o_operador_pode_corrigir_o_que_o_algoritmo_mediu(tmp_path: Path):
    _canal_no_disco(tmp_path / "peixao")
    alinhamento.gravar_deslocamento(tmp_path / "peixao", 5.0, "consenso")

    alinhamento.gravar_deslocamento(tmp_path / "peixao", 30.0, "manual")

    valor, origem, _ = alinhamento.ler_deslocamento(tmp_path / "peixao")
    assert valor == 30.0 and origem == "manual"


def test_cada_gol_novo_puxa_a_media_do_canal(tmp_path: Path):
    _canal_no_disco(tmp_path / "peixao")

    alinhamento.gravar_deslocamento(tmp_path / "peixao", 10.0)
    alinhamento.gravar_deslocamento(tmp_path / "peixao", 20.0)

    valor, _, medidas = alinhamento.ler_deslocamento(tmp_path / "peixao")
    assert valor == 15.0 and medidas == 2


def test_canal_sem_medida_nenhuma_nao_entra_na_lista(tmp_path: Path):
    """Sem medida o corte usa o horario cru; poluir a lista com zeros esconde isso."""
    _canal_no_disco(tmp_path / "medido")
    _canal_no_disco(tmp_path / "virgem")
    alinhamento.gravar_deslocamento(tmp_path / "medido", 7.0)

    assert alinhamento.deslocamentos_do_jogo(tmp_path) == {"medido": 7.0}


def test_guardar_consenso_escreve_todos_os_canais_de_uma_vez(tmp_path: Path):
    for nome in ("a", "b"):
        _canal_no_disco(tmp_path / nome)
    consenso = alinhamento.medir({"a": (100.0, 9.0), "b": (110.0, 9.0)})

    gravados = alinhamento.guardar_consenso(tmp_path, consenso)

    assert gravados == {"a": -5.0, "b": 5.0}
    assert alinhamento.deslocamentos_do_jogo(tmp_path) == {"a": -5.0, "b": 5.0}


def test_consenso_de_canal_que_sumiu_do_disco_e_ignorado(tmp_path: Path):
    _canal_no_disco(tmp_path / "a")
    consenso = alinhamento.medir({"a": (100.0, 9.0), "apagado": (110.0, 9.0)})

    gravados = alinhamento.guardar_consenso(tmp_path, consenso)

    assert set(gravados) == {"a"}
