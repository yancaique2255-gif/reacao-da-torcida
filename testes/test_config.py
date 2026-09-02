import json
from pathlib import Path

from nucleo import config


def test_padroes_sao_usados_quando_nao_ha_arquivo():
    c = config.carregar(None)
    assert c["altura_maxima"] == 720
    assert c["biblioteca"].endswith("REACAO DA TORCIDA")
    assert c["segundos_antes"] == 8
    assert c["segundos_depois"] == 12


def test_arquivo_do_usuario_sobrepoe_apenas_o_que_traz(tmp_path: Path):
    arquivo = tmp_path / "config.json"
    arquivo.write_text(json.dumps({"altura_maxima": 480}), encoding="utf-8")

    c = config.carregar(arquivo)

    assert c["altura_maxima"] == 480
    assert c["segundos_antes"] == 8  # continua vindo do padrao
