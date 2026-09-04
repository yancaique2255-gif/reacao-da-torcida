"""Dado um clipe e uma duracao alvo, qual e a melhor janela.

Nao abre video, nao chama ffmpeg, nao toca em disco: recebe uma curva de
numeros e devolve dois numeros. A curva vem do `detector.curva_db`, que ja
existe e ja e testado.

O corte que sai daqui e um ponto de partida, nao uma sentenca: ele chega no
painel como duas alcas que o operador arrasta. E a diferenca entre uma maquina
que ajuda e uma maquina que decide.
"""
import numpy as np

# Onde o pico cai dentro da janela. Um terco de subida, dois tercos de reacao:
# ver a cara do sujeito ANTES da explosao e o que faz a explosao ter graca.
FRACAO_ANTES = 0.35


def janela(
    curva_db, quadro_s: float, duracao_alvo: float, tem_pico: bool
) -> tuple[float, float]:
    """(inicio, fim) em segundos, sempre dentro do clipe.

    Duas estrategias, escolhidas pelo `tem_pico` que o detector ja decidiu:
    com pico, a janela se posiciona pelo pico; sem pico, nao houve grito e o
    melhor palpite e o trecho de maior energia media.
    """
    curva = np.asarray(curva_db, dtype=float)
    total = len(curva) * quadro_s
    if duracao_alvo <= 0 or total <= duracao_alvo:
        return (0.0, round(total, 3))

    if tem_pico:
        inicio = int(np.argmax(curva)) * quadro_s - FRACAO_ANTES * duracao_alvo
    else:
        inicio = _maior_energia(curva, quadro_s, duracao_alvo)
    return _presa(inicio, duracao_alvo, total)


def janela_do_clipe(clipe: dict, duracao_alvo: float) -> tuple[float, float]:
    """A mesma janela, tirada do que o catalogo ja sabe do clipe.

    O detector rodou uma vez e gravou `instante`, `confianca_db` e `tem_pico`
    em cada clipe. Para propor o corte no painel nao ha por que abrir o audio
    de novo - e sao dezenas de clipes por jogo.

    Sem a curva nao da para procurar o trecho de maior energia, entao clipe sem
    pico usa o mesmo instante: e o maior movimento que o detector achou, e o
    painel ja marca esse clipe como fraco.
    """
    duracao = float(clipe.get("duracao") or 0.0)
    inicio = float(clipe.get("instante") or 0.0) - FRACAO_ANTES * duracao_alvo
    if duracao <= 0:
        # Clipe cortado antes de o catalogo anotar duracao: da para nao comecar
        # antes do zero, nao da para saber onde e o fim. Prender no que se sabe.
        return (round(max(0.0, inicio), 3), round(max(0.0, inicio) + duracao_alvo, 3))
    if duracao <= duracao_alvo:
        return (0.0, round(duracao, 3))
    return _presa(inicio, duracao_alvo, duracao)


def _presa(inicio: float, duracao_alvo: float, total: float) -> tuple[float, float]:
    """Nunca comeca antes de zero, nunca termina depois do fim do clipe."""
    inicio = min(max(0.0, inicio), total - duracao_alvo)
    return (round(inicio, 3), round(inicio + duracao_alvo, 3))


def _maior_energia(curva: np.ndarray, quadro_s: float, duracao_alvo: float) -> float:
    """Comeco da janela de maior media, deslizando quadro a quadro.

    Media dos decibeis, e nao da energia linear: a maquina nao tem GPU e a conta
    tem que ser aritmetica simples, como no resto do detector.
    """
    largura = max(1, int(round(duracao_alvo / quadro_s)))
    if largura >= len(curva):
        return 0.0
    somas = np.cumsum(np.insert(curva, 0, 0.0))
    medias = somas[largura:] - somas[:-largura]
    return int(np.argmax(medias)) * quadro_s
