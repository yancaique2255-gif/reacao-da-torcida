from pathlib import Path

from nucleo import cortador, relogio

FFMPEG = r"C:\yt-dlp\ffmpeg.exe"


def test_comando_de_corte_recodifica_para_ser_preciso():
    cmd = cortador.comando_corte(Path("a.ts"), 100.0, 20.0, Path("saida.mp4"), FFMPEG)
    texto = " ".join(cmd)
    assert cmd[0] == FFMPEG
    assert "-ss" in cmd and "100.0" in cmd
    assert "-t" in cmd and "20.0" in cmd
    assert "libx264" in texto, "corte precisa recodificar, senao pula para o keyframe"
    assert "-c copy" not in texto


def test_comando_de_audio_pede_mono_16k_wav():
    cmd = cortador.comando_audio(Path("a.ts"), 10.0, 30.0, Path("t.wav"), FFMPEG)
    texto = " ".join(cmd)
    assert "-vn" in cmd
    assert "16000" in texto
    assert "-ac" in cmd and "1" in cmd


def test_um_trecho_so_usa_o_arquivo_direto(tmp_path: Path):
    trechos = [relogio.Trecho("parte-000.ts", 100.0, 120.0)]
    chamadas = []

    fonte, deslocamento = cortador.preparar_fonte(
        trechos, tmp_path, tmp_path / "junto.ts", FFMPEG, executar=chamadas.append
    )

    assert fonte == tmp_path / "parte-000.ts"
    assert deslocamento == 100.0
    assert chamadas == [], "com um trecho so nao ha nada a juntar"


def test_dois_trechos_sao_juntados_antes_do_corte(tmp_path: Path):
    trechos = [
        relogio.Trecho("parte-000.ts", 595.0, 600.0),
        relogio.Trecho("parte-001.ts", 0.0, 15.0),
    ]
    chamadas = []

    fonte, deslocamento = cortador.preparar_fonte(
        trechos, tmp_path, tmp_path / "junto.ts", FFMPEG, executar=chamadas.append
    )

    assert fonte == tmp_path / "junto.ts"
    assert deslocamento == 0.0
    assert len(chamadas) == 1
    assert "concat" in " ".join(chamadas[0])


def test_lista_de_concat_nomeia_os_arquivos_na_ordem(tmp_path: Path):
    trechos = [
        relogio.Trecho("parte-000.ts", 595.0, 600.0),
        relogio.Trecho("parte-001.ts", 0.0, 15.0),
    ]
    lista = cortador.escrever_lista_concat(trechos, tmp_path, tmp_path / "lista.txt")
    conteudo = lista.read_text(encoding="utf-8")
    assert conteudo.index("parte-000.ts") < conteudo.index("parte-001.ts")
    assert conteudo.count("file ") == 2
    assert "inpoint 595.0" in conteudo and "outpoint 600.0" in conteudo
    assert "inpoint 0.0" in conteudo and "outpoint 15.0" in conteudo


def test_duracao_le_o_numero_que_o_ffprobe_devolve():
    def rodar_falso(comando):
        assert "ffprobe" in comando[0]
        return "  412.480000\n"

    assert cortador.duracao(Path("a.ts"), "ffprobe", rodar=rodar_falso) == 412.48


def test_duracao_de_arquivo_ilegivel_devolve_zero():
    """Pedaco truncado no fim da gravacao: nao pode estourar."""
    assert cortador.duracao(Path("a.ts"), "ffprobe", rodar=lambda c: "N/A\n") == 0.0


# ---------------------------------------------- o ffmpeg que trava e o que ele diz

import subprocess

import pytest


def test_executar_poe_tempo_limite_no_ffmpeg(monkeypatch):
    """Sem `timeout=`, ffmpeg travado deixa o render esperando para sempre.

    Medido em 03/09: travou com 0% de CPU e ~1,4 GB presos, por 11 minutos, ate
    alguem matar na mao. O painel ficou "rodando" o tempo todo.
    """
    pedidos = {}

    def falso(comando, **kwargs):
        pedidos.update(kwargs)
        return subprocess.CompletedProcess(comando, 0)

    monkeypatch.setattr(cortador.subprocess, "run", falso)
    cortador.executar(["ffmpeg", "-i", "a.ts", "b.mp4"])

    assert pedidos["timeout"] == cortador.TEMPO_LIMITE
    assert pedidos["check"] is True


def test_executar_aceita_outro_tempo_limite(monkeypatch):
    pedidos = {}
    monkeypatch.setattr(
        cortador.subprocess, "run",
        lambda comando, **k: (pedidos.update(k), subprocess.CompletedProcess(comando, 0))[1],
    )

    cortador.executar(["ffmpeg"], timeout=30)

    assert pedidos["timeout"] == 30


def test_o_motivo_mostra_as_ultimas_linhas_do_stderr():
    """O `capture_output` engolia o stderr, e o operador via um traceback de Python."""
    erro = subprocess.CalledProcessError(
        1, ["ffmpeg"],
        stderr=b"\n".join(f"linha {n}".encode() for n in range(1, 21)),
    )

    recado = cortador.motivo(erro)

    assert "linha 20" in recado
    assert "linha 1\n" not in recado, "so as ultimas linhas, senao inunda o console"


def test_o_motivo_de_um_travamento_diz_que_travou():
    erro = subprocess.TimeoutExpired(["ffmpeg"], 900, stderr=b"frame=  120")

    recado = cortador.motivo(erro)

    assert "travou" in recado.lower() and "900" in recado


def test_o_motivo_aguenta_erro_sem_stderr_nenhum():
    assert cortador.motivo(subprocess.CalledProcessError(1, ["ffmpeg"]))


def test_as_falhas_do_ffmpeg_pegam_travamento_e_codigo_de_erro():
    """Quem chama precisa de um `except` so; travar e falhar doem igual."""
    assert subprocess.CalledProcessError in cortador.FALHAS
    assert subprocess.TimeoutExpired in cortador.FALHAS


def test_o_clipe_intermediario_nao_e_espremido(tmp_path: Path):
    """O corte sai a 1,22 Mbps de uma fonte de 2,27, e nao volta mais.

    Medido no jogo de 03/09: 46% perdidos antes de a montagem comecar. O clipe e
    descartavel - existe para revisao e para a montagem consumir - entao
    comprimi-lo e a perda mais barata de evitar que existe. O preco e o dobro de
    disco, temporario.
    """
    comando = cortador.comando_corte(
        tmp_path / "bruto.ts", 10.0, 60.0, tmp_path / "clipe.mp4", "ffmpeg.exe"
    )

    assert comando[comando.index("-crf") + 1] == "16"
