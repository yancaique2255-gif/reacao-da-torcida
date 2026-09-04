"""Titulo, descricao e tags - o `publicar.md` que acompanha o video.

Sai quase de graca porque os dados ja estao no disco: o `JOGO.md` guarda, para
cada live, o canal, a torcida e o link, e o bloco de creditos e um `for` em cima
disso. Nada de novo precisa ser anotado.

Os creditos nao sao opcionais. Publicar reacao de terceiro sem creditar e a
unica parte deste projeto que da problema de verdade, e o canal de referencia
credita cada live com link na descricao. Por isso o bloco e gerado sozinho.

Nao sobe nada: publicar e acao de fora, e acao de fora se confirma.
"""
from pathlib import Path

from nucleo import canais as mod_canais
from nucleo import ficha, gravador, receita, times as mod_times

ARQUIVO = "publicar.md"
PASTA_SAIDA = "saida"


def _lados(dados: dict, dados_receita: dict, cadastrados: dict) -> tuple[dict, dict, dict]:
    """As fichas do mandante, do visitante e de quem perdeu."""
    partida = dados.get("partida") or {}
    mandante = mod_times.achar(partida.get("mandante", ""), cadastrados)
    visitante = mod_times.achar(partida.get("visitante", ""), cadastrados)
    alvo = mod_times.achar(dados_receita.get("torcida_alvo", ""), cadastrados)
    return mandante, visitante, alvo


def titulo(dados: dict, dados_receita: dict, cadastrados: dict | None = None) -> str:
    """O padrao rigido, tirado de vinte videos do canal de referencia.

    `REAÇÕES dos {TORCIDA} - {MANDANTE} {A}x{B} {VISITANTE} - {GANCHO} -
    VAMOS RIR DO {TIME}!`

    Sem apelido cadastrado entra o nome do time: melhor sem graca do que
    inventado.
    """
    cadastrados = mod_times.carregar() if cadastrados is None else cadastrados
    partida = dados.get("partida") or {}
    mandante, visitante, alvo = _lados(dados, dados_receita, cadastrados)

    quem = alvo["apelido"] or alvo["curto"] or alvo["nome"].upper()
    placar = ""
    if "gols_mandante" in partida:
        placar = f"{partida['gols_mandante']}x{partida['gols_visitante']}"
    # O nome por extenso no placar e o curto so no "VAMOS RIR DO": e assim que
    # os videos do canal de referencia escrevem, e o titulo e a primeira coisa
    # que a pessoa le.
    jogo = (
        f"{mandante['nome'].upper()} {placar} {visitante['nome'].upper()}"
    ).replace("  ", " ").strip()

    partes = [f"REAÇÕES dos {quem}", jogo]
    gancho = (dados_receita.get("textos") or {}).get("gancho") or ""
    if gancho:
        partes.append(gancho.upper())
    partes.append(f"VAMOS RIR DO {alvo['curto'] or alvo['nome'].upper()}!")
    return " - ".join(p for p in partes if p)


def creditos(
    pasta_jogo: Path,
    dados: dict,
    dados_receita: dict,
    cadastro: dict | None = None,
) -> list[dict]:
    """Canal, nome de verdade e link de cada live que ENTROU no video.

    So quem entrou: creditar quem nao apareceu e tao errado quanto deixar de
    creditar quem apareceu.

    O nome sai do cadastro e nao da pasta: a pasta se chama `baldasso-tv` e o
    canal se chama "Baldasso TV". O credito e publico, e escrever o apelido de
    pasta seria creditar errado quem emprestou o material.
    """
    if cadastro is None:
        cadastro = mod_canais.carregar(mod_canais.ARQUIVO)
    nomes = {
        gravador.apelido(canal.nome): canal.nome
        for lista in cadastro.values()
        for canal in lista
    }
    entraram = {i["canal"] for i in receita.itens_do_video(dados_receita)}
    vistos = []
    for live in ficha.lives(pasta_jogo):
        if live["canal"] in entraram and live["canal"] not in [c["canal"] for c in vistos]:
            vistos.append({
                "canal": live["canal"],
                "nome": nomes.get(live["canal"], live["canal"]),
                "url": live["url"],
            })
    return vistos


def descricao(
    pasta_jogo: Path, dados: dict, dados_receita: dict, cadastrados: dict | None = None
) -> str:
    cadastrados = mod_times.carregar() if cadastrados is None else cadastrados
    partida = dados.get("partida") or {}
    mandante, visitante, alvo = _lados(dados, dados_receita, cadastrados)

    linhas = [
        f"Reações da torcida do {alvo['nome'] or alvo['curto']} em "
        f"{mandante['nome']} x {visitante['nome']}"
        + (f", pela {partida['liga']}" if partida.get("liga") else "")
        + ".",
        "",
        "Créditos do vídeo:",
    ]
    for credito in creditos(pasta_jogo, dados, dados_receita):
        linhas.append(f"🔗 {credito['nome']} {credito['url']}".rstrip())
    linhas += ["", " ".join(
        hashtag(t) for t in tags(dados, dados_receita, cadastrados)
    )]
    return "\n".join(linhas)


def hashtag(tag: str) -> str:
    """`copa-do-brasil` -> `#copadobrasil`.

    Hashtag com hifen nao funciona no YouTube nem no Instagram: os dois cortam
    a tag no hifen, e o que sobra e `#copa`. O espaco tambem sai, que era o
    unico caso tratado antes.
    """
    limpa = "".join(letra for letra in (tag or "") if letra not in " -_.")
    return f"#{limpa}"


def tags(
    dados: dict, dados_receita: dict, cadastrados: dict | None = None
) -> list[str]:
    cadastrados = mod_times.carregar() if cadastrados is None else cadastrados
    partida = dados.get("partida") or {}
    mandante, visitante, alvo = _lados(dados, dados_receita, cadastrados)

    cruas = [
        "reação da torcida", "reação", "torcida",
        mandante["nome"], visitante["nome"], partida.get("liga", ""),
        alvo["apelido"], alvo["nome"],
    ]
    saida = []
    for tag in cruas:
        limpa = (tag or "").strip().lower()
        if limpa and limpa not in saida:
            saida.append(limpa)
    return saida


def montar(
    pasta_jogo: Path, dados: dict, dados_receita: dict, cadastrados: dict | None = None
) -> str:
    cadastrados = mod_times.carregar() if cadastrados is None else cadastrados
    return "\n".join([
        f"# {Path(pasta_jogo).name}",
        "",
        "## Título",
        "",
        titulo(dados, dados_receita, cadastrados),
        "",
        "## Descrição",
        "",
        descricao(pasta_jogo, dados, dados_receita, cadastrados),
        "",
        "## Tags",
        "",
        ", ".join(tags(dados, dados_receita, cadastrados)),
        "",
    ])


def escrever(
    pasta_jogo: Path, dados: dict, dados_receita: dict, cadastrados: dict | None = None
) -> Path:
    """Grava o `publicar.md` ao lado do video. Copiar e colar e do operador."""
    pasta = Path(pasta_jogo) / PASTA_SAIDA
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / ARQUIVO
    arquivo.write_text(
        montar(pasta_jogo, dados, dados_receita, cadastrados), encoding="utf-8"
    )
    return arquivo
