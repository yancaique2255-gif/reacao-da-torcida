"""A torcida do canal deixou de ser opcional.

O primeiro jogo de verdade gravou seis canais e tres ficaram em branco - entre
eles o `baldasso-tv`, o melhor material da noite. Com a regra editorial ligada
(publica-se so o lado que perdeu), campo vazio significa canal fora do video,
sem ninguem perceber. Estes testes travam as duas pontas: nao deixar nascer
vazio, e saber consertar o que ja nasceu.
"""
import json
from pathlib import Path

import pytest

from nucleo import canais, catalogo, torcidas


def _canal_gravado(
    bruto: Path, pasta: str, url: str = "https://y/1", torcida: str | None = None
) -> Path:
    destino = bruto / pasta
    destino.mkdir(parents=True, exist_ok=True)
    dados = {"url": url, "sessoes": [{"numero": 1, "t0": "2026-09-03T20:00:00"}]}
    if torcida is not None:
        dados["torcida"] = torcida
    (destino / "gravacao.json").write_text(
        json.dumps(dados, ensure_ascii=False), encoding="utf-8"
    )
    return destino


def _jogo(tmp_path: Path) -> Path:
    """Um jogo de mentira com tres canais: um certo, um vazio, um sem o campo."""
    pasta = tmp_path / "2026-09-03 gremio x internacional"
    bruto = pasta / "bruto"
    _canal_gravado(bruto, "paulo-brito", torcida="inter")
    _canal_gravado(bruto, "baldasso-tv", torcida="")
    _canal_gravado(bruto, "gaucha-esportes")  # nem o campo existe
    dados = catalogo.novo(pasta.name)
    dados = catalogo.registrar_gol(dados, 1, "2026-09-03T20:13:32", "")
    for nome in ("paulo-brito", "baldasso-tv", "gaucha-esportes"):
        dados = catalogo.registrar_clipe(
            dados, 1, nome, f"clipes/gol-01/{nome}.mp4", 0.0, 9.0, True,
            "inter" if nome == "paulo-brito" else "",
        )
    catalogo.salvar(pasta, dados)
    return pasta


# --- o vocabulario ---------------------------------------------------------


def test_torcida_e_sempre_a_mesma_palavra_escrita_do_mesmo_jeito():
    """"Grêmio " e "gremio" nao podem virar duas torcidas diferentes."""
    assert canais.normalizar_torcida(" Grêmio ") == "gremio"
    assert canais.normalizar_torcida("São Paulo") == "sao-paulo"
    assert canais.normalizar_torcida("INTER") == "inter"
    assert canais.normalizar_torcida("") == ""
    assert canais.normalizar_torcida(None) == ""


def test_cadastrar_sem_torcida_e_recusado_e_a_recusa_ensina_a_saida():
    with pytest.raises(ValueError) as erro:
        canais.exigir_torcida("   ")
    assert canais.NEUTRO in str(erro.value), "quem nao tem lado precisa saber o que digitar"


def test_neutro_e_uma_resposta_valida_e_diferente_de_vazio():
    """Narracao sem lado existe; o que nao existe e nao responder."""
    assert canais.exigir_torcida("Neutro") == canais.NEUTRO
    assert canais.NEUTRO != ""


# --- ler o que esta no disco ----------------------------------------------


def test_le_a_torcida_de_cada_canal_gravado(tmp_path: Path):
    pasta = _jogo(tmp_path)
    assert torcidas.gravadas(pasta) == {
        "baldasso-tv": "", "gaucha-esportes": "", "paulo-brito": "inter",
    }


def test_canal_sem_torcida_aparece_marcado_e_nao_some(tmp_path: Path):
    """A regra mais forte do projeto: o que esta errado aparece, nao desaparece."""
    pasta = _jogo(tmp_path)
    assert torcidas.em_branco(pasta) == ["baldasso-tv", "gaucha-esportes"]
    assert "baldasso-tv" in torcidas.gravadas(pasta)


def test_jogo_sem_bruto_nao_quebra(tmp_path: Path):
    assert torcidas.gravadas(tmp_path / "nao-existe") == {}
    assert torcidas.em_branco(tmp_path / "nao-existe") == []


# --- aplicar ---------------------------------------------------------------


