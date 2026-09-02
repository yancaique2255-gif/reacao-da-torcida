import time
import json
from datetime import datetime
from pathlib import Path

from nucleo import canais, gravador

CFG = {
    "altura_maxima": 720,
    "duracao_pedaco": 600,
    "teto_canais": 20,
    "disco_minimo_gb": 60,
    "caminho_ytdlp": r"C:\yt-dlp\yt-dlp.exe",
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
}


def test_comando_respeita_as_travas_do_projeto(tmp_path: Path):
    cmd = gravador.comando("https://x/watch?v=1", tmp_path, 1, CFG)

    assert "height<=720" in cmd, "trava de banda: nunca 1080p"
    assert "-c copy" in cmd, "gravacao nao recodifica"
    assert "mpegts" in cmd, "mp4 interrompido fica ilegivel"
    assert "-segment_time 600" in cmd
    assert "segment_list" in cmd and "csv" in cmd
    assert cmd.count("|") == 1, "e um cano de yt-dlp para ffmpeg"


def test_comando_baixa_pelo_downloader_do_ytdlp_e_nao_pelo_ffmpeg(tmp_path: Path):
    """Sem isto a gravacao morre calada por volta dos trinta segundos.

    Para live, o yt-dlp entrega o HLS ao ffmpeg. O ffmpeg guarda a URL dos
    pedacos e para de renovar; o YouTube passa a responder 403 em todos eles.
    Medido nesta maquina em quatro canais: sempre entre 31 e 35 segundos, com o
    processo VIVO - por isso o supervisor nao percebia.
    """
    cmd = gravador.comando("https://x/watch?v=1", tmp_path, 1, CFG)

    assert "m3u8:native" in cmd, "o download do HLS e do yt-dlp, nao do ffmpeg"
    assert "--hls-use-mpegts" in cmd, "o cano tem que sair em TS"
    assert "+ba" not in cmd, "juntar duas faixas na saida padrao nao da; formato unico"


def test_sessoes_diferentes_nao_sobrescrevem_arquivos(tmp_path: Path):
    um = gravador.comando("https://x", tmp_path, 1, CFG)
    dois = gravador.comando("https://x", tmp_path, 2, CFG)
    assert "s01" in um and "s02" in dois
    assert um != dois


def test_apelido_vira_nome_de_pasta_seguro():
    assert gravador.apelido("Canal do Cruzeiro Ao Vivo!") == "canal-do-cruzeiro-ao-vivo"
    assert gravador.apelido("Seleção É 10") == "selecao-e-10"


def test_espaco_insuficiente_impede_comecar(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(gravador, "espaco_livre_gb", lambda caminho: 12.0)
    try:
        gravador.verificar_espaco(tmp_path, 60)
    except RuntimeError as erro:
        assert "12" in str(erro) and "60" in str(erro)
    else:
        raise AssertionError("deveria ter recusado")


def test_acima_do_teto_avisa_mas_nao_bloqueia():
    assert gravador.avaliar_banda(13, teto=20) is None
    aviso = gravador.avaliar_banda(25, teto=20)
    assert aviso is not None and "25" in aviso and "20" in aviso


def test_gravacao_json_guarda_o_horario_do_primeiro_frame(tmp_path: Path):
    t0 = datetime(2026, 9, 1, 21, 0, 0)
    arquivo = gravador.escrever_gravacao(tmp_path, "https://x", 1, t0)
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dados["sessoes"][0]["t0"] == "2026-09-01T21:00:00"
    assert dados["sessoes"][0]["numero"] == 1


def test_segunda_sessao_e_acrescentada_e_nao_apaga_a_primeira(tmp_path: Path):
    gravador.escrever_gravacao(tmp_path, "https://x", 1, datetime(2026, 9, 1, 21, 0, 0))
    arquivo = gravador.escrever_gravacao(
        tmp_path, "https://x", 2, datetime(2026, 9, 1, 21, 27, 0)
    )
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert [s["numero"] for s in dados["sessoes"]] == [1, 2]


def test_iniciar_abre_um_processo_por_canal_escolhido(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(gravador, "espaco_livre_gb", lambda caminho: 300.0)
    abertos = []

    def abrir_falso(comando, pasta):
        abertos.append(comando)
        return object()

    escolhidos = [
        (canais.Canal("A", "https://x/watch?v=1", True), "https://x/watch?v=1"),
        (canais.Canal("B", "https://x/watch?v=2", True), "https://x/watch?v=2"),
    ]
    processos = gravador.iniciar(
        escolhidos, tmp_path, "jogo-teste", CFG, abrir=abrir_falso
    )

    assert len(processos) == 2
    assert len(abertos) == 2
    assert (tmp_path / "jogo-teste" / "bruto" / "a" / "gravacao.json").is_file()


class ProcessoFalso:
    """Devolve None enquanto vivo; um codigo de saida depois de `vive_por` conferencias."""

    def __init__(self, vive_por: int = 999):
        self.vive_por = vive_por
        self.conferencias = 0

    def poll(self):
        self.conferencias += 1
        return None if self.conferencias <= self.vive_por else 1


SUPERVISAO = {**CFG, "segundos_entre_conferencias": 0}


def test_processo_vivo_nao_e_reiniciado(tmp_path: Path):
    abertos = []
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso()
    )

    gravador.supervisionar(
        [pr], SUPERVISAO,
        abrir=lambda c, p: abertos.append(c), dormir=lambda s: None, voltas=3,
    )

    assert abertos == []
    assert pr.sessao == 1


def test_gravacao_que_cai_volta_em_nova_sessao(tmp_path: Path):
    gravador.escrever_gravacao(tmp_path, "https://x", 1, datetime(2026, 9, 1, 21, 0, 0))
    abertos = []
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso(vive_por=1)
    )

    gravador.supervisionar(
        [pr], SUPERVISAO,
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(),
        dormir=lambda s: None, voltas=2,
    )

    assert pr.sessao == 2
    assert len(abertos) == 1
    assert "s02" in abertos[0], "a nova sessao nao pode sobrescrever os arquivos da s01"
    dados = json.loads((tmp_path / "gravacao.json").read_text(encoding="utf-8"))
    assert [s["numero"] for s in dados["sessoes"]] == [1, 2]


