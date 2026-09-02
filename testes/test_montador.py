from pathlib import Path

from nucleo import montador

FFMPEG = "ffmpeg"


def test_cartela_normaliza_e_escreve_o_nome_do_canal():
    cmd = montador.comando_cartela(Path("a.mp4"), "Canal do Zé", Path("b.mp4"), FFMPEG)
    texto = " ".join(cmd)
    assert "1280" in texto and "720" in texto, "canais entregam formatos diferentes"
    assert "fps=30" in texto
    assert "drawtext" in texto
    assert "Canal do" in texto


def test_nome_com_aspas_nao_quebra_o_filtro():
    cmd = montador.comando_cartela(
        Path("a.mp4"), "Canal 'X': o melhor", Path("b.mp4"), FFMPEG
    )
    texto = " ".join(cmd)
    assert r"\:" in texto or r"\'" in texto, "dois-pontos e aspas precisam de escape"


def test_montar_gera_um_intermediario_por_clipe_e_um_concat(tmp_path: Path):
    chamadas = []
    escolhidos = [
        {"gol": 1, "canal": "canal-a", "arquivo": "clipes/gol-01/canal-a.mp4"},
        {"gol": 1, "canal": "canal-b", "arquivo": "clipes/gol-01/canal-b.mp4"},
    ]
    cfg = {"caminho_ffmpeg": FFMPEG}

    saida = montador.montar(escolhidos, tmp_path, cfg, executar=chamadas.append)

    assert len(chamadas) == 3, "duas cartelas e uma juncao"
    assert "concat" in " ".join(chamadas[-1])
    assert saida == tmp_path / "saida" / "compilacao.mp4"


def test_montar_sem_escolhidos_avisa_em_vez_de_gerar_vazio(tmp_path: Path):
    try:
        montador.montar([], tmp_path, {"caminho_ffmpeg": FFMPEG}, executar=lambda c: None)
    except ValueError as erro:
        assert "nenhum" in str(erro).lower()
    else:
        raise AssertionError("deveria ter recusado montar do nada")
