import json
from datetime import datetime, timedelta
from pathlib import Path

from nucleo import catalogo, placar, vigia


def _partida(gc=0, gf=0, estado="STATUS_SECOND_HALF"):
    return placar.Partida("1", "Vitória", "Vasco da Gama", gc, gf, estado)


def _relogio(inicio=datetime(2026, 9, 2, 23, 0, 0)):
    """Relogio falso que anda 20s a cada olhada, como o laco de verdade."""
    passos = iter(range(0, 10000, 20))
    return lambda: inicio + timedelta(seconds=next(passos))


def test_gol_no_placar_vira_marca_no_catalogo(tmp_path: Path):
    respostas = iter([[_partida(0, 0)], [_partida(0, 1)]])

    marcados = vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=2,
        buscar=lambda liga: next(respostas), agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    assert marcados == [1]
    dados = catalogo.carregar(tmp_path)
    assert dados["gols"][0]["origem"] == "espn"
    assert dados["gols"][0]["confirmado"] is False, "so o audio acha o instante certo"


def test_a_primeira_leitura_nunca_marca_gol(tmp_path: Path):
    """Entrar num jogo que ja esta 2x0 nao pode gerar dois cortes do nada."""
    marcados = vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=1,
        buscar=lambda liga: [_partida(2, 0)], agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    assert marcados == []
    assert catalogo.carregar(tmp_path)["gols"] == []


def test_placar_parado_nao_marca_nada(tmp_path: Path):
    marcados = vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=5,
        buscar=lambda liga: [_partida(1, 1)], agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    assert marcados == []


def test_dois_gols_entre_consultas_viram_duas_marcas(tmp_path: Path):
    respostas = iter([[_partida(0, 0)], [_partida(1, 1)]])

    marcados = vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=2,
        buscar=lambda liga: next(respostas), agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    assert marcados == [1, 2]


def test_gol_anulado_pelo_var_nao_apaga_nem_inverte(tmp_path: Path):
    respostas = iter([[_partida(0, 0)], [_partida(1, 0)], [_partida(0, 0)]])

    marcados = vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=3,
        buscar=lambda liga: next(respostas), agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    assert marcados == [1], "o gol anulado ja tinha sido marcado; some no painel, na mao"


def test_o_laco_para_sozinho_no_fim_do_jogo(tmp_path: Path):
    respostas = iter([[_partida(0, 1)], [_partida(0, 1, "STATUS_FULL_TIME")]])
    consultas = []

    vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=50,
        buscar=lambda liga: consultas.append(1) or next(respostas),
        agora=_relogio(), dormir=lambda s: None, avisar=lambda t: None,
    )

    assert len(consultas) == 2, "parou no apito, sem gastar as 50 voltas"


def test_rede_fora_nao_derruba_o_laco(tmp_path: Path):
    """A gravacao esta rodando: o vigia falhar nao pode custar o jogo."""
    respostas = iter([[], [], [_partida(0, 0)], [_partida(0, 1)]])

    marcados = vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=4,
        buscar=lambda liga: next(respostas), agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    assert marcados == [1], "as duas consultas vazias so adiaram o comeco"


def test_jogo_que_ainda_nao_comecou_e_espera_e_nao_erro(tmp_path: Path):
    outro = placar.Partida("9", "Santos", "Palmeiras", 0, 0, "STATUS_SCHEDULED")

    marcados = vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=3,
        buscar=lambda liga: [outro], agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    assert marcados == []


def test_marcar_gol_nao_apaga_os_que_o_operador_ja_tinha(tmp_path: Path):
    dados = catalogo.registrar_gol(catalogo.novo("j"), 1, "2026-09-02T23:12:36", "")
    catalogo.salvar(tmp_path, dados)

    numero = vigia.marcar_gol(tmp_path, datetime(2026, 9, 2, 23, 29, 3))

    assert numero == 2
    assert len(catalogo.carregar(tmp_path)["gols"]) == 2


def test_o_intervalo_padrao_e_educado_com_a_api():
    assert vigia.SEGUNDOS_ENTRE_CONSULTAS >= 15


