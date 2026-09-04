"""A capa e metade do clique no YouTube.

Um video bom com capa fraca rende menos que um video medio com capa forte, e por
isso ela entra nesta rodada. Os rostos saem dos proprios clipes, no instante do
pico - que e onde a cara esta mais expressiva, e e justamente o numero que o
detector ja guardou.
"""
from pathlib import Path

import pytest
from PIL import Image

from nucleo import capa, catalogo, receita

CFG = {
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
    "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
}
TIMES = {
    "internacional": {
        "nome": "Internacional", "torcida": "inter", "apelido": "COLORADOS",
        "adjetivo": "COLORADAS", "curto": "INTER", "cor": "#c8102e", "escudo": "",
    },
    "gremio": {
        "nome": "Grêmio", "torcida": "gremio", "apelido": "GREMISTAS",
        "adjetivo": "GREMISTAS", "curto": "GRÊMIO", "cor": "#0d80bf", "escudo": "",
    },
}


def _jogo(pasta: Path) -> dict:
    dados = catalogo.registrar_partida(
        catalogo.novo(pasta.name), "Copa do Brasil", "Grêmio", "Internacional"
    )
    dados = catalogo.registrar_placar(dados, 3, 1)
    dados = catalogo.registrar_gol(dados, 1, "2026-09-03T20:13:00", "")
    for canal, db in [("baldasso-tv", 15.2), ("paulo-brito", 7.8)]:
        dados = catalogo.registrar_clipe(
            dados, 1, canal, f"clipes/gol-01/{canal}.mp4", 100.0, db, True, "inter", 175.0
        )
    catalogo.salvar(pasta, dados)
    return dados


class Rostos:
    """ffmpeg de mentira: escreve um quadro verde no lugar do rosto."""

    def __init__(self):
        self.comandos = []

    def __call__(self, comando):
        self.comandos.append(comando)
        Path(comando[-1]).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (640, 360), (0, 200, 0)).save(comando[-1])


def test_a_capa_sai_no_tamanho_do_youtube(tmp_path: Path):
    dados = _jogo(tmp_path)

    arquivo = capa.gerar(
        tmp_path, dados, receita.padrao(dados), CFG, TIMES, executar=Rostos()
    )

    assert arquivo.name == "capa.jpg"
    assert Image.open(arquivo).size == capa.TAMANHO


def test_o_rosto_e_o_quadro_do_pico(tmp_path: Path):
    """O instante do pico e onde a cara esta mais expressiva - e o detector ja sabe."""
    dados = _jogo(tmp_path)
    executor = Rostos()

    capa.gerar(tmp_path, dados, receita.padrao(dados), CFG, TIMES, executar=executor)

    assert "-ss" in executor.comandos[0]
    assert "100.0" in executor.comandos[0]


def test_o_fundo_e_da_cor_de_quem_perdeu(tmp_path: Path):
    """A capa veste a torcida que vai rir de si mesma, e nao a do vencedor."""
    dados = _jogo(tmp_path)

    arquivo = capa.gerar(
        tmp_path, dados, receita.padrao(dados), CFG, TIMES, executar=Rostos()
    )

    canto = Image.open(arquivo).convert("RGB").getpixel((640, 8))
    assert canto[0] > canto[2], f"o vermelho do Inter nao apareceu: {canto}"


