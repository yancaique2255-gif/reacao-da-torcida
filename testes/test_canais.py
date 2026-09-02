import json
from pathlib import Path

from nucleo import canais


def test_carrega_as_urls_exatas_escolhidas_pelo_operador(tmp_path: Path):
    arquivo = tmp_path / "canais.json"
    arquivo.write_text(
        json.dumps(
            {
                "cruzeiro": [
                    {
                        "nome": "Canal A",
                        "url": "https://www.youtube.com/watch?v=abc123",
                        "ativo": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    cadastro = canais.carregar(arquivo)

    assert cadastro["cruzeiro"][0] == canais.Canal(
        "Canal A", "https://www.youtube.com/watch?v=abc123", True
    )


def test_selecionados_preservam_a_ordem_manual_e_nao_alteram_a_url():
    cadastro = {
        "cruzeiro": [
            canais.Canal("Mais views", "https://youtube.com/watch?v=mais", True),
            canais.Canal("Segundo", "https://youtube.com/watch?v=segundo", True),
        ]
    }

    selecionados = canais.selecionados_do_time("cruzeiro", cadastro)

    assert [(c.nome, url) for c, url in selecionados] == [
        ("Mais views", "https://youtube.com/watch?v=mais"),
        ("Segundo", "https://youtube.com/watch?v=segundo"),
    ]


def test_canal_inativo_nao_e_selecionado():
    cadastro = {
        "t": [
            canais.Canal("Ligado", "https://youtube.com/watch?v=1", True),
            canais.Canal("Desligado", "https://youtube.com/watch?v=2", False),
        ]
    }

    selecionados = canais.selecionados_do_time("t", cadastro)

    assert [c.nome for c, _ in selecionados] == ["Ligado"]


def test_time_sem_canais_devolve_lista_vazia():
    assert canais.selecionados_do_time("inexistente", {}) == []


def test_cadastro_ainda_nao_criado_devolve_estrutura_vazia(tmp_path: Path):
    assert canais.carregar(tmp_path / "canais.json") == {}
