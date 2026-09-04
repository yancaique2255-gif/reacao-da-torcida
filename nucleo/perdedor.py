"""Quem perdeu, e quais canais entram no video por causa disso.

Gravamos os dois lados e publicamos so o lado que perdeu: a graca e a reacao de
quem se frustrou, e reacao de vencedor nao rende. Isto aqui e so aritmetica em
cima do que ja esta no catalogo - placar da partida e torcida de cada clipe.

O padrao e o perdedor; a troca e sempre possivel. E uma sugestao, nao uma trava:
quem manda e quem esta olhando.
"""
from dataclasses import dataclass

from nucleo import canais

# Onde a escolha do operador mora no catalogo. O painel escreve "rindo do:".
CAMPO = "rindo_de"


@dataclass(frozen=True)
class Alvo:
    """De que torcida e o video."""

    torcida: str  # normalizada; vazia quando ninguem decidiu ainda
    time: str     # o nome como a partida escreve, para a tela mostrar
    motivo: str   # "perdeu", "empate", "escolha do operador" ou "sem placar"

    @property
    def decidido(self) -> bool:
        return bool(self.torcida)


def combina(torcida: str, time: str) -> bool:
    """"inter" e "Internacional" sao a mesma gente.

    A torcida do canal e um apelido curto e o nome do time vem da ESPN por
    extenso. Sem acento e sem grafia exata, um cabe dentro do outro - o mesmo
    truque que `placar.achar` usa para casar os nomes da partida.
    """
    um = canais.normalizar_torcida(torcida)
    outro = canais.normalizar_torcida(time)
    if not um or not outro:
        return False
    return um in outro or outro in um


def quem_perdeu(
    mandante: str, visitante: str, gols_mandante: int, gols_visitante: int
) -> str:
    """O time que perdeu. Vazio no empate, porque empate nao tem perdedor."""
    if gols_mandante > gols_visitante:
        return visitante
    if gols_visitante > gols_mandante:
        return mandante
    return ""


def alvo(dados: dict) -> Alvo:
    """A torcida de quem entra no video: a escolha do operador, ou o perdedor."""
    partida = dados.get("partida") or {}

    escolhida = canais.normalizar_torcida(dados.get(CAMPO))
    if escolhida:
        return Alvo(escolhida, _time_da_torcida(escolhida, partida), "escolha do operador")

    if "gols_mandante" not in partida or "gols_visitante" not in partida:
        return Alvo("", "", "sem placar")

    time = quem_perdeu(
        partida.get("mandante", ""), partida.get("visitante", ""),
        partida["gols_mandante"], partida["gols_visitante"],
    )
    if not time:
        return Alvo("", "", "empate")
    return Alvo(_torcida_do_time(time, dados), time, "perdeu")


def escolher(dados: dict, torcida: str) -> dict:
    """Grava a escolha do operador. Vazio apaga e devolve a decisao ao placar."""
    limpa = canais.normalizar_torcida(torcida)
    if limpa:
        dados[CAMPO] = limpa
    else:
        dados.pop(CAMPO, None)
    return dados


def entram(dados: dict) -> list[dict]:
    """Os clipes que vao para o video, do mais explosivo para o mais morno.

    Neutro e vazio ficam de fora: o primeiro nao tem lado para se frustrar, o
    segundo ninguem preencheu. O vazio nao some da tela por causa disso -
    `sem_torcida` diz quem e, e o painel mostra em vermelho.
    """
    escolhida = alvo(dados).torcida
    if not escolhida or escolhida == canais.NEUTRO:
        return []
    dentro = [
        clipe
        for clipe in dados.get("clipes", [])
        if _tem_lado(clipe) and combina(clipe["torcida"], escolhida)
    ]
    return sorted(
        dentro,
        key=lambda c: (c["gol"], -float(c.get("confianca_db") or 0.0), c["canal"]),
    )


def sem_torcida(dados: dict) -> list[str]:
    """Os canais que nao dizem de que torcida sao. Nunca sumir calado."""
    return sorted(
        {
            clipe["canal"]
            for clipe in dados.get("clipes", [])
            if not (clipe.get("torcida") or "")
        }
    )


def _tem_lado(clipe: dict) -> bool:
    return (clipe.get("torcida") or "") not in ("", canais.NEUTRO)


def _torcida_do_time(time: str, dados: dict) -> str:
    """O apelido cadastrado daquele time, ou o nome dele normalizado.

    Sem canal gravado daquele lado nao ha apelido para achar; mesmo assim o
    alvo e ele, e nao o vencedor - a tela precisa dizer que o material do
    perdedor nao foi gravado, em vez de trocar de perdedor calada.
    """
    candidatas = sorted({clipe.get("torcida") or "" for clipe in dados.get("clipes", [])})
    for torcida in candidatas:
        if torcida and torcida != canais.NEUTRO and combina(torcida, time):
            return torcida
    return canais.normalizar_torcida(time)


def _time_da_torcida(torcida: str, partida: dict) -> str:
    for nome in (partida.get("mandante", ""), partida.get("visitante", "")):
        if nome and combina(torcida, nome):
            return nome
    return ""