def test_preencher_grava_na_gravacao_e_em_cada_clipe(tmp_path: Path):
    """Dois arquivos, duas leituras: a ficha le a gravacao, o painel le o catalogo."""
    pasta = _jogo(tmp_path)

    mexidos = torcidas.aplicar(
        pasta, {"baldasso-tv": "Inter", "gaucha-esportes": "neutro"}
    )

    assert mexidos == ["baldasso-tv", "gaucha-esportes"]
    assert torcidas.gravadas(pasta) == {
        "baldasso-tv": "inter", "gaucha-esportes": "neutro", "paulo-brito": "inter",
    }
    do_catalogo = {c["canal"]: c["torcida"] for c in catalogo.carregar(pasta)["clipes"]}
    assert do_catalogo == {
        "baldasso-tv": "inter", "gaucha-esportes": "neutro", "paulo-brito": "inter",
    }


def test_preencher_refaz_a_ficha_do_jogo(tmp_path: Path):
    pasta = _jogo(tmp_path)

    torcidas.aplicar(pasta, {"baldasso-tv": "inter"})

    assert "inter" in (pasta / "JOGO.md").read_text(encoding="utf-8")


def test_preencher_nao_apaga_o_resto_da_gravacao(tmp_path: Path):
    pasta = _jogo(tmp_path)

    torcidas.aplicar(pasta, {"baldasso-tv": "inter"})

    dados = json.loads(
        (pasta / "bruto" / "baldasso-tv" / "gravacao.json").read_text(encoding="utf-8")
    )
    assert dados["url"] == "https://y/1" and len(dados["sessoes"]) == 1


def test_canal_que_nao_existe_no_jogo_nao_muda_nada(tmp_path: Path):
    """Tudo ou nada: metade aplicado seria pior do que nada aplicado."""
    pasta = _jogo(tmp_path)

    with pytest.raises(KeyError):
        torcidas.aplicar(pasta, {"baldasso-tv": "inter", "fantasma": "gremio"})

    assert torcidas.gravadas(pasta)["baldasso-tv"] == ""


def test_preencher_com_vazio_e_recusado(tmp_path: Path):
    pasta = _jogo(tmp_path)

    with pytest.raises(ValueError):
        torcidas.aplicar(pasta, {"baldasso-tv": "  "})

    assert torcidas.gravadas(pasta)["baldasso-tv"] == ""


# --- o cadastro, que e a origem -------------------------------------------


def test_o_cadastro_diz_a_torcida_pelo_apelido_do_canal():
    cadastro = {
        "gremio-x-internacional": [
            canais.Canal("BALDASSO TV", "https://y/1", True, "inter"),
            canais.Canal("Bagé TV", "https://y/2", True, "gremio"),
            canais.Canal("Sem lado ainda", "https://y/3", True, ""),
        ]
    }

    assert torcidas.do_cadastro(cadastro) == {
        "baldasso-tv": "inter", "bage-tv": "gremio",
    }


def test_consertar_o_cadastro_para_o_buraco_nao_voltar(tmp_path: Path):
    """Consertar o jogo conserta um jogo; consertar o cadastro conserta os proximos."""
    arquivo = tmp_path / "canais.json"
    arquivo.write_text(json.dumps({
        "gremio-x-internacional": [
            {"nome": "BALDASSO TV", "url": "https://y/1", "ativo": True, "torcida": ""},
            {"nome": "Paulo Brito", "url": "https://y/2", "ativo": True, "torcida": "inter"},
        ]
    }, ensure_ascii=False), encoding="utf-8")

    mexidos = torcidas.definir_no_cadastro(arquivo, {"baldasso-tv": "inter"})

    assert mexidos == ["gremio-x-internacional/baldasso-tv"]
    relido = json.loads(arquivo.read_text(encoding="utf-8"))
    assert relido["gremio-x-internacional"][0]["torcida"] == "inter"
    assert relido["gremio-x-internacional"][1]["torcida"] == "inter", "nao mexeu em quem ja estava"


def test_cadastro_que_ja_diz_a_mesma_coisa_nao_e_reescrito(tmp_path: Path):
    arquivo = tmp_path / "canais.json"
    arquivo.write_text(json.dumps({
        "j": [{"nome": "Paulo Brito", "url": "u", "ativo": True, "torcida": "inter"}]
    }), encoding="utf-8")
    antes = arquivo.read_text(encoding="utf-8")

    assert torcidas.definir_no_cadastro(arquivo, {"paulo-brito": "inter"}) == []
    assert arquivo.read_text(encoding="utf-8") == antes


def test_cadastro_inexistente_nao_quebra(tmp_path: Path):
    assert torcidas.definir_no_cadastro(tmp_path / "nao-existe.json", {"a": "b"}) == []
