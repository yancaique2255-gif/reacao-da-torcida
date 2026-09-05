"""A recepcao do estudio, porta 8773: a biblioteca inteira numa tela.

O estudio da 8770 serve UM jogo, escolhido no terminal na largada. Aqui o jogo
vai na ROTA - e e isso que estes testes cobram: trocar de jogo nao reinicia
nada, o nome que vem da URL nunca vira caminho sem passar pela lista do disco,
e toda escolha continua gravando em disco na hora.
"""
import urllib.parse
from pathlib import Path

from nucleo import catalogo
from painel import recepcao
from testes.test_acervo import CFG, jogo

PAGINA = Path(recepcao.__file__).resolve().parent / "recepcao.html"
AGORA = 1_788_000_000.0
NOME = "2026-09-03 gremio x internacional"


def _pedir(rota: str, corpo: dict, biblioteca: Path, **extra):
    return recepcao.montar_resposta(rota, corpo, biblioteca, CFG, agora=AGORA, **extra)


def _rota(nome: str, acao: str = "") -> str:
    caminho = "/api/jogo/" + urllib.parse.quote(nome)
    return caminho + (f"/{acao}" if acao else "")


# --- o acervo e o jogo na rota --------------------------------------------


def test_o_panorama_traz_todos_os_jogos(tmp_path: Path):
    jogo(tmp_path, "2026-09-01 santos x palmeiras")
    jogo(tmp_path, NOME)

    codigo, corpo = _pedir("GET /api/panorama", {}, tmp_path)

    assert codigo == 200
    assert len(corpo["jogos"]) == 2
    assert corpo["biblioteca"] == str(tmp_path)


def test_a_tela_do_jogo_vem_inteira_numa_chamada(tmp_path: Path):
    """Uma chamada e nao tres: os numeros nao podem discordar nem por um instante."""
    jogo(tmp_path, NOME, gols=2, escolhidos=None)

    codigo, corpo = _pedir("GET " + _rota(NOME), {}, tmp_path)

    assert codigo == 200
    assert corpo["resumo"]["titulo"] == "Gremio x Internacional"
    assert [g["numero"] for g in corpo["gols"]] == [1, 2]
    assert len(corpo["clipes"]) == 6
    assert corpo["faltas"] == []
    assert "neutro" in corpo["torcidas"] and "inter" in corpo["torcidas"]


def test_dois_jogos_atendem_na_mesma_porta_sem_reiniciar(tmp_path: Path):
    """A queixa que criou esta tela: trocar de jogo era fechar a janela."""
    jogo(tmp_path, "2026-09-01 santos x palmeiras")
    jogo(tmp_path, NOME)

    um = _pedir("GET " + _rota(NOME), {}, tmp_path)[1]
    outro = _pedir("GET " + _rota("2026-09-01 santos x palmeiras"), {}, tmp_path)[1]

    assert um["resumo"]["pasta"] == NOME
    assert outro["resumo"]["pasta"] == "2026-09-01 santos x palmeiras"


def test_jogo_que_nao_existe_devolve_404(tmp_path: Path):
    jogo(tmp_path, NOME)

    codigo, corpo = _pedir("GET " + _rota("2020-01-01 jogo inventado"), {}, tmp_path)

    assert codigo == 404 and "inventado" in corpo["erro"]


def test_nome_de_jogo_com_atalho_de_pasta_nao_vira_caminho(tmp_path: Path):
    """O nome vem da URL, e URL e coisa que se digita.

    Casar com a lista do disco e o que impede um `..` de virar leitura de
    qualquer pasta da maquina.
    """
    jogo(tmp_path, NOME)

    for tentativa in ("../..", "..%2F..%2FWindows", "C:/Windows"):
        codigo, _ = _pedir("GET /api/jogo/" + tentativa, {}, tmp_path)
        assert codigo == 404, tentativa


def test_rota_desconhecida_devolve_404(tmp_path: Path):
    assert _pedir("GET /api/nada", {}, tmp_path)[0] == 404


# --- escolher clipe -------------------------------------------------------


def test_escolha_grava_no_disco_na_hora(tmp_path: Path):
    jogo(tmp_path, NOME, gols=1, escolhidos=None)

    codigo, corpo = _pedir(
        "POST " + _rota(NOME, "escolha"),
        {"gol": 1, "canal": "paulo-brito", "escolhido": True},
        tmp_path,
    )

    assert codigo == 200
    gravado = [c for c in catalogo.carregar(tmp_path / NOME)["clipes"]
               if c["canal"] == "paulo-brito"][0]
    assert gravado["escolhido"] is True
    # A resposta ja vem com a contagem nova: a tela nao precisa recarregar.
    assert corpo["resumo"]["clipes"]["escolhidos"] == 1


