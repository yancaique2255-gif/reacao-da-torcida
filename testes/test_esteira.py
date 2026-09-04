import os
import json
from datetime import datetime
from pathlib import Path

import pytest

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
        "limiar_confianca_db": 6.0,
        "margem_sem_alinhamento": 30,
    }
    chamadas = []
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)
    monkeypatch.setattr(esteira.cortador, "executar", chamadas.append)

    codigo = esteira.etapa_cortar([jogo, "--gols", "20:05:00"])

    assert codigo == 0
    assert len(chamadas) == 2, "o corte, e depois a extracao de audio que mede a reacao"
    corte, audio = chamadas
    # Sem alinhamento confirmado o canal ganha 30s de margem de cada lado:
    # 20:05:00 menos 8 de janela menos 30 de margem = 262s dentro do pedaco.
    assert "262.0" in corte
    assert "80.0" in corte, "20s de janela mais 60s de margem"
    assert "-vn" in audio, "a medicao so precisa do audio"
    dados = catalogo.carregar(tmp_path / jogo)
    # Com o ffmpeg de mentira nenhum wav e escrito, entao a medicao devolve zero -
    # e o clipe fica registrado do mesmo jeito, que e o comportamento exigido.
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


def test_sem_gols_digitados_usa_o_que_o_painel_anotou():
    """O caminho normal e o botao: o horario nasce certo, do relogio da maquina."""
    dados = catalogo.novo("jogo")
    dados = catalogo.registrar_gol(dados, 1, "2026-09-02T21:47:13", "")
    dados = catalogo.registrar_gol(dados, 3, "2026-09-02T22:31:02", "")

    marcados = esteira._gols_a_cortar(None, dados, [], datetime(2026, 9, 2).date())

    assert marcados == [
        (1, datetime(2026, 9, 2, 21, 47, 13)),
        (3, datetime(2026, 9, 2, 22, 31, 2)),
    ]


def test_gols_digitados_continuam_valendo_e_ganham_a_frente():
    dados = catalogo.registrar_gol(catalogo.novo("jogo"), 1, "2026-09-02T21:00:00", "")

    marcados = esteira._gols_a_cortar(
        ["22:05:30"], dados, [], datetime(2026, 9, 2).date()
    )

    assert marcados == [(1, datetime(2026, 9, 2, 22, 5, 30))]


def test_sem_marca_nenhuma_devolve_lista_vazia():
    assert esteira._gols_a_cortar(None, catalogo.novo("jogo"), [], None) == []


def test_a_data_do_gol_sai_da_cobertura_de_todos_os_canais():
    """Se o primeiro canal da pasta caiu cedo, ele nao pode decidir sozinho."""
    caiu_cedo = relogio.Sessao(
        t0=datetime(2026, 9, 2, 21, 30, 0),
        pedacos=[relogio.Pedaco("a.ts", 0.0, 60.0)],
    )
    foi_ate_o_fim = relogio.Sessao(
        t0=datetime(2026, 9, 2, 23, 30, 0),
        pedacos=[relogio.Pedaco("b.ts", 0.0, 3600.0)],
    )

    momento = esteira.resolver_horario(
        "00:15:00", [caiu_cedo, foi_ate_o_fim], datetime(2026, 9, 2).date()
    )

    assert momento == datetime(2026, 9, 3, 0, 15, 0), "gol depois da meia-noite"


def _jogo_falso(raiz: Path, nome: str) -> None:
    (raiz / nome / "bruto").mkdir(parents=True)


def test_lista_jogos_do_mais_novo_para_o_mais_velho(tmp_path: Path):
    _jogo_falso(tmp_path, "2026-09-01 gremio x inter")
    _jogo_falso(tmp_path, "2026-09-02 santos x palmeiras")
    (tmp_path / "ensaios").mkdir()  # sem bruto: nao e jogo

    assert esteira.listar_jogos(tmp_path) == [
        "2026-09-02 santos x palmeiras",
        "2026-09-01 gremio x inter",
    ]


def test_um_jogo_so_entra_direto_sem_perguntar(tmp_path: Path):
    _jogo_falso(tmp_path, "2026-09-02 santos x palmeiras")
    perguntou = []

    escolhido = esteira.escolher_jogo(
        tmp_path, ler=lambda _: perguntou.append(1) or "1", escrever=lambda *a: None
    )

    assert escolhido == "2026-09-02 santos x palmeiras"
    assert perguntou == [], "com um jogo so, perguntar e so atrito"


def test_menu_devolve_o_jogo_do_numero_digitado(tmp_path: Path):
    _jogo_falso(tmp_path, "2026-09-02 santos x palmeiras")
    _jogo_falso(tmp_path, "2026-09-02 vitoria x vasco")

    escolhido = esteira.escolher_jogo(
        tmp_path, ler=lambda _: "2", escrever=lambda *a: None
    )

    assert escolhido == "2026-09-02 santos x palmeiras", "o 2 e o segundo da lista"


