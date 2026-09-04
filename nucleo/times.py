"""O dicionario dos times: como cada torcida se chama e de que cor ela e.

E o que veste o video e a capa. Sem ele, o titulo diria "REAÇÕES do
INTERNACIONAL" onde o canal de referencia diz "REAÇÕES dos COLORADOS" - e a
diferenca entre as duas frases e a diferenca entre parecer do ramo e parecer
robo.

Comeca com os times que o operador grava e cresce conforme aparecem. Time que
nao esta aqui nao quebra nada e nao ganha apelido inventado: usa o proprio nome
e a cor neutra.
"""
import json
from pathlib import Path

from nucleo import perdedor

ARQUIVO = Path(__file__).resolve().parent.parent / "dados" / "times.json"
COR_NEUTRA = "#101418"


def carregar(caminho: Path = ARQUIVO) -> dict:
    arquivo = Path(caminho)
    if not arquivo.is_file():
        return {}
    return json.loads(arquivo.read_text(encoding="utf-8"))


def achar(nome_ou_torcida: str, cadastrados: dict | None = None) -> dict:
    """A ficha do time, pelo nome por extenso ou pelo apelido da torcida.

    "inter" e "Internacional" chegam aqui pelos dois lados: o cadastro dos
    canais guarda o apelido curto e a ESPN responde o nome por extenso.
    """
    cadastrados = carregar() if cadastrados is None else cadastrados
    procurado = nome_ou_torcida or ""
    for chave, ficha in cadastrados.items():
        candidatos = [chave, ficha.get("nome", ""), ficha.get("torcida", "")]
        if any(perdedor.combina(procurado, c) for c in candidatos if c):
            return {**_vazio(procurado), **ficha}
    return _vazio(procurado)


def _vazio(nome: str) -> dict:
    return {
        "nome": nome,
        "torcida": "",
        "apelido": "",   # "COLORADOS" - como a torcida se chama
        "adjetivo": "",  # "COLORADAS" - o que vai na capa
        "curto": nome.upper(),
        "cor": COR_NEUTRA,
        "escudo": "",
    }
