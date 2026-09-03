import os
import time
import json
from datetime import datetime
from pathlib import Path

from nucleo import canais, gravador

CFG = {
    "altura_maxima": 720,
    "duracao_pedaco": 600,
    "teto_canais": 20,
    "disco_minimo_gb": 60,
    "caminho_ytdlp": r"C:\yt-dlp\yt-dlp.exe",
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
}


def test_comando_respeita_as_travas_do_projeto(tmp_path: Path):
    cmd = gravador.comando("https://x/watch?v=1", tmp_path, 1, CFG)

    assert "height<=720" in cmd, "trava de banda: nunca 1080p"
    assert "-c copy" in cmd, "gravacao nao recodifica"
    assert "mpegts" in cmd, "mp4 interrompido fica ilegivel"
    assert "-segment_time 600" in cmd
    assert "segment_list" in cmd and "csv" in cmd
    assert cmd.count("|") == 1, "e um cano de yt-dlp para ffmpeg"


def test_comando_pede_runtime_js_e_saida_em_ts(tmp_path: Path):
    """Sem runtime JS o yt-dlp avisa que a extracao esta obsoleta e perde formato.

    O node ja esta na maquina (projeto LEGENDAR VIDEO), mas o yt-dlp so o usa
    quando mandam. Sem `--hls-use-mpegts` a saida padrao nao vira TS e o ffmpeg
    do outro lado do cano nao le nada.
    """
    cmd = gravador.comando("https://x/watch?v=1", tmp_path, 1, CFG)

    assert "--js-runtimes node" in cmd
    assert "--hls-use-mpegts" in cmd


def test_sessoes_diferentes_nao_sobrescrevem_arquivos(tmp_path: Path):
    um = gravador.comando("https://x", tmp_path, 1, CFG)
    dois = gravador.comando("https://x", tmp_path, 2, CFG)
    assert "s01" in um and "s02" in dois
    assert um != dois


def test_apelido_vira_nome_de_pasta_seguro():
    assert gravador.apelido("Canal do Cruzeiro Ao Vivo!") == "canal-do-cruzeiro-ao-vivo"
    assert gravador.apelido("Seleção É 10") == "selecao-e-10"


def test_espaco_insuficiente_impede_comecar(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(gravador, "espaco_livre_gb", lambda caminho: 12.0)
    try:
        gravador.verificar_espaco(tmp_path, 60)
    except RuntimeError as erro:
        assert "12" in str(erro) and "60" in str(erro)
    else:
        raise AssertionError("deveria ter recusado")


def test_acima_do_teto_avisa_mas_nao_bloqueia():
    assert gravador.avaliar_banda(13, teto=20) is None
    aviso = gravador.avaliar_banda(25, teto=20)
    assert aviso is not None and "25" in aviso and "20" in aviso


def test_gravacao_json_guarda_o_horario_do_primeiro_frame(tmp_path: Path):
    t0 = datetime(2026, 9, 1, 21, 0, 0)
    arquivo = gravador.escrever_gravacao(tmp_path, "https://x", 1, t0)
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dados["sessoes"][0]["t0"] == "2026-09-01T21:00:00"
    assert dados["sessoes"][0]["numero"] == 1


def test_segunda_sessao_e_acrescentada_e_nao_apaga_a_primeira(tmp_path: Path):
    gravador.escrever_gravacao(tmp_path, "https://x", 1, datetime(2026, 9, 1, 21, 0, 0))
    arquivo = gravador.escrever_gravacao(
        tmp_path, "https://x", 2, datetime(2026, 9, 1, 21, 27, 0)
    )
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert [s["numero"] for s in dados["sessoes"]] == [1, 2]


def test_iniciar_abre_um_processo_por_canal_escolhido(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(gravador, "espaco_livre_gb", lambda caminho: 300.0)
    abertos = []

    def abrir_falso(comando, pasta):
        abertos.append(comando)
        return object()

    escolhidos = [
        (canais.Canal("A", "https://x/watch?v=1", True), "https://x/watch?v=1"),
        (canais.Canal("B", "https://x/watch?v=2", True), "https://x/watch?v=2"),
    ]
    processos = gravador.iniciar(
        escolhidos, tmp_path, "jogo-teste", CFG, abrir=abrir_falso
    )

    assert len(processos) == 2
    assert len(abertos) == 2
    assert (tmp_path / "jogo-teste" / "bruto" / "a" / "gravacao.json").is_file()


class ProcessoFalso:
    """Devolve None enquanto vivo; um codigo de saida depois de `vive_por` conferencias."""

    def __init__(self, vive_por: int = 999):
        self.vive_por = vive_por
        self.conferencias = 0

    def poll(self):
        self.conferencias += 1
        return None if self.conferencias <= self.vive_por else 1


SUPERVISAO = {**CFG, "segundos_entre_conferencias": 0}


def test_processo_vivo_nao_e_reiniciado(tmp_path: Path):
    abertos = []
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso()
    )

    gravador.supervisionar(
        [pr], SUPERVISAO,
        abrir=lambda c, p: abertos.append(c), dormir=lambda s: None, voltas=3,
    )

    assert abertos == []
    assert pr.sessao == 1


def test_gravacao_que_cai_volta_em_nova_sessao(tmp_path: Path):
    gravador.escrever_gravacao(tmp_path, "https://x", 1, datetime(2026, 9, 1, 21, 0, 0))
    abertos = []
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso(vive_por=1)
    )

    gravador.supervisionar(
        [pr], SUPERVISAO,
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(),
        dormir=lambda s: None, voltas=2,
    )

    assert pr.sessao == 2
    assert len(abertos) == 1
    assert "s02" in abertos[0], "a nova sessao nao pode sobrescrever os arquivos da s01"
    dados = json.loads((tmp_path / "gravacao.json").read_text(encoding="utf-8"))
    assert [s["numero"] for s in dados["sessoes"]] == [1, 2]


