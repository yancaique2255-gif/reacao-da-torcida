import json
from pathlib import Path

from nucleo import importar

YTDLP = r"C:\yt-dlp\yt-dlp.exe"


def test_le_o_nome_do_canal_com_acento_inteiro():
    """Sem UTF-8 o acento se perdia e virava nome de pasta errado para sempre."""
    rodar = lambda c: "Diário do Peixe|is_live\n"

    nome, situacao = importar.descrever("https://y/1", YTDLP, rodar)

    assert nome == "Diário do Peixe" and situacao == "is_live"


def test_pede_utf8_ao_yt_dlp():
    comandos = []

    def rodar(comando):
        comandos.append(comando)
        return "Canal|is_live"

    importar.descrever("https://y/1", YTDLP, rodar)

    assert "--encoding" in comandos[0]
    assert comandos[0][comandos[0].index("--encoding") + 1] == "UTF-8"


def test_aviso_na_frente_nao_vira_nome_de_canal():
    rodar = lambda c: "WARNING: algo estranho\nCanto Rubro-Negro|is_live\n"

    nome, _ = importar.descrever("https://y/1", YTDLP, rodar)

    assert nome == "Canto Rubro-Negro"


def test_url_ilegivel_e_pulada_com_aviso():
    ditos = []

    canais = importar.importar(
        ["https://y/1", "https://y/2"], YTDLP, rodar=lambda c: "", avisar=ditos.append
    )

    assert canais == []
    assert sum("pulando" in d for d in ditos) == 2


def test_lote_importado_ja_nasce_com_a_torcida():
    canais = importar.importar(
        ["https://y/1"], YTDLP, torcida="santos",
        rodar=lambda c: "A Sereia Revoltada|is_live", avisar=lambda t: None,
    )

    assert canais == [{
        "nome": "A Sereia Revoltada",
        "url": "https://y/1",
        "ativo": True,
        "torcida": "santos",
    }]


def test_juntar_acrescenta_sem_duplicar():
    """Cadastrar um time de cada vez so funciona se o segundo lote nao apagar o primeiro."""
    cadastro = {"jogo": [{"nome": "Ja tinha", "url": "https://y/1", "ativo": True, "torcida": "santos"}]}
    novos = [
        {"nome": "Repetido", "url": "https://y/1", "ativo": True, "torcida": "palmeiras"},
        {"nome": "Novo", "url": "https://y/2", "ativo": True, "torcida": "palmeiras"},
    ]

    junto = importar.juntar(cadastro, "jogo", novos)

    assert [c["nome"] for c in junto["jogo"]] == ["Ja tinha", "Novo"]


def test_juntar_em_chave_que_ainda_nao_existe():
    junto = importar.juntar({}, "novo-jogo", [{"nome": "A", "url": "u", "ativo": True, "torcida": ""}])

    assert [c["nome"] for c in junto["novo-jogo"]] == ["A"]


def test_grava_e_le_o_cadastro_em_utf8(tmp_path: Path):
    arquivo = tmp_path / "canais.json"

    importar.salvar(arquivo, {"j": [{"nome": "Peixão TV", "url": "u", "ativo": True, "torcida": ""}]})

    assert importar.carregar_cru(arquivo)["j"][0]["nome"] == "Peixão TV"
    assert "Peixão" in arquivo.read_text(encoding="utf-8"), "sem escapar em \\u"


def test_cadastro_inexistente_comeca_vazio(tmp_path: Path):
    assert importar.carregar_cru(tmp_path / "nao-existe.json") == {}