def test_nao_dorme_antes_da_primeira_consulta(tmp_path: Path):
    """Esperar 20s para so entao olhar o placar atrasaria o comeco a toa."""
    dormidas = []

    vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=1,
        buscar=lambda liga: [_partida(0, 0)], agora=_relogio(),
        dormir=dormidas.append, avisar=lambda t: None,
    )

    assert dormidas == []


def _com_lances(gc, gf, segundo_agora, lances, estado="STATUS_SECOND_HALF"):
    return placar.Partida(
        "1", "Vitória", "Vasco da Gama", gc, gf, estado,
        segundo_de_jogo=segundo_agora, lances=lances,
    )


def test_o_gol_e_marcado_no_minuto_do_jogo_e_nao_na_hora_da_consulta():
    """Numeros reais de 02/09/2026: gol aos 4810s, percebido com o jogo em 4900s."""
    partida = _com_lances(0, 1, 4900.0, [{"segundo_de_jogo": 4810.0}])
    lido = datetime(2026, 9, 2, 23, 14, 6)

    momento, minuto = vigia.hora_do_lance(partida, partida.lances[0], lido)

    # 90 segundos de jogo separam o gol da leitura, entao a bola entrou 90s antes
    assert momento == datetime(2026, 9, 2, 23, 12, 36)
    assert minuto == 4810.0


def test_gol_sem_minuto_fica_na_hora_da_consulta():
    """A ESPN as vezes muda o placar antes de listar o lance."""
    partida = _com_lances(0, 1, 4900.0, [])
    lido = datetime(2026, 9, 2, 23, 14, 6)

    momento, minuto = vigia.hora_do_lance(partida, {}, lido)

    assert momento == lido and minuto is None


def test_gol_de_outra_metade_nao_atravessa_o_intervalo():
    """Gol do primeiro tempo so percebido no segundo: os quinze minutos de
    descanso entrariam na conta como se fossem jogo."""
    partida = _com_lances(0, 1, 3000.0, [{"segundo_de_jogo": 2000.0}])
    lido = datetime(2026, 9, 2, 23, 0, 0)

    momento, minuto = vigia.hora_do_lance(partida, partida.lances[0], lido)

    assert momento == lido, "melhor a hora da leitura do que uma hora errada"
    assert minuto == 2000.0


def test_o_gol_marcado_pelo_minuto_ja_nasce_confirmado(tmp_path: Path):
    respostas = iter([
        [_com_lances(0, 0, 4700.0, [])],
        [_com_lances(0, 1, 4900.0, [{"segundo_de_jogo": 4810.0, "minuto": "81'"}])],
    ])

    vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=2,
        buscar=lambda liga: next(respostas),
        agora=_relogio(datetime(2026, 9, 2, 23, 14, 6)),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    gol = catalogo.carregar(tmp_path)["gols"][0]
    assert gol["confirmado"] is True
    assert gol["minuto_do_jogo"] == 4810.0
    assert gol["horario"].endswith("23:12:56"), "a leitura foi 20s depois do primeiro tick"


def test_o_gol_sem_minuto_nasce_por_confirmar(tmp_path: Path):
    respostas = iter([
        [_com_lances(0, 0, 4700.0, [])],
        [_com_lances(0, 1, 4900.0, [])],
    ])

    vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=2,
        buscar=lambda liga: next(respostas), agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
    )

    assert catalogo.carregar(tmp_path)["gols"][0]["confirmado"] is False


def test_quem_quiser_pode_ser_avisado_de_cada_gol(tmp_path: Path):
    """E o gancho do corte automatico: o gol sai, o corte roda."""
    respostas = iter([
        [_com_lances(0, 0, 4700.0, [])],
        [_com_lances(0, 1, 4900.0, [{"segundo_de_jogo": 4810.0}])],
    ])
    recados = []

    vigia.vigiar(
        "copa-do-brasil", "vitoria", "vasco", tmp_path, voltas=2,
        buscar=lambda liga: next(respostas), agora=_relogio(),
        dormir=lambda s: None, avisar=lambda t: None,
        ao_marcar=lambda numero, momento: recados.append((numero, momento)),
    )

    assert len(recados) == 1 and recados[0][0] == 1
