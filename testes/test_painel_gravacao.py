import json
from datetime import datetime
import os
import time
from pathlib import Path

from nucleo import catalogo
from painel import gravacao


def _canal(pasta: Path, nome: str, escrito_ha: float) -> None:
    d = pasta / nome
    d.mkdir(parents=True)
    (d / "gravacao.json").write_text(
        json.dumps({"url": "u", "sessoes": [{"numero": 1, "t0": "2026-09-02T21:00:00"}]}),
        encoding="utf-8",
    )
    ts = d / "s01-parte-000.ts"
    ts.write_bytes(b"x" * 1_000_000)
    marca = time.time() - escrito_ha
    os.utime(ts, (marca, marca))


def test_estado_soma_os_dois_jogos(tmp_path: Path):
    _canal(tmp_path / "2026-09-02 santos x palmeiras" / "bruto", "peixao", 1)
    _canal(tmp_path / "2026-09-02 vitoria x vasco" / "bruto", "arena", 1)
    _canal(tmp_path / "2026-09-02 vitoria x vasco" / "bruto", "canto", 500)

    d = gravacao.estado(tmp_path, time.time())

    assert d["total"] == 3 and d["gravando"] == 2
    assert round(d["mb"]) == 3
    assert len(d["jogos"]) == 2
    assert ":" in d["hora"]


def test_estado_de_biblioteca_vazia_nao_estoura(tmp_path: Path):
    d = gravacao.estado(tmp_path, time.time())
    assert d["jogos"] == [] and d["total"] == 0


def test_pagina_existe_e_pede_o_estado(tmp_path: Path):
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "/api/estado" in html
    assert "não para a gravação" in html, "o aviso e o que impede o usuario de fechar errado"


def test_marcar_grava_o_gol_em_disco_na_hora_do_clique(tmp_path: Path):
    """O passo mais fragil era anotar no papel e digitar depois."""
    jogo = "2026-09-02 santos x palmeiras"
    _canal(tmp_path / jogo / "bruto", "peixao", 1)

    r = gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 47, 13))

    assert r == {"numero": 1, "horario": "21:47:13"}
    salvo = json.loads((tmp_path / jogo / "catalogo.json").read_text(encoding="utf-8"))
    assert salvo["gols"][0]["horario"] == "2026-09-02T21:47:13"


def test_marcar_desconta_o_atraso_da_tela_de_quem_assiste(tmp_path: Path):
    """Quem assiste pela TV esta adiantado em relacao ao que o YouTube entrega."""
    jogo = "j"
    (tmp_path / jogo).mkdir()

    r = gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 47, 13), atraso=25)

    assert r["horario"] == "21:46:48"


def test_marcas_seguidas_recebem_numeros_diferentes(tmp_path: Path):
    jogo = "j"
    (tmp_path / jogo).mkdir()

    gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 40, 0))
    segundo = gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 22, 10, 0))

    assert segundo["numero"] == 2
    assert len(gravacao.gols_do_jogo(tmp_path, jogo)) == 2


def test_mover_e_apagar_a_marca(tmp_path: Path):
    jogo = "j"
    (tmp_path / jogo).mkdir()
    gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 40, 0))

    gravacao.mover(tmp_path, jogo, 1, -8)
    assert gravacao.gols_do_jogo(tmp_path, jogo)[0]["horario"] == "21:39:52"

    gravacao.apagar(tmp_path, jogo, 1)
    assert gravacao.gols_do_jogo(tmp_path, jogo) == []


def test_nome_de_jogo_nao_pode_escapar_da_biblioteca(tmp_path: Path):
    """A pagina manda o nome do jogo; nome nenhum pode virar caminho de fuga."""
    for nome in ("../fora", r"..\fora", r"C:\Windows"):
        try:
            gravacao.marcar(tmp_path, nome, datetime(2026, 9, 2, 21, 40, 0))
        except (ValueError, OSError):
            continue
        raise AssertionError(f"deveria ter recusado: {nome}")


