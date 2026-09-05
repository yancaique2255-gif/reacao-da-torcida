"""O acervo: todos os jogos da biblioteca e em que pé cada um está.

O estúdio nasceu para um jogo só. A pasta era escolhida no terminal, na
largada, e trocar de jogo era fechar a janela e abrir de novo - com dois jogos
no disco isso já não se sustenta, e uma semana depois ninguém lembra qual dos
dois ficou com gol sem clipe escolhido.

Nada aqui é informação nova: tudo o que este módulo diz já está gravado no
`catalogo.json`, no `receita.json`, no `render.json` e no que existe dentro de
`saida`. É leitura, e só leitura - a recepção não escreve nada em disco.
"""
from datetime import datetime
from pathlib import Path

from nucleo import catalogo, estudio, ficha, monitor, perdedor, receita

ETAPAS = {
    "gravando": "gravando agora",
    "vazio": "sem gol anotado",
    "cortar": "falta cortar",
    "escolher": "falta escolher",
    "editar": "pronto para editar",
    "renderizando": "renderizando",
    "pronto": "vídeo pronto",
    "erro": "não deu para ler",
}

# As etapas que ainda pedem o operador. Serve à recepção para achar por onde
# continuar: jogo gravando não é trabalho de estúdio, e jogo pronto acabou.
TRABALHO = ("cortar", "escolher", "editar")


def video(
    pasta_jogo: Path, assinatura_agora: str = "", assinatura_do_render: str = ""
) -> dict:
    """O vídeo que já saiu deste jogo, se saiu.

    Vale o mais novo de `saida`: o `compilacao.mp4` da montagem simples e o
    `compilacao-deitado.mp4` do render podem coexistir na mesma pasta.

    "Vencido" é o mp4 que não corresponde mais à edição de agora, e quem diz
    isso é a assinatura que o render gravou - não o mtime dos arquivos. A tela
    de edição regrava a receita cada vez que abre, e por mtime todo vídeo
    parecia velho um minuto depois de sair. Render antigo, de antes da
    assinatura existir, não afirma nada: aviso falso ensina a ignorar aviso.
    """
    saida = Path(pasta_jogo) / "saida"
    if not saida.is_dir():
        return {}
    achados = sorted(saida.glob("compilacao*.mp4"), key=lambda a: a.stat().st_mtime)
    if not achados:
        return {}
    arquivo = achados[-1]
    return {
        "arquivo": str(arquivo),
        "nome": arquivo.name,
        "gb": round(arquivo.stat().st_size / 1024 ** 3, 2),
        "quando": datetime.fromtimestamp(
            arquivo.stat().st_mtime
        ).strftime("%d/%m %H:%M"),
        "vencido": bool(assinatura_do_render)
        and assinatura_do_render != assinatura_agora,
        "capa": (saida / "capa.jpg").is_file(),
        "publicar": (saida / "publicar.md").is_file(),
    }


def faltas(dados: dict, canais_gravados: list[str]) -> list[dict]:
    """Os pares gol × canal que não têm clipe nenhum. Nunca sumir calado.

    Canal que gravou o jogo e não tem clipe daquele gol precisa aparecer
    marcado. Se sai da lista, ninguém repara que faltou material.
    """
    tem = {(c["gol"], c["canal"]) for c in dados.get("clipes") or []}
    return [
        {"gol": gol["numero"], "canal": canal}
        for gol in sorted(dados.get("gols") or [], key=lambda g: g["numero"])
        for canal in canais_gravados
        if (gol["numero"], canal) not in tem
    ]


def etapa(resumo_do_jogo: dict) -> str:
    """Em que pé o jogo está: o primeiro degrau ainda não vencido.

    A ordem é a da esteira, de propósito - assim a recepção aponta o próximo
    trabalho, e não o último feito.
    """
    r = resumo_do_jogo
    if r["lives"]["gravando"]:
        return "gravando"
    if not r["gols"]:
        return "vazio"
    if not r["clipes"]["total"] or r["gols_sem_clipe"]:
        return "cortar"
    if not r["clipes"]["escolhidos"]:
        return "escolher"
    if r["render"].get("rodando"):
        return "renderizando"
    if r["video"] and not r["video"]["vencido"]:
        return "pronto"
    return "editar"


def _plural(quantos: int, um: str, muitos: str) -> str:
    return f"{quantos} {um if quantos == 1 else muitos}"