def test_numero_fora_da_lista_nao_escolhe_nada(tmp_path: Path):
    _jogo_falso(tmp_path, "a")
    _jogo_falso(tmp_path, "b")
    for digitado in ("0", "9", "banana", ""):
        assert esteira.escolher_jogo(
            tmp_path, ler=lambda _, d=digitado: d, escrever=lambda *a: None
        ) is None


def test_biblioteca_vazia_avisa_e_nao_escolhe(tmp_path: Path):
    ditos = []
    assert esteira.escolher_jogo(tmp_path, ler=lambda _: "1", escrever=ditos.append) is None
    assert any("Nenhum jogo" in d for d in ditos)


def test_cortar_um_canal_apaga_a_juncao_que_criou(tmp_path: Path):
    """Sem isto sobra um .ts do tamanho da janela dentro da pasta do canal."""
    (tmp_path / "a.ts").write_bytes(b"x")
    (tmp_path / "b.ts").write_bytes(b"x")
    destino = tmp_path / "clipes"
    destino.mkdir()
    recortes = [
        relogio.Trecho("a.ts", 0.0, 30.0),
        relogio.Trecho("b.ts", 0.0, 90.0),
    ]
    rodados = []

    plano = esteira.PlanoDoCanal("peixao", recortes, 120.0, False, False)
    clipe = esteira.cortar_um_canal(
        plano, tmp_path, 1, destino, CFG_CORTE, executar=rodados.append,
    )

    assert clipe.canal == "peixao" and clipe.arquivo == destino / "peixao.mp4"
    assert clipe.deslocamento == 0.0, "com juncao, o corte comeca do zero do arquivo novo"
    assert not (tmp_path / "janela-manual-01.ts").exists()
    assert not (tmp_path / "janela-manual-01.txt").exists()


def test_cortar_um_canal_com_um_trecho_so_nao_junta_nada(tmp_path: Path):
    (tmp_path / "a.ts").write_bytes(b"x")
    destino = tmp_path / "clipes"
    destino.mkdir()
    rodados = []

    plano = esteira.PlanoDoCanal(
        "peixao", [relogio.Trecho("a.ts", 42.0, 162.0)], 120.0, False, False
    )
    clipe = esteira.cortar_um_canal(
        plano, tmp_path, 1, destino, CFG_CORTE, executar=rodados.append,
    )

    assert clipe.deslocamento == 42.0, "corta direto do pedaco, no ponto certo"
    assert len(rodados) == 2, "o corte e a extracao de audio que mede a reacao"


CFG_CORTE = {
    "caminho_ffmpeg": "ffmpeg",
    "segundos_antes": 60,
    "segundos_depois": 60,
    "limiar_confianca_db": 6.0,
}


def test_cada_canal_corta_no_relogio_dele(tmp_path: Path, monkeypatch):
    """A mesma jogada aparece em instantes diferentes conforme o atraso do canal.

    Dois canais gravando o mesmo jogo, um deles 30s atras do outro: o corte
    tem que buscar 30s adiante naquele, senao sai o lance errado.
    """
    jogo = "2026-09-02 vitoria x vasco"
    bruto = tmp_path / jogo / "bruto"
    for nome, deslocamento in (("na-hora", None), ("atrasado", 30.0)):
        pasta = bruto / nome
        pasta.mkdir(parents=True)
        (pasta / "gravacao.json").write_text(
            json.dumps({
                "url": "u",
                "sessoes": [{"numero": 1, "t0": "2026-09-02T23:00:00"}],
                **({"deslocamento": deslocamento, "deslocamento_de": "consenso"}
                   if deslocamento else {}),
            }),
            encoding="utf-8",
        )
        (pasta / "s01-parte-000.ts").write_bytes(b"x")
        (pasta / "s01-segmentos.csv").write_text(
            "s01-parte-000.ts,0.0,3600.0\n", encoding="utf-8"
        )

    cfg = {
        "biblioteca": str(tmp_path), "segundos_antes": 10, "segundos_depois": 10,
        "caminho_ffmpeg": "ffmpeg", "caminho_ffprobe": "ffprobe",
        "limiar_confianca_db": 6.0, "cortes_em_paralelo": 1,
        "margem_sem_alinhamento": 0,  # aqui o que se testa e o deslocamento
    }
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)
    monkeypatch.setattr(esteira, "ancorar_t0", lambda sessao, pasta: sessao)
    chamadas = []
    monkeypatch.setattr(esteira.cortador, "executar", chamadas.append)

    esteira.etapa_cortar([jogo, "--gols", "23:10:00"])

    # 23:10:00 e 600s depois do t0; menos 10s da janela = 590 no canal em dia.
    cortes = [c for c in chamadas if "-c:v" in c]
    posicoes = sorted(float(c[c.index("-ss") + 1]) for c in cortes)
    assert posicoes == [590.0, 620.0], "o atrasado busca 30s adiante"