def test_desiste_do_canal_depois_de_muitas_quedas_seguidas(tmp_path: Path):
    """Live encerrada de verdade: nao pode ficar religando pra sempre."""
    abertos = []
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso(vive_por=0)
    )
    lista = [pr]

    gravador.supervisionar(
        lista, SUPERVISAO,
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(vive_por=0),
        dormir=lambda s: None, voltas=20,
    )

    assert len(abertos) == gravador.MAX_TENTATIVAS
    assert lista == [], "canal desistido sai da lista e o laco termina"


def test_um_canal_desistindo_nao_derruba_o_outro(tmp_path: Path):
    pasta_a = tmp_path / "a"
    pasta_b = tmp_path / "b"
    pasta_a.mkdir()
    pasta_b.mkdir()
    ruim = gravador.Processo(
        canais.Canal("Ruim", "u", True), "https://r", pasta_a, 1, ProcessoFalso(vive_por=0)
    )
    bom = gravador.Processo(
        canais.Canal("Bom", "u", True), "https://b", pasta_b, 1, ProcessoFalso()
    )
    lista = [ruim, bom]

    gravador.supervisionar(
        lista, SUPERVISAO,
        abrir=lambda c, p: ProcessoFalso(vive_por=0),
        dormir=lambda s: None, voltas=20,
    )

    assert [p.canal.nome for p in lista] == ["Bom"]


class ProcessoEmperrado:
    """Vivo para sempre, mas nao escreve nada. E o caso que enganava o supervisor."""

    def __init__(self):
        self.morto = False

    def poll(self):
        return 1 if self.morto else None

    def kill(self):
        self.morto = True


def test_gravacao_que_emperra_com_o_processo_vivo_e_derrubada_e_religada(tmp_path: Path):
    """Medido em jogo: o download morre e o processo continua de pe, mudo."""
    travado = ProcessoEmperrado()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, travado,
        inicio=time.time() - 300,  # nada escrito ha cinco minutos
    )
    abertos = []

    gravador.supervisionar(
        [pr], {**SUPERVISAO, "segundos_sem_crescer": 90},
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(),
        dormir=lambda s: None, voltas=1,
    )

    assert travado.morto, "processo emperrado tem que ser derrubado"
    assert pr.sessao == 2 and len(abertos) == 1


def test_pedaco_crescendo_conta_como_gravacao_viva(tmp_path: Path):
    (tmp_path / "s01-parte-000.ts").write_bytes(b"x")  # escrito agora
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoEmperrado(),
        inicio=time.time() - 300,
    )
    abertos = []

    gravador.supervisionar(
        [pr], {**SUPERVISAO, "segundos_sem_crescer": 90},
        abrir=lambda c, p: abertos.append(c), dormir=lambda s: None, voltas=1,
    )

    assert abertos == [] and pr.sessao == 1


def test_sessao_recem_aberta_tem_folga_para_o_ytdlp_negociar(tmp_path: Path):
    """Nos primeiros segundos ainda nao existe .ts nenhum - nao e travamento."""
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoEmperrado()
    )

    assert not gravador.travou(pr, 90, time.time())


