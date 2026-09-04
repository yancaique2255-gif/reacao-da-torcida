"""A ficha do jogo, em texto, para ler no Explorador.

Um mes depois ninguem lembra QUAIS lives entraram num jogo. A informacao esta
no disco - espalhada por um `gravacao.json` dentro de cada canal - mas ninguem
vai abrir seis arquivos json para descobrir. A ficha junta isso numa pagina so.

Nao guarda nada de novo: tudo que ela mostra ja esta gravado em outro lugar.
Apagar `JOGO.md` nao perde informacao nenhuma - `escrever` refaz igual.
"""
import json
from datetime import datetime
from pathlib import Path

from nucleo import catalogo

ARQUIVO = "JOGO.md"
ARQUIVO_INDICE = "JOGOS.md"


def _data_legivel(nome_do_jogo: str) -> str:
    """"2026-09-03 gremio x internacional" -> "03/09/2026"."""
    try:
        return datetime.strptime(nome_do_jogo[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return ""


def _lives(pasta_jogo: Path) -> list[dict]:
    """As lives gravadas, lidas do `gravacao.json` de cada canal."""
    bruto = Path(pasta_jogo) / "bruto"
    if not bruto.is_dir():
        return []
    lives = []
    for pasta in sorted(bruto.iterdir()):
        arquivo = pasta / "gravacao.json"
        if not arquivo.is_file():
            continue
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        lives.append({
            "canal": pasta.name,
            "url": dados.get("url", ""),
            "torcida": dados.get("torcida", ""),
            "sessoes": len(dados.get("sessoes") or []),
        })
    return lives


def lives(pasta_jogo: Path) -> list[dict]:
    """As lives gravadas deste jogo. O bloco de creditos da publicacao sai daqui."""
    return _lives(pasta_jogo)


def montar(pasta_jogo: Path) -> str:
    """A ficha inteira em Markdown."""
    pasta_jogo = Path(pasta_jogo)
    dados = catalogo.carregar(pasta_jogo)
    partida = dados.get("partida") or {}
    lives = _lives(pasta_jogo)

    mandante = partida.get("mandante") or ""
    visitante = partida.get("visitante") or ""
    titulo = f"{mandante} x {visitante}".strip(" x ") or pasta_jogo.name

    linhas = [f"# {titulo}", ""]
    data = _data_legivel(pasta_jogo.name)
    if data:
        linhas.append(f"- **Data:** {data}")
    if partida.get("liga"):
        linhas.append(f"- **Competição:** {partida['liga']}")
    linhas.append(f"- **Pasta:** `{pasta_jogo.name}`")
    linhas.append("")

    linhas += ["## Lives gravadas", ""]
    if lives:
        linhas += ["| Canal | Torcida | Link |", "| --- | --- | --- |"]
        for live in lives:
            # Canal que caiu e religou tem mais de uma sessao: dizer isso aqui
            # evita a duvida de por que o bruto dele esta partido em dois.
            marca = f" _(religou {live['sessoes']}x)_" if live["sessoes"] > 1 else ""
            linhas.append(
                f"| {live['canal']}{marca} | {live['torcida'] or '—'} | {live['url']} |"
            )
    else:
        linhas.append("Nenhuma live gravada nesta pasta.")
    linhas.append("")

    linhas += ["## Gols", ""]
    gols = dados.get("gols") or []
    if gols:
        linhas += ["| # | Horário | Clipes |", "| --- | --- | --- |"]
        for gol in sorted(gols, key=lambda g: g["numero"]):
            quantos = sum(
                1 for c in dados.get("clipes", []) if c.get("gol") == gol["numero"]
            )
            linhas.append(
                f"| {gol['numero']} | {gol['horario'][11:19]} | "
                f"{quantos} de {len(lives)} |"
            )
    else:
        linhas.append("Nenhum gol anotado.")
    linhas.append("")

    return "\n".join(linhas)


def escrever(pasta_jogo: Path) -> Path:
    """Grava a ficha na pasta do jogo, sempre por cima da anterior."""
    destino = Path(pasta_jogo) / ARQUIVO
    destino.write_text(montar(pasta_jogo), encoding="utf-8")
    return destino


def jogos(biblioteca: Path) -> list[Path]:
    """As pastas de jogo da biblioteca, da mais nova para a mais velha.

    Quem tem `bruto` dentro e jogo. E o mesmo criterio do `monitor.panorama`:
    assim `CONTATO`, `ensaios` e o que mais o operador guardar ali ficam de fora
    sem precisar de lista de excecao.
    """
    raiz = Path(biblioteca)
    if not raiz.is_dir():
        return []
    return [
        pasta for pasta in sorted(raiz.iterdir(), reverse=True)
        if pasta.is_dir() and (pasta / "bruto").is_dir()
    ]


def montar_indice(biblioteca: Path) -> str:
    """Uma linha por jogo - o arquivo de tudo, visto do Explorador."""
    linhas = ["# Jogos gravados", ""]
    encontrados = jogos(biblioteca)
    if not encontrados:
        linhas.append("Nenhum jogo gravado ainda.")
        return "\n".join(linhas) + "\n"

    linhas += ["| Data | Jogo | Lives | Gols | Pasta |", "| --- | --- | --- | --- | --- |"]
    for pasta in encontrados:
        dados = catalogo.carregar(pasta)
        partida = dados.get("partida") or {}
        titulo = (
            f"{partida.get('mandante', '')} x {partida.get('visitante', '')}".strip(" x ")
            or pasta.name[11:]
        )
        linhas.append(
            f"| {_data_legivel(pasta.name) or '—'} | {titulo} | "
            f"{len(_lives(pasta))} | {len(dados.get('gols') or [])} | "
            f"[{pasta.name}](<{pasta.name}/{ARQUIVO}>) |"
        )
    linhas.append("")
    return "\n".join(linhas)


def escrever_indice(biblioteca: Path) -> Path:
    destino = Path(biblioteca) / ARQUIVO_INDICE
    destino.write_text(montar_indice(biblioteca), encoding="utf-8")
    return destino