CFG_JANELA = {
    "segundos_antes": 60, "segundos_depois": 60,
    "margem_sem_alinhamento": 60, "caminho_ffmpeg": "ffmpeg",
    "limiar_confianca_db": 6.0,
}


def _sessao_cheia(t0=datetime(2026, 9, 2, 23, 0, 0), duracao=3600.0):
    return [relogio.Sessao(t0=t0, pedacos=[relogio.Pedaco("a.ts", 0.0, duracao)])]


def test_canal_sem_alinhamento_ganha_margem_dos_dois_lados():
    """Nao se sabe onde a reacao esta nele: melhor sobrar video do que faltar.

    Cortar o lance ao meio nao tem conserto; clipe longo demais o operador
    apara no estudio.
    """
    plano = esteira.planejar_corte(
        "novato", _sessao_cheia(), datetime(2026, 9, 2, 23, 12, 36), CFG_JANELA
    )

    assert plano.duracao == 240.0, "120 da janela mais 60 de margem de cada lado"
    assert plano.largo and not plano.parcial


def test_canal_ja_alinhado_corta_justo():
    """A margem some sozinha conforme o alinhamento e confirmado pelos gols."""
    plano = esteira.planejar_corte(
        "conhecido", _sessao_cheia(), datetime(2026, 9, 2, 23, 12, 36),
        CFG_JANELA, deslocamento=12.0,
    )

    assert plano.duracao == 120.0 and not plano.largo


def test_o_deslocamento_move_a_janela_do_canal():
    """Canal atrasado procura adiante; a duracao do clipe nao muda por isso."""
    cedo = esteira.planejar_corte(
        "c", _sessao_cheia(), datetime(2026, 9, 2, 23, 12, 36), CFG_JANELA,
        deslocamento=0.0,
    )
    tarde = esteira.planejar_corte(
        "c", _sessao_cheia(), datetime(2026, 9, 2, 23, 12, 36), CFG_JANELA,
        deslocamento=30.0,
    )

    assert cedo.duracao == tarde.duracao
    assert tarde.recortes[0].inicio - cedo.recortes[0].inicio == 30.0


def test_cobertura_parcial_nao_e_mais_descartada():
    """Metade do lance vale mais que nada: o operador decide no estudio."""
    # gravacao que termina 30s depois do gol, cortando a janela ao meio
    sessoes = [relogio.Sessao(
        t0=datetime(2026, 9, 2, 23, 0, 0),
        pedacos=[relogio.Pedaco("a.ts", 0.0, 786.0)],  # ate 23:13:06
    )]

    plano = esteira.planejar_corte(
        "cortado", sessoes, datetime(2026, 9, 2, 23, 12, 36), CFG_JANELA
    )

    assert plano.parcial, "avisa que faltou pedaco"
    assert plano.duracao > 0, "mas entrega o que existe"
    assert plano.recortes, "ha material para cortar"


def test_canal_sem_nada_na_janela_nao_tem_o_que_cortar():
    """Aqui nao ha o que salvar: o trecho nem chegou a ser baixado."""
    sessoes = [relogio.Sessao(
        t0=datetime(2026, 9, 2, 21, 0, 0),
        pedacos=[relogio.Pedaco("a.ts", 0.0, 600.0)],  # so ate 21:10
    )]

    plano = esteira.planejar_corte(
        "atrasado", sessoes, datetime(2026, 9, 2, 23, 12, 36), CFG_JANELA
    )

    assert plano.duracao == 0.0 and plano.recortes == []


def test_o_clipe_e_medido_pela_duracao_que_ele_tem(tmp_path: Path):
    """Clipe largo medido pela janela curta perderia a reacao que esta no fim."""
    pedidos = []
    esteira.medir_reacao(tmp_path / "c.mp4", CFG_JANELA, pedidos.append, duracao=240.0)

    comando = pedidos[0]
    assert comando[comando.index("-t") + 1] == "240.0"