def pendencias(resumo_do_jogo: dict) -> list[dict]:
    """O que falta neste jogo, escrito. Cor sozinha não diz o que fazer.

    O tom é o vocabulário do DESIGN.md: "parou" trava o vídeo, "confira" deixa
    passar mas merece olhada, "vivo" está acontecendo agora.
    """
    r = resumo_do_jogo
    lista = []

    if r["lives"]["gravando"]:
        lista.append({"tom": "vivo", "texto":
                      f"{r['lives']['gravando']} de {r['lives']['total']} lives "
                      "gravando agora - o estúdio espera o fim do jogo"})
    if not r["gols"]:
        lista.append({"tom": "confira", "texto":
                      "nenhum gol anotado: quem marca é o painel da gravação"})
    if r["gols_sem_clipe"]:
        numeros = ", ".join(str(n) for n in r["gols_sem_clipe"])
        lista.append({"tom": "parou", "texto":
                      f"gol {numeros} sem clipe nenhum: falta cortar"})
    if r["sem_torcida"]:
        lista.append({"tom": "parou", "texto":
                      _plural(len(r["sem_torcida"]), "canal", "canais") +
                      " sem torcida (" + ", ".join(r["sem_torcida"]) + "): "
                      "sem isso ficam de fora do vídeo"})
    if r["alvo"]["motivo"] in ("sem placar", "empate"):
        lista.append({"tom": "confira", "texto":
                      f"o vídeo não tem lado ({r['alvo']['motivo']}): "
                      "escolha a torcida na edição"})
    if r["clipes"]["indecisos"]:
        lista.append({"tom": "confira", "texto":
                      _plural(r["clipes"]["indecisos"], "clipe", "clipes") +
                      " sem decisão: nem usado, nem descartado"})
    if r["faltando"]:
        lista.append({"tom": "confira", "texto":
                      _plural(r["faltando"], "vez", "vezes") +
                      " em que um canal não tem material do gol"})
    if r["clipes"]["parciais"]:
        lista.append({"tom": "confira", "texto":
                      _plural(r["clipes"]["parciais"], "clipe", "clipes") +
                      " com cobertura parcial: veio o que existia no disco"})
    render = r["render"]
    if (not render.get("rodando") and render.get("mensagem")
            and render.get("feito", 0) < render.get("total", 0)):
        lista.append({"tom": "parou", "texto":
                      f"o render parou no meio: {render['mensagem']}"})
    if r["video"] and r["video"]["vencido"]:
        lista.append({"tom": "confira", "texto":
                      "a edição mudou depois do vídeo: renderize de novo"})
    if r["cache_gb"] and r["cache_gb"] > r["teto_cache_gb"]:
        lista.append({"tom": "confira", "texto":
                      f"{r['cache_gb']:.1f} GB de intermediários no disco, "
                      f"acima do teto de {r['teto_cache_gb']} GB"})
    return lista


def _canais_do_jogo(pasta_jogo: Path, dados: dict, agora: float) -> list[dict]:
    """Uma linha por live gravada, com o que ela rendeu de clipe.

    Duas fontes, porque nenhuma das duas basta sozinha: o `monitor` lista as
    pastas de canal (inclusive a do canal que morreu antes de escrever o
    manifesto) e a `ficha` sabe o link e a torcida de cada um.
    """
    ao_vivo = {
        c["canal"]: c
        for c in monitor.estados(Path(pasta_jogo) / "bruto", agora)
    }
    fichas = {live["canal"]: live for live in ficha.lives(pasta_jogo)}
    clipes = dados.get("clipes") or []

    canais = []
    for nome in sorted(set(ao_vivo) | set(fichas)):
        do_canal = [c for c in clipes if c["canal"] == nome]
        medidas = [float(c.get("confianca_db") or 0.0) for c in do_canal]
        canais.append({
            "canal": nome,
            "torcida": fichas.get(nome, {}).get("torcida", ""),
            "url": fichas.get(nome, {}).get("url", ""),
            "sessoes": fichas.get(nome, {}).get("sessoes", 0),
            "gravando": ao_vivo.get(nome, {}).get("gravando", False),
            "mb": round(ao_vivo.get(nome, {}).get("mb", 0.0), 1),
            "clipes": len(do_canal),
            "escolhidos": sum(1 for c in do_canal if c.get("escolhido") is True),
            "db": round(sum(medidas) / len(medidas), 1) if medidas else 0.0,
        })
    return canais


