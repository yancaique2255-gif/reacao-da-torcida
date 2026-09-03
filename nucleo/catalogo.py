"""Estado do jogo em disco. Nada vive so na memoria da pagina aberta."""
import json
from pathlib import Path

NOME = "catalogo.json"


def caminho(pasta_jogo: Path) -> Path:
    return Path(pasta_jogo) / NOME


def novo(jogo: str) -> dict:
    return {"jogo": jogo, "gols": [], "clipes": []}


def carregar(pasta_jogo: Path) -> dict:
    arquivo = caminho(pasta_jogo)
    if not arquivo.is_file():
        return novo(Path(pasta_jogo).name)
    return json.loads(arquivo.read_text(encoding="utf-8"))


def salvar(pasta_jogo: Path, dados: dict) -> None:
    Path(pasta_jogo).mkdir(parents=True, exist_ok=True)
    caminho(pasta_jogo).write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def registrar_gol(dados: dict, numero: int, horario: str, descricao: str) -> dict:
    dados["gols"] = [g for g in dados["gols"] if g["numero"] != numero]
    dados["gols"].append(
        {"numero": numero, "horario": horario, "descricao": descricao}
    )
    dados["gols"].sort(key=lambda g: g["numero"])
    return dados


def proximo_numero(dados: dict) -> int:
    """Numero do proximo gol. Nao reaproveita numero de gol apagado.

    Reaproveitar trocaria o dono de uma pasta `gol-03` que ja existe no disco.
    """
    return max((g["numero"] for g in dados["gols"]), default=0) + 1


def remover_gol(dados: dict, numero: int) -> dict:
    """Tira o gol e os clipes dele. Marcar errado no calor do jogo e normal."""
    dados["gols"] = [g for g in dados["gols"] if g["numero"] != numero]
    dados["clipes"] = [c for c in dados["clipes"] if c["gol"] != numero]
    return dados


def mover_gol(dados: dict, numero: int, segundos: float) -> dict:
    """Empurra o horario de um gol para tras ou para frente.

    O dedo vai no botao depois do lance, nunca antes. Acertar em segundos
    depois, olhando o clipe, e mais facil do que acertar no susto.
    """
    from datetime import datetime, timedelta

    for gol in dados["gols"]:
        if gol["numero"] == numero:
            novo = datetime.fromisoformat(gol["horario"]) + timedelta(seconds=segundos)
            gol["horario"] = novo.isoformat(timespec="seconds")
            return dados
    raise KeyError(f"gol {numero} nao existe")


def _achar_clipe(dados: dict, gol: int, canal: str) -> dict | None:
    for clipe in dados["clipes"]:
        if clipe["gol"] == gol and clipe["canal"] == canal:
            return clipe
    return None


def registrar_clipe(
    dados: dict,
    gol: int,
    canal: str,
    arquivo: str,
    instante: float,
    confianca_db: float,
    tem_pico: bool,
) -> dict:
    existente = _achar_clipe(dados, gol, canal)
    campos = {
        "gol": gol,
        "canal": canal,
        "arquivo": arquivo,
        "instante": instante,
        "confianca_db": confianca_db,
        "tem_pico": tem_pico,
    }
    if existente is not None:
        existente.update(campos)
    else:
        dados["clipes"].append({**campos, "escolhido": None})
    return dados


def marcar_escolha(dados: dict, gol: int, canal: str, escolhido: bool) -> dict:
    clipe = _achar_clipe(dados, gol, canal)
    if clipe is None:
        raise KeyError(f"clipe do gol {gol} no canal {canal} nao existe")
    clipe["escolhido"] = escolhido
    return dados


def escolhidos(dados: dict) -> list[dict]:
    marcados = [c for c in dados["clipes"] if c.get("escolhido") is True]
    return sorted(marcados, key=lambda c: (c["gol"], c["canal"]))
