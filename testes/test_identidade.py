"""A identidade do canal: um arquivo por instalacao, e campo vazio nao desenha.

O dono ainda nao tem logo, arte nem contas nas redes. O desenho e feito para que
isso nao bloqueie nada: constroi-se agora, preenche-se depois, um campo de cada
vez. O que estes testes cobram e essa promessa - com o arquivo recem-criado, o
video sai identico ao de hoje - e a trava da escala, que e o que impede os
arranjos de palco de perderem a nitidez que sao a razao de existirem.
"""
import json
from pathlib import Path

import pytest

from nucleo import identidade


def test_identidade_recem_criada_nao_desenha_nada(tmp_path: Path):
    """Arquivo que nao existe nao e erro: e a identidade vazia."""
    valores = identidade.carregar(tmp_path / "nao-existe.json")

    assert valores["arranjo"] == "quadro-cheio"
    assert valores["escala"] == 1.0
    assert valores["deslocamento"] == 0.0
    assert valores["arte_de_fundo"] == "" and valores["logo"] == ""
    assert set(valores["redes"]) == set(identidade.REDES)
    assert all(arroba == "" for arroba in valores["redes"].values())


def test_o_arquivo_grava_e_volta_igual(tmp_path: Path):
    arquivo = tmp_path / "identidade.json"
    valores = identidade.mexer(
        identidade.carregar(arquivo), logo=r"C:\arte\logo.png", chamada="SE INSCREVE"
    )

    identidade.salvar(valores, arquivo)

    assert json.loads(arquivo.read_text(encoding="utf-8"))["chamada"] == "SE INSCREVE"
    assert identidade.carregar(arquivo)["logo"] == r"C:\arte\logo.png"


def test_mexer_numa_rede_nao_apaga_as_outras(tmp_path: Path):
    valores = identidade.mexer(
        identidade.carregar(tmp_path / "x.json"), redes={"youtube": "@veia"}
    )

    valores = identidade.mexer(valores, redes={"tiktok": "@veiatk"})

    assert valores["redes"]["youtube"] == "@veia"
    assert valores["redes"]["tiktok"] == "@veiatk"
    assert valores["redes"]["instagram"] == ""


def test_escala_acima_de_um_e_recusada_dizendo_por_que():
    """A trava da seccao 3: escala 1,00 e o 1:1 com a fonte de 720p."""
    with pytest.raises(ValueError) as erro:
        identidade.conferir({"escala": 1.05, "deslocamento": 0.0})

    recado = str(erro.value)
    assert "1280x720" in recado, "o recado tem que dizer QUAL e o limite"
    assert "0.6" in recado or "0,6" in recado


def test_escala_de_um_exato_e_aceita():
    identidade.conferir({"escala": 1.0, "deslocamento": 0.0})
    identidade.conferir({"escala": identidade.ESCALA_MINIMA, "deslocamento": 0.0})


def test_escala_pequena_demais_tambem_e_recusada():
    with pytest.raises(ValueError):
        identidade.conferir({"escala": 0.4, "deslocamento": 0.0})


def test_deslocamento_fora_do_limite_e_recusado():
    with pytest.raises(ValueError) as erro:
        identidade.conferir({"escala": 1.0, "deslocamento": 0.3})

    assert "162" in str(erro.value)


def test_o_jogo_sem_moldagem_usa_o_padrao_do_canal(tmp_path: Path):
    """Ausente - que e o normal - o jogo usa o padrao do canal."""
    do_canal = identidade.mexer(
        identidade.carregar(tmp_path / "x.json"), arranjo="palco-alto", escala=0.9
    )

    resolvida = identidade.moldagem(do_canal, {"formato": "deitado"})

    assert resolvida == {"arranjo": "palco-alto", "escala": 0.9, "deslocamento": 0.0}


def test_o_desvio_do_jogo_sobrepoe_campo_a_campo(tmp_path: Path):
    do_canal = identidade.mexer(
        identidade.carregar(tmp_path / "x.json"), arranjo="palco-alto", escala=0.9
    )

    resolvida = identidade.moldagem(do_canal, {"moldagem": {"escala": 0.8}})

    assert resolvida == {"arranjo": "palco-alto", "escala": 0.8, "deslocamento": 0.0}


def test_o_desvio_fica_marcado():
    """Sair do padrao e permitido, mas nunca por acidente."""
    assert identidade.desviou({"moldagem": {"escala": 0.8}}) is True
    assert identidade.desviou({"formato": "deitado"}) is False
    assert identidade.desviou(None) is False


def test_desvio_com_numero_fora_da_trava_reclama_ao_resolver(tmp_path: Path):
    """Receita editada na mao nao pode furar a trava calada."""
    do_canal = identidade.carregar(tmp_path / "x.json")

    with pytest.raises(ValueError):
        identidade.moldagem(do_canal, {"moldagem": {"escala": 1.4}})
