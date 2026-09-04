"""Tudo o que o operador escolheu, num arquivo so, na pasta do jogo.

A receita e a ponte entre o catalogo (o que o disco tem) e o estudio (o que vai
virar video). Ela tem tres propriedades, e as tres sao promessas ao operador:

1. **Nasce sozinha.** Na primeira vez e derivada do catalogo: entram os canais
   da torcida que perdeu, na ordem da forca da reacao, com o corte que o
   `melhor` propos. Abrir o painel ja da um video montavel.
2. **A escolha dele ganha.** Recortar o jogo de novo nao desfaz o que ele
   mexeu: item tocado fica marcado, e o que esta marcado nao se re-deriva.
3. **Grava na hora.** Cada clique escreve o arquivo antes de a tela mudar.

Apagar a `receita.json` e seguro: ela volta ao padrao. Nao se perde gravacao,
so se perde a edicao.
"""
import json
from pathlib import Path

from nucleo import melhor, perdedor

NOME = "receita.json"
FORMATO_PADRAO = "deitado"
DURACAO_POR_CLIPE = 60.0
# Quanto dura cada clipe em cada formato. No deitado o operador ajusta entre 45
# e 90; no em pe sao 20s, que e o que faz caber uns seis canais em ~2 min.
DURACAO_DO_FORMATO = {"deitado": 60.0, "em-pe": 20.0}
# O curto tem ~2 min: Shorts aceita ate 3, mas a graca do formato e ser curto.
# Marcar dez clipes de 20s daria um "curto" de 3:20 sem ninguem perceber.
TETO_DO_CURTO = 120.0
TETO_DO_FORMATO = {"em-pe": TETO_DO_CURTO}
MARGEM = 0.05
CAMPOS_DO_OPERADOR = ("entra", "de", "ate", "ordem")
TEXTOS_DO_OPERADOR = ("titulo", "gancho", "frase_da_capa")


def caminho(pasta_jogo: Path) -> Path:
    return Path(pasta_jogo) / NOME


def padrao(
    dados: dict,
    formato: str = FORMATO_PADRAO,
    duracao_por_clipe: float = DURACAO_POR_CLIPE,
) -> dict:
    """A receita derivada do catalogo, sem nada que o operador tenha tocado.

    Os clipes da torcida alvo entram marcados, na ordem da forca da reacao. Os
    outros ficam na lista desmarcados - nunca sumir calado vale aqui tambem: o
    canal do vencedor e o canal sem torcida aparecem, so que sem marca.
    """
    entram = perdedor.entram(dados)
    dentro = {(c["gol"], c["canal"]) for c in entram}
    restantes = sorted(
        (c for c in dados.get("clipes", []) if (c["gol"], c["canal"]) not in dentro),
        key=lambda c: (c["gol"], c["canal"]),
    )

    itens = []
    for ordem, clipe in enumerate(list(entram) + restantes, start=1):
        de, ate = melhor.janela_do_clipe(clipe, duracao_por_clipe)
        itens.append({
            "gol": clipe["gol"],
            "canal": clipe["canal"],
            "entra": (clipe["gol"], clipe["canal"]) in dentro,
            "de": de,
            "ate": ate,
            "ordem": ordem,
            "tocado": False,
        })

    return {
        "formato": formato,
        "torcida_alvo": perdedor.alvo(dados).torcida,
        "molde": {"margem": MARGEM, "duracao_por_clipe": duracao_por_clipe},
        "itens": itens,
        "textos": {"titulo": "", "gancho": "", "frase_da_capa": ""},
    }


def casar(velha: dict, dados: dict) -> dict:
    """Re-deriva do catalogo mantendo o que o operador tocou.

    Clipe novo (gol cortado depois) entra; clipe que sumiu do catalogo (gol
    marcado errado e apagado) sai; item tocado atravessa inteiro, com o corte e
    a marca que ele deixou.
    """
    molde_velho = velha.get("molde") or {}
    nova = padrao(
        dados,
        velha.get("formato", FORMATO_PADRAO),
        molde_velho.get("duracao_por_clipe", DURACAO_POR_CLIPE),
    )
    tocados = {
        (i["gol"], i["canal"]): i for i in velha.get("itens", []) if i.get("tocado")
    }
    itens = [tocados.get((i["gol"], i["canal"]), i) for i in nova["itens"]]
    itens.sort(key=lambda i: (i["ordem"], i["gol"], i["canal"]))
    nova["itens"] = itens
    nova["textos"] = {**nova["textos"], **(velha.get("textos") or {})}
    return nova


