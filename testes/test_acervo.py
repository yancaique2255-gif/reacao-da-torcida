"""O acervo: a biblioteca inteira, e em que pe cada jogo esta.

O que estes testes cobram e o motivo de o modulo existir: com mais de um jogo
no disco, a pergunta que importa nao e "quais gols tem" - e "por onde eu
continuo", e "o que falta para este virar video". Nada aqui pode escrever no
disco: a recepcao so le.
"""
import json
import time
from pathlib import Path

from nucleo import acervo, catalogo, estudio, receita

CFG = {
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
    "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
    "teto_cache_gb": 5,
}
AGORA = 1_788_000_000.0

CANAIS = [
    ("paulo-brito", "inter", 15.2),
    ("baldasso-tv", "inter", 9.4),
    ("radio-imortal", "gremio", 11.0),
]


def _canal(pasta_jogo: Path, nome: str, torcida: str, sessoes: int = 1) -> None:
    pasta = pasta_jogo / "bruto" / nome
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "gravacao.json").write_text(
        json.dumps({
            "url": f"https://youtu.be/{nome}",
            "torcida": torcida,
            "sessoes": [{"numero": n} for n in range(1, sessoes + 1)],
        }),
        encoding="utf-8",
    )


def jogo(
    biblioteca: Path,
    nome: str = "2026-09-03 gremio x internacional",
    gols: int = 2,
    canais=CANAIS,
    clipes_do_gol=None,
    escolhidos: bool | None = True,
    placar=(3, 1),
) -> Path:
    """Uma pasta de jogo completa: lives no bruto e catalogo com gols e clipes."""
    pasta = biblioteca / nome
    pasta.mkdir(parents=True, exist_ok=True)
    for canal, torcida, _ in canais:
        _canal(pasta, canal, torcida)

    dados = catalogo.registrar_partida(
        catalogo.novo(nome), "copa-do-brasil", "Gremio", "Internacional"
    )
    if placar:
        dados = catalogo.registrar_placar(dados, *placar)
    for numero in range(1, gols + 1):
        dados = catalogo.registrar_gol(
            dados, numero, f"2026-09-03T20:{10 + numero:02d}:00", ""
        )
        if clipes_do_gol is not None and numero not in clipes_do_gol:
            continue
        for canal, torcida, db in canais:
            dados = catalogo.registrar_clipe(
                dados, numero, canal, f"clipes/gol-{numero:02d}/{canal}.mp4",
                100.0, db, True, torcida, 175.0,
            )
    if escolhidos is not None:
        for clipe in dados["clipes"]:
            clipe["escolhido"] = escolhidos
    catalogo.salvar(pasta, dados)
    return pasta


def _resumo(pasta: Path) -> dict:
    return acervo.resumo(pasta, AGORA, CFG, vivo=lambda pid: False)


# --- em que pe o jogo esta -------------------------------------------------


def test_o_jogo_gravado_e_cortado_espera_escolha(tmp_path: Path):
    pasta = jogo(tmp_path, escolhidos=None)

    r = _resumo(pasta)

    assert r["etapa"] == "escolher"
    assert r["etapa_texto"] == "falta escolher"
    assert r["clipes"]["total"] == 6 and r["clipes"]["indecisos"] == 6
    assert r["lives"]["total"] == 3


def test_gol_sem_clipe_nenhum_volta_para_o_corte(tmp_path: Path):
    """A etapa e o primeiro degrau ainda nao vencido, nao o ultimo feito."""
    pasta = jogo(tmp_path, gols=3, clipes_do_gol=[1, 2])

    r = _resumo(pasta)

    assert r["etapa"] == "cortar"
    assert r["gols_sem_clipe"] == [3]
    assert any("gol 3" in p["texto"] for p in r["pendencias"])


def test_jogo_com_tudo_escolhido_esta_pronto_para_editar(tmp_path: Path):
    pasta = jogo(tmp_path)

    r = _resumo(pasta)

    assert r["etapa"] == "editar"
    assert r["no_video"] and r["duracao"] > 0, "a duracao prevista sai antes de editar"


def test_canal_gravando_agora_deixa_o_jogo_em_gravando(tmp_path: Path):
    pasta = jogo(tmp_path)
    pedaco = pasta / "bruto" / "paulo-brito" / "000.ts"
    pedaco.write_bytes(b"x" * 10)
    import os

    os.utime(pedaco, (AGORA, AGORA))

    r = _resumo(pasta)

    assert r["etapa"] == "gravando"
    assert r["lives"]["gravando"] == 1
    assert any("gravando agora" in p["texto"] for p in r["pendencias"])


def test_jogo_sem_gol_nao_finge_que_tem_trabalho(tmp_path: Path):
    pasta = jogo(tmp_path, gols=0)

    r = _resumo(pasta)

    assert r["etapa"] == "vazio"
    assert any("nenhum gol anotado" in p["texto"] for p in r["pendencias"])