def test_desiste_do_canal_depois_de_muitas_quedas_seguidas(tmp_path: Path):
    """Live encerrada de verdade: nao pode ficar religando pra sempre."""
    abertos = []
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso(vive_por=0)
    )
    lista = [pr]

    gravador.supervisionar(
        lista, SUPERVISAO,
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(vive_por=0),
        dormir=lambda s: None, voltas=20,
    )

    assert len(abertos) == gravador.MAX_TENTATIVAS
    assert lista == [], "canal desistido sai da lista e o laco termina"


def test_um_canal_desistindo_nao_derruba_o_outro(tmp_path: Path):
    pasta_a = tmp_path / "a"
    pasta_b = tmp_path / "b"
    pasta_a.mkdir()
    pasta_b.mkdir()
    ruim = gravador.Processo(
        canais.Canal("Ruim", "u", True), "https://r", pasta_a, 1, ProcessoFalso(vive_por=0)
    )
    bom = gravador.Processo(
        canais.Canal("Bom", "u", True), "https://b", pasta_b, 1, ProcessoFalso()
    )
    lista = [ruim, bom]

    gravador.supervisionar(
        lista, SUPERVISAO,
        abrir=lambda c, p: ProcessoFalso(vive_por=0),
        dormir=lambda s: None, voltas=20,
    )

    assert [p.canal.nome for p in lista] == ["Bom"]


class ProcessoEmperrado:
    """Vivo para sempre, mas nao escreve nada. E o caso que enganava o supervisor."""

    def __init__(self):
        self.morto = False

    def poll(self):
        return 1 if self.morto else None

    def kill(self):
        self.morto = True


def test_gravacao_que_emperra_com_o_processo_vivo_e_derrubada_e_religada(tmp_path: Path):
    """Medido em jogo: o download morre e o processo continua de pe, mudo."""
    travado = ProcessoEmperrado()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, travado,
        inicio=time.time() - 300,  # nada escrito ha cinco minutos
    )
    abertos = []

    gravador.supervisionar(
        [pr], {**SUPERVISAO, "segundos_sem_crescer": 90},
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(),
        dormir=lambda s: None, voltas=1,
    )

    assert travado.morto, "processo emperrado tem que ser derrubado"
    assert pr.sessao == 2 and len(abertos) == 1


def test_pedaco_crescendo_conta_como_gravacao_viva(tmp_path: Path):
    (tmp_path / "s01-parte-000.ts").write_bytes(b"x")  # escrito agora
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoEmperrado(),
        inicio=time.time() - 300,
    )
    abertos = []

    gravador.supervisionar(
        [pr], {**SUPERVISAO, "segundos_sem_crescer": 90},
        abrir=lambda c, p: abertos.append(c), dormir=lambda s: None, voltas=1,
    )

    assert abertos == [] and pr.sessao == 1


def test_sessao_recem_aberta_tem_folga_para_o_ytdlp_negociar(tmp_path: Path):
    """Nos primeiros segundos ainda nao existe .ts nenhum - nao e travamento."""
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoEmperrado()
    )

    assert not gravador.travou(pr, 90, time.time())
