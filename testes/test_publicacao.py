"""O texto da publicacao sai quase de graca: os dados ja estao no disco.

O titulo segue um padrao rigido, tirado de vinte videos do canal de referencia,
e o bloco de creditos e um `for` em cima do que a ficha do jogo ja guarda. Nada
de novo precisa ser anotado - e por isso os creditos nao sao opcionais: publicar
reacao de terceiro sem creditar seria a unica parte deste projeto que da
problema de verdade.
"""
import json
from pathlib import Path

from nucleo import catalogo, publicacao, receita, times

TIMES = {
    "internacional": {
        "nome": "Internacional", "torcida": "inter", "apelido": "COLORADOS",
        "adjetivo": "COLORADAS", "cor": "#e02020", "curto": "INTER",
    },
    "gremio": {
        "nome": "Grêmio", "torcida": "gremio", "apelido": "GREMISTAS",
        "adjetivo": "GREMISTAS", "cor": "#1c8ad6", "curto": "GRÊMIO",
    },
}


def _jogo(pasta: Path) -> dict:
    dados = catalogo.registrar_partida(
        catalogo.novo(pasta.name), "Copa do Brasil", "Grêmio", "Internacional"
    )
    dados = catalogo.registrar_placar(dados, 3, 1)
    dados = catalogo.registrar_gol(dados, 1, "2026-09-03T20:13:00", "")
    for canal, torcida, db in [
        ("baldasso-tv", "inter", 15.2),
        ("paulo-brito", "inter", 7.8),
        ("radio-imortal", "gremio", 11.4),
    ]:
        dados = catalogo.registrar_clipe(
            dados, 1, canal, f"clipes/gol-01/{canal}.mp4", 100.0, db, True, torcida, 175.0
        )
        destino = pasta / "bruto" / canal
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "gravacao.json").write_text(
            json.dumps({"url": f"https://www.youtube.com/watch?v={canal}",
                        "torcida": torcida, "sessoes": []}),
            encoding="utf-8",
        )
    catalogo.salvar(pasta, dados)
    return dados


def test_o_titulo_segue_o_padrao_do_canal(tmp_path: Path):
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    feita["textos"]["gancho"] = "ELIMINADO DA COPA DO BRASIL"

    titulo = publicacao.titulo(dados, feita, TIMES)

    assert titulo == (
        "REAÇÕES dos COLORADOS - GRÊMIO 3x1 INTERNACIONAL - "
        "ELIMINADO DA COPA DO BRASIL - VAMOS RIR DO INTER!"
    )


def test_sem_gancho_o_titulo_nao_fica_com_traco_solto(tmp_path: Path):
    """O gancho e a unica parte que muda de verdade, e as vezes nao existe."""
    dados = _jogo(tmp_path)

    titulo = publicacao.titulo(dados, receita.padrao(dados), TIMES)

    assert " -  - " not in titulo
    assert titulo.endswith("VAMOS RIR DO INTER!")


def test_os_creditos_trazem_toda_live_que_entrou_com_link(tmp_path: Path):
    dados = _jogo(tmp_path)

    creditos = publicacao.creditos(tmp_path, dados, receita.padrao(dados))

    assert [c["canal"] for c in creditos] == ["baldasso-tv", "paulo-brito"]
    assert creditos[0]["url"] == "https://www.youtube.com/watch?v=baldasso-tv"


def test_canal_que_nao_entrou_no_video_nao_e_creditado(tmp_path: Path):
    """Creditar quem nao apareceu e tao errado quanto nao creditar quem apareceu."""
    dados = _jogo(tmp_path)

    creditos = publicacao.creditos(tmp_path, dados, receita.padrao(dados))

    assert "radio-imortal" not in [c["canal"] for c in creditos]


def test_a_descricao_tem_o_bloco_de_creditos_com_o_link_de_cada_um(tmp_path: Path):
    dados = _jogo(tmp_path)

    descricao = publicacao.descricao(tmp_path, dados, receita.padrao(dados), TIMES)

    assert "Créditos do vídeo:" in descricao
    assert descricao.count("https://www.youtube.com/watch?v=") == 2


def test_as_tags_saem_dos_times_e_da_competicao(tmp_path: Path):
    dados = _jogo(tmp_path)

    tags = publicacao.tags(dados, receita.padrao(dados), TIMES)

    assert "reação da torcida" in tags
    assert "internacional" in tags
    assert "copa do brasil" in tags


def test_o_publicar_md_fica_pronto_para_copiar_e_colar(tmp_path: Path):
    dados = _jogo(tmp_path)

    arquivo = publicacao.escrever(tmp_path, dados, receita.padrao(dados), TIMES)

    texto = arquivo.read_text(encoding="utf-8")
    assert arquivo.name == "publicar.md"
    assert arquivo.parent.name == "saida"
    assert "## Título" in texto and "## Descrição" in texto and "## Tags" in texto


def test_time_que_nao_esta_no_dicionario_nao_inventa_apelido(tmp_path: Path):
    """Sem o apelido da torcida, usa o nome do time - e nunca chuta um."""
    dados = _jogo(tmp_path)

    titulo = publicacao.titulo(dados, receita.padrao(dados), {})

    assert "COLORADOS" not in titulo
    assert "INTERNACIONAL" in titulo


def test_o_dicionario_de_times_do_projeto_tem_os_times_que_ele_grava():
    """dados/times.json e o que veste a capa e o titulo. Comeca com quem ja jogou."""
    cadastrados = times.carregar()

    for time in ("internacional", "gremio"):
        assert time in cadastrados, time
        assert cadastrados[time]["apelido"], time
        assert cadastrados[time]["cor"].startswith("#"), time


def test_achar_o_time_aceita_o_apelido_da_torcida_e_o_nome_por_extenso():
    cadastrados = times.carregar()

    assert times.achar("inter", cadastrados)["nome"] == "Internacional"
    assert times.achar("Internacional", cadastrados)["nome"] == "Internacional"
    assert times.achar("Grêmio", cadastrados)["curto"] == "GRÊMIO"


def test_time_desconhecido_devolve_uma_ficha_honesta():
    """Nao quebra e nao inventa: o nome e o proprio, e a cor e a neutra."""
    ficha = times.achar("Ferroviária", {})

    assert ficha["nome"] == "Ferroviária"
    assert ficha["apelido"] == ""
    assert ficha["cor"]


def test_o_credito_usa_o_nome_de_verdade_do_canal(tmp_path: Path):
    """A pasta se chama "baldasso-tv"; o canal se chama "Baldasso TV".

    O credito e publico e vai com link: escrever o apelido de pasta seria
    creditar errado quem emprestou o material.
    """
    from nucleo import canais as mod_canais

    dados = _jogo(tmp_path)
    cadastro = {
        "gremio-x-inter": [
            mod_canais.Canal("Baldasso TV", "https://y/1", True, "inter"),
        ]
    }

    creditos = publicacao.creditos(tmp_path, dados, receita.padrao(dados), cadastro)

    assert creditos[0]["nome"] == "Baldasso TV"
    assert creditos[0]["canal"] == "baldasso-tv"
