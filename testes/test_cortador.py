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