def ajustar(
    dados_receita: dict,
    dados: dict,
    formato: str | None = None,
    duracao_por_clipe: float | None = None,
) -> dict:
    """Troca o formato ou a duracao por clipe e recalcula o que ninguem tocou.

    Trocar de deitado para em pe nao e so outro enquadramento: e outra duracao,
    porque o curto tem ~2 min no total. Quem foi tocado atravessa igual - o
    operador escolheu aquele trecho olhando a cara do sujeito, e isso nao muda
    porque o video virou de lado.
    """
    novo = dict(dados_receita)
    if formato:
        novo["formato"] = formato
        if duracao_por_clipe is None:
            duracao_por_clipe = DURACAO_DO_FORMATO.get(formato, DURACAO_POR_CLIPE)
    if duracao_por_clipe is not None:
        novo["molde"] = {**(novo.get("molde") or {}),
                         "duracao_por_clipe": float(duracao_por_clipe)}
    return _caber_no_teto(casar(novo, dados))


def _caber_no_teto(dados_receita: dict) -> dict:
    """Desmarca o que passa do teto daquele formato, do fim da fila para tras.

    So mexe em quem o operador nao tocou: se ele marcou aquele clipe, e porque
    quer aquele clipe, e o teto e sugestao como todo o resto aqui.
    """
    teto = TETO_DO_FORMATO.get(dados_receita.get("formato", ""))
    if not teto:
        return dados_receita
    gasto = 0.0
    for item in itens_do_video(dados_receita):
        duracao = item["ate"] - item["de"]
        if gasto + duracao <= teto or item.get("tocado"):
            gasto += duracao
        else:
            item["entra"] = False
    return dados_receita


def carregar(pasta_jogo: Path, dados: dict) -> dict:
    """A receita do disco, sempre casada com o catalogo de agora.

    Sem arquivo, o padrao - e por isso apagar e seguro.
    """
    arquivo = caminho(pasta_jogo)
    if not arquivo.is_file():
        return padrao(dados)
    return casar(json.loads(arquivo.read_text(encoding="utf-8")), dados)


def salvar(pasta_jogo: Path, dados_receita: dict) -> Path:
    Path(pasta_jogo).mkdir(parents=True, exist_ok=True)
    arquivo = caminho(pasta_jogo)
    arquivo.write_text(
        json.dumps(dados_receita, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return arquivo


def mexer(dados_receita: dict, gol: int, canal: str, **campos) -> dict:
    """Muda um item e marca que foi o operador. So ele marca `tocado`."""
    desconhecidos = sorted(set(campos) - set(CAMPOS_DO_OPERADOR))
    if desconhecidos:
        raise KeyError(
            f"a receita nao tem os campos {', '.join(desconhecidos)} - "
            f"o operador mexe em {', '.join(CAMPOS_DO_OPERADOR)}"
        )
    for item in dados_receita.get("itens", []):
        if item["gol"] == gol and item["canal"] == canal:
            item.update(campos)
            item["tocado"] = True
            return dados_receita
    raise KeyError(f"a receita nao tem o gol {gol} do canal {canal}")


def esquecer_canal(dados_receita: dict, canal: str) -> dict:
    """Desfaz o `tocado` dos itens de um canal, para eles se re-derivarem.

    Serve para uma coisa so: quando o LADO daquele canal muda. O operador marcou
    aquele clipe acreditando que o canal era da outra torcida, e item tocado
    atravessa inteiro - com a marca que ele deixou. Sem isto, trocar a torcida
    de um canal deixava os clipes dele no video, calado.

    Foi o que aconteceu em 03/09: o `farid-germano-filho` estava cadastrado como
    `inter`, e e canal do Gremio.
    """
    for item in dados_receita.get("itens", []):
        if item["canal"] == canal:
            item["tocado"] = False
    return dados_receita


def definir_textos(dados_receita: dict, **textos) -> dict:
    """O gancho e a frase da capa, que sao escolha do operador.

    Moram com a edicao e nao no catalogo: sao opiniao sobre o jogo, e nao fato
    do jogo. Apagar a receita apaga junto, e e o que se espera.
    """
    desconhecidos = sorted(set(textos) - set(TEXTOS_DO_OPERADOR))
    if desconhecidos:
        raise KeyError(
            f"a receita nao tem os textos {', '.join(desconhecidos)} - "
            f"os que existem sao {', '.join(TEXTOS_DO_OPERADOR)}"
        )
    dados_receita["textos"] = {**(dados_receita.get("textos") or {}), **textos}
    return dados_receita


def itens_do_video(dados_receita: dict) -> list[dict]:
    """So o que entra, na ordem que vai virar video."""
    return sorted(
        (i for i in dados_receita.get("itens", []) if i.get("entra")),
        key=lambda i: (i["ordem"], i["gol"], i["canal"]),
    )