def test_estado_traz_as_marcas_de_cada_jogo(tmp_path: Path):
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 55, 0))

    d = gravacao.estado(tmp_path, time.time())

    marcas = d["jogos"][0]["gols"]
    assert len(marcas) == 1
    assert marcas[0]["numero"] == 1 and marcas[0]["horario"] == "21:55:00"


def test_pagina_avisa_e_apita_quando_um_canal_cai():
    """Canal caido tem que gritar: o painel fica aberto de canto de olho."""
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "apitar" in html and "AudioContext" in html
    assert "pararam de gravar" in html
    assert "document.title" in html, "o aviso tem que aparecer na aba tambem"


def test_pagina_mostra_o_quadro_de_cada_canal():
    """Saber que grava nao basta: o que importa e se tem cara na camera."""
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "/api/quadro?jogo=" in html
    assert "encodeURIComponent" in html, "nome de canal tem espaco e acento"


def test_canal_de_outro_jogo_nao_pode_ser_alcancado_por_caminho(tmp_path: Path):
    jogo = "2026-09-02 santos x palmeiras"
    _canal(tmp_path / jogo / "bruto", "peixao", 1)
    cfg = {"caminho_ffmpeg": "ffmpeg"}

    for canal in ("../../fora", r"..\..\fora"):
        try:
            gravacao.quadro_do_canal(tmp_path, jogo, canal, cfg)
        except (ValueError, OSError):
            continue
        raise AssertionError(f"deveria ter recusado: {canal}")


def _gravacao_com_pids(pasta: Path, canal: str, pids: list[int]) -> None:
    d = pasta / "bruto" / canal
    d.mkdir(parents=True, exist_ok=True)
    (d / "gravacao.json").write_text(
        json.dumps({
            "url": "u",
            "sessoes": [{"numero": i + 1, "t0": "2026-09-02T21:30:00", "pid": p}
                        for i, p in enumerate(pids)],
        }),
        encoding="utf-8",
    )


def test_parar_derruba_o_supervisor_antes_dos_canais(tmp_path: Path):
    """Ao contrario, o supervisor ainda vivo religaria tudo em seguida."""
    jogo = "2026-09-02 santos x palmeiras"
    (tmp_path / jogo).mkdir(parents=True)
    (tmp_path / jogo / "supervisor.pid").write_text("1000", encoding="utf-8")
    _gravacao_com_pids(tmp_path / jogo, "peixao", [2001, 2002])
    mortos = []

    r = gravacao.parar_gravacao(tmp_path, jogo, matar=mortos.append)

    assert mortos[0] == 1000, "o supervisor cai primeiro"
    assert set(mortos[1:]) == {2001, 2002}, "depois todas as sessoes do canal"
    assert r["derrubados"] == 3


def test_parar_um_jogo_nao_encosta_no_outro(tmp_path: Path):
    """Duas partidas gravam juntas: parar uma nao pode derrubar a outra."""
    for jogo, pid in (("jogo A", 3001), ("jogo B", 4001)):
        (tmp_path / jogo).mkdir(parents=True)
        _gravacao_com_pids(tmp_path / jogo, "canal", [pid])
    mortos = []

    gravacao.parar_gravacao(tmp_path, "jogo A", matar=mortos.append)

    assert mortos == [3001]


def test_parar_gravacao_ja_parada_nao_estoura(tmp_path: Path):
    jogo = "j"
    (tmp_path / jogo).mkdir()

    assert gravacao.parar_gravacao(tmp_path, jogo, matar=lambda p: None)["derrubados"] == 0


def test_o_arquivo_de_pid_some_depois_de_parar(tmp_path: Path):
    """Deixar o arquivo faria o proximo PARAR mirar num pid ja reciclado."""
    jogo = "j"
    (tmp_path / jogo).mkdir()
    (tmp_path / jogo / "supervisor.pid").write_text("1000", encoding="utf-8")

    gravacao.parar_gravacao(tmp_path, jogo, matar=lambda p: None)

    assert not (tmp_path / jogo / "supervisor.pid").exists()


