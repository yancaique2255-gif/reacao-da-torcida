"""Descobre quanto cada canal atrasa em relacao aos outros, pelo grito do gol.

Cada live transmite o jogo com o seu proprio atraso - encoder, plataforma, o
tempo que o apresentador leva para reagir. Dois canais podem estar gravando
perfeitamente e mostrar o mesmo gol com meio minuto de diferenca.

Isso e invisivel para qualquer medida de disco; so o conteudo revela. E a
medida cai de graca no colo: quando sai um gol, todo canal que o transmite
explode, e a diferenca entre os picos E o atraso entre eles.
"""
from dataclasses import dataclass
from statistics import median

MINIMO_PARA_CONSENSO = 2  # um canal sozinho nao tem com quem concordar
ESPALHAMENTO_SUSPEITO = 45.0  # segundos entre o primeiro e o ultimo pico


@dataclass(frozen=True)
class Consenso:
    referencia: float               # instante tido como o do gol
    deslocamentos: dict[str, float] # canal -> segundos a somar
    espalhamento: float             # do pico mais cedo ao mais tarde
    participantes: list[str]        # quem explodiu o bastante para ter voto
    confiavel: bool


def _com_voto(picos: dict[str, tuple[float, float]], limiar_db: float) -> dict:
    """So vota quem explodiu. Canal que nao reagiu nao opina sobre quando foi."""
    return {
        canal: instante
        for canal, (instante, forca) in picos.items()
        if forca >= limiar_db
    }


def medir(
    picos: dict[str, tuple[float, float]], limiar_db: float = 6.0
) -> Consenso | None:
    """picos: canal -> (instante em segundos, forca em dB). None se nao houver consenso.

    A referencia e a MEDIANA dos instantes, nunca a media. Caso real de
    02/09/2026: tres canais acusaram o mesmo gol em 23:11:49, 23:12:45 e
    23:12:47 - o primeiro ficou 56s fora, e a media teria ido atras dele.
    """
    votos = _com_voto(picos, limiar_db)
    if len(votos) < MINIMO_PARA_CONSENSO:
        return None  # sem consenso nao se inventa deslocamento

    instantes = sorted(votos.values())
    referencia = float(median(instantes))
    espalhamento = instantes[-1] - instantes[0]
    return Consenso(
        referencia=referencia,
        deslocamentos={c: round(i - referencia, 2) for c, i in votos.items()},
        espalhamento=round(espalhamento, 2),
        participantes=sorted(votos),
        confiavel=espalhamento <= ESPALHAMENTO_SUSPEITO,
    )


def combinar(antigo: float | None, novo: float, peso_do_antigo: int = 1) -> float:
    """Junta a estimativa nova com a que ja existia. Cada gol melhora a media."""
    if antigo is None:
        return round(novo, 2)
    total = peso_do_antigo + 1
    return round((antigo * peso_do_antigo + novo) / total, 2)


def aplicar(deslocamentos: dict[str, float], canal: str, momento: float) -> float:
    """Onde procurar a reacao deste canal. Canal sem medida fica no horario cru."""
    return momento + deslocamentos.get(canal, 0.0)
