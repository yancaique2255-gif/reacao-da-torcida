"""Descobre quanto cada canal atrasa em relacao aos outros, pelo grito do gol.

Cada live transmite o jogo com o seu proprio atraso - encoder, plataforma, o
tempo que o apresentador leva para reagir. Dois canais podem estar gravando
perfeitamente e mostrar o mesmo gol com meio minuto de diferenca.

Isso e invisivel para qualquer medida de disco; so o conteudo revela. E a
medida cai de graca no colo: quando sai um gol, todo canal que o transmite
explode, e a diferenca entre os picos E o atraso entre eles.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

from nucleo import cortador, detector, relogio

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


# Janela de BUSCA, bem mais larga que a do corte: ela precisa conter o pico
# mesmo com o canal dessincronizado. Nao tem relacao com o tamanho do clipe.
BUSCA_ANTES = 90
BUSCA_DEPOIS = 120


def pico_do_canal(
    pasta_canal: Path, sessoes, momento: datetime, cfg: dict, executar=None
) -> tuple[float, float] | None:
    """(instante em segundos desde `momento`, forca em dB). None se nao deu.

    Devolve o instante RELATIVO ao horario procurado, para o consenso comparar
    canais sem se importar com o relogio de cada um.
    """
    executar = executar or cortador.executar
    inicio = momento - timedelta(seconds=BUSCA_ANTES)
    fim = momento + timedelta(seconds=BUSCA_DEPOIS)
    recortes = relogio.trechos(sessoes, inicio, fim)
    if not recortes:
        return None

    pasta_canal = Path(pasta_canal)
    temporaria = pasta_canal / "busca-alinhamento.ts"
    wav = pasta_canal / "busca-alinhamento.wav"
    try:
        fonte, deslocamento = cortador.preparar_fonte(
            recortes, pasta_canal, temporaria, cfg["caminho_ffmpeg"], executar
        )
        duracao = sum(t.fim - t.inicio for t in recortes)
        executar(
            cortador.comando_audio(
                fonte, deslocamento, duracao, wav, cfg["caminho_ffmpeg"]
            )
        )
        achado = detector.analisar(wav, cfg["limiar_confianca_db"])
    except Exception:
        return None  # medir e um extra: falhar aqui nao pode custar o corte
    finally:
        for arquivo in (temporaria, temporaria.with_suffix(".txt"), wav):
            arquivo.unlink(missing_ok=True)

    # `achado.instante` conta do inicio da janela; o consenso quer a distancia
    # ate o horario marcado, que pode ser negativa.
    return achado.instante - BUSCA_ANTES, achado.confianca_db


def picos_do_gol(
    por_canal: dict, pasta_bruto: Path, momento: datetime, cfg: dict, executar=None
) -> dict[str, tuple[float, float]]:
    """Mede todos os canais do jogo ao mesmo tempo. Quem falhar fica de fora."""
    trabalhadores = max(1, min(cfg.get("cortes_em_paralelo", 3), len(por_canal) or 1))
    picos = {}
    with ThreadPoolExecutor(max_workers=trabalhadores) as equipe:
        futuros = {
            equipe.submit(
                pico_do_canal, Path(pasta_bruto) / nome, sessoes, momento, cfg, executar
            ): nome
            for nome, sessoes in por_canal.items()
        }
        for futuro, nome in futuros.items():
            try:
                medida = futuro.result()
            except Exception:
                medida = None
            if medida is not None:
                picos[nome] = medida
    return picos