def test_os_rostos_entram_na_capa(tmp_path: Path):
    dados = _jogo(tmp_path)

    arquivo = capa.gerar(
        tmp_path, dados, receita.padrao(dados), CFG, TIMES, executar=Rostos()
    )

    imagem = Image.open(arquivo).convert("RGB")
    ponto = capa.caixas(2)[0]
    meio = imagem.getpixel((ponto[0] + ponto[2] // 2, ponto[1] + ponto[3] // 2))
    assert meio[1] > meio[0] and meio[1] > meio[2], f"o rosto nao foi colado: {meio}"


def test_sem_clipe_nenhum_a_capa_ainda_sai(tmp_path: Path):
    """Nunca sumir calado: sem rosto ela sai mesmo assim, para o operador ver."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    for item in list(feita["itens"]):
        feita = receita.mexer(feita, item["gol"], item["canal"], entra=False)

    arquivo = capa.gerar(tmp_path, dados, feita, CFG, TIMES, executar=Rostos())

    assert Image.open(arquivo).size == capa.TAMANHO


def test_a_frase_longa_encolhe_ate_caber(tmp_path: Path):
    """PIL sabe medir texto, e por isso a capa nunca corta a frase na borda."""
    curta = capa.fonte_que_cabe("VERGONHA!", 1200, 64, Path(CFG["fonte_cartela"]))
    longa = capa.fonte_que_cabe(
        "VERGONHA! INTER ELIMINADO DA COPA DO BRASIL PELO MAIOR RIVAL EM CASA",
        1200, 64, Path(CFG["fonte_cartela"]),
    )

    assert curta == 64
    assert longa < 64


def test_o_rosto_de_cada_canal_e_reaproveitado(tmp_path: Path):
    """Regerar a capa nao pode reextrair quadro que ja esta no disco."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    capa.gerar(tmp_path, dados, feita, CFG, TIMES, executar=Rostos())

    depois = Rostos()
    capa.gerar(tmp_path, dados, feita, CFG, TIMES, executar=depois)

    assert depois.comandos == []


# ------------------------------------------------ a capa se adapta a quantos vem

def _area(caixa) -> int:
    return caixa[2] * caixa[3]


def _cruzam(a, b) -> bool:
    return (
        a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
        and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    )


@pytest.mark.parametrize("quantos", [1, 2, 3, 4, 5])
def test_a_grade_de_rostos_tem_uma_caixa_por_rosto(quantos):
    assert len(capa.caixas(quantos)) == quantos


@pytest.mark.parametrize("quantos", [1, 2, 3, 4, 5])
def test_as_caixas_nao_se_cruzam_e_nao_saem_da_regiao(quantos):
    regiao = capa.REGIAO
    for indice, caixa in enumerate(capa.caixas(quantos)):
        assert caixa[0] >= regiao[0] and caixa[1] >= regiao[1], caixa
        assert caixa[0] + caixa[2] <= regiao[0] + regiao[2], caixa
        assert caixa[1] + caixa[3] <= regiao[1] + regiao[3], caixa
        for outra in capa.caixas(quantos)[indice + 1:]:
            assert not _cruzam(caixa, outra), f"{caixa} cruza {outra}"


@pytest.mark.parametrize("quantos", [1, 2, 3, 4, 5])
def test_a_grade_nao_deixa_buraco(quantos):
    """Tres canais num layout de cinco deixavam um quadrante vermelho vazio.

    Foi o que aconteceu no jogo de 03/09: `CAIXAS` era fixo em 1 rosto grande
    mais 4 pequenos, entraram tres, e a composicao saiu torta com um buraco
    embaixo a direita.
    """
    ocupado = sum(_area(c) for c in capa.caixas(quantos))

    assert ocupado >= 0.92 * _area(capa.REGIAO), (
        f"{quantos} rosto(s) cobrem so {ocupado / _area(capa.REGIAO):.0%} da regiao"
    )


def test_com_tres_canais_nenhum_quadrante_fica_vazio(tmp_path: Path):
    """A prova em pixel: o quadro verde de mentira tem de estar nas tres caixas."""
    dados = _jogo(tmp_path)
    dados = catalogo.registrar_clipe(
        dados, 1, "farid-germano-filho", "clipes/gol-01/farid-germano-filho.mp4",
        100.0, 12.0, True, "inter", 175.0,
    )
    catalogo.salvar(tmp_path, dados)

    arquivo = capa.gerar(
        tmp_path, dados, receita.padrao(dados), CFG, TIMES, executar=Rostos()
    )

    imagem = Image.open(arquivo).convert("RGB")
    for x, y, largura, altura in capa.caixas(3):
        ponto = imagem.getpixel((x + largura // 2, y + altura // 2))
        assert ponto[1] > ponto[0] and ponto[1] > ponto[2], (
            f"a caixa em {x},{y} ficou sem rosto: {ponto}"
        )
