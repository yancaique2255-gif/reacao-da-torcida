import json
from datetime import datetime
from pathlib import Path

from nucleo import canais, catalogo, esteira


def test_nome_do_jogo_usa_data_e_apelidos():
    nome = esteira.nome_do_jogo("Atlético-MG", "Cruzeiro", datetime(2026, 9, 1))
    assert nome == "2026-09-01 atletico-mg x cruzeiro"


def test_nome_do_jogo_serve_como_pasta():
    nome = esteira.nome_do_jogo("São Paulo", "Grêmio", datetime(2026, 9, 1))
    assert ":" not in nome and "?" not in nome
    assert nome == "2026-09-01 sao-paulo x gremio"


def test_etapa_canais_lista_a_escolha_manual_sem_descoberta(monkeypatch, capsys):
    cadastro = {
        "cruzeiro": [
            canais.Canal("Mais views", "https://youtube.com/watch?v=mais", True),
            canais.Canal("Inativo", "https://youtube.com/watch?v=nao", False),
        ]
    }
    monkeypatch.setattr(esteira, "_cadastro", lambda: cadastro)

    codigo = esteira.etapa_canais(["cruzeiro"])

    saida = capsys.readouterr().out
    assert codigo == 0
    assert "Mais views" in saida and "watch?v=mais" in saida
    assert "Inativo" not in saida
    assert "1 canal(is) selecionado(s)" in saida


def test_etapa_gravar_entrega_as_urls_manuais_ao_gravador(monkeypatch, tmp_path: Path):
    cadastro = {
        "cruzeiro": [
            canais.Canal("A", "https://youtube.com/watch?v=escolhido", True)
        ]
    }
    cfg = {"biblioteca": str(tmp_path)}
    recebidos = []

    class ProcessoFalso:
        def wait(self):
            return 0

    def iniciar_falso(escolhidos, biblioteca, jogo, configuracao):
        recebidos.extend(escolhidos)
        return [type("P", (), {"processo": ProcessoFalso()})()]

    monkeypatch.setattr(esteira, "_cadastro", lambda: cadastro)
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)
    monkeypatch.setattr(esteira.gravador, "iniciar", iniciar_falso)

    codigo = esteira.etapa_gravar(["cruzeiro", "Cruzeiro", "Atlético-MG"])

    assert codigo == 0
    assert recebidos[0][1] == "https://youtube.com/watch?v=escolhido"


def test_etapa_cortar_usa_o_horario_manual_com_oito_antes_e_doze_depois(
    monkeypatch, tmp_path: Path
):
    jogo = "2026-09-02 cruzeiro x atletico-mg"
    pasta_canal = tmp_path / jogo / "bruto" / "canal-a"
    pasta_canal.mkdir(parents=True)
    (pasta_canal / "gravacao.json").write_text(
        json.dumps(
            {
                "url": "https://youtube.com/watch?v=x",
                "sessoes": [{"numero": 1, "t0": "2026-09-02T20:00:00"}],
            }
        ),
        encoding="utf-8",
    )
    (pasta_canal / "s01-segmentos.csv").write_text(
        "s01-parte-000.ts,0.0,600.0\n", encoding="utf-8"
    )
    cfg = {
        "biblioteca": str(tmp_path),
        "segundos_antes": 8,
        "segundos_depois": 12,
        "caminho_ffmpeg": "ffmpeg",
    }
    chamadas = []
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)
    monkeypatch.setattr(esteira.cortador, "executar", chamadas.append)

    codigo = esteira.etapa_cortar([jogo, "--gols", "20:05:00"])

    assert codigo == 0
    assert len(chamadas) == 1
    assert "292.0" in chamadas[0], "20:05:00 menos 8 segundos"
    assert "20.0" in chamadas[0]
    dados = catalogo.carregar(tmp_path / jogo)
    assert dados["clipes"][0]["confianca_db"] == 0.0
    assert dados["clipes"][0]["tem_pico"] is False