def test_sessao_que_gravou_de_verdade_zera_o_contador_de_quedas(tmp_path: Path):
    """Religar nao pode gastar as cinco chances: o contador e para live encerrada.

    Uma gravacao que roda um bom tempo e cai e outra historia de uma live que
    morre no mesmo segundo, toda vez. Sem zerar, um canal saudavel que reconecta
    algumas vezes seria abandonado no meio do jogo.
    """
    pedaco = tmp_path / "s01-parte-000.ts"
    pedaco.write_bytes(b"x")
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1,
        ProcessoFalso(vive_por=0), tentativas=4,
        inicio=time.time() - 600,  # gravou dez minutos antes de cair
    )
    lista = [pr]

    gravador.supervisionar(
        lista, SUPERVISAO,
        abrir=lambda c, p: ProcessoFalso(), dormir=lambda s: None, voltas=1,
    )

    assert pr.tentativas == 1, "gravou muito antes de cair: recomeca a contagem"
    assert lista == [pr], "canal produtivo nao pode ser abandonado"


class TarefaPronta:
    def __init__(self, valor=None, erro=None):
        self.valor, self.erro = valor, erro

    def done(self):
        return True

    def result(self):
        if self.erro:
            raise self.erro
        return self.valor


class TarefasFalsas:
    """Executa na hora, para o teste nao depender de thread nem de relogio."""

    def __init__(self):
        self.pedidos = []

    def submit(self, funcao, *args):
        self.pedidos.append(args)
        try:
            return TarefaPronta(valor=funcao(*args))
        except Exception as erro:
            return TarefaPronta(erro=erro)


def test_live_encerrada_faz_o_supervisor_trocar_de_endereco(tmp_path: Path):
    """Live encerrada nao volta na mesma URL: o canal abre outra."""
    tarefas = TarefasFalsas()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://www.youtube.com/watch?v=VELHA",
        tmp_path, 1, ProcessoFalso(vive_por=0),
    )
    abertos = []

    gravador.supervisionar(
        [pr], SUPERVISAO,
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(vive_por=0),
        dormir=lambda s: None, voltas=3, tarefas=tarefas,
        procurar=lambda url, ytdlp, canal: (
            "https://www.youtube.com/watch?v=NOVA", "https://youtube.com/@a"
        ),
    )

    assert pr.url == "https://www.youtube.com/watch?v=NOVA"
    assert pr.canal_url == "https://youtube.com/@a"
    assert any("NOVA" in c for c in abertos), "a nova sessao ja usa o endereco novo"


def test_a_primeira_queda_nao_manda_procurar_live_nova(tmp_path: Path):
    """Queda solta e solucao de rede: religar na mesma URL resolve e e barato."""
    tarefas = TarefasFalsas()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso(vive_por=0)
    )

    gravador.supervisionar(
        [pr], SUPERVISAO, abrir=lambda c, p: ProcessoFalso(),
        dormir=lambda s: None, voltas=1, tarefas=tarefas,
        procurar=lambda *a: ("", ""),
    )

    assert tarefas.pedidos == []


def test_endereco_do_canal_ja_descoberto_e_reaproveitado(tmp_path: Path):
    tarefas = TarefasFalsas()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1,
        ProcessoFalso(vive_por=0), canal_url="https://youtube.com/@ja-sabia",
    )

    gravador.supervisionar(
        [pr], SUPERVISAO, abrir=lambda c, p: ProcessoFalso(vive_por=0),
        dormir=lambda s: None, voltas=3, tarefas=tarefas,
        procurar=lambda *a: ("", ""),
    )

    assert all(pedido[2] == "https://youtube.com/@ja-sabia" for pedido in tarefas.pedidos)


def test_busca_que_estoura_nao_derruba_a_gravacao(tmp_path: Path):
    """Procurar e um luxo: falhar nele nao pode custar o jogo."""
    tarefas = TarefasFalsas()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso(vive_por=0)
    )
    lista = [pr]

    def explode(*a):
        raise RuntimeError("yt-dlp sumiu")

    gravador.supervisionar(
        lista, SUPERVISAO, abrir=lambda c, p: ProcessoFalso(vive_por=0),
        dormir=lambda s: None, voltas=4, tarefas=tarefas, procurar=explode,
    )

    assert pr.url == "https://x" and lista == [pr]


