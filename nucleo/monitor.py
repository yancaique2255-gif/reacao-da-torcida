"""Janela de acompanhamento da gravacao: so le o disco, nunca mexe em nada.

A gravacao roda sem janela. Sem isto, a unica forma de saber se um canal caiu
era abrir a pasta e reparar no tamanho dos arquivos.
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from nucleo import config

PARADO_APOS = 20  # segundos sem escrever ja e sinal de canal caido


def estado_do_canal(pasta: Path, agora: float) -> dict:
    """Le do disco o que da para saber de um canal, sem perguntar a ninguem."""
    arquivo = pasta / "gravacao.json"
    sessoes = 0
    if arquivo.is_file():
        sessoes = len(json.loads(arquivo.read_text(encoding="utf-8"))["sessoes"])
    pedacos = list(pasta.glob("*.ts"))
    tamanho = sum(p.stat().st_size for p in pedacos)
    ultima = max((p.stat().st_mtime for p in pedacos), default=0.0)
    return {
        "canal": pasta.name,
        "mb": tamanho / 1e6,
        "sessoes": sessoes,
        "silencio": int(agora - ultima) if ultima else -1,
        "gravando": bool(ultima) and (agora - ultima) < PARADO_APOS,
    }


def estados(pasta_bruto: Path, agora: float) -> list[dict]:
    if not pasta_bruto.is_dir():
        return []
    canais = [d for d in sorted(pasta_bruto.iterdir()) if d.is_dir()]
    return [estado_do_canal(d, agora) for d in canais]


def linhas(pasta_bruto: Path, agora: float) -> list[str]:
    """O quadro inteiro em texto, pronto para imprimir."""
    tudo = estados(pasta_bruto, agora)
    if not tudo:
        return ["Nenhuma gravacao ainda em " + str(pasta_bruto)]

    vivos = [e for e in tudo if e["gravando"]]
    saida = [
        f"{'CANAL':<38} {'MB':>7}  {'SESSOES':>7}  SITUACAO",
        "-" * 74,
    ]
    for e in sorted(tudo, key=lambda x: (not x["gravando"], -x["mb"])):
        if e["gravando"]:
            situacao = "gravando"
        elif e["silencio"] < 0:
            situacao = "sem nada no disco"
        else:
            situacao = f"PARADO ha {e['silencio']}s"
        saida.append(
            f"{e['canal']:<38} {e['mb']:7.0f}  {e['sessoes']:>7}  {situacao}"
        )
    total = sum(e["mb"] for e in tudo)
    saida.append("-" * 74)
    saida.append(
        f"{len(vivos)} de {len(tudo)} gravando   |   {total:.0f} MB no disco   |   "
        f"{datetime.fromtimestamp(agora):%H:%M:%S}"
    )
    return saida


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Acompanha a gravacao em andamento.")
    p.add_argument("jogo")
    p.add_argument("--segundos", type=int, default=5)
    args = p.parse_args(argv)
    cfg = config.carregar()
    bruto = Path(cfg["biblioteca"]) / args.jogo / "bruto"

    print("Esta janela so olha. Fechar aqui NAO para a gravacao.\n")
    while True:
        quadro = linhas(bruto, time.time())
        print("\033[H\033[J", end="")  # limpa sem piscar
        print("REACAO DA TORCIDA - " + args.jogo)
        print("Esta janela so olha. Fechar aqui NAO para a gravacao.\n")
        print("\n".join(quadro))
        time.sleep(args.segundos)


if __name__ == "__main__":
    raise SystemExit(main())
