"""O relógio do jogo como referência comum entre a ESPN e cada live.

A ideia é do operador, e é melhor do que alinhar os canais entre si: quase toda
transmissão mostra o cronômetro da partida na tela. Se a ESPN diz que o jogo
está em 12:53 e a live mostra 12:59, aquela live está seis segundos adiantada -
e isso se mede a qualquer momento, sem esperar um gol acontecer.

Alinhar contra a ESPN dá uma referência ABSOLUTA. O consenso de áudio só dava
uma referência relativa: os canais concordavam entre si, mas todos podiam estar
deslocados juntos.
"""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

SEGUNDOS_POR_TEMPO = 45 * 60  # o segundo tempo começa em 45:00 do relógio corrido
TETO_DA_ESPN = 5400.0         # 90:00; daí para cima a ESPN trava e só o texto cresce


@dataclass(frozen=True)
class Ancora:
    """Num instante de relógio, a tela do canal mostrava este segundo de jogo."""
    quando: datetime
    segundo_de_jogo: float


def segundos_do_texto(texto: str, tempo: int = 0) -> float | None:
    """Lê o cronômetro em qualquer das formas que aparecem na tela.

    Aceita "35:22", "2T 35:22", "81'", "90'+7'". O `tempo` (1 ou 2) diz de que
    metade veio um "MM:SS" solto; um prefixo "2T" no texto manda nele.

    Devolve segundos corridos de jogo, contando o segundo tempo a partir de
    45:00 - que é como a ESPN conta.
    """
    if not texto:
        return None
    limpo = texto.strip().lower().replace("º", "").replace("°", "")

    prefixo = re.match(r"^([12])\s*[t]\b", limpo)
    if prefixo:
        tempo = int(prefixo.group(1))
        limpo = limpo[prefixo.end():].strip()

    # Formato da ESPN: 81'  ou  90'+7'
    acrescimo = re.fullmatch(r"(\d{1,3})'?\s*\+\s*(\d{1,2})'?", limpo)
    if acrescimo:
        return (int(acrescimo.group(1)) + int(acrescimo.group(2))) * 60.0
    minuto_seco = re.fullmatch(r"(\d{1,3})'", limpo)
    if minuto_seco:
        return int(minuto_seco.group(1)) * 60.0

    # Formato da tela: MM:SS
    relogio = re.fullmatch(r"(\d{1,3})[:.](\d{1,2})", limpo)
    if not relogio:
        return None
    minutos, segundos = int(relogio.group(1)), int(relogio.group(2))
    if segundos >= 60:
        return None
    corridos = minutos * 60.0 + segundos
    if tempo == 2:
        # A tela do canal costuma zerar no intervalo; a ESPN não zera.
        corridos += SEGUNDOS_POR_TEMPO
    return corridos


def segundos_da_espn(valor: float | None, texto: str) -> float | None:
    """O segundo de jogo segundo a ESPN, preferindo o número ao texto.

    `value` é exato (4810.0 = 80:10) enquanto `displayValue` arredonda para o
    minuto de cima ("81'"). Mas no acréscimo a ESPN trava o número em 5400 e só
    o texto continua andando, e aí é o texto que vale.
    """
    do_texto = segundos_do_texto(texto)
    travado = valor is not None and valor >= TETO_DA_ESPN
    if valor is not None and not travado:
        return float(valor)
    return do_texto


def atraso(segundos_espn: float, segundos_do_canal: float) -> float:
    """Quantos segundos este canal mostra o jogo depois da ESPN.

    Positivo: a live está atrasada e a reação aparece nela mais tarde - é o
    valor a somar ao horário do gol. Negativo: a live está adiantada.
    """
    return round(segundos_espn - segundos_do_canal, 2)


def ancora_da_espn(agora: datetime, segundos_de_jogo: float) -> Ancora:
    return Ancora(quando=agora, segundo_de_jogo=float(segundos_de_jogo))


def momento_do_minuto(ancora: Ancora, segundo_de_jogo: float) -> datetime:
    """Que hora de relógio corresponde a um dado segundo de jogo.

    Só vale dentro da mesma metade da partida: entre a âncora e o alvo não pode
    ter passado o intervalo, senão os quinze minutos de descanso entrariam na
    conta como se fossem jogo.
    """
    return ancora.quando + timedelta(
        seconds=segundo_de_jogo - ancora.segundo_de_jogo
    )


def mesma_metade(um: float, outro: float) -> bool:
    """Os dois segundos de jogo estão do mesmo lado do intervalo?"""
    return (um >= SEGUNDOS_POR_TEMPO) == (outro >= SEGUNDOS_POR_TEMPO)