def _pasta_gravando(tmp_path: Path, nome: str, sessao: int, pid: int, idade: float) -> Path:
    pasta = tmp_path / nome
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "gravacao.json").write_text(
        json.dumps({
            "url": "https://www.youtube.com/watch?v=ATUAL",
            "sessoes": [{"numero": sessao, "t0": "2026-09-02T21:30:00", "pid": pid}],
        }),
        encoding="utf-8",
    )
    ts = pasta / f"s{sessao:02d}-parte-000.ts"
    ts.write_bytes(b"x" * 1000)
    marca = time.time() - idade
    os.utime(ts, (marca, marca))
    return pasta


def test_gravacao_em_andamento_e_adotada_em_vez_de_duplicada(tmp_path: Path):
    """Trocar o codigo do supervisor nao pode custar o jogo inteiro."""
    pasta = _pasta_gravando(tmp_path, "peixao", sessao=3, pid=4321, idade=2)

    adotado = gravador.adotar(
        canais.Canal("Peixao", "https://outra", True), pasta,
        {"segundos_sem_crescer": 45}, time.time(),
    )

    assert adotado is not None
    assert adotado.sessao == 3, "continua na sessao que ja estava rodando"
    assert adotado.url == "https://www.youtube.com/watch?v=ATUAL", (
        "vale o endereco que esta gravando, que o religador pode ter trocado"
    )
    assert adotado.processo.pid == 4321


def test_pasta_parada_ha_tempo_nao_e_adotada(tmp_path: Path):
    pasta = _pasta_gravando(tmp_path, "morto", sessao=1, pid=1, idade=600)

    assert gravador.adotar(
        canais.Canal("Morto", "u", True), pasta,
        {"segundos_sem_crescer": 45}, time.time(),
    ) is None


def test_pasta_nova_nao_tem_o_que_adotar(tmp_path: Path):
    (tmp_path / "novo").mkdir()

    assert gravador.adotar(
        canais.Canal("Novo", "u", True), tmp_path / "novo",
        {"segundos_sem_crescer": 45}, time.time(),
    ) is None


def test_adotado_se_diz_vivo_e_quem_julga_e_o_disco(tmp_path: Path):
    """Nao ha handle: o dono do processo era outro Python, que ja morreu."""
    adotado = gravador.Adotado(pid=999)

    assert adotado.poll() is None

    pr = gravador.Processo(
        canais.Canal("A", "u", True), "u", tmp_path, 1, adotado,
        inicio=time.time() - 300,
    )
    assert gravador.travou(pr, 45, time.time()), "sem byte novo, o disco condena"


def test_derrubar_adotado_mata_a_arvore_inteira(tmp_path: Path):
    """Sem o /T o cmd morre e o ffmpeg fica orfao, gravando para sempre."""
    comandos = []
    gravador.derrubar_arvore(4321, rodar=comandos.append)

    assert comandos == [["taskkill", "/T", "/F", "/PID", "4321"]]


def test_derrubar_sem_pid_nao_faz_nada():
    comandos = []
    gravador.derrubar_arvore(None, rodar=comandos.append)
    assert comandos == []


def test_iniciar_adota_quem_ja_grava_e_sobe_so_o_resto(tmp_path: Path):
    biblioteca = tmp_path / "lib"
    jogo = "2026-09-02 santos x palmeiras"
    vivo = canais.Canal("Peixao", "https://a", True)
    parado = canais.Canal("Novato", "https://b", True)
    pasta_viva = gravador.pasta_do_canal(biblioteca, jogo, vivo)
    pasta_viva.mkdir(parents=True)
    _pasta_gravando(pasta_viva.parent, pasta_viva.name, sessao=2, pid=77, idade=1)
    abertos = []

    processos = gravador.iniciar(
        [(vivo, "https://a"), (parado, "https://b")], biblioteca, jogo,
        {**CFG, "segundos_sem_crescer": 45, "disco_minimo_gb": 0},
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(),
    )

    assert len(processos) == 2
    assert len(abertos) == 1, "so o canal que nao estava gravando foi aberto"
    assert "Novato".lower() in abertos[0].lower() or "https://b" in abertos[0]
    adotado, novo = processos
    assert isinstance(adotado.processo, gravador.Adotado)
    assert adotado.sessao == 2 and novo.sessao == 1