def resumo(pasta_jogo: Path, agora: float, cfg: dict, vivo=None) -> dict:
    """Um jogo inteiro numa resposta: identidade, contagem, etapa e pendência."""
    pasta_jogo = Path(pasta_jogo)
    dados = catalogo.carregar(pasta_jogo)
    partida = dados.get("partida") or {}
    gols = sorted(dados.get("gols") or [], key=lambda g: g["numero"])
    clipes = dados.get("clipes") or []
    canais = _canais_do_jogo(pasta_jogo, dados, agora)
    com_clipe = {c["gol"] for c in clipes}
    alvo = perdedor.alvo(dados)
    edicao = receita.carregar(pasta_jogo, dados)
    no_video = receita.itens_do_video(edicao)
    render = estudio.estado(pasta_jogo, vivo=vivo)

    placar = ""
    if "gols_mandante" in partida and "gols_visitante" in partida:
        placar = f"{partida['gols_mandante']} x {partida['gols_visitante']}"

    resumo_do_jogo = {
        "pasta": pasta_jogo.name,
        "titulo": ficha.titulo(dados) or pasta_jogo.name[11:] or pasta_jogo.name,
        "data": ficha.data_legivel(pasta_jogo.name),
        "liga": partida.get("liga", ""),
        "placar": placar,
        "alvo": {"torcida": alvo.torcida, "time": alvo.time, "motivo": alvo.motivo},
        "lives": {
            "total": len(canais),
            "gravando": sum(1 for c in canais if c["gravando"]),
            "religaram": sum(1 for c in canais if c["sessoes"] > 1),
        },
        "canais": canais,
        "gols": len(gols),
        "gols_sem_clipe": [g["numero"] for g in gols if g["numero"] not in com_clipe],
        "clipes": {
            "total": len(clipes),
            "escolhidos": sum(1 for c in clipes if c.get("escolhido") is True),
            "descartados": sum(1 for c in clipes if c.get("escolhido") is False),
            "indecisos": sum(1 for c in clipes if c.get("escolhido") is None),
            "parciais": sum(1 for c in clipes if c.get("parcial")),
            "largos": sum(1 for c in clipes if c.get("largo")),
        },
        "faltando": len(faltas(dados, [c["canal"] for c in canais])),
        "sem_torcida": perdedor.sem_torcida(dados),
        "formato": edicao.get("formato", ""),
        "no_video": len(no_video),
        "duracao": round(sum(
            max(0.0, float(i["ate"]) - float(i["de"])) for i in no_video
        ), 1),
        "cache_gb": round(estudio.tamanho_do_cache(pasta_jogo) / 1024 ** 3, 2),
        "teto_cache_gb": cfg.get("teto_cache_gb", 5),
        "video": video(
            pasta_jogo,
            estudio.assinatura(dados, edicao, cfg),
            render.get("assinatura", ""),
        ),
        "render": render,
    }
    resumo_do_jogo["etapa"] = etapa(resumo_do_jogo)
    resumo_do_jogo["etapa_texto"] = ETAPAS[resumo_do_jogo["etapa"]]
    resumo_do_jogo["pendencias"] = pendencias(resumo_do_jogo)
    return resumo_do_jogo


def _quebrado(pasta_jogo: Path, erro: Exception) -> dict:
    """Jogo que não deu para ler aparece na lista, marcado.

    O `except` largo é de propósito: um `catalogo.json` truncado numa pasta não
    pode apagar da tela os outros seis jogos que estão inteiros.
    """
    return {
        "pasta": Path(pasta_jogo).name,
        "titulo": Path(pasta_jogo).name,
        "data": ficha.data_legivel(Path(pasta_jogo).name),
        "etapa": "erro",
        "etapa_texto": ETAPAS["erro"],
        "pendencias": [{"tom": "parou", "texto": f"{type(erro).__name__}: {erro}"}],
    }


def panorama(biblioteca: Path, agora: float, cfg: dict, vivo=None) -> dict:
    """A biblioteca inteira, do jogo mais novo para o mais velho."""
    jogos = []
    for pasta in ficha.jogos(biblioteca):
        try:
            jogos.append(resumo(pasta, agora, cfg, vivo=vivo))
        except Exception as erro:  # noqa: BLE001 - ver _quebrado
            jogos.append(_quebrado(pasta, erro))

    pendentes = [j for j in jogos if j["etapa"] in TRABALHO]
    return {
        "biblioteca": str(biblioteca),
        "jogos": jogos,
        "totais": {
            "jogos": len(jogos),
            "lives": sum(j.get("lives", {}).get("total", 0) for j in jogos),
            "gols": sum(j.get("gols", 0) for j in jogos),
            "prontos": sum(1 for j in jogos if j["etapa"] == "pronto"),
            "pendentes": len(pendentes),
        },
        # Por onde continuar: o jogo mais novo que ainda pede trabalho. É ele
        # que ganha a única pílula preta da recepção.
        "proximo": pendentes[0]["pasta"] if pendentes else "",
    }