def test_parar_recusa_jogo_de_fora_da_biblioteca(tmp_path: Path):
    for nome in ("../fora", r"..\fora"):
        try:
            gravacao.parar_gravacao(tmp_path, nome, matar=lambda p: None)
        except (ValueError, OSError):
            continue
        raise AssertionError(f"deveria ter recusado: {nome}")


def test_pagina_tem_botao_de_parar_com_confirmacao():
    """Parar e irreversivel no meio do jogo: nao pode ser um clique solto."""
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "/api/parar" in html
    assert "confirm(" in html, "um clique sem querer nao pode derrubar a gravacao"


def test_pagina_abre_o_quadro_grande_para_ler_o_relogio_do_jogo():
    """A miniatura nao deixa ler o cronometro; e ele que revela o atraso do canal."""
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "abrirLupa" in html and "lupa-img" in html
    assert "ArrowRight" in html, "percorrer os canais e o que permite comparar"
    assert "v=${Date.now()}" in html, "no grande a foto tem que ser a mais nova"


def test_ajustar_grava_o_atraso_que_o_operador_digitou(tmp_path: Path):
    """E o 'atrasador de canal': ele ve o relogio na tela e diz quanto falta."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)

    r = gravacao.ajustar(tmp_path, jogo, "arena", 18.5)

    assert r["deslocamento"] == 18.5
    from nucleo import alinhamento
    valor, origem, _ = alinhamento.ler_deslocamento(tmp_path / jogo / "bruto" / "arena")
    assert valor == 18.5 and origem == "manual"


def test_ajustar_recusa_canal_de_fora(tmp_path: Path):
    jogo = "j"
    (tmp_path / jogo / "bruto").mkdir(parents=True)
    for canal in ("../fora", r"..\fora"):
        try:
            gravacao.ajustar(tmp_path, jogo, canal, 5.0)
        except (ValueError, OSError):
            continue
        raise AssertionError(f"deveria ter recusado: {canal}")


def test_alinhar_por_gol_que_nao_existe_reclama(tmp_path: Path):
    jogo = "j"
    _canal(tmp_path / jogo / "bruto", "arena", 1)

    try:
        gravacao.medir_alinhamento(tmp_path, jogo, 9, {"limiar_confianca_db": 6.0})
    except KeyError:
        return
    raise AssertionError("deveria ter reclamado")


def test_o_estado_diz_o_atraso_de_cada_canal(tmp_path: Path):
    """O campo na tela precisa vir preenchido com o que ja foi medido."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _canal(tmp_path / jogo / "bruto", "sem-medida", 1)
    gravacao.ajustar(tmp_path, jogo, "arena", 12.0)

    d = gravacao.estado(tmp_path, time.time())

    por_nome = {c["canal"]: c["deslocamento"] for c in d["jogos"][0]["canais"]}
    assert por_nome["arena"] == 12.0
    assert por_nome["sem-medida"] is None, "canal sem medida nao inventa zero"


def test_pagina_tem_o_campo_de_atraso_e_o_botao_de_alinhar():
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "/api/ajustar" in html and "/api/alinhar" in html
    assert "s de atraso" in html
    assert "discordaram em" in html, "espalhamento alto tem que virar aviso na tela"


def _partida_no_catalogo(pasta: Path, liga="copa-do-brasil") -> None:
    from nucleo import catalogo as cat
    dados = cat.registrar_partida(cat.carregar(pasta), liga, "vitoria", "vasco")
    cat.salvar(pasta, dados)