def test_sessao_nova_nunca_reaproveita_numero_ja_usado(tmp_path: Path):
    """Reaproveitar sobrescreveria os pedacos que ja estao no disco."""
    biblioteca = tmp_path / "lib"
    jogo = "j"
    canal = canais.Canal("Peixao", "https://a", True)
    pasta = gravador.pasta_do_canal(biblioteca, jogo, canal)
    pasta.mkdir(parents=True)
    _pasta_gravando(pasta.parent, pasta.name, sessao=4, pid=9, idade=999)  # parou

    processos = gravador.iniciar(
        [(canal, "https://a")], biblioteca, jogo,
        {**CFG, "segundos_sem_crescer": 45, "disco_minimo_gb": 0},
        abrir=lambda c, p: ProcessoFalso(),
    )

    assert processos[0].sessao == 5


def test_o_pid_da_sessao_vai_para_o_disco(tmp_path: Path):
    class ComPid(ProcessoFalso):
        pid = 5150

    gravador.iniciar(
        [(canais.Canal("A", "https://a", True), "https://a")], tmp_path, "j",
        {**CFG, "disco_minimo_gb": 0}, abrir=lambda c, p: ComPid(),
    )

    pasta = gravador.pasta_do_canal(tmp_path, "j", canais.Canal("A", "https://a", True))
    dados = json.loads((pasta / "gravacao.json").read_text(encoding="utf-8"))
    assert dados["sessoes"][-1]["pid"] == 5150


def test_teto_de_banda_conta_os_canais_dos_dois_jogos(tmp_path: Path):
    """Cada jogo tem seu supervisor; sozinho, cada um so via metade da banda."""
    _pasta_gravando(tmp_path / "jogo A" / "bruto", "um", 1, 1, idade=2)
    _pasta_gravando(tmp_path / "jogo A" / "bruto", "dois", 1, 2, idade=2)
    _pasta_gravando(tmp_path / "jogo B" / "bruto", "tres", 1, 3, idade=2)
    _pasta_gravando(tmp_path / "jogo B" / "bruto", "parado", 1, 4, idade=999)

    de_fora = gravador.gravando_em_outros_jogos(tmp_path, "jogo B", time.time(), 45)

    assert de_fora == 2, "os dois do jogo A; o parado do proprio jogo nao conta"


def test_biblioteca_sem_outros_jogos_nao_soma_nada(tmp_path: Path):
    assert gravador.gravando_em_outros_jogos(tmp_path, "j", time.time(), 45) == 0
    assert gravador.gravando_em_outros_jogos(tmp_path / "nao-existe", "j", time.time(), 45) == 0


def test_disco_acabando_no_meio_do_jogo_avisa(tmp_path: Path, monkeypatch):
    """Conferir so ao comecar nao bastava: duas partidas comem dezenas de GB."""
    monkeypatch.setattr(gravador, "espaco_livre_gb", lambda caminho: 8.0)
    pr = gravador.Processo(canais.Canal("A", "u", True), "u", tmp_path, 1, ProcessoFalso())
    ditos = []

    ok = gravador.conferir_disco([pr], {"disco_minimo_gb": 60}, ditos.append)

    assert not ok
    assert any("8 GB" in d and "AGORA" in d for d in ditos)