def test_canal_com_pouquissimo_material_nao_vira_arquivo(tmp_path: Path, monkeypatch):
    """Tres segundos de video nao ajudam ninguem; viram ruido na pasta."""
    jogo = "2026-09-02 vitoria x vasco"
    bruto = tmp_path / jogo / "bruto"
    for nome, fim in (("inteiro", 3600.0), ("quase-nada", 700.0)):
        pasta = bruto / nome
        pasta.mkdir(parents=True)
        (pasta / "gravacao.json").write_text(
            json.dumps({"url": "u", "sessoes": [{"numero": 1, "t0": "2026-09-02T23:00:00"}]}),
            encoding="utf-8",
        )
        (pasta / "s01-parte-000.ts").write_bytes(b"x")
        (pasta / "s01-segmentos.csv").write_text(
            f"s01-parte-000.ts,0.0,{fim}\n", encoding="utf-8"
        )

    cfg = {
        "biblioteca": str(tmp_path), "segundos_antes": 60, "segundos_depois": 60,
        "margem_sem_alinhamento": 0, "minimo_do_clipe": 15,
        "caminho_ffmpeg": "ffmpeg", "caminho_ffprobe": "ffprobe",
        "limiar_confianca_db": 6.0, "cortes_em_paralelo": 1,
    }
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)
    monkeypatch.setattr(esteira, "ancorar_t0", lambda sessao, pasta: sessao)
    monkeypatch.setattr(esteira.cortador, "executar", lambda c: None)

    esteira.etapa_cortar([jogo, "--gols", "23:12:36"])

    dados = catalogo.carregar(tmp_path / jogo)
    canais = {c["canal"] for c in dados["clipes"]}
    assert canais == {"inteiro"}, "o de 4s de cobertura fica de fora"


def test_o_catalogo_conta_que_o_clipe_saiu_largo(tmp_path: Path, monkeypatch):
    """O estudio precisa avisar que aquele clipe pede aparo."""
    jogo = "j"
    bruto = tmp_path / jogo / "bruto" / "canal"
    bruto.mkdir(parents=True)
    (bruto / "gravacao.json").write_text(
        json.dumps({"url": "u", "sessoes": [{"numero": 1, "t0": "2026-09-02T23:00:00"}]}),
        encoding="utf-8",
    )
    (bruto / "s01-parte-000.ts").write_bytes(b"x")
    (bruto / "s01-segmentos.csv").write_text(
        "s01-parte-000.ts,0.0,3600.0\n", encoding="utf-8"
    )
    cfg = {
        "biblioteca": str(tmp_path), "segundos_antes": 60, "segundos_depois": 60,
        "margem_sem_alinhamento": 60, "caminho_ffmpeg": "ffmpeg",
        "caminho_ffprobe": "ffprobe", "limiar_confianca_db": 6.0,
        "cortes_em_paralelo": 1,
    }
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)
    monkeypatch.setattr(esteira, "ancorar_t0", lambda sessao, pasta: sessao)
    monkeypatch.setattr(esteira.cortador, "executar", lambda c: None)

    esteira.etapa_cortar([jogo, "--gols", "23:12:36"])

    clipe = catalogo.carregar(tmp_path / jogo)["clipes"][0]
    assert clipe["largo"] is True and clipe["duracao"] == 240.0
    assert clipe["parcial"] is False


def _jogo_com_um_canal(tmp_path: Path, jogo: str, nome: str = "canal") -> Path:
    pasta = tmp_path / jogo / "bruto" / nome
    pasta.mkdir(parents=True)
    (pasta / "gravacao.json").write_text(
        json.dumps({"url": "u", "sessoes": [{"numero": 1, "t0": "2026-09-02T23:00:00"}]}),
        encoding="utf-8",
    )
    (pasta / "s01-parte-000.ts").write_bytes(b"x")
    (pasta / "s01-segmentos.csv").write_text(
        "s01-parte-000.ts,0.0,3600.0\n", encoding="utf-8"
    )
    return tmp_path / jogo


def test_cortar_gols_e_o_mesmo_caminho_do_corte_a_mao(tmp_path: Path, monkeypatch):
    """Gol marcado durante o jogo corta igual a gol digitado depois."""
    pasta_jogo = _jogo_com_um_canal(tmp_path, "j")
    monkeypatch.setattr(esteira, "ancorar_t0", lambda sessao, pasta: sessao)
    monkeypatch.setattr(esteira.cortador, "executar", lambda c: None)
    cfg = {
        "biblioteca": str(tmp_path), "segundos_antes": 60, "segundos_depois": 60,
        "margem_sem_alinhamento": 0, "minimo_do_clipe": 15,
        "caminho_ffmpeg": "ffmpeg", "caminho_ffprobe": "ffprobe",
        "limiar_confianca_db": 6.0, "cortes_em_paralelo": 1,
    }

    dados = esteira.cortar_gols(
        pasta_jogo, [(1, datetime(2026, 9, 2, 23, 12, 36))], cfg, avisar=lambda t: None
    )

    assert [c["canal"] for c in dados["clipes"]] == ["canal"]
    assert dados["gols"][0]["numero"] == 1