def test_escolha_de_clipe_que_nao_existe_devolve_404(tmp_path: Path):
    jogo(tmp_path, NOME, gols=1)

    codigo, corpo = _pedir(
        "POST " + _rota(NOME, "escolha"),
        {"gol": 9, "canal": "fantasma", "escolhido": True},
        tmp_path,
    )

    assert codigo == 404 and "erro" in corpo


def test_preencher_torcida_conserta_o_jogo_e_o_cadastro(tmp_path: Path, monkeypatch):
    from nucleo import canais

    cadastro = tmp_path / "canais.json"
    monkeypatch.setattr(canais, "ARQUIVO", cadastro)
    cadastro.write_text(
        '{"internacional": [{"nome": "Misterioso TV", "url": "https://y/1"}]}',
        encoding="utf-8",
    )
    jogo(tmp_path, NOME, gols=1, canais=[("misterioso-tv", "", 8.0)])

    codigo, corpo = _pedir(
        "POST " + _rota(NOME, "torcida"),
        {"canal": "misterioso-tv", "torcida": "Inter"},
        tmp_path,
    )

    assert codigo == 200
    assert catalogo.carregar(tmp_path / NOME)["clipes"][0]["torcida"] == "inter"
    assert corpo["resumo"]["sem_torcida"] == []
    # O cadastro e a origem: sem consertar la, o buraco volta no proximo jogo.
    assert '"torcida": "inter"' in cadastro.read_text(encoding="utf-8")


def test_torcida_vazia_devolve_400(tmp_path: Path, monkeypatch):
    from nucleo import canais

    monkeypatch.setattr(canais, "ARQUIVO", tmp_path / "canais.json")
    jogo(tmp_path, NOME, gols=1, canais=[("misterioso-tv", "", 8.0)])

    codigo, corpo = _pedir(
        "POST " + _rota(NOME, "torcida"),
        {"canal": "misterioso-tv", "torcida": " "},
        tmp_path,
    )

    assert codigo == 400 and "neutro" in corpo["erro"]


# --- abrir o que ja existe ------------------------------------------------


def test_abrir_a_pasta_chama_o_explorador_com_o_caminho_certo(tmp_path: Path):
    pasta = jogo(tmp_path, NOME)
    abertos = []

    codigo, corpo = _pedir(
        "POST " + _rota(NOME, "abrir"), {"o_que": "pasta"}, tmp_path,
        abrir=abertos.append,
    )

    assert codigo == 200 and abertos == [pasta]
    assert corpo["caminho"] == str(pasta)


def test_abrir_video_que_ainda_nao_existe_diz_isso(tmp_path: Path):
    """Fingir que abriu e pior que erro: o operador espera uma janela que nao vem."""
    jogo(tmp_path, NOME)
    abertos = []

    codigo, corpo = _pedir(
        "POST " + _rota(NOME, "abrir"), {"o_que": "video"}, tmp_path,
        abrir=abertos.append,
    )

    assert codigo == 404 and not abertos
    assert "ainda não existe" in corpo["erro"]


def test_abrir_o_video_pronto_abre_o_mp4(tmp_path: Path):
    pasta = jogo(tmp_path, NOME)
    (pasta / "saida").mkdir()
    (pasta / "saida" / "compilacao-deitado.mp4").write_bytes(b"video")
    abertos = []

    codigo, _ = _pedir(
        "POST " + _rota(NOME, "abrir"), {"o_que": "video"}, tmp_path,
        abrir=abertos.append,
    )

    assert codigo == 200
    assert abertos[0].name == "compilacao-deitado.mp4"


# --- a edicao de cada jogo, sob demanda -----------------------------------


def test_a_edicao_sobe_por_jogo_e_devolve_a_porta(tmp_path: Path):
    pasta = jogo(tmp_path, NOME)
    pedidos = []

    codigo, corpo = _pedir(
        "POST " + _rota(NOME, "edicao"), {}, tmp_path,
        subir=lambda p: (pedidos.append(p), 8780)[1],
    )

    assert codigo == 200 and pedidos == [pasta]
    assert corpo["porta"] == 8780
    assert corpo["url"] == "http://127.0.0.1:8780/"


