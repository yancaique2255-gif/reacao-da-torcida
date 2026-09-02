import os
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
    cfg = {"biblioteca": str(tmp_path), "segundos_entre_conferencias": 0}
    recebidos = []
    supervisionados = []

    def iniciar_falso(escolhidos, biblioteca, jogo, configuracao):
        recebidos.extend(escolhidos)
        return ["processo-de-mentira"]

    monkeypatch.setattr(esteira, "_cadastro", lambda: cadastro)
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)
    monkeypatch.setattr(esteira.gravador, "iniciar", iniciar_falso)
    # A supervisao tem testes proprios em test_gravador; aqui so confirmamos
    # que a etapa entrega as URLs manuais e passa a bola para ela.
    monkeypatch.setattr(
        esteira.gravador, "supervisionar",
        lambda processos, configuracao: supervisionados.extend(processos),
    )

    codigo = esteira.etapa_gravar(["cruzeiro", "Cruzeiro", "Atlético-MG"])

    assert codigo == 0
    assert recebidos[0][1] == "https://youtube.com/watch?v=escolhido"
    assert supervisionados == ["processo-de-mentira"], "a gravacao fica supervisionada"


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


from datetime import date  # noqa: E402

from nucleo import relogio  # noqa: E402


def sessao_da_noite() -> relogio.Sessao:
    """Gravacao das 21:30 as 00:10 do dia seguinte."""
    return relogio.Sessao(
        t0=datetime(2026, 9, 1, 21, 30, 0),
        pedacos=[
            relogio.Pedaco(f"s01-parte-{i:03d}.ts", i * 600.0, (i + 1) * 600.0)
            for i in range(16)
        ],
    )


def test_horario_do_primeiro_tempo_fica_no_dia_do_jogo():
    momento = esteira.resolver_horario(
        "21:47:00", [sessao_da_noite()], date(2026, 9, 1)
    )
    assert momento == datetime(2026, 9, 1, 21, 47, 0)


def test_gol_depois_da_meia_noite_cai_no_dia_seguinte():
    """Copa do Brasil comeca 21:30; gol no fim do segundo tempo passa da meia-noite."""
    momento = esteira.resolver_horario(
        "00:05:00", [sessao_da_noite()], date(2026, 9, 1)
    )
    assert momento == datetime(2026, 9, 2, 0, 5, 0), "nao pode voltar 12h para 01/09"


def test_sem_gravacao_nenhuma_usa_a_data_da_pasta():
    momento = esteira.resolver_horario("21:47:00", [], date(2026, 9, 1))
    assert momento == datetime(2026, 9, 1, 21, 47, 0)


def test_pedaco_final_fora_do_csv_e_recuperado(tmp_path: Path, monkeypatch):
    """Fechar a janela mata o ffmpeg no meio do pedaco: o .ts existe, o CSV nao o cita."""
    (tmp_path / "s01-parte-000.ts").write_bytes(b"x")
    (tmp_path / "s01-parte-001.ts").write_bytes(b"x")  # o que ficou de fora
    sessao = relogio.Sessao(
        t0=datetime(2026, 9, 1, 21, 0, 0),
        pedacos=[relogio.Pedaco("s01-parte-000.ts", 0.0, 600.0)],
    )
    monkeypatch.setattr(esteira.cortador, "duracao", lambda arquivo, ffprobe: 137.0)

    completada = esteira._completar_pedaco_final(
        sessao, tmp_path, {"caminho_ffprobe": "ffprobe"}, "s01"
    )

    assert [p.arquivo for p in completada.pedacos] == [
        "s01-parte-000.ts",
        "s01-parte-001.ts",
    ]
    assert completada.pedacos[1] == relogio.Pedaco("s01-parte-001.ts", 600.0, 737.0)


def test_pedaco_final_ilegivel_e_ignorado(tmp_path: Path, monkeypatch):
    (tmp_path / "s01-parte-001.ts").write_bytes(b"")
    monkeypatch.setattr(esteira.cortador, "duracao", lambda arquivo, ffprobe: 0.0)

    completada = esteira._completar_pedaco_final(
        relogio.Sessao(datetime(2026, 9, 1, 21, 0, 0), []),
        tmp_path,
        {"caminho_ffprobe": "ffprobe"},
        "s01",
    )

    assert completada.pedacos == []


def _tocar(arquivo: Path, quando: datetime) -> None:
    arquivo.write_bytes(b"x")
    marca = quando.timestamp()
    os.utime(arquivo, (marca, marca))


def test_t0_e_ancorado_pelo_relogio_do_disco_e_nao_pelo_lancamento(tmp_path: Path):
    """O t0 gravado e a hora em que o processo subiu, nao a do primeiro frame.

    Entre um e outro cabem o arranque do yt-dlp e o trecho velho que o ffmpeg
    puxa acelerado para alcancar o ao vivo. Meio minuto de erro joga o corte
    inteiro para fora do lance.
    """
    _tocar(tmp_path / "s01-parte-000.ts", datetime(2026, 9, 2, 21, 40, 30))
    _tocar(tmp_path / "s01-parte-001.ts", datetime(2026, 9, 2, 21, 50, 30))
    sessao = relogio.Sessao(
        t0=datetime(2026, 9, 2, 21, 30, 0),  # lancamento
        pedacos=[
            relogio.Pedaco("s01-parte-000.ts", 0.0, 600.0),
            relogio.Pedaco("s01-parte-001.ts", 600.0, 1200.0),
        ],
    )

    ancorada = esteira.ancorar_t0(sessao, tmp_path)

    # 21:40:30 menos os 600s do primeiro pedaco: o frame zero e de 21:30:30.
    assert ancorada.t0 == datetime(2026, 9, 2, 21, 30, 30)
    assert ancorada.pedacos == sessao.pedacos


def test_ancora_escolhe_o_instante_mais_perto_do_ao_vivo(tmp_path: Path):
    """Pedaco que demorou a fechar so mostra que a maquina ficou para tras.

    A ancora e o menor dos palpites: o momento em que a gravacao esteve mais
    colada no ao vivo. Assim, canal que atrasa no fim do jogo nao arrasta o
    horario de todos os gols anteriores.
    """
    _tocar(tmp_path / "s01-parte-000.ts", datetime(2026, 9, 2, 21, 40, 30))
    _tocar(tmp_path / "s01-parte-001.ts", datetime(2026, 9, 2, 21, 51, 10))  # 40s atras
    sessao = relogio.Sessao(
        t0=datetime(2026, 9, 2, 21, 30, 0),
        pedacos=[
            relogio.Pedaco("s01-parte-000.ts", 0.0, 600.0),
            relogio.Pedaco("s01-parte-001.ts", 600.0, 1200.0),
        ],
    )

    assert esteira.ancorar_t0(sessao, tmp_path).t0 == datetime(2026, 9, 2, 21, 30, 30)


def test_ancora_sem_arquivo_no_disco_mantem_o_t0_gravado(tmp_path: Path):
    sessao = relogio.Sessao(
        t0=datetime(2026, 9, 2, 21, 30, 0),
        pedacos=[relogio.Pedaco("sumiu.ts", 0.0, 600.0)],
    )

    assert esteira.ancorar_t0(sessao, tmp_path).t0 == datetime(2026, 9, 2, 21, 30, 0)