def test_cortar_um_gol_nao_mexe_nos_clipes_dos_outros(tmp_path: Path, monkeypatch):
    """O corte automatico roda gol a gol; nao pode apagar o que ja foi cortado."""
    pasta_jogo = _jogo_com_um_canal(tmp_path, "j")
    monkeypatch.setattr(esteira, "ancorar_t0", lambda sessao, pasta: sessao)
    monkeypatch.setattr(esteira.cortador, "executar", lambda c: None)
    cfg = {
        "biblioteca": str(tmp_path), "segundos_antes": 60, "segundos_depois": 60,
        "margem_sem_alinhamento": 0, "minimo_do_clipe": 15,
        "caminho_ffmpeg": "ffmpeg", "caminho_ffprobe": "ffprobe",
        "limiar_confianca_db": 6.0, "cortes_em_paralelo": 1,
    }

    esteira.cortar_gols(pasta_jogo, [(1, datetime(2026, 9, 2, 23, 12, 36))], cfg, lambda t: None)
    dados = esteira.cortar_gols(
        pasta_jogo, [(2, datetime(2026, 9, 2, 23, 29, 3))], cfg, lambda t: None
    )

    assert sorted(g["numero"] for g in dados["gols"]) == [1, 2]
    assert sorted(c["gol"] for c in dados["clipes"]) == [1, 2]


# --- torcida obrigatoria ---------------------------------------------------


def test_cadastrar_sem_dizer_a_torcida_nao_grava_nada(monkeypatch, capsys, tmp_path: Path):
    """Sem torcida o canal some do video mais tarde, calado. Melhor recusar agora."""
    arquivo = tmp_path / "canais.json"
    monkeypatch.setattr(esteira.mod_canais, "ARQUIVO", arquivo)
    monkeypatch.setattr(esteira.config, "carregar", lambda: {"caminho_ytdlp": "yt"})
    monkeypatch.setattr(
        esteira.importar, "importar",
        lambda *a, **k: pytest.fail("nao podia nem ter tentado ler as URLs"),
    )

    codigo = esteira.etapa_canais(["um-jogo", "--importar", "https://y/1"])

    assert codigo == 2
    assert not arquivo.exists()
    assert "neutro" in capsys.readouterr().out


def test_cadastrar_com_torcida_normaliza_a_grafia(monkeypatch, tmp_path: Path):
    arquivo = tmp_path / "canais.json"
    monkeypatch.setattr(esteira.mod_canais, "ARQUIVO", arquivo)
    monkeypatch.setattr(esteira.config, "carregar", lambda: {"caminho_ytdlp": "yt", "teto_canais": 20})
    recebidas = []
    monkeypatch.setattr(
        esteira.importar, "importar",
        lambda urls, ytdlp, torcida="", **k: recebidas.append(torcida) or [],
    )

    esteira.etapa_canais(["um-jogo", "--torcida", " Grêmio ", "--importar", "https://y/1"])

    assert recebidas == ["gremio"]


def _jogo_para_torcida(tmp_path: Path) -> Path:
    pasta = tmp_path / "2026-09-03 gremio x internacional"
    for nome, torcida in (("paulo-brito", "inter"), ("baldasso-tv", ""), ("bage-tv", "")):
        canal = pasta / "bruto" / nome
        canal.mkdir(parents=True)
        (canal / "gravacao.json").write_text(
            json.dumps({"url": f"https://y/{nome}", "sessoes": [], "torcida": torcida}),
            encoding="utf-8",
        )
    catalogo.salvar(pasta, catalogo.novo(pasta.name))
    return pasta


def test_etapa_torcida_preenche_o_que_o_operador_disser(monkeypatch, tmp_path, capsys):
    pasta = _jogo_para_torcida(tmp_path)
    monkeypatch.setattr(esteira.config, "carregar", lambda: {"biblioteca": str(tmp_path)})
    monkeypatch.setattr(esteira.mod_canais, "ARQUIVO", tmp_path / "canais.json")

    codigo = esteira.etapa_torcida([pasta.name, "--definir", "baldasso-tv=inter", "bage-tv=Grêmio"])

    assert codigo == 0
    assert esteira.torcidas.gravadas(pasta) == {
        "bage-tv": "gremio", "baldasso-tv": "inter", "paulo-brito": "inter",
    }
    assert "SEM TORCIDA" not in capsys.readouterr().out


