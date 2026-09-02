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