# --- o que falta, escrito --------------------------------------------------


def test_canal_sem_torcida_aparece_na_pendencia(tmp_path: Path):
    """Campo vazio tira o canal do video sem ninguem perceber. Aqui ele grita."""
    pasta = jogo(tmp_path, canais=[("paulo-brito", "inter", 9.0),
                                   ("misterioso-tv", "", 8.0)])

    r = _resumo(pasta)

    assert r["sem_torcida"] == ["misterioso-tv"]
    recado = next(p for p in r["pendencias"] if "sem torcida" in p["texto"])
    assert recado["tom"] == "parou"
    assert "misterioso-tv" in recado["texto"]


def test_faltas_apontam_o_canal_que_nao_tem_material_do_gol(tmp_path: Path):
    """Nunca sumir calado: o par gol x canal sem clipe tem que ser nomeavel."""
    pasta = jogo(tmp_path, gols=1)
    dados = catalogo.carregar(pasta)
    dados["clipes"] = [c for c in dados["clipes"] if c["canal"] != "baldasso-tv"]
    catalogo.salvar(pasta, dados)

    buracos = acervo.faltas(catalogo.carregar(pasta), [c for c, _, _ in CANAIS])

    assert buracos == [{"gol": 1, "canal": "baldasso-tv"}]
    assert _resumo(pasta)["faltando"] == 1


def test_empate_avisa_que_o_video_nao_tem_lado(tmp_path: Path):
    pasta = jogo(tmp_path, placar=(2, 2))

    r = _resumo(pasta)

    assert r["alvo"]["torcida"] == ""
    assert any("empate" in p["texto"] for p in r["pendencias"])


# --- o video que ja saiu ---------------------------------------------------


def _renderizar(pasta: Path, com_assinatura: bool = True) -> None:
    """Finge um render terminado: o mp4 no lugar e o estado no render.json."""
    saida = pasta / "saida"
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "compilacao-deitado.mp4").write_bytes(b"video")
    dados = catalogo.carregar(pasta)
    edicao = receita.carregar(pasta, dados)
    receita.salvar(pasta, edicao)
    estudio.anotar(
        pasta, rodando=False, feito=4, total=4, mensagem="pronto",
        saida=str(saida / "compilacao-deitado.mp4"),
        assinatura=estudio.assinatura(dados, edicao, CFG) if com_assinatura else "",
    )


def test_video_no_disco_com_a_assinatura_de_agora_esta_pronto(tmp_path: Path):
    pasta = jogo(tmp_path)
    _renderizar(pasta)

    r = _resumo(pasta)

    assert r["etapa"] == "pronto"
    assert r["video"]["vencido"] is False
    assert r["video"]["nome"] == "compilacao-deitado.mp4"


def test_mexer_no_corte_depois_do_render_vence_o_video(tmp_path: Path):
    pasta = jogo(tmp_path)
    _renderizar(pasta)

    dados = catalogo.carregar(pasta)
    edicao = receita.carregar(pasta, dados)
    primeiro = receita.itens_do_video(edicao)[0]
    edicao = receita.mexer(edicao, primeiro["gol"], primeiro["canal"], ate=120.0)
    receita.salvar(pasta, edicao)

    r = _resumo(pasta)

    assert r["video"]["vencido"] is True
    assert r["etapa"] == "editar", "video que nao corresponde a edicao nao esta pronto"
    assert any("renderize de novo" in p["texto"] for p in r["pendencias"])


def test_so_abrir_a_tela_de_edicao_nao_vence_o_video(tmp_path: Path):
    """A tela de edicao regrava a receita a cada abertura.

    Por mtime, todo video parecia velho um minuto depois de sair - e aviso
    falso ensina o operador a ignorar o aviso que um dia sera verdade.
    """
    pasta = jogo(tmp_path)
    _renderizar(pasta)

    dados = catalogo.carregar(pasta)
    receita.salvar(pasta, receita.carregar(pasta, dados))  # foi o que a tela faz
    import os

    arquivo = pasta / "saida" / "compilacao-deitado.mp4"
    os.utime(arquivo, (AGORA - 3600, AGORA - 3600))  # o mp4 e bem mais velho

    assert _resumo(pasta)["video"]["vencido"] is False
    assert _resumo(pasta)["etapa"] == "pronto"


def test_render_antigo_sem_assinatura_nao_afirma_nada(tmp_path: Path):
    pasta = jogo(tmp_path)
    _renderizar(pasta, com_assinatura=False)

    r = _resumo(pasta)

    assert r["video"]["vencido"] is False
    assert not any("renderize de novo" in p["texto"] for p in r["pendencias"])


