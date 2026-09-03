import json
from datetime import datetime
import os
import time
from pathlib import Path

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

    assert d["jogos"][0]["gols"] == [{"numero": 1, "horario": "21:55:00"}]


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
