from pathlib import Path

from nucleo import teste_vod


def test_resumo_aprova_quando_a_maioria_esta_dentro_da_tolerancia():
    medidas = [
        teste_vod.Medida(1, 100.0, 101.0, 1.0, 14.0, True),
        teste_vod.Medida(2, 200.0, 201.5, 1.5, 12.0, True),
        teste_vod.Medida(3, 300.0, 290.0, 10.0, 4.0, False),
        teste_vod.Medida(4, 400.0, 400.5, 0.5, 20.0, True),
        teste_vod.Medida(5, 500.0, 502.0, 2.0, 9.0, True),
    ]
    resumo = teste_vod.resumir(medidas, tolerancia=3.0)
    assert resumo["total"] == 5
    assert resumo["dentro"] == 4
    assert resumo["fracao"] == 0.8
    assert resumo["aprovado"] is True


def test_resumo_reprova_abaixo_de_oitenta_por_cento():
    medidas = [
        teste_vod.Medida(1, 100.0, 130.0, 30.0, 3.0, False),
        teste_vod.Medida(2, 200.0, 201.0, 1.0, 12.0, True),
    ]
    assert teste_vod.resumir(medidas, tolerancia=3.0)["aprovado"] is False


def test_medir_abre_uma_janela_por_gol_e_soma_o_offset(tmp_path: Path, monkeypatch):
    """A janela comeca antes do gol, entao o instante achado precisa voltar
    para a escala do arquivo somando o comeco da janela."""
    chamadas = []

    def executar_falso(comando):
        chamadas.append(comando)
        # o proximo passo do medir vai ler este wav; cria um vazio valido
        Path(comando[-1]).write_bytes(b"")

    def analisar_falso(caminho, limiar_db):
        # o detector diz "a subida comecou 35s depois do inicio da janela"
        from nucleo import detector

        return detector.Achado(instante=35.0, confianca_db=15.0, tem_pico=True)

    monkeypatch.setattr(teste_vod.detector, "analisar", analisar_falso)

    cfg = {
        "janela_antes": 30,
        "janela_depois": 180,
        "limiar_confianca_db": 6.0,
        "caminho_ffmpeg": "ffmpeg",
    }

    medidas = teste_vod.medir(
        Path("jogo.mp4"), [1000.0], cfg, tmp_path, executar=executar_falso
    )

    assert len(medidas) == 1
    # janela comecou em 1000-30 = 970; 970 + 35 = 1005
    assert medidas[0].achado == 1005.0
    assert medidas[0].erro == 5.0
    assert len(chamadas) == 1


def test_janela_nao_comeca_antes_do_inicio_do_arquivo(tmp_path: Path, monkeypatch):
    def executar_falso(comando):
        Path(comando[-1]).write_bytes(b"")

    def analisar_falso(caminho, limiar_db):
        from nucleo import detector

        return detector.Achado(instante=0.0, confianca_db=15.0, tem_pico=True)

    monkeypatch.setattr(teste_vod.detector, "analisar", analisar_falso)
    cfg = {
        "janela_antes": 30,
        "janela_depois": 180,
        "limiar_confianca_db": 6.0,
        "caminho_ffmpeg": "ffmpeg",
    }

    medidas = teste_vod.medir(
        Path("j.mp4"), [10.0], cfg, tmp_path, executar=executar_falso
    )

    assert medidas[0].achado == 0.0, "janela travada em zero, nao em -20"
