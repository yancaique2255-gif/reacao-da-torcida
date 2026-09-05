"""O painel do estudio de edicao, porta 8772.

Nasce ao lado do estudio da 8770, e nao no lugar dele: reforma grande nao se faz
na ferramenta que esta em uso. O novo prova que funciona num jogo de verdade, e
so entao o velho sai.

O que estes testes cobram e a promessa do projeto inteiro: toda escolha do
operador grava em disco NA HORA, e nada some calado da tela.
"""
import json
from pathlib import Path

import pytest

from nucleo import catalogo, estudio, identidade, receita
from painel import edicao

CFG = {
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
    "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
    "biblioteca": "C:\\",
}

CLIPES = [
    ("farid-germano-filho", "inter", 15.2),
    ("paulo-brito", "inter", 7.8),
    ("radio-imortal", "gremio", 11.4),
    ("baldasso-tv", "", 9.0),
]


def _jogo(pasta: Path, placar=(3, 1)) -> dict:
    dados = catalogo.registrar_partida(
        catalogo.novo(pasta.name), "copa-do-brasil", "Grêmio", "Internacional"
    )
    dados = catalogo.registrar_placar(dados, *placar)
    dados = catalogo.registrar_gol(dados, 1, "2026-09-03T20:13:00", "")
    dados["gols"][0]["placar"] = [1, 0]
    for canal, torcida, db in CLIPES:
        dados = catalogo.registrar_clipe(
            dados, 1, canal, f"clipes/gol-01/{canal}.mp4",
            100.0, db, True, torcida, 175.0,
        )
    catalogo.salvar(pasta, dados)
    return dados


def _pedir(rota, corpo, pasta, **extra):
    return edicao.montar_resposta(rota, corpo, pasta, CFG, **extra)


def test_a_tela_abre_com_a_edicao_ja_derivada(tmp_path: Path):
    """Sem nenhum clique, ja ha um video montavel na tela."""
    _jogo(tmp_path)

    codigo, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert codigo == 200
    assert corpo["alvo"]["torcida"] == "inter"
    assert corpo["alvo"]["motivo"] == "perdeu"
    assert [g["numero"] for g in corpo["gols"]] == [1]
    entram = [i["canal"] for i in corpo["gols"][0]["itens"] if i["entra"]]
    assert entram == ["farid-germano-filho", "paulo-brito"]


def test_o_canal_sem_torcida_aparece_marcado_e_nao_some(tmp_path: Path):
    _jogo(tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    canais = [i["canal"] for i in corpo["gols"][0]["itens"]]
    assert "baldasso-tv" in canais
    assert corpo["sem_torcida"] == ["baldasso-tv"]


def test_desmarcar_um_clipe_grava_na_hora(tmp_path: Path):
    """Recarregar a pagina nao pode perder trabalho."""
    dados = _jogo(tmp_path)

    codigo, _ = _pedir(
        "POST /api/item", {"gol": 1, "canal": "paulo-brito", "entra": False}, tmp_path
    )

    assert codigo == 200
    do_disco = json.loads((tmp_path / receita.NOME).read_text(encoding="utf-8"))
    item = [i for i in do_disco["itens"] if i["canal"] == "paulo-brito"][0]
    assert item["entra"] is False
    assert item["tocado"] is True


def test_arrastar_as_alcas_grava_o_corte(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/item",
        {"gol": 1, "canal": "paulo-brito", "de": 12.5, "ate": 72.5},
        tmp_path,
    )

    assert codigo == 200
    item = [i for i in corpo["gols"][0]["itens"] if i["canal"] == "paulo-brito"][0]
    assert (item["de"], item["ate"]) == (12.5, 72.5)


def test_alca_fora_do_clipe_e_recusada(tmp_path: Path):
    """Corte que passa do fim do clipe vira video preto no meio da compilacao."""
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/item", {"gol": 1, "canal": "paulo-brito", "de": 0, "ate": 900},
        tmp_path,
    )

    assert codigo == 400
    assert "175" in corpo["erro"]


def test_trocar_de_quem_se_ri_grava_no_catalogo_e_refaz_a_receita(tmp_path: Path):
    """E sugestao, nao trava: o operador discorda e a escolha vale na hora."""
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/alvo", {"torcida": "gremio"}, tmp_path)

    assert codigo == 200
    assert corpo["alvo"]["torcida"] == "gremio"
    assert catalogo.carregar(tmp_path)["rindo_de"] == "gremio"
    entram = [i["canal"] for i in corpo["gols"][0]["itens"] if i["entra"]]
    assert entram == ["radio-imortal"]