def test_render_que_morreu_no_meio_aparece_como_parou(tmp_path: Path):
    pasta = jogo(tmp_path)
    estudio.anotar(pasta, rodando=False, feito=3, total=16,
                   mensagem="o ffmpeg saiu com codigo 1")

    r = _resumo(pasta)

    recado = next(p for p in r["pendencias"] if "parou no meio" in p["texto"])
    assert recado["tom"] == "parou"
    assert "codigo 1" in recado["texto"]


# --- a biblioteca inteira --------------------------------------------------


def test_panorama_lista_do_mais_novo_para_o_mais_velho(tmp_path: Path):
    jogo(tmp_path, "2026-09-01 santos x palmeiras")
    jogo(tmp_path, "2026-09-03 gremio x internacional")

    tudo = acervo.panorama(tmp_path, AGORA, CFG, vivo=lambda pid: False)

    assert [j["pasta"] for j in tudo["jogos"]] == [
        "2026-09-03 gremio x internacional",
        "2026-09-01 santos x palmeiras",
    ]
    assert tudo["totais"]["jogos"] == 2
    assert tudo["totais"]["lives"] == 6
    assert tudo["totais"]["gols"] == 4


def test_o_proximo_e_o_jogo_mais_novo_que_ainda_pede_trabalho(tmp_path: Path):
    velho = jogo(tmp_path, "2026-09-01 santos x palmeiras")
    novo = jogo(tmp_path, "2026-09-03 gremio x internacional")
    _renderizar(novo)  # o mais novo acabou

    tudo = acervo.panorama(tmp_path, AGORA, CFG, vivo=lambda pid: False)

    assert tudo["proximo"] == velho.name
    assert tudo["totais"]["prontos"] == 1
    assert tudo["totais"]["pendentes"] == 1


def test_jogo_gravando_nao_entra_no_por_onde_continuar(tmp_path: Path):
    """Jogo no ar nao e trabalho de estudio: o video se monta depois do apito."""
    pasta = jogo(tmp_path, escolhidos=None)
    pedaco = pasta / "bruto" / "paulo-brito" / "000.ts"
    pedaco.write_bytes(b"x")
    import os

    os.utime(pedaco, (AGORA, AGORA))

    tudo = acervo.panorama(tmp_path, AGORA, CFG, vivo=lambda pid: False)

    assert tudo["jogos"][0]["etapa"] == "gravando"
    assert tudo["proximo"] == ""


def test_pasta_sem_bruto_nao_e_jogo(tmp_path: Path):
    """CONTATO, ensaios e o que mais o operador guardar ali ficam de fora."""
    jogo(tmp_path)
    (tmp_path / "CONTATO").mkdir()
    (tmp_path / "ensaios").mkdir()

    tudo = acervo.panorama(tmp_path, AGORA, CFG, vivo=lambda pid: False)

    assert [j["pasta"] for j in tudo["jogos"]] == ["2026-09-03 gremio x internacional"]


def test_jogo_ilegivel_aparece_marcado_e_nao_derruba_os_outros(tmp_path: Path):
    """Um json truncado numa pasta nao pode apagar da tela os jogos inteiros."""
    jogo(tmp_path, "2026-09-01 santos x palmeiras")
    quebrado = jogo(tmp_path, "2026-09-03 gremio x internacional")
    catalogo.caminho(quebrado).write_text('{"jogo": "corta', encoding="utf-8")

    tudo = acervo.panorama(tmp_path, AGORA, CFG, vivo=lambda pid: False)

    assert len(tudo["jogos"]) == 2
    ruim = tudo["jogos"][0]
    assert ruim["etapa"] == "erro" and ruim["pendencias"][0]["tom"] == "parou"
    assert tudo["jogos"][1]["etapa"] == "editar"


def test_ler_o_acervo_nao_escreve_nada_no_disco(tmp_path: Path):
    """A recepcao so le. Escrever aqui mexeria no trabalho de outro processo."""
    pasta = jogo(tmp_path)
    antes = {a.name: a.stat().st_mtime_ns for a in sorted(pasta.rglob("*"))}

    acervo.panorama(tmp_path, AGORA, CFG, vivo=lambda pid: False)

    depois = {a.name: a.stat().st_mtime_ns for a in sorted(pasta.rglob("*"))}
    assert antes == depois


def test_o_canal_traz_o_que_rendeu_de_clipe(tmp_path: Path):
    """A visao por live e a resposta a "e se tiver mais live": onze canais
    pedem uma linha por canal, e nao so uma parede de video por gol."""
    pasta = jogo(tmp_path, gols=2, canais=[("paulo-brito", "inter", 12.0)])

    canal = _resumo(pasta)["canais"][0]

    assert canal["canal"] == "paulo-brito"
    assert canal["clipes"] == 2 and canal["escolhidos"] == 2
    assert canal["db"] == 12.0
    assert canal["url"].endswith("paulo-brito")