def test_cronometrar_mede_o_atraso_comparando_os_dois_relogios(tmp_path: Path, monkeypatch):
    """O caso que o operador descreveu: ESPN em 12:53 e a live em 12:59."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _partida_no_catalogo(tmp_path / jogo)
    monkeypatch.setattr(gravacao, "espn_do_jogo", lambda *a, **k: {
        "segundo_de_jogo": 773.0,             # 12:53
        "lido_em": "2026-09-02T22:00:00",
    })

    r = gravacao.cronometrar(
        tmp_path, jogo, "arena", "12:59", 1, "2026-09-02T22:00:00",
        {"caminho_ffmpeg": "ffmpeg"},
    )

    assert r["deslocamento"] == -6.0, "a live esta seis segundos adiantada"


def test_cronometrar_leva_a_espn_de_volta_ao_instante_do_quadro(tmp_path: Path, monkeypatch):
    """O quadro e de segundos atras; comparar com a ESPN de agora erraria por isso."""
    jogo = "j"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _partida_no_catalogo(tmp_path / jogo)
    monkeypatch.setattr(gravacao, "espn_do_jogo", lambda *a, **k: {
        "segundo_de_jogo": 800.0,
        "lido_em": "2026-09-02T22:00:30",     # lido 30s depois do quadro
    })

    r = gravacao.cronometrar(
        tmp_path, jogo, "arena", "12:50", 1, "2026-09-02T22:00:00",
        {"caminho_ffmpeg": "ffmpeg"},
    )

    # no instante do quadro a ESPN estava em 800-30 = 770s; a tela, em 770s
    assert r["espn_no_quadro"] == 770.0
    assert r["deslocamento"] == 0.0


def test_cronometro_da_outra_metade_e_recusado(tmp_path: Path, monkeypatch):
    """Entre uma metade e outra ha o intervalo, que nao e tempo de jogo."""
    jogo = "j"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _partida_no_catalogo(tmp_path / jogo)
    monkeypatch.setattr(gravacao, "espn_do_jogo", lambda *a, **k: {
        "segundo_de_jogo": 4800.0,            # segundo tempo
        "lido_em": "2026-09-02T23:00:00",
    })

    try:
        gravacao.cronometrar(
            tmp_path, jogo, "arena", "12:50", 1, "2026-09-02T23:00:00",
            {"caminho_ffmpeg": "ffmpeg"},
        )
    except ValueError as erro:
        assert "metade" in str(erro)
        return
    raise AssertionError("deveria ter recusado")


def test_cronometro_ilegivel_e_recusado(tmp_path: Path, monkeypatch):
    jogo = "j"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _partida_no_catalogo(tmp_path / jogo)
    monkeypatch.setattr(gravacao, "espn_do_jogo", lambda *a, **k: {
        "segundo_de_jogo": 773.0, "lido_em": "2026-09-02T22:00:00",
    })

    try:
        gravacao.cronometrar(
            tmp_path, jogo, "arena", "banana", 1, "2026-09-02T22:00:00",
            {"caminho_ffmpeg": "ffmpeg"},
        )
    except ValueError as erro:
        assert "cronometro" in str(erro)
        return
    raise AssertionError("deveria ter recusado")


def test_sem_espn_o_cronometro_manda_usar_o_campo_na_mao(tmp_path: Path, monkeypatch):
    jogo = "j"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    monkeypatch.setattr(gravacao, "espn_do_jogo", lambda *a, **k: None)

    try:
        gravacao.cronometrar(
            tmp_path, jogo, "arena", "12:50", 1, "2026-09-02T22:00:00",
            {"caminho_ffmpeg": "ffmpeg"},
        )
    except ValueError as erro:
        assert "na mao" in str(erro)
        return
    raise AssertionError("deveria ter recusado")


def test_jogo_sem_liga_cadastrada_nao_pergunta_a_espn(tmp_path: Path):
    """Jogo gravado sem informar a liga simplesmente nao tem placar."""
    jogo = "j"
    (tmp_path / jogo).mkdir()

    assert gravacao.espn_do_jogo(tmp_path, jogo) is None


def test_a_lupa_compara_o_cronometro_da_tela_com_o_da_espn():
    """E o alinhamento que nao depende de gol: qualquer quadro da partida serve."""
    html = gravacao.PAGINA.read_text(encoding="utf-8")

    assert "/api/cronometrar" in html
    assert "X-Instante" in html, "sem o instante do quadro a comparacao erra"
    assert "ESPN neste instante" in html
    assert "lido_em" in html, "a ESPN precisa voltar ao instante do quadro"


def test_a_marca_de_gol_pode_ser_desfeita_na_hora():
    """As teclas 1 e 2 marcam direto - basta clicar na pagina e digitar.

    Aconteceu duas vezes na noite de 02/09/2026, nos dois jogos. O desfazer
    resolve sem tirar a pressa de quem esta vendo o lance.
    """
    html = gravacao.PAGINA.read_text(encoding="utf-8")

    assert "desfazer" in html
    assert "avisar(" in html and "/api/apagar" in html


# --- estado do corte de cada gol --------------------------------------------
# O painel so le o disco. Estas provas descrevem como ele descobre em que pe
# esta o corte sem perguntar nada a quem corta.

def _gol_marcado(biblioteca: Path, jogo: str, numero: int = 1) -> None:
    pasta = biblioteca / jogo
    dados = catalogo.registrar_gol(
        catalogo.carregar(pasta), numero, "2026-09-02T21:55:00", ""
    )
    catalogo.salvar(pasta, dados)


def _clipe_no_catalogo(biblioteca: Path, jogo: str, numero: int, canal: str) -> None:
    pasta = biblioteca / jogo
    dados = catalogo.registrar_clipe(
        catalogo.carregar(pasta), numero, canal,
        f"clipes/gol-{numero:02d}/{canal}.mp4", 0.0, 8.0, True,
    )
    catalogo.salvar(pasta, dados)


def _mp4_do_corte(biblioteca: Path, jogo: str, numero: int, canal: str,
                  escrito_ha: float = 0.0) -> Path:
    destino = biblioteca / jogo / "clipes" / f"gol-{numero:02d}"
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / f"{canal}.mp4"
    arquivo.write_bytes(b"x")
    marca = time.time() - escrito_ha
    os.utime(arquivo, (marca, marca))
    os.utime(destino, (marca, marca))
    return arquivo


def test_corte_aguardando_enquanto_a_pasta_nao_existe(tmp_path: Path):
    """Gol marcado e pasta ausente: o corte ainda nao comecou."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _gol_marcado(tmp_path, jogo)

    corte = gravacao.estado_do_corte(tmp_path / jogo, 1, 6, time.time())

    assert corte["situacao"] == "aguardando"
    assert corte["feitos"] == 0 and corte["total"] == 6
    assert corte["pasta"] is False, "sem pasta, o botao de abrir nao pode aparecer"


