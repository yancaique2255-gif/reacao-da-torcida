import os
import time
from pathlib import Path

from nucleo import miniatura


def _pedaco(pasta: Path, nome: str, idade: float) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / nome
    arquivo.write_bytes(b"x")
    marca = time.time() - idade
    os.utime(arquivo, (marca, marca))
    return arquivo


def test_usa_sempre_o_pedaco_mais_novo(tmp_path: Path):
    _pedaco(tmp_path, "s01-parte-000.ts", idade=600)
    novo = _pedaco(tmp_path, "s01-parte-003.ts", idade=2)

    assert miniatura.pedaco_mais_novo(tmp_path) == novo


def test_canal_sem_nada_no_disco_nao_gera_quadro(tmp_path: Path):
    assert miniatura.pedaco_mais_novo(tmp_path) is None
    assert miniatura.gerar(tmp_path, tmp_path / "m.jpg", "ffmpeg", rodar=lambda c: None) is None


def test_quadro_recente_nao_e_tirado_de_novo(tmp_path: Path):
    """A pagina atualiza a cada 3s; tirar quadro toda vez seria desperdicio."""
    _pedaco(tmp_path, "s01-parte-000.ts", idade=1)
    destino = tmp_path / "m.jpg"
    destino.write_bytes(b"jpeg")
    chamadas = []

    miniatura.gerar(tmp_path, destino, "ffmpeg", rodar=chamadas.append)

    assert chamadas == []


def test_quadro_velho_e_tirado_de_novo(tmp_path: Path):
    _pedaco(tmp_path, "s01-parte-000.ts", idade=1)
    destino = tmp_path / "m.jpg"
    destino.write_bytes(b"jpeg")
    antigo = time.time() - 600
    os.utime(destino, (antigo, antigo))
    chamadas = []

    miniatura.gerar(tmp_path, destino, "ffmpeg", rodar=lambda c: chamadas.append(c))

    assert len(chamadas) == 1


def test_comando_le_so_o_fim_do_arquivo(tmp_path: Path):
    """O pedaco tem centenas de MB; ler tudo para pegar um quadro seria absurdo."""
    cmd = miniatura.comando(tmp_path / "a.ts", tmp_path / "m.jpg", "ffmpeg")

    assert "-sseof" in cmd
    assert cmd[cmd.index("-sseof") + 1].startswith("-")
    assert cmd[cmd.index("-frames:v") + 1] == "1"
    assert "scale=320:-2" in cmd


def test_ffmpeg_que_falha_nao_estoura_o_painel(tmp_path: Path):
    _pedaco(tmp_path, "s01-parte-000.ts", idade=1)

    def explode(comando):
        raise OSError("ffmpeg sumiu")

    assert miniatura.gerar(tmp_path, tmp_path / "m.jpg", "ffmpeg", rodar=explode) is None