def test_a_tela_oferece_as_torcidas_que_existem_no_jogo(tmp_path: Path):
    _jogo(tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert corpo["torcidas"] == ["gremio", "inter"]


def test_trocar_para_em_pe_aperta_a_janela(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/molde", {"formato": "em-pe"}, tmp_path)

    assert codigo == 200
    assert corpo["formato"] == "em-pe"
    assert corpo["molde"]["largura"] == 1080
    item = corpo["gols"][0]["itens"][0]
    assert round(item["ate"] - item["de"], 1) == 20.0


def test_formato_que_nao_existe_e_recusado(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/molde", {"formato": "quadrado"}, tmp_path)

    assert codigo == 400
    assert "deitado" in corpo["erro"]


def test_preencher_a_torcida_ali_mesmo_poe_o_canal_no_video(tmp_path: Path):
    """Mandar o operador abrir um json no meio da curadoria e garantir o campo vazio."""
    _jogo(tmp_path)
    (tmp_path / "bruto" / "baldasso-tv").mkdir(parents=True)
    (tmp_path / "bruto" / "baldasso-tv" / "gravacao.json").write_text(
        json.dumps({"url": "https://y/1", "torcida": ""}), encoding="utf-8"
    )

    codigo, corpo = _pedir(
        "POST /api/torcida", {"canal": "baldasso-tv", "torcida": "inter"}, tmp_path
    )

    assert codigo == 200
    assert corpo["sem_torcida"] == []
    entram = [i["canal"] for i in corpo["gols"][0]["itens"] if i["entra"]]
    assert "baldasso-tv" in entram


def test_espiar_devolve_um_quadro_para_a_tela(tmp_path: Path):
    _jogo(tmp_path)
    rodados = []

    def ffmpeg_de_mentira(comando):
        rodados.append(comando)
        Path(comando[-1]).write_bytes(b"png de mentira")

    codigo, corpo = _pedir(
        "POST /api/espiar", {"gol": 1, "canal": "paulo-brito"}, tmp_path,
        executar=ffmpeg_de_mentira,
    )

    assert codigo == 200
    assert corpo["arquivo"].startswith("/midia/intermediarios/espiada-1-paulo-brito.png")
    assert "-frames:v" in rodados[0]


def test_o_render_final_roda_em_outro_processo(tmp_path: Path):
    """Minutos de CPU: travar o painel enquanto isso seria travar o operador."""
    _jogo(tmp_path)
    lancados = []

    codigo, corpo = _pedir("POST /api/render", {}, tmp_path, lancar=lancados.append)

    assert codigo == 200
    assert lancados == [tmp_path]
    assert estudio.estado(tmp_path)["rodando"] is True
    assert corpo["render"]["rodando"] is True


def test_dois_cliques_no_render_nao_viram_dois_renders(tmp_path: Path):
    _jogo(tmp_path)
    lancados = []
    _pedir("POST /api/render", {}, tmp_path, lancar=lancados.append)

    codigo, corpo = _pedir("POST /api/render", {}, tmp_path, lancar=lancados.append)

    assert codigo == 409
    assert len(lancados) == 1
    assert "rodando" in corpo["erro"]


def test_sem_nada_marcado_o_render_nao_sai_e_diz_por_que(tmp_path: Path):
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    for item in list(feita["itens"]):
        feita = receita.mexer(feita, item["gol"], item["canal"], entra=False)
    receita.salvar(tmp_path, feita)

    codigo, corpo = _pedir("POST /api/render", {}, tmp_path, lancar=lambda p: None)

    assert codigo == 400
    assert "marque" in corpo["erro"].lower()


def test_o_progresso_do_render_e_lido_do_disco(tmp_path: Path):
    _jogo(tmp_path)
    estudio.anotar(tmp_path, rodando=True, feito=2, total=5, mensagem="2 de 5")

    codigo, corpo = _pedir("GET /api/estado", {}, tmp_path)

    assert codigo == 200
    assert (corpo["feito"], corpo["total"]) == (2, 5)


def test_limpar_devolve_o_espaco_e_diz_quanto(tmp_path: Path):
    _jogo(tmp_path)
    (tmp_path / estudio.PASTA_CACHE).mkdir()
    (tmp_path / estudio.PASTA_CACHE / "peca.mp4").write_bytes(b"x" * 4096)

    codigo, corpo = _pedir("POST /api/limpar", {}, tmp_path)

    assert codigo == 200
    assert corpo["liberado"] == 4096
    assert estudio.tamanho_do_cache(tmp_path) == 0


def test_a_tela_diz_quanto_video_vai_sair(tmp_path: Path):
    """12:08 de video e 12 clipes: o operador precisa saber antes de renderizar.

    Soma so os trechos: o video nao tem abertura nem cartela para somar junto.
    """
    _jogo(tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert corpo["quantos"] == 2
    assert corpo["segundos"] == 2 * 60


def test_rota_que_nao_existe_da_404(tmp_path: Path):
    codigo, corpo = _pedir("POST /api/inventada", {}, tmp_path)

    assert codigo == 404
    assert "inventada" in corpo["erro"]


def test_o_painel_guarda_o_pid_do_render(tmp_path: Path):
    """Sem o PID nao da para saber se o render morreu no meio - e ai a tela
    fica dizendo "rodando" para sempre, esperando um arquivo que nao vem."""
    _jogo(tmp_path)

    _pedir("POST /api/render", {}, tmp_path, lancar=lambda pasta: 4242)

    assert json.loads((tmp_path / estudio.NOME_ESTADO).read_text(encoding="utf-8"))["pid"] == 4242


def test_a_frase_da_capa_grava_na_hora(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/textos", {"frase_da_capa": "VERGONHA!", "gancho": "ELIMINADO"},
        tmp_path,
    )

    assert codigo == 200
    assert corpo["textos"]["frase_da_capa"] == "VERGONHA!"
    do_disco = json.loads((tmp_path / receita.NOME).read_text(encoding="utf-8"))
    assert do_disco["textos"]["gancho"] == "ELIMINADO"


def test_a_capa_sai_da_tela_e_volta_como_imagem(tmp_path: Path):
    from PIL import Image

    _jogo(tmp_path)

    def rosto_de_mentira(comando):
        Path(comando[-1]).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (640, 360), (0, 200, 0)).save(comando[-1])

    codigo, corpo = _pedir(
        "POST /api/capa", {}, tmp_path, executar=rosto_de_mentira
    )

    assert codigo == 200
    assert corpo["arquivo"].startswith("/midia/saida/capa.jpg")
    assert (tmp_path / "saida" / "capa.jpg").is_file()


def test_o_publicar_md_sai_da_tela_com_titulo_e_creditos(tmp_path: Path):
    _jogo(tmp_path)
    (tmp_path / "bruto" / "farid-germano-filho").mkdir(parents=True)
    (tmp_path / "bruto" / "farid-germano-filho" / "gravacao.json").write_text(
        json.dumps({"url": "https://y/1", "torcida": "inter"}), encoding="utf-8"
    )

    codigo, corpo = _pedir("POST /api/publicar", {}, tmp_path)

    assert codigo == 200
    assert "VAMOS RIR DO" in corpo["texto"]
    assert (tmp_path / "saida" / "publicar.md").is_file()


# ---------------------------------------------------- onde digitar o placar

def _jogo_sem_placar(pasta: Path) -> dict:
    """Como o jogo de 03/09 chegou ao estudio: gols marcados, placar nenhum.

    A `vigia` so escreve placar enquanto a partida esta no ar. Jogo cortado sem
    a liga configurada, ou com a ESPN fora, chega assim - e sem placar o estudio
    abre com "sem placar", nada marcado, cartela escrita so "GOL 3" e o titulo
    do publicar.md sem o 3x1.
    """
    dados = catalogo.registrar_partida(
        catalogo.novo(pasta.name), "copa-do-brasil", "Grêmio", "Internacional"
    )
    for numero in (1, 2):
        dados = catalogo.registrar_gol(dados, numero, f"2026-09-03T20:1{numero}:00", "")
    for canal, torcida, db in CLIPES:
        for numero in (1, 2):
            dados = catalogo.registrar_clipe(
                dados, numero, canal, f"clipes/gol-0{numero}/{canal}.mp4",
                100.0, db, True, torcida, 175.0,
            )
    catalogo.salvar(pasta, dados)
    return dados


def test_digitar_o_placar_decide_de_quem_o_video_ri(tmp_path: Path):
    _jogo_sem_placar(tmp_path)
    antes, corpo = _pedir("GET /api/edicao", {}, tmp_path)
    assert corpo["alvo"]["decidido"] is False

    codigo, corpo = _pedir(
        "POST /api/placar", {"gols_mandante": 3, "gols_visitante": 1}, tmp_path
    )

    assert codigo == 200
    assert corpo["partida"]["gols_mandante"] == 3
    assert corpo["alvo"]["torcida"] == "inter" and corpo["alvo"]["motivo"] == "perdeu"


def test_o_placar_digitado_grava_no_catalogo_na_hora(tmp_path: Path):
    _jogo_sem_placar(tmp_path)

    _pedir("POST /api/placar", {"gols_mandante": 3, "gols_visitante": 1}, tmp_path)

    guardado = catalogo.carregar(tmp_path)["partida"]
    assert (guardado["gols_mandante"], guardado["gols_visitante"]) == (3, 1)


def test_placar_que_nao_e_numero_e_recusado_e_nada_muda(tmp_path: Path):
    _jogo_sem_placar(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/placar", {"gols_mandante": "tres", "gols_visitante": 1}, tmp_path
    )

    assert codigo == 400 and "erro" in corpo
    assert "gols_mandante" not in catalogo.carregar(tmp_path)["partida"]


def test_o_placar_de_cada_gol_fica_anotado_no_catalogo(tmp_path: Path):
    """O placar do momento nao entra mais no video - o video e limpo.

    Continua sendo anotacao do jogo: e o que a tela mostra ao lado de cada gol,
    e e de onde sai o texto da capa e da legenda do post.
    """
    _jogo_sem_placar(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/placar-do-gol",
        {"gol": 2, "gols_mandante": 2, "gols_visitante": 0}, tmp_path,
    )

    assert codigo == 200
    dados = catalogo.carregar(tmp_path)
    assert estudio.placar_do_gol(dados, 2) == "Grêmio 2 x 0 Internacional"
    assert [g["placar"] for g in corpo["gols"] if g["numero"] == 2] == ["Grêmio 2 x 0 Internacional"]


def test_placar_de_gol_que_nao_existe_da_404(tmp_path: Path):
    _jogo_sem_placar(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/placar-do-gol",
        {"gol": 9, "gols_mandante": 1, "gols_visitante": 0}, tmp_path,
    )

    assert codigo == 404 and "9" in corpo["erro"]


def test_a_tela_tem_onde_digitar_o_placar():
    """A rota sem campo na tela nao serve de nada - foi o que faltou em 03/09.

    A secao 14.2 da spec mandou o placar para este painel e ele nao veio: nem
    rota nem campo. O teste cobra os dois lados.
    """
    pagina = edicao.PAGINA.read_text(encoding="utf-8")

    assert 'id="placar-mandante"' in pagina and 'id="placar-visitante"' in pagina
    assert "/api/placar" in pagina
    assert "/api/placar-do-gol" in pagina, "cada gol tambem precisa do seu"


def test_previa_que_trava_volta_erro_e_nao_derruba_o_painel(tmp_path: Path):
    """Travamento e falha doem igual para a tela: as duas viram um recado."""
    import subprocess

    _jogo(tmp_path)

    def travar(comando):
        raise subprocess.TimeoutExpired(comando, 900, stderr=b"frame=  120")

    codigo, corpo = _pedir(
        "POST /api/previa", {"gol": 1, "canal": "farid-germano-filho"},
        tmp_path, executar=travar,
    )

    assert codigo == 500 and "travou" in corpo["erro"]


def test_a_tela_marca_o_clipe_que_veio_de_outro_momento_do_jogo(tmp_path: Path):
    """Mitigacao do defeito 5 do laudo: o estudio nao conserta, mas avisa."""
    dados = _jogo(tmp_path)
    for clipe in dados["clipes"]:
        clipe["largo"] = True
        clipe["duracao"] = 240.0
    dados["clipes"][0]["instante"] = 11.0     # 45 min fora do lugar
    dados["clipes"][1]["instante"] = 119.0    # na hora do gol
    catalogo.salvar(tmp_path, dados)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    fora = {i["canal"]: i["fora_de_hora"] for i in corpo["gols"][0]["itens"]}
    assert fora[dados["clipes"][0]["canal"]] is True
    assert fora[dados["clipes"][1]["canal"]] is False


def test_a_tela_avisa_quantas_pecas_o_render_vai_ter(tmp_path: Path):
    """O painel escrevia 12 e o render trocava para 16: a barra andava para tras.

    Sem cartela, uma peca por trecho marcado - e o painel tem que dizer isso, e
    nao o numero de antes.
    """
    _jogo(tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert corpo["pecas"] == corpo["quantos"]


def test_o_render_comeca_com_o_total_que_o_painel_prometeu(tmp_path: Path):
    _jogo(tmp_path)
    _, tela = _pedir("GET /api/edicao", {}, tmp_path)

    _pedir("POST /api/render", {}, tmp_path, lancar=lambda p: 4242)

    assert estudio.estado(tmp_path, vivo=lambda p: True)["total"] == tela["pecas"]


@pytest.fixture(autouse=True)
def identidade_isolada(tmp_path: Path, monkeypatch):
    """Nenhum teste escreve na identidade real da maquina.

    As rotas gravam com `identidade.salvar()` sem caminho, e ele resolve o
    `ARQUIVO` do modulo na hora - trocar o atributo aqui basta.
    """
    monkeypatch.setattr(identidade, "ARQUIVO", tmp_path / "dados" / "identidade.json")


def test_a_tela_traz_a_moldagem_do_canal_ja_resolvida(tmp_path: Path):
    _jogo(tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert corpo["moldagem"] == {
        "arranjo": "quadro-cheio", "escala": 1.0, "deslocamento": 0.0
    }
    assert corpo["arranjos"] == ["quadro-cheio", "palco-alto", "palco-lateral"]
    assert corpo["fora_do_padrao"] is False
    assert corpo["palco_desenha"] == [], "identidade vazia nao desenha nada"


def test_escolher_o_arranjo_grava_na_identidade_do_canal(tmp_path: Path):
    """O palco e o estilo da casa: escolher aqui vale para todo jogo."""
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/moldagem", {"arranjo": "palco-alto"}, tmp_path)

    assert codigo == 200
    assert corpo["moldagem"]["arranjo"] == "palco-alto"
    assert identidade.carregar()["arranjo"] == "palco-alto"
    assert corpo["fora_do_padrao"] is False


def test_so_neste_jogo_grava_o_desvio_na_receita_e_marca(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/moldagem",
        {"arranjo": "palco-lateral", "so_neste_jogo": True},
        tmp_path,
    )

    assert codigo == 200
    assert corpo["fora_do_padrao"] is True
    assert corpo["moldagem"]["arranjo"] == "palco-lateral"
    gravada = json.loads((tmp_path / receita.NOME).read_text(encoding="utf-8"))
    assert gravada["moldagem"]["arranjo"] == "palco-lateral"
    assert identidade.carregar()["arranjo"] == "quadro-cheio", "o canal nao mudou"


def test_mexer_no_padrao_do_canal_apaga_o_desvio_do_jogo(tmp_path: Path):
    _jogo(tmp_path)
    _pedir("POST /api/moldagem", {"escala": 0.8, "so_neste_jogo": True}, tmp_path)

    _, corpo = _pedir("POST /api/moldagem", {"escala": 0.9}, tmp_path)

    assert corpo["fora_do_padrao"] is False
    assert corpo["moldagem"]["escala"] == 0.9


def test_escala_acima_de_um_e_recusada_pela_rota(tmp_path: Path):
    """O navegador ja prende o campo; quem garante e este lado."""
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/moldagem", {"escala": 1.5}, tmp_path)

    assert codigo == 400
    assert "1280x720" in corpo["erro"]
    assert identidade.carregar()["escala"] == 1.0, "nada mudou no disco"


def test_arranjo_que_nao_existe_e_recusado_pela_rota(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/moldagem", {"arranjo": "palco-do-mickey"}, tmp_path
    )

    assert codigo == 400
    assert "palco-alto" in corpo["erro"]


def test_os_arrobas_gravam_na_hora(tmp_path: Path):
    """Nada so na memoria da pagina aberta."""
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/identidade", {"redes": {"youtube": "@veiabanguela"}}, tmp_path
    )

    assert codigo == 200
    assert corpo["identidade"]["redes"]["youtube"] == "@veiabanguela"
    assert identidade.carregar()["redes"]["youtube"] == "@veiabanguela"


def test_conferir_palco_sem_marca_nenhuma_diz_que_nao_ha_o_que_desenhar(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/palco", {}, tmp_path)

    assert codigo == 200
    assert corpo["arquivo"] == ""
    assert "arte" in corpo["recado"].lower()


def test_conferir_palco_devolve_o_png_para_a_tela(tmp_path: Path):
    from PIL import Image

    _jogo(tmp_path)
    arte = tmp_path / "arte.png"
    Image.new("RGB", (1920, 1080), (12, 90, 40)).save(arte)
    _pedir("POST /api/identidade", {"arte_de_fundo": str(arte)}, tmp_path)

    codigo, corpo = _pedir("POST /api/palco", {}, tmp_path)

    assert codigo == 200
    assert corpo["arquivo"].startswith("/midia/intermediarios/formas/palco-deitado-")
    assert "?v=" in corpo["arquivo"], "sem contador o navegador mostra o palco velho"


def test_a_tela_diz_o_que_o_palco_vai_desenhar(tmp_path: Path):
    from PIL import Image

    _jogo(tmp_path)
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (400, 400), (255, 0, 0, 255)).save(logo)
    _pedir("POST /api/moldagem", {"arranjo": "palco-alto"}, tmp_path)
    _pedir("POST /api/identidade", {"logo": str(logo)}, tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert corpo["palco_desenha"] == ["logo"]


def test_a_previa_da_tela_traz_as_caixas_do_arranjo_escolhido(tmp_path: Path):
    """A previa usa `para_pagina`, que ja devolve as caixas em pixels."""
    _jogo(tmp_path)
    _pedir("POST /api/moldagem", {"arranjo": "palco-alto"}, tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    caixas = {c["nome"]: c for c in corpo["molde"]["camadas"]}
    assert (caixas["quadro"]["largura"], caixas["quadro"]["altura"]) == (1280, 720)
    assert "logo" in caixas and "barra" in caixas


def test_abrir_a_pasta_chama_o_explorador_com_o_caminho_inteiro(tmp_path: Path):
    """O nome do jogo tem espacos: o caminho vai como ARGUMENTO, nunca como
    texto para o operador copiar."""
    _jogo(tmp_path)
    saida = tmp_path / "saida" / "compilacao-deitado.mp4"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_bytes(b"video de mentira")
    estudio.anotar(tmp_path, rodando=False, saida=str(saida))
    abertos = []

    codigo, _ = _pedir("POST /api/abrir-pasta", {}, tmp_path, abrir=abertos.append)

    assert codigo == 200
    assert abertos == [saida]


def test_abrir_a_pasta_sem_video_pronto_diz_que_nao_tem(tmp_path: Path):
    _jogo(tmp_path)
    abertos = []

    codigo, corpo = _pedir("POST /api/abrir-pasta", {}, tmp_path, abrir=abertos.append)

    assert codigo == 404
    assert abertos == []
    assert "video" in corpo["erro"].lower()


def test_receita_editada_na_mao_fora_da_trava_ainda_abre_a_tela(tmp_path: Path):
    """Tela que nao abre e pior do que tela com recado."""
    dados = _jogo(tmp_path)
    edicao_ruim = receita.padrao(dados)
    edicao_ruim["moldagem"] = {"escala": 1.9}
    receita.salvar(tmp_path, edicao_ruim)

    codigo, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert codigo == 200
    assert corpo["moldagem"]["escala"] == 1.0, "caiu no padrao do canal"
    assert "1280x720" in corpo["recado_da_moldagem"]


def test_a_tela_tem_o_cartao_da_moldagem_antes_do_render():
    """A seccao 8: o lugar que faltava e depois de escolher os clipes, antes de gerar."""
    pagina = edicao.PAGINA.read_text(encoding="utf-8")

    assert 'id="moldagem"' in pagina
    assert 'id="botao-palco"' in pagina
    assert 'id="abrir-pasta"' in pagina
    assert pagina.index('id="moldagem"') < pagina.index('id="render"')
