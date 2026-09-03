"""Transforma uma lista de URLs coladas em cadastro de canais.

O operador acha as lives no YouTube e cola os enderecos. Digitar o nome de
cada canal a mao depois disso e trabalho repetido - e e onde nasciam os nomes
errados, com acento quebrado, que viravam nome de pasta para sempre.
"""
import json
import subprocess
from pathlib import Path
from typing import Callable

TEMPO_LIMITE = 120


def _rodar(comando: list[str]) -> str:
    """Sempre UTF-8: sem isto o yt-dlp escreve na pagina de codigo do console.

    Medido nesta maquina: "Diario do Peixe" voltava como bytes cp1252 e virava
    pasta "dirio-do-peixe", porque o acento se perdia antes do apelido.
    """
    try:
        r = subprocess.run(comando, capture_output=True, timeout=TEMPO_LIMITE)
    except (subprocess.SubprocessError, OSError):
        return ""
    return (r.stdout or b"").decode("utf-8", errors="replace")


def descrever(
    url: str, ytdlp: str, rodar: Callable[[list[str]], str] = _rodar
) -> tuple[str, str]:
    """(nome do canal, situacao da live). Nome vazio quando nao deu para ler."""
    saida = rodar([
        ytdlp, "--no-warnings", "--encoding", "UTF-8", "--skip-download",
        "--print", "%(channel)s|%(live_status)s", url,
    ])
    for linha in saida.splitlines():
        linha = linha.strip()
        if not linha or "|" not in linha or linha.startswith(("WARNING", "ERROR")):
            continue
        nome, situacao = linha.rsplit("|", 1)
        if nome.strip():
            return nome.strip(), situacao.strip()
    return "", ""


def importar(
    urls: list[str], ytdlp: str, torcida: str = "",
    rodar: Callable[[list[str]], str] = _rodar, avisar=print,
) -> list[dict]:
    """Cada URL vira uma entrada de cadastro, com o nome que o YouTube diz."""
    canais = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        nome, situacao = descrever(url, ytdlp, rodar)
        if not nome:
            avisar(f"nao consegui ler {url} - pulando")
            continue
        avisar(f"  {situacao or 'sem situacao':<12} {nome}")
        canais.append({
            "nome": nome, "url": url, "ativo": True, "torcida": torcida,
        })
    return canais


def juntar(cadastro: dict, chave: str, novos: list[dict]) -> dict:
    """Acrescenta sem duplicar: mesma URL ja cadastrada nao entra de novo.

    Acrescentar e nao substituir e o que deixa cadastrar um time de cada vez,
    com a torcida certa em cada lote.
    """
    lista = list(cadastro.get(chave, []))
    ja_tem = {c["url"] for c in lista}
    lista.extend(c for c in novos if c["url"] not in ja_tem)
    return {**cadastro, chave: lista}


def carregar_cru(arquivo: Path) -> dict:
    caminho = Path(arquivo)
    if not caminho.is_file():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def salvar(arquivo: Path, cadastro: dict) -> None:
    Path(arquivo).write_text(
        json.dumps(cadastro, ensure_ascii=False, indent=2), encoding="utf-8"
    )
