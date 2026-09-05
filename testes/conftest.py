"""Ajustes que valem para a bateria inteira.

A identidade do canal e um arquivo da MAQUINA, e nao do repositorio: sem esta
trava a bateria le o `dados/identidade.json` de quem estiver rodando, e teste
que passa aqui reprova na maquina do lado - foi exatamente o que aconteceu em
05/09, quando o arranjo `palco-lateral` gravado pelo dono derrubou um teste de
formato em-pe que nada tinha a ver com identidade.
"""
import pytest

from nucleo import identidade


@pytest.fixture(autouse=True)
def identidade_da_maquina_fora(tmp_path, monkeypatch):
    monkeypatch.setattr(
        identidade, "ARQUIVO", tmp_path / "identidade-de-teste.json"
    )
