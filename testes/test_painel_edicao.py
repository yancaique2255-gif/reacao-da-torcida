"""O painel do estudio de edicao, porta 8772.

Nasce ao lado do estudio da 8770, e nao no lugar dele: reforma grande nao se faz
na ferramenta que esta em uso. O novo prova que funciona num jogo de verdade, e
so entao o velho sai.

O que estes testes cobram e a promessa do projeto inteiro: toda escolha do
operador grava em disco NA HORA, e nada some calado da tela.
"""
import json
from pathlib import Path

from nucleo import catalogo, estudio, receita
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
    """12:08 de video e 12 clipes: o operador precisa saber antes de renderizar."""
    _jogo(tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert corpo["quantos"] == 2
    assert corpo["segundos"] == 2 * 60 + estudio.DURACAO_DA_CARTELA


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


def test_o_placar_de_cada_gol_escreve_a_cartela(tmp_path: Path):
    """A cartela saia "GOL 3" pelado porque so a vigia sabia o placar do momento."""
    _jogo_sem_placar(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/placar-do-gol",
        {"gol": 2, "gols_mandante": 2, "gols_visitante": 0}, tmp_path,
    )

    assert codigo == 200
    dados = catalogo.carregar(tmp_path)
    assert estudio.texto_da_cartela(dados, 2) == "GOL 2 - Grêmio 2 x 0 Internacional"
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
