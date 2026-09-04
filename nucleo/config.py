"""Configuracao do projeto: padroes e sobreposicao pelo arquivo do usuario."""
import json
from pathlib import Path

PADROES = {
    # Disco LOCAL, sempre. O `G:` e o Google Drive: gravar la dispara upload
    # durante o jogo, e o upload disputa a mesma placa de 100 Mbps que baixa as
    # lives. So a compilacao pronta sobe para o Drive.
    "biblioteca": r"C:\REACAO DA TORCIDA",
    "altura_maxima": 720,
    "segundos_antes": 8,
    "segundos_depois": 12,
    "janela_antes": 30,
    "janela_depois": 180,
    "limiar_confianca_db": 6.0,
    "duracao_pedaco": 600,
    "teto_canais": 20,
    "disco_minimo_gb": 60,
    "segundos_entre_conferencias": 20,
    # Vivo mas sem escrever por tanto tempo: derruba e religa.
    "segundos_sem_crescer": 90,
    "max_tentativas": 60,       # nunca abandonar um canal no meio do jogo
    # Canal que baixa mais devagar que o jogo escreve bytes o tempo todo e
    # mesmo assim nao tem o gol no disco. Medido em jogo: saudavel fica em 0,2
    # min de atraso; o quebrado, em 60. Cinco minutos separa os dois com folga.
    "atraso_maximo": 300,
    "carencia_do_arranque": 120,
    "cortes_em_paralelo": 3,    # o corte recodifica; nao adianta passar dos nucleos
    # Canal sem alinhamento confirmado corta com esta margem a mais de cada
    # lado: clipe longo demais o operador apara no estudio, clipe que corta o
    # lance ao meio nao tem conserto. A margem some sozinha conforme os gols
    # vao confirmando o atraso daquele canal.
    "margem_sem_alinhamento": 60,
    "minimo_do_clipe": 15,      # abaixo disso o trecho nao ajuda ninguem
    # Quanto esperar, depois do gol, para o corte automatico rodar. No instante
    # em que o placar muda, os segundos DEPOIS do gol ainda estao sendo
    # baixados - e sao eles que trazem a reacao.
    "espera_para_cortar": 240,
    # Os tres papeis de letra do `docs/DESIGN-DO-VIDEO.md`. Duas das tres sao
    # exatamente o que o sistema da Ollama manda: `ui-sans-serif` no Windows E
    # a Segoe UI, e a Consolas esta nomeada na propria cadeia de fallback do
    # `ui-monospace`. O display e a unica troca: a SF Pro Rounded e da Apple, e
    # a Bahnschrift (DIN 1451) e a letra de placar de estadio - melhor para um
    # video de futebol, e ja vem no Windows.
    # O drawtext no Windows exige fontfile= explicito, senao falha com
    # "Cannot find a valid font".
    "fonte_display": r"C:\Windows\Fonts\bahnschrift.ttf",
    "fonte_sans": r"C:\Windows\Fonts\segoeuib.ttf",
    "fonte_mono": r"C:\Windows\Fonts\consolab.ttf",
    # Herdada: vale para qualquer dos tres papeis que nao exista na maquina.
    # Fonte que nao carrega deixa o texto em letra de sistema - feio, legivel.
    "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
    # Os intermediarios do render sao uma copia inteira do video: 1 a 2 GB por
    # jogo. Passando disto o painel avisa, e o operador limpa quando quiser.
    "teto_cache_gb": 5,
    # A APU encoda: medido nesta maquina, 11x tempo real em 640x360. A
    # qualidade nao serve para o arquivo final, mas para conferir movimento e
    # som numa previa e de sobra.
    "codec_previa": "h264_amf",
    "caminho_ytdlp": r"C:\yt-dlp\yt-dlp.exe",
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
    # Conferido na maquina: o ffprobe NAO mora junto do ffmpeg do C:\yt-dlp.
    "caminho_ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",
}

PADRAO_ARQUIVO = Path(__file__).resolve().parent.parent / "dados" / "config.json"


def carregar(caminho: Path | None = PADRAO_ARQUIVO) -> dict:
    """Devolve os padroes com o arquivo do usuario sobreposto por cima."""
    valores = dict(PADROES)
    if caminho is not None and Path(caminho).is_file():
        do_usuario = json.loads(Path(caminho).read_text(encoding="utf-8"))
        valores.update(do_usuario)
    return valores
