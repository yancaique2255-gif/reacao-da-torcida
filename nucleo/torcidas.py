"""De que torcida e cada canal - no cadastro, na gravacao e no catalogo.

O estudio de edicao publica so o lado que perdeu, e para isso precisa saber de
que torcida e cada live. O campo existia desde o comeco, mas era opcional: no
primeiro jogo de verdade tres dos seis canais ficaram em branco, entre eles o
`baldasso-tv` - o melhor material da noite, que com a regra ligada sairia do
video por causa de um campo vazio.

Agora o cadastro exige. Este modulo cuida do resto: dizer quem ainda esta em
branco e gravar a resposta nos lugares onde a torcida vive. Sao tres, e cada um
existe por um motivo diferente:

- `dados/canais.json` - a origem. Consertar aqui conserta os proximos jogos.
- `bruto/<canal>/gravacao.json` - o que aquela gravacao registrou. E o que a
  ficha `JOGO.md` le.
- `catalogo.json` - repetido em cada clipe, porque e o que o painel le.
"""
import json
from pathlib import Path

from nucleo import canais as mod_canais
from nucleo import catalogo, ficha, gravador, importar


def gravadas(pasta_jogo: Path) -> dict[str, str]:
    """Canal (nome da pasta) -> torcida anotada. Vazio quando falta."""
    bruto = Path(pasta_jogo) / "bruto"
    if not bruto.is_dir():
        return {}
    achadas = {}
    for pasta in sorted(bruto.iterdir()):
        arquivo = pasta / "gravacao.json"
        if not arquivo.is_file():
            continue
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        achadas[pasta.name] = mod_canais.normalizar_torcida(dados.get("torcida"))
    return achadas


def em_branco(pasta_jogo: Path) -> list[str]:
    """Os canais gravados que ainda nao dizem de que torcida sao."""
    return [nome for nome, torcida in gravadas(pasta_jogo).items() if not torcida]


def do_cadastro(cadastro: dict[str, list[mod_canais.Canal]]) -> dict[str, str]:
    """Apelido do canal -> torcida, juntando todos os times do cadastro.

    O apelido e o que virou nome de pasta na hora de gravar; e por ele que se
    casa o cadastro com o que esta no disco. A URL nao serve de chave: quando a
    live cai e volta outra, o religador troca o endereco no meio do jogo.
    """
    return {
        gravador.apelido(canal.nome): canal.torcida
        for lista in cadastro.values()
        for canal in lista
        if canal.torcida
    }


def aplicar(pasta_jogo: Path, definicoes: dict[str, str], avisar=print) -> list[str]:
    """Grava a torcida na gravacao do canal E em cada clipe dele no catalogo.

    Os dois arquivos porque sao duas leituras do mesmo fato: a ficha do jogo le
    a gravacao, o painel le o catalogo. Consertar so um deixa a tela mentindo
    sobre o disco.

    Tudo ou nada: canal que nao existe neste jogo derruba a chamada inteira
    antes de escrever qualquer coisa. Metade aplicado e pior que nada aplicado,
    porque ninguem sabe qual metade.
    """
    pasta_jogo = Path(pasta_jogo)
    limpas = {
        canal: mod_canais.exigir_torcida(torcida)
        for canal, torcida in definicoes.items()
    }
    desconhecidos = sorted(set(limpas) - set(gravadas(pasta_jogo)))
    if desconhecidos:
        raise KeyError(
            f"nao ha gravacao destes canais em {pasta_jogo.name}: "
            + ", ".join(desconhecidos)
        )
    if not limpas:
        return []

    bruto = pasta_jogo / "bruto"
    for canal, torcida in limpas.items():
        arquivo = bruto / canal / "gravacao.json"
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        dados["torcida"] = torcida
        arquivo.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    dados = catalogo.carregar(pasta_jogo)
    for clipe in dados.get("clipes", []):
        if clipe.get("canal") in limpas:
            clipe["torcida"] = limpas[clipe["canal"]]
    catalogo.salvar(pasta_jogo, dados)

    # A ficha e derivada: refazer e barato e a deixa sempre igual ao disco.
    # Falhar aqui nao pode custar o conserto, que ja esta gravado.
    try:
        ficha.escrever(pasta_jogo)
        ficha.escrever_indice(pasta_jogo.parent)
    except Exception as erro:
        avisar(f"nao deu para atualizar a ficha do jogo: {erro}")
    return sorted(limpas)


def definir_no_cadastro(arquivo: Path, definicoes: dict[str, str]) -> list[str]:
    """Escreve a torcida no cadastro, casando pelo apelido do nome do canal.

    Sem isto o buraco volta no proximo jogo: o cadastro e a origem e a gravacao
    so copia o que ele diz. Consertar o jogo conserta um jogo; consertar o
    cadastro conserta todos os proximos.
    """
    cru = importar.carregar_cru(arquivo)
    mexidos = []
    for time, lista in cru.items():
        for entrada in lista:
            apelidado = gravador.apelido(entrada.get("nome", ""))
            if apelidado not in definicoes:
                continue
            nova = mod_canais.normalizar_torcida(definicoes[apelidado])
            if mod_canais.normalizar_torcida(entrada.get("torcida")) == nova:
                continue
            entrada["torcida"] = nova
            mexidos.append(f"{time}/{apelidado}")
    if mexidos:
        importar.salvar(arquivo, cru)
    return sorted(mexidos)
