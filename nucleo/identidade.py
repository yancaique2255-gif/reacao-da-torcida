"""A identidade do canal: o que veste TODO video, e nao um jogo.

Um arquivo por instalacao. O palco e a camada de marca - fundo com a arte do
canal, logo num canto, faixa de redes no alto - e isso e estilo da casa, nao
escolha de jogo.

**Campo vazio e camada que NAO EXISTE.** Nao e camada transparente, nao e
espaco reservado: o PIL simplesmente nao desenha. Com o arquivo recem-criado, o
video sai identico ao de hoje, e e assim que isto entra em producao sem susto.

A moldagem - arranjo, escala e deslocamento - mora aqui porque e do canal. O
jogo pode desviar, num campo `moldagem` opcional da receita, e a tela marca
quando isso acontece: o padrao e um so, e sair dele e permitido, nunca por
acidente.
"""
import json
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "dados" / "identidade.json"

# A ordem daqui e a ordem em que os @s aparecem na barra do palco.
REDES = ("youtube", "instagram", "tiktok", "facebook")
CAMPOS_DA_MOLDAGEM = ("arranjo", "escala", "deslocamento")

# Acima de 1,00 a janela fica maior que os 1280x720 da fonte e o ffmpeg volta a
# esticar o 720p - o esticao de 1,35x que o palco existe para acabar. Abaixo de
# 0,60 nao se ve mais a cara de ninguem, que e o conteudo do canal.
ESCALA_MINIMA = 0.60
ESCALA_MAXIMA = 1.00
# 0,15 de 1080 = 162px para cada lado. Mais do que isso empurra a janela para
# fora do palco em qualquer arranjo.
DESLOCAMENTO_MAXIMO = 0.15

PADROES = {
    "arranjo": "quadro-cheio",
    "escala": 1.0,
    "deslocamento": 0.0,
    "arte_de_fundo": "",
    "logo": "",
    "redes": {rede: "" for rede in REDES},
    "chamada": "INSCREVA-SE E DEIXE UM LIKE!",
}


def carregar(caminho: Path | None = None) -> dict:
    """Os padroes com o arquivo do usuario sobreposto por cima.

    O caminho e resolvido AQUI, e nao no valor padrao do parametro: valor padrao
    e amarrado na importacao, e ai trocar `ARQUIVO` no teste nao teria efeito -
    a bateria escreveria na identidade real da maquina.
    """
    valores = {**PADROES, "redes": dict(PADROES["redes"])}
    arquivo = Path(ARQUIVO if caminho is None else caminho)
    if not arquivo.is_file():
        return valores
    do_disco = json.loads(arquivo.read_text(encoding="utf-8"))
    valores.update({c: v for c, v in do_disco.items() if c != "redes"})
    valores["redes"] = {**valores["redes"], **(do_disco.get("redes") or {})}
    return valores


def salvar(valores: dict, caminho: Path | None = None) -> Path:
    conferir(valores)
    arquivo = Path(ARQUIVO if caminho is None else caminho)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(
        json.dumps(valores, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return arquivo


def mexer(valores: dict, **campos) -> dict:
    """Sobrepoe campo a campo e confere antes de devolver.

    `redes` se mescla em vez de trocar: gravar o @ do TikTok nao pode apagar o
    do YouTube que ja estava la.
    """
    novas = campos.pop("redes", None) or {}
    novos = {**valores, "redes": {**(valores.get("redes") or {}), **novas}}
    novos.update(campos)
    conferir(novos)
    return novos


def conferir(valores: dict) -> None:
    """A trava da seccao 3 do desenho, com o motivo dentro do recado.

    Recusar sem explicar ensina o operador a tentar numeros ate um passar. O
    recado diz o numero, o limite e por que o limite existe.
    """
    escala = float(valores.get("escala", 1.0))
    if escala > ESCALA_MAXIMA:
        raise ValueError(
            f"escala {escala:g} estica o clipe: a fonte e 720p e na escala 1,00 "
            f"a janela ja mede 1280x720 cravado. Acima disso o ffmpeg reamostra "
            f"e a imagem so borra - use de {ESCALA_MINIMA:g} a {ESCALA_MAXIMA:g}."
        )
    if escala < ESCALA_MINIMA:
        raise ValueError(
            f"escala {escala:g} deixa a janela pequena demais para se ver a cara "
            f"de alguem - use de {ESCALA_MINIMA:g} a {ESCALA_MAXIMA:g}."
        )
    deslocamento = float(valores.get("deslocamento", 0.0))
    if abs(deslocamento) > DESLOCAMENTO_MAXIMO:
        raise ValueError(
            f"deslocamento {deslocamento:g} joga a janela para fora do palco - o "
            f"limite e {DESLOCAMENTO_MAXIMO:g} para cada lado, que da 162px."
        )


def moldagem(
    valores: dict, dados_receita: dict | None = None, formato: str | None = None
) -> dict:
    """Arranjo, escala e deslocamento JA RESOLVIDOS para aquele jogo.

    O desvio da receita sobrepoe campo a campo; ausente - que e o normal - vale
    o padrao do canal. Quem chama isto nao precisa saber de onde veio cada
    numero, e e por isso que a assinatura do palco pode levar o resultado.

    Com o `formato` na mao, arranjo que nao existe naquele formato cai no padrao
    dele: o canal escolhe `palco-lateral` para o deitado e manda montar um 9:16,
    e o em-pe so tem `quadro-cheio`. Sem esta queda o render morre no meio do
    jogo, e a escolha nem era do operador - e o formato que nao tem o arranjo.
    """
    from nucleo import molde
    resolvida = {
        campo: valores.get(campo, PADROES[campo]) for campo in CAMPOS_DA_MOLDAGEM
    }
    resolvida.update({
        campo: valor
        for campo, valor in ((dados_receita or {}).get("moldagem") or {}).items()
        if campo in CAMPOS_DA_MOLDAGEM
    })
    if formato and resolvida["arranjo"] not in molde.arranjos(formato):
        resolvida["arranjo"] = molde.ARRANJO_PADRAO
    resolvida["escala"] = float(resolvida["escala"])
    resolvida["deslocamento"] = float(resolvida["deslocamento"])
    conferir(resolvida)
    return resolvida


def desviou(dados_receita: dict | None) -> bool:
    """Se este jogo sai do padrao do canal. A tela marca quando sai."""
    return bool((dados_receita or {}).get("moldagem"))