def test_etapa_torcida_puxa_do_cadastro_o_que_ele_ja_sabe(monkeypatch, tmp_path):
    """O cadastro e a origem: se ele sabe, o jogo velho nao precisa ser digitado."""
    pasta = _jogo_para_torcida(tmp_path)
    monkeypatch.setattr(esteira.config, "carregar", lambda: {"biblioteca": str(tmp_path)})
    monkeypatch.setattr(esteira.mod_canais, "ARQUIVO", tmp_path / "canais.json")
    monkeypatch.setattr(esteira, "_cadastro", lambda: {
        "j": [canais.Canal("BALDASSO TV", "https://y/1", True, "inter")]
    })

    esteira.etapa_torcida([pasta.name])

    assert esteira.torcidas.gravadas(pasta)["baldasso-tv"] == "inter"


def test_etapa_torcida_avisa_quem_ficou_faltando_e_ensina_o_comando(monkeypatch, tmp_path, capsys):
    pasta = _jogo_para_torcida(tmp_path)
    monkeypatch.setattr(esteira.config, "carregar", lambda: {"biblioteca": str(tmp_path)})
    monkeypatch.setattr(esteira.mod_canais, "ARQUIVO", tmp_path / "canais.json")
    monkeypatch.setattr(esteira, "_cadastro", lambda: {})

    codigo = esteira.etapa_torcida([pasta.name])

    saida = capsys.readouterr().out
    assert codigo == 0
    assert "SEM TORCIDA" in saida and "baldasso-tv" in saida and "bage-tv" in saida
    assert "--definir" in saida, "o aviso tem que trazer o comando pronto"


def test_etapa_torcida_recusa_canal_que_nao_existe(monkeypatch, tmp_path, capsys):
    pasta = _jogo_para_torcida(tmp_path)
    monkeypatch.setattr(esteira.config, "carregar", lambda: {"biblioteca": str(tmp_path)})
    monkeypatch.setattr(esteira.mod_canais, "ARQUIVO", tmp_path / "canais.json")
    monkeypatch.setattr(esteira, "_cadastro", lambda: {})

    codigo = esteira.etapa_torcida([pasta.name, "--definir", "fantasma=inter"])

    assert codigo == 2
    assert "fantasma" in capsys.readouterr().out


def _jogo_pronto_para_render(pasta: Path) -> dict:
    """Um jogo com placar, um gol e dois clipes da torcida que perdeu."""
    from nucleo import catalogo

    dados = catalogo.registrar_partida(
        catalogo.novo(pasta.name), "copa-do-brasil", "Grêmio", "Internacional"
    )
    dados = catalogo.registrar_placar(dados, 3, 1)
    dados = catalogo.registrar_gol(dados, 1, "2026-09-03T20:13:00", "")
    dados["gols"][0]["placar"] = [1, 0]
    for canal, db in [("farid-germano-filho", 15.2), ("paulo-brito", 7.8)]:
        dados = catalogo.registrar_clipe(
            dados, 1, canal, f"clipes/gol-01/{canal}.mp4", 100.0, db, True, "inter", 175.0
        )
    catalogo.salvar(pasta, dados)
    return dados