def test_corte_cortando_enquanto_os_mp4_vao_aparecendo(tmp_path: Path):
    """Arquivos no disco e catalogo ainda vazio: o corte esta em andamento."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _gol_marcado(tmp_path, jogo)
    _mp4_do_corte(tmp_path, jogo, 1, "arena")
    _mp4_do_corte(tmp_path, jogo, 1, "canto")

    corte = gravacao.estado_do_corte(tmp_path / jogo, 1, 6, time.time())

    assert corte["situacao"] == "cortando"
    assert corte["feitos"] == 2 and corte["total"] == 6
    assert corte["pasta"] is True


def test_corte_pronto_quando_o_catalogo_registrou_os_clipes(tmp_path: Path):
    """Quem diz que acabou e o catalogo: ele so e salvo no fim do corte."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _gol_marcado(tmp_path, jogo)
    for canal in ("arena", "canto"):
        _mp4_do_corte(tmp_path, jogo, 1, canal)
        _clipe_no_catalogo(tmp_path, jogo, 1, canal)

    corte = gravacao.estado_do_corte(tmp_path / jogo, 1, 2, time.time())

    assert corte["situacao"] == "pronto"
    assert corte["feitos"] == 2 and corte["total"] == 2


def test_corte_pronto_conta_so_os_clipes_do_gol_pedido(tmp_path: Path):
    """Dois gols no mesmo catalogo nao podem somar os clipes um do outro."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _gol_marcado(tmp_path, jogo, 1)
    _gol_marcado(tmp_path, jogo, 2)
    _clipe_no_catalogo(tmp_path, jogo, 1, "arena")
    _clipe_no_catalogo(tmp_path, jogo, 2, "arena")
    _clipe_no_catalogo(tmp_path, jogo, 2, "canto")

    assert gravacao.estado_do_corte(tmp_path / jogo, 1, 2, time.time())["feitos"] == 1
    assert gravacao.estado_do_corte(tmp_path / jogo, 2, 2, time.time())["feitos"] == 2


def test_corte_pronto_faltando_canal_continua_pronto(tmp_path: Path):
    """Canal SEM MATERIAL nao trava o gol em 'cortando' para sempre.

    O contador e que conta a historia: 1 de 6 diz que cinco canais nao tinham
    o trecho no disco. Nunca sumir calado, mas tambem nunca mentir que ainda
    esta trabalhando.
    """
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _gol_marcado(tmp_path, jogo)
    _mp4_do_corte(tmp_path, jogo, 1, "arena")
    _clipe_no_catalogo(tmp_path, jogo, 1, "arena")

    corte = gravacao.estado_do_corte(tmp_path / jogo, 1, 6, time.time())

    assert corte["situacao"] == "pronto"
    assert corte["feitos"] == 1 and corte["total"] == 6


def test_corte_que_parou_no_meio_nao_finge_que_esta_cortando(tmp_path: Path):
    """Pasta parada ha muito tempo e catalogo vazio: o corte morreu no meio.

    Sem este estado, um corte que estourou fica 'cortando' para sempre e o
    operador espera por um arquivo que nunca vem.
    """
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _gol_marcado(tmp_path, jogo)
    _mp4_do_corte(tmp_path, jogo, 1, "arena", escrito_ha=gravacao.CORTE_PARADO_APOS + 60)

    corte = gravacao.estado_do_corte(tmp_path / jogo, 1, 6, time.time())

    assert corte["situacao"] == "parou"
    assert corte["feitos"] == 1 and corte["pasta"] is True


def test_estado_traz_o_corte_de_cada_gol(tmp_path: Path):
    """O painel inteiro, do jeito que a pagina recebe."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    gravacao.marcar(tmp_path, jogo, datetime(2026, 9, 2, 21, 55, 0))

    d = gravacao.estado(tmp_path, time.time())

    gol = d["jogos"][0]["gols"][0]
    assert gol["numero"] == 1 and gol["horario"] == "21:55:00"
    assert gol["corte"]["situacao"] == "aguardando"
    assert gol["corte"]["total"] == 1, "o total vem de quantos canais o jogo tem"


