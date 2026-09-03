from pathlib import Path

from nucleo import catalogo
from painel import servidor

CFG = {"caminho_ffmpeg": "ffmpeg"}


def preparar(tmp_path: Path) -> Path:
    dados = catalogo.novo("jogo")
    dados = catalogo.registrar_clipe(
        dados, 1, "canal-a", "clipes/gol-01/a.mp4", 10.0, 12.0, True
    )
    catalogo.salvar(tmp_path, dados)
    return tmp_path


def test_get_catalogo_devolve_os_clipes(tmp_path: Path):
    pasta = preparar(tmp_path)
    codigo, corpo = servidor.montar_resposta("GET /api/catalogo", {}, pasta, CFG)
    assert codigo == 200
    assert corpo["clipes"][0]["canal"] == "canal-a"


def test_escolha_grava_no_disco_na_hora(tmp_path: Path):
    pasta = preparar(tmp_path)

    codigo, _ = servidor.montar_resposta(
        "POST /api/escolha",
        {"gol": 1, "canal": "canal-a", "escolhido": True},
        pasta,
        CFG,
    )

    assert codigo == 200
    relido = catalogo.carregar(pasta)
    assert relido["clipes"][0]["escolhido"] is True


def test_escolha_de_clipe_inexistente_devolve_404(tmp_path: Path):
    pasta = preparar(tmp_path)
    codigo, corpo = servidor.montar_resposta(
        "POST /api/escolha",
        {"gol": 9, "canal": "fantasma", "escolhido": True},
        pasta,
        CFG,
    )
    assert codigo == 404
    assert "erro" in corpo


def test_montar_sem_escolhidos_devolve_400_com_recado(tmp_path: Path):
    pasta = preparar(tmp_path)
    codigo, corpo = servidor.montar_resposta("POST /api/montar", {}, pasta, CFG)
    assert codigo == 400
    assert "nenhum" in corpo["erro"].lower()


def test_rota_desconhecida_devolve_404(tmp_path: Path):
    codigo, _ = servidor.montar_resposta("GET /api/nada", {}, tmp_path, CFG)
    assert codigo == 404


def test_estudio_ordena_pelo_mais_explosivo_e_separa_por_torcida():
    """Com onze canais por gol, a ordem e o filtro sao o que poupa o olho."""
    from painel import servidor

    html = (Path(servidor.__file__).resolve().parent / "pagina.html").read_text(
        encoding="utf-8"
    )

    assert "confianca_db) || 0) - (Number(a.confianca_db)" in html, "mais forte primeiro"
    assert "torcidaEscolhida" in html and "desenharFiltros" in html
    assert "Reação fraca" in html, "o clipe fraco tem que se explicar"


def test_estudio_avisa_qual_clipe_pede_aparo():
    """Clipe largo tem a reacao dentro, mas com folga: o operador precisa saber."""
    from painel import servidor

    html = (Path(servidor.__file__).resolve().parent / "pagina.html").read_text(
        encoding="utf-8"
    )

    assert "Janela larga" in html and "apare no seu editor" in html
    assert "Parcial" in html, "cobertura incompleta tambem se explica"
    assert "clipe.duracao" in html, "a duracao na tela e o que denuncia o clipe longo"