def test_clicar_duas_vezes_nao_sobe_dois_servidores(tmp_path: Path):
    """Dois servidores no mesmo jogo disputariam o mesmo receita.json."""
    pasta = jogo(tmp_path, NOME)
    abertas: dict[str, int] = {}
    subidas = []

    def falso_popen(pasta_jogo, abertas=abertas):
        # Imita `subir_edicao` sem processo: a porta e reaproveitada quando o
        # jogo ja tem uma.
        if pasta_jogo.name in abertas:
            return abertas[pasta_jogo.name]
        subidas.append(pasta_jogo.name)
        abertas[pasta_jogo.name] = 8780 + len(abertas)
        return abertas[pasta_jogo.name]

    primeira = _pedir("POST " + _rota(NOME, "edicao"), {}, tmp_path, subir=falso_popen)[1]
    segunda = _pedir("POST " + _rota(NOME, "edicao"), {}, tmp_path, subir=falso_popen)[1]

    assert primeira["porta"] == segunda["porta"]
    assert subidas == [pasta.name]


def test_porta_livre_pula_a_que_esta_ocupada():
    """8770/8771/8772 sao os paineis do operador: a edicao comeca depois."""
    assert recepcao.PRIMEIRA_PORTA > 8772
    assert recepcao.porta_livre() >= recepcao.PRIMEIRA_PORTA


# --- a tela ---------------------------------------------------------------


def _html() -> str:
    return PAGINA.read_text(encoding="utf-8")


def test_a_tela_nao_esconde_o_canal_sem_material():
    """A regra mais forte do projeto: o que deu errado aparece, nao some."""
    html = _html()

    assert "cartaoFalta" in html and "Sem material" in html
    assert "sem torcida" in html, "o estado vai escrito, nao so colorido"
    assert "var(--morta)" in html


def test_a_tela_diz_por_onde_continuar():
    html = _html()

    assert "proximo" in html and "continuar" in html
    assert "passoPrincipal" in html, "cada cartao diz o proximo passo daquele jogo"


def test_a_tela_agrupa_por_gol_e_por_live():
    """A resposta a "e se tiver mais live": onze canais pedem as duas visoes."""
    html = _html()

    assert "porGol" in html and "porLive" in html
    assert "religou" in html, "canal que caiu e religou tem que se explicar"


def test_a_acao_principal_da_recepcao_e_a_pilula_preta():
    html = _html()

    assert "#continuar, #editar { background: var(--texto); color: var(--fundo);" in html
    assert "box-shadow" not in html, "o sistema da Ollama separa por fio"


def test_preencher_a_rodada_muda_o_jogo_de_gaveta(tmp_path: Path):
    """O jogo chega do gravador sem rodada. Mandar o operador abrir o
    `catalogo.json` a mao e o jeito garantido de a gaveta "sem rodada" nunca
    esvaziar - entao a tela que mostra a falta e a que conserta.
    """
    jogo(tmp_path, NOME)

    codigo, corpo = _pedir("POST " + _rota(NOME, "rodada"), {"rodada": "Semifinal"},
                           tmp_path)

    assert codigo == 200
    # A recepcao inteira volta: mudar a rodada muda de prateleira, e trocar so
    # o texto do cartao mostraria o jogo na gaveta errada.
    assert corpo["grupos"][0]["rodadas"][0]["rodada_texto"] == "Semifinal"
    assert corpo["jogos"][0]["rodada"] == "Semifinal"
    # E no disco na hora, nao so na tela.
    do_disco = catalogo.carregar(tmp_path / NOME)
    assert do_disco["partida"]["rodada"] == "Semifinal"
    assert "**Rodada:** Semifinal" in (tmp_path / NOME / "JOGO.md").read_text(
        encoding="utf-8"
    )


def test_apagar_a_rodada_devolve_o_jogo_para_sem_rodada(tmp_path: Path):
    jogo(tmp_path, NOME, rodada="24")

    codigo, corpo = _pedir("POST " + _rota(NOME, "rodada"), {"rodada": ""}, tmp_path)

    assert codigo == 200
    assert corpo["grupos"][0]["rodadas"][0]["rodada_texto"] == "sem rodada"
    assert "rodada" not in catalogo.carregar(tmp_path / NOME)["partida"]


def test_a_tela_agrupa_com_o_que_o_servidor_manda():
    """Prateleira montada na pagina discordaria da contagem do servidor no dia
    em que a regra mudar num dos dois lados."""
    pagina = PAGINA.read_text(encoding="utf-8")

    assert "dados.grupos" in pagina
    assert "campeonato_texto" in pagina and "rodada_texto" in pagina
    # O filtro de time compara a chave que o servidor calculou, e nao o nome
    # escrito na tela: "Internacional" e "inter" sao o mesmo clube.
    assert "t.chave === estado.time" in pagina


def test_nada_da_tela_vive_so_na_pagina_aberta():
    """Recarregar nao pode perder trabalho: escolha vai para o disco na hora."""
    html = _html()

    assert "/escolha" in html and "/torcida" in html
    assert "location.hash" in html, "o jogo aberto sobrevive ao recarregar"
