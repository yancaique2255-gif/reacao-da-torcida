"""Descobre quanto cada canal atrasa em relacao aos outros, pelo grito do gol.

Cada live transmite o jogo com o seu proprio atraso - encoder, plataforma, o
tempo que o apresentador leva para reagir. Dois canais podem estar gravando
perfeitamente e mostrar o mesmo gol com meio minuto de diferenca.

Isso e invisivel para qualquer medida de disco; so o conteudo revela. E a
medida cai de graca no colo: quando sai um gol, todo canal que o transmite
explode, e a diferenca entre os picos E o atraso entre eles.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

from nucleo import cortador, detector, relogio

MINIMO_PARA_CONSENSO = 2  # um canal sozinho nao tem com quem concordar
ESPALHAMENTO_SUSPEITO = 45.0  # segundos entre o primeiro e o ultimo pico
# Duas medidas do MESMO canal que discordam mais que isto sao ruido, nao atraso:
# o atraso de um canal nao muda de meio minuto de um gol para o outro.
DISCORDANCIA_MAXIMA = 15.0


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


ARQUIVO_DO_CANAL = "gravacao.json"


def ler_deslocamento(pasta_canal: Path) -> tuple[float, str, list]:
    """(segundos, de onde veio, as medidas cruas que ja entraram)."""
    arquivo = Path(pasta_canal) / ARQUIVO_DO_CANAL
    if not arquivo.is_file():
        return 0.0, "", []
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    return (
        float(dados.get("deslocamento") or 0.0),
        dados.get("deslocamento_de", ""),
        list(dados.get("deslocamento_medidas") or []),
    )


def estavel(medidas: list[float]) -> bool:
    """As medidas deste canal concordam entre si?

    Medido em 02/09/2026: dois canais deram +8,5/+10,0 e +12,5/+11,5 nos dois
    gols - estaveis. Um terceiro deu -54,5 e +29,5, oitenta e quatro segundos
    de diferenca. O atraso de um canal nao muda assim entre dois gols do mesmo
    jogo: aquilo era o detector achando outra coisa no audio, e aplicar aquele
    numero jogou o corte para fora do lance.
    """
    if len(medidas) < 2:
        return False  # uma medida sozinha nao se confirma
    return max(medidas) - min(medidas) <= DISCORDANCIA_MAXIMA


def gravar_deslocamento(
    pasta_canal: Path, segundos: float, origem: str = "consenso"
) -> float:
    """Guarda o deslocamento no arquivo do canal, sem perder o que ja estava la.

    Deslocamento MANUAL vence o de consenso: o operador viu, o algoritmo
    estimou. Uma medida nova nunca sobrescreve o que ele digitou.
    """
    arquivo = Path(pasta_canal) / ARQUIVO_DO_CANAL
    if not arquivo.is_file():
        return 0.0
    dados = json.loads(arquivo.read_text(encoding="utf-8"))

    if origem == "consenso" and dados.get("deslocamento_de") == "manual":
        return float(dados.get("deslocamento") or 0.0)

    if origem == "manual":
        # O operador viu: uma palavra dele basta, sem precisar de confirmacao.
        dados["deslocamento"] = round(float(segundos), 2)
        dados["deslocamento_de"] = "manual"
        dados["deslocamento_medidas"] = []
        arquivo.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return dados["deslocamento"]

    brutas = list(dados.get("deslocamento_medidas") or [])
    brutas.append(round(float(segundos), 2))
    dados["deslocamento_medidas"] = brutas

    if estavel(brutas):
        valor = round(sum(brutas) / len(brutas), 2)
        dados["deslocamento"] = valor
        dados["deslocamento_de"] = "consenso"
    else:
        # Sem confirmacao o canal corta no horario cru, que e o certo: e melhor
        # do que aplicar um numero que pode jogar o clipe para fora do lance.
        valor = 0.0
        dados.pop("deslocamento", None)
        dados["deslocamento_de"] = ""
    arquivo.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return valor


def deslocamentos_do_jogo(pasta_bruto: Path) -> dict[str, float]:
    """O que cada canal do jogo tem guardado. Canal sem medida nao entra."""
    raiz = Path(pasta_bruto)
    if not raiz.is_dir():
        return {}
    achados = {}
    for pasta in sorted(raiz.iterdir()):
        if not pasta.is_dir():
            continue
        valor, origem, _ = ler_deslocamento(pasta)
        if origem:
            achados[pasta.name] = valor
    return achados


def guardar_consenso(
    pasta_bruto: Path, consenso: Consenso, forcar: bool = False
) -> dict[str, float]:
    """Escreve os deslocamentos de um consenso, canal por canal.

    Canal que ficou longe demais da referencia nao entra: num consenso frouxo o
    problema quase nunca e todo mundo, e sim um canal sozinho puxando para
    longe. Descartar o consenso inteiro jogaria fora a medida boa dos outros.

    Devolve so quem de fato ganhou deslocamento aplicavel - lembrando que uma
    medida sozinha ainda nao vale: `gravar_deslocamento` exige confirmacao.

    O operador pode mandar gravar tudo mesmo assim (`forcar`), depois de olhar.
    """
    gravados = {}
    for canal, valor in consenso.deslocamentos.items():
        # Num consenso frouxo, o problema quase nunca e todo mundo: e um canal
        # sozinho puxando para longe. Medido em 02/09/2026 - dois canais
        # concordavam em 4s e o terceiro estava 63s fora. Descartar o consenso
        # inteiro jogaria fora a medida boa dos outros dois.
        if not forcar and abs(valor) > ESPALHAMENTO_SUSPEITO:
            continue
        pasta = Path(pasta_bruto) / canal
        if pasta.is_dir():
            gravar_deslocamento(pasta, valor, "consenso")
            atual, origem, _ = ler_deslocamento(pasta)
            if origem:
                gravados[canal] = atual
    return gravados
