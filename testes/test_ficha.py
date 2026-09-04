"""A ficha do jogo: quem jogou, que lives foram usadas e o que saiu de clipe.

Tudo lido do disco. A ficha nao guarda nada que ja nao esteja gravado - se ela
sumir, um comando a escreve de novo igual.
"""
import json
from pathlib import Path

from nucleo import catalogo, ficha


def _canal(bruto: Path, nome: str, url: str, torcida: str = "") -> None:
    d = bruto / nome
    d.mkdir(parents=True)
    (d / "gravacao.json").write_text(
        json.dumps({
            "url": url,
            "sessoes": [{"numero": 1, "t0": "2026-09-03T20:12:24"}],
            "torcida": torcida,
        }),
        encoding="utf-8",
    )


def _jogo(tmp_path: Path, nome: str = "2026-09-03 gremio x internacional") -> Path:
    pasta = tmp_path / nome
    _canal(pasta / "bruto", "radio-imortal", "https://youtu.be/aaa", "gremio")
    _canal(pasta / "bruto", "paulo-brito", "https://youtu.be/bbb", "inter")
    _canal(pasta / "bruto", "gaucha-esportes", "https://youtu.be/ccc")
    dados = catalogo.registrar_partida(
        catalogo.novo(nome), "copa-do-brasil", "Gremio", "Internacional"
    )
    catalogo.salvar(pasta, dados)
    return pasta


def test_ficha_identifica_o_jogo(tmp_path: Path):
    pasta = _jogo(tmp_path)

    texto = ficha.montar(pasta)

    assert "Gremio x Internacional" in texto
    assert "copa-do-brasil" in texto
    assert "03/09/2026" in texto, "a data sai legivel, nao no formato da pasta"


def test_ficha_traz_o_link_de_cada_live(tmp_path: Path):
    """E o motivo da ficha existir: saber depois QUAIS lives foram gravadas."""
    pasta = _jogo(tmp_path)

    texto = ficha.montar(pasta)

    for url in ("https://youtu.be/aaa", "https://youtu.be/bbb", "https://youtu.be/ccc"):
        assert url in texto
    assert "radio-imortal" in texto and "gremio" in texto


def test_ficha_lista_os_gols_com_quantos_clipes_sairam(tmp_path: Path):
    pasta = _jogo(tmp_path)
    dados = catalogo.carregar(pasta)
    dados = catalogo.registrar_gol(dados, 1, "2026-09-03T20:13:32", "")
    dados = catalogo.registrar_gol(dados, 2, "2026-09-03T20:23:50", "")
    dados = catalogo.registrar_clipe(
        dados, 1, "radio-imortal", "clipes/gol-01/radio-imortal.mp4", 0.0, 3.1, False
    )
    catalogo.salvar(pasta, dados)

    texto = ficha.montar(pasta)

    assert "20:13:32" in texto and "20:23:50" in texto
    assert "1 de 3" in texto, "gol 1 cortou um canal dos tres"
    assert "0 de 3" in texto, "gol 2 nao cortou nenhum ainda"


def test_ficha_de_jogo_sem_gol_nao_estoura(tmp_path: Path):
    pasta = _jogo(tmp_path)

    texto = ficha.montar(pasta)

    assert "nenhum gol" in texto.lower()


def test_escrever_grava_o_arquivo_na_pasta_do_jogo(tmp_path: Path):
    pasta = _jogo(tmp_path)

    destino = ficha.escrever(pasta)

    assert destino == pasta / "JOGO.md"
    assert destino.read_text(encoding="utf-8") == ficha.montar(pasta)


def test_escrever_de_novo_atualiza_em_vez_de_duplicar(tmp_path: Path):
    pasta = _jogo(tmp_path)
    ficha.escrever(pasta)
    dados = catalogo.registrar_gol(
        catalogo.carregar(pasta), 1, "2026-09-03T21:05:00", ""
    )
    catalogo.salvar(pasta, dados)

    texto = ficha.escrever(pasta).read_text(encoding="utf-8")

    titulos = [linha for linha in texto.splitlines() if linha.startswith("# ")]
    assert len(titulos) == 1, "um titulo so: a ficha e reescrita, nao somada"
    assert "21:05:00" in texto


def test_indice_lista_os_jogos_do_mais_novo_para_o_mais_velho(tmp_path: Path):
    _jogo(tmp_path, "2026-09-03 gremio x internacional")
    _jogo(tmp_path, "2026-09-01 santos x palmeiras")

    texto = ficha.montar_indice(tmp_path)

    novo = texto.index("gremio x internacional")
    velho = texto.index("santos x palmeiras")
    assert novo < velho


def test_indice_ignora_pasta_que_nao_e_jogo(tmp_path: Path):
    """Pasta sem `bruto` dentro nao e jogo - CONTATO e ensaios nao entram."""
    _jogo(tmp_path)
    (tmp_path / "CONTATO").mkdir()
    (tmp_path / "ensaios").mkdir()

    texto = ficha.montar_indice(tmp_path)

    assert "CONTATO" not in texto and "ensaios" not in texto


def test_escrever_indice_grava_na_raiz_da_biblioteca(tmp_path: Path):
    _jogo(tmp_path)

    destino = ficha.escrever_indice(tmp_path)

    assert destino == tmp_path / "JOGOS.md"
    assert "gremio x internacional" in destino.read_text(encoding="utf-8")


def test_indice_de_biblioteca_vazia_nao_estoura(tmp_path: Path):
    texto = ficha.montar_indice(tmp_path)
    assert "nenhum jogo" in texto.lower()