def test_etapa_render_monta_o_video_do_jogo(tmp_path: Path, monkeypatch):
    """A casca e fina: quem monta e o estudio, o comando so escolhe o jogo."""
    pasta = tmp_path / "2026-09-03 gremio x internacional"
    pasta.mkdir()
    _jogo_pronto_para_render(pasta)
    cfg = {
        "biblioteca": str(tmp_path),
        "caminho_ffmpeg": "ffmpeg.exe",
        "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
    }
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)
    comandos = []

    def executar(comando):
        comandos.append(comando)
        Path(comando[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(comando[-1]).write_bytes(b"x")

    monkeypatch.setattr(esteira.cortador, "executar", executar)

    codigo = esteira.etapa_render([pasta.name])

    from nucleo import estudio

    assert codigo == 0
    assert (pasta / "receita.json").is_file(), "a receita nasce na primeira montagem"
    assert estudio.estado(pasta)["rodando"] is False
    da_montagem = [c for c in comandos if "-filter_complex" in c or "concat" in c]
    assert len(da_montagem) == 4, "cartela, dois clipes e a emenda"


def test_etapa_limpar_apaga_os_intermediarios(tmp_path: Path, monkeypatch, capsys):
    from nucleo import estudio

    pasta = tmp_path / "2026-09-03 gremio x internacional"
    (pasta / estudio.PASTA_CACHE).mkdir(parents=True)
    (pasta / estudio.PASTA_CACHE / "peca.mp4").write_bytes(b"x" * 2048)
    monkeypatch.setattr(esteira.config, "carregar", lambda: {"biblioteca": str(tmp_path)})

    codigo = esteira.etapa_limpar([pasta.name])

    assert codigo == 0
    assert estudio.tamanho_do_cache(pasta) == 0
    assert "MB" in capsys.readouterr().out


def test_etapa_render_aceita_o_caminho_inteiro_do_jogo(tmp_path: Path, monkeypatch):
    """O painel manda o caminho, e nao o nome: a pasta do jogo pode nao estar
    dentro da biblioteca configurada, e ai o render montava um jogo vazio."""
    pasta = tmp_path / "fora-da-biblioteca" / "2026-09-03 gremio x internacional"
    pasta.mkdir(parents=True)
    _jogo_pronto_para_render(pasta)
    cfg = {
        "biblioteca": str(tmp_path / "outra"),
        "caminho_ffmpeg": "ffmpeg.exe",
        "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
    }
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)

    def executar(comando):
        Path(comando[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(comando[-1]).write_bytes(b"x")

    monkeypatch.setattr(esteira.cortador, "executar", executar)

    codigo = esteira.etapa_render([str(pasta)])

    assert codigo == 0
    assert (pasta / "saida" / "compilacao-deitado.mp4").is_file()


def test_o_render_entrega_video_capa_e_publicar_md(tmp_path: Path, monkeypatch):
    """Tres pecas saem de cada jogo, e o operador nao devia ter que pedir cada uma."""
    from PIL import Image

    pasta = tmp_path / "2026-09-03 gremio x internacional"
    pasta.mkdir()
    _jogo_pronto_para_render(pasta)
    cfg = {
        "biblioteca": str(tmp_path),
        "caminho_ffmpeg": "ffmpeg.exe",
        "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
    }
    monkeypatch.setattr(esteira.config, "carregar", lambda: cfg)

    def executar(comando):
        destino = Path(comando[-1])
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.suffix == ".jpg":
            Image.new("RGB", (640, 360), (0, 200, 0)).save(destino)
        else:
            destino.write_bytes(b"x")

    monkeypatch.setattr(esteira.cortador, "executar", executar)

    esteira.etapa_render([str(pasta)])

    assert (pasta / "saida" / "compilacao-deitado.mp4").is_file()
    assert (pasta / "saida" / "capa.jpg").is_file()
    assert (pasta / "saida" / "publicar.md").is_file()


# --------------------------------------------------------- o instante do pico

def _wav_com_pico(destino: Path, duracao: float, pico_em: float) -> Path:
    """Um wav de verdade: quase silencio e uma explosao curta na hora marcada.

    O detector nao e enganado por mock nenhum - ele mede energia RMS. Entao o
    jeito honesto de testar "o instante que voltou e o do pico" e dar a ele um
    audio em que se sabe onde o pico esta.
    """
    import math
    import wave

    taxa = 16000
    amostras = []
    for indice in range(int(duracao * taxa)):
        segundo = indice / taxa
        alto = pico_em <= segundo < pico_em + 6.0
        volume = 12000 if alto else 300
        amostras.append(int(volume * math.sin(2 * math.pi * 220 * segundo)))
    destino.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(b"".join(int(a).to_bytes(2, "little", signed=True) for a in amostras))
    return destino


def test_medir_reacao_devolve_o_instante_do_pico(tmp_path: Path):
    """O detector ja sabe onde o grito comeca; jogar esse numero fora custou o video.

    No jogo de 03/09 o `instante` gravado era o deslocamento dentro do .ts de
    origem, e nao o pico dentro do clipe - por isso a janela proposta pegava o
    minuto ANTES do gol e o video saiu sem reacao nenhuma.
    """
    clipe = tmp_path / "peixao.mp4"
    clipe.write_bytes(b"nao importa: quem le o audio e o wav")

    forca, tem_pico, instante = esteira.medir_reacao(
        clipe, CFG_CORTE, executar=lambda c: _wav_com_pico(Path(c[-1]), 100.0, 80.0),
        duracao=100.0,
    )

    assert tem_pico is True and forca > 6.0
    assert 74.0 <= instante <= 82.0, f"o pico esta em 80s, voltou {instante}"


def test_medir_reacao_sem_audio_legivel_devolve_instante_zero(tmp_path: Path):
    """Medir e um luxo para ordenar a lista; falhar nele nao pode custar o clipe."""
    clipe = tmp_path / "peixao.mp4"
    clipe.write_bytes(b"nao e video")

    assert esteira.medir_reacao(clipe, CFG_CORTE, executar=lambda c: None) == (
        0.0, False, 0.0
    )
    assert not (tmp_path / "peixao.wav").exists(), "o wav de medicao nao pode ficar"


def test_o_instante_do_clipe_e_o_pico_e_nao_o_deslocamento_da_fonte(tmp_path: Path):
    """O que vai para o catalogo tem que ser medido DENTRO do clipe cortado."""
    (tmp_path / "a.ts").write_bytes(b"x")
    destino = tmp_path / "clipes"
    destino.mkdir()

    def executar(comando):
        alvo = Path(comando[-1])
        if alvo.suffix == ".wav":
            _wav_com_pico(alvo, 120.0, 70.0)
        else:
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(b"clipe de mentira")

    plano = esteira.PlanoDoCanal(
        "peixao", [relogio.Trecho("a.ts", 42.0, 162.0)], 120.0, False, False
    )
    clipe = esteira.cortar_um_canal(plano, tmp_path, 1, destino, CFG_CORTE, executar)

    assert clipe.deslocamento == 42.0, "de onde se cortou continua sendo 42s"
    assert 64.0 <= clipe.instante <= 72.0, f"o pico esta em 70s, veio {clipe.instante}"


def _jogo_ja_cortado(pasta: Path, instante: float = 0.0) -> dict:
    """Um jogo como os de antes do conserto: clipe no disco, `instante` errado."""
    dados = catalogo.novo(pasta.name)
    dados = catalogo.registrar_gol(dados, 1, "2026-09-03T20:13:32", "")
    for canal in ("farid-germano-filho", "baldasso-tv"):
        arquivo = pasta / "clipes" / "gol-01" / f"{canal}.mp4"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_bytes(b"clipe de mentira")
        dados = catalogo.registrar_clipe(
            dados, 1, canal, f"clipes/gol-01/{canal}.mp4",
            instante, 0.0, False, "inter", 120.0,
        )
    catalogo.salvar(pasta, dados)
    return dados


def test_remedir_recalcula_o_instante_dos_clipes_que_ja_estao_no_disco(tmp_path: Path):
    """Os jogos cortados antes do conserto ficaram com o `instante` errado no disco.

    Refazer o corte deles seria uma hora de recodificacao; medir de novo o audio
    de um clipe que ja existe leva segundos e nao toca em video nenhum.
    """
    _jogo_ja_cortado(tmp_path)

    esteira.remedir_clipes(
        tmp_path, CFG_CORTE, avisar=lambda t: None,
        executar=lambda c: _wav_com_pico(Path(c[-1]), 120.0, 70.0),
    )

    depois = catalogo.carregar(tmp_path)
    for clipe in depois["clipes"]:
        assert 64.0 <= clipe["instante"] <= 72.0, clipe
        assert clipe["tem_pico"] is True and clipe["confianca_db"] > 6.0


def test_remedir_nao_recodifica_video_nenhum(tmp_path: Path):
    _jogo_ja_cortado(tmp_path)
    comandos = []

    esteira.remedir_clipes(
        tmp_path, CFG_CORTE, avisar=lambda t: None,
        executar=lambda c: (comandos.append(c), _wav_com_pico(Path(c[-1]), 120.0, 70.0))[1],
    )

    for comando in comandos:
        assert comando[-1].endswith(".wav"), f"remedir pediu video ao ffmpeg: {comando}"
        assert "libx264" not in " ".join(comando)


def test_remedir_avisa_o_clipe_que_nao_da_para_ler_e_nao_o_apaga(tmp_path: Path):
    """Os tres clipes do gol 5 de 03/09 sairam sem `moov`, de um corte interrompido.

    Nunca sumir calado: quem nao da para medir e nomeado, e continua no catalogo
    com zero - o painel ja mostra clipe sem pico como fraco.
    """
    _jogo_ja_cortado(tmp_path, instante=3.0)
    ditos = []

    esteira.remedir_clipes(
        tmp_path, CFG_CORTE, avisar=ditos.append, executar=lambda c: None
    )

    depois = catalogo.carregar(tmp_path)
    assert len(depois["clipes"]) == 2, "clipe ilegivel nao sai do catalogo"
    recado = " ".join(ditos)
    assert "baldasso-tv" in recado and "farid-germano-filho" in recado
    assert "ILEGIVEL" in recado.upper()


def test_etapa_remedir_roda_no_jogo_pedido(tmp_path: Path, monkeypatch, capsys):
    """A casca do comando: acha o jogo na biblioteca e manda medir."""
    biblioteca = tmp_path / "MIDIA"
    pasta = biblioteca / "2026-09-03 gremio x internacional"
    pasta.mkdir(parents=True)
    _jogo_ja_cortado(pasta)
    monkeypatch.setattr(
        esteira.config, "carregar", lambda *a, **k: {**CFG_CORTE, "biblioteca": str(biblioteca)}
    )
    monkeypatch.setattr(
        esteira, "remedir_clipes",
        lambda p, cfg, avisar=print, **k: (print(f"medi {Path(p).name}"), {})[1],
    )

    codigo = esteira.etapa_remedir(["2026-09-03 gremio x internacional"])

    assert codigo == 0
    assert "medi 2026-09-03 gremio x internacional" in capsys.readouterr().out