# --- abrir a pasta do corte no Explorador ------------------------------------

def test_abrir_pasta_chama_o_explorador_com_a_pasta_do_gol(tmp_path: Path):
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    _mp4_do_corte(tmp_path, jogo, 2, "arena")
    abertas = []

    r = gravacao.abrir_pasta(tmp_path, jogo, 2, abrir=abertas.append)

    assert r["ok"] is True
    assert abertas == [tmp_path / jogo / "clipes" / "gol-02"]


def test_abrir_pasta_avisa_quando_o_corte_ainda_nao_saiu(tmp_path: Path):
    """Sem pasta nao ha o que abrir - e um recado, nao um estouro."""
    jogo = "2026-09-02 vitoria x vasco"
    _canal(tmp_path / jogo / "bruto", "arena", 1)
    abertas = []

    r = gravacao.abrir_pasta(tmp_path, jogo, 1, abrir=abertas.append)

    assert r["ok"] is False and r["motivo"]
    assert abertas == [], "nada pode ser aberto quando a pasta nao existe"


def test_abrir_pasta_recusa_jogo_de_fora_da_biblioteca(tmp_path: Path):
    """O nome do jogo vem da pagina; nome nenhum pode virar caminho de fuga."""
    for nome in ("../fora", r"..\fora", r"C:\Windows"):
        try:
            gravacao.abrir_pasta(tmp_path, nome, 1, abrir=lambda p: None)
        except (ValueError, OSError):
            continue
        raise AssertionError(f"deveria ter recusado: {nome}")


def test_pagina_mostra_o_corte_e_o_botao_de_abrir():
    html = gravacao.PAGINA.read_text(encoding="utf-8")
    assert "/api/abrir" in html
    assert "corte" in html