def test_disco_folgado_nao_reclama(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(gravador, "espaco_livre_gb", lambda caminho: 300.0)
    pr = gravador.Processo(canais.Canal("A", "u", True), "u", tmp_path, 1, ProcessoFalso())
    ditos = []

    assert gravador.conferir_disco([pr], {"disco_minimo_gb": 60}, ditos.append)
    assert ditos == []


def test_conferir_disco_sem_canal_nenhum_nao_estoura():
    assert gravador.conferir_disco([], {"disco_minimo_gb": 60}, lambda t: None)


CFG_ATRASO = {
    **CFG, "caminho_ffprobe": "ffprobe", "atraso_maximo": 300,
    "carencia_do_arranque": 120, "segundos_entre_conferencias": 0,
    "segundos_sem_crescer": 45, "disco_minimo_gb": 0,
}


def _sessao_no_disco(pasta: Path, sessao: int, fechados: list[tuple[str, float]]) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    prefixo = f"s{sessao:02d}"
    linhas = [f"{nome},{i * 300.0},{fim}" for i, (nome, fim) in enumerate(fechados)]
    (pasta / f"{prefixo}-segmentos.csv").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    for nome, _ in fechados:
        (pasta / nome).write_bytes(b"x")


def test_conteudo_soma_o_csv_com_o_pedaco_ainda_aberto(tmp_path: Path, monkeypatch):
    """O CSV so ganha linha quando o pedaco fecha; o aberto tem minutos dentro."""
    _sessao_no_disco(tmp_path, 1, [("s01-parte-000.ts", 300.0), ("s01-parte-001.ts", 600.0)])
    (tmp_path / "s01-parte-002.ts").write_bytes(b"x")  # aberto, fora do CSV
    monkeypatch.setattr(gravador.cortador, "duracao", lambda a, f: 137.0)

    assert gravador.conteudo_da_sessao(tmp_path, 1, "ffprobe") == 737.0


def test_sessao_sem_nada_no_disco_tem_conteudo_zero(tmp_path: Path):
    assert gravador.conteudo_da_sessao(tmp_path, 1, "ffprobe") == 0.0


def test_canal_que_baixa_mais_devagar_que_o_jogo_e_pego(tmp_path: Path, monkeypatch):
    """Escreve bytes o tempo todo, passa por saudavel - e nao tem o gol no disco."""
    _sessao_no_disco(tmp_path, 1, [("s01-parte-000.ts", 1800.0)])
    monkeypatch.setattr(gravador.cortador, "duracao", lambda a, f: 0.0)
    agora = time.time()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "u", tmp_path, 1, ProcessoFalso(),
        inicio_sessao=agora - 5400,  # noventa minutos gravando
    )

    assert round(gravador.atraso_do_ao_vivo(pr, CFG_ATRASO, agora)) == 3600
    assert gravador.ficou_para_tras(pr, CFG_ATRASO, agora)


def test_canal_no_ritmo_do_jogo_nao_e_acusado(tmp_path: Path, monkeypatch):
    _sessao_no_disco(tmp_path, 1, [("s01-parte-000.ts", 5400.0)])
    monkeypatch.setattr(gravador.cortador, "duracao", lambda a, f: 0.0)
    agora = time.time()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "u", tmp_path, 1, ProcessoFalso(),
        inicio_sessao=agora - 5460,  # 60s de atraso: o normal do HLS
    )

    assert not gravador.ficou_para_tras(pr, CFG_ATRASO, agora)


def test_sessao_recem_aberta_tem_carencia_para_o_arranque(tmp_path: Path, monkeypatch):
    """No comeco o yt-dlp ainda negocia: acusar ai derrubaria todo canal saudavel."""
    monkeypatch.setattr(gravador.cortador, "duracao", lambda a, f: 0.0)
    agora = time.time()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "u", tmp_path, 1, ProcessoFalso(),
        inicio_sessao=agora - 30,
    )

    assert not gravador.ficou_para_tras(pr, CFG_ATRASO, agora)


def test_supervisor_recomeca_o_canal_que_ficou_para_tras(tmp_path: Path, monkeypatch):
    _sessao_no_disco(tmp_path, 1, [("s01-parte-000.ts", 600.0)])
    monkeypatch.setattr(gravador.cortador, "duracao", lambda a, f: 0.0)
    travado = ProcessoEmperrado()
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "u", tmp_path, 1, travado,
        inicio=time.time(), inicio_sessao=time.time() - 5400, tentativas=3,
    )
    abertos = []

    gravador.supervisionar(
        [pr], CFG_ATRASO,
        abrir=lambda c, p: abertos.append(c) or ProcessoFalso(),
        dormir=lambda s: None, voltas=1, tarefas=TarefasFalsas(),
        procurar=lambda *a: ("", ""),
    )

    assert travado.morto, "so recomecando da para voltar a ponta do ao vivo"
    assert pr.sessao == 2 and len(abertos) == 1
    assert pr.tentativas == 0, "corrigir o rumo nao e queda: nao gasta tentativa"


def test_adotado_herda_o_t0_verdadeiro_da_sessao(tmp_path: Path):
    """Sem isso, o atraso de um canal adotado seria medido a partir da adocao."""
    pasta = _pasta_gravando(tmp_path, "peixao", sessao=1, pid=1, idade=2)
    dados = json.loads((pasta / "gravacao.json").read_text(encoding="utf-8"))
    dados["sessoes"][0]["t0"] = datetime(2026, 9, 2, 21, 30, 0).isoformat()
    (pasta / "gravacao.json").write_text(json.dumps(dados), encoding="utf-8")

    adotado = gravador.adotar(
        canais.Canal("P", "u", True), pasta, {"segundos_sem_crescer": 45}, time.time()
    )

    assert adotado.inicio_sessao == datetime(2026, 9, 2, 21, 30, 0).timestamp()
