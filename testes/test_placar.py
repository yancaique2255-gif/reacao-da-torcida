"""Nenhum teste aqui toca a rede: a amostra e um JSON gravado do dia 02/09/2026."""
import json
from pathlib import Path

from nucleo import placar

AMOSTRA = Path(__file__).resolve().parent / "amostras" / "espn-copa-do-brasil.json"


def _partida(casa="Vitória", fora="Vasco", gc=0, gf=0, estado="STATUS_SECOND_HALF", ident="1"):
    return placar.Partida(ident, casa, fora, gc, gf, estado)


def test_le_a_resposta_de_verdade_da_espn():
    partidas = placar.interpretar(AMOSTRA.read_text(encoding="utf-8"))

    assert len(partidas) == 2
    nomes = {f"{p.mandante} x {p.visitante}" for p in partidas}
    assert "Santos x Palmeiras" in nomes
    assert "Vitória x Vasco da Gama" in nomes


def test_placar_e_estado_saem_certos_da_amostra():
    partidas = placar.interpretar(AMOSTRA.read_text(encoding="utf-8"))
    vitoria = placar.achar(partidas, "vitoria", "vasco")

    assert vitoria.placar == (0, 2)
    assert vitoria.acabou
    assert str(vitoria) == "Vitória 0 x 2 Vasco da Gama"


def test_os_gols_do_jogo_vem_com_autor_e_minuto():
    partidas = placar.interpretar(AMOSTRA.read_text(encoding="utf-8"))
    vitoria = placar.achar(partidas, "vitoria", "vasco")

    assert len(vitoria.lances) == 2, "os dois gols do Vasco"
    assert all(l["quem"] for l in vitoria.lances)
    assert all(l["minuto"] for l in vitoria.lances)


def test_achar_ignora_acento_e_nome_pela_metade():
    """O operador escreve 'vitoria'; a ESPN responde 'Vitória'."""
    partidas = placar.interpretar(AMOSTRA.read_text(encoding="utf-8"))

    assert placar.achar(partidas, "vitoria", "vasco") is not None
    assert placar.achar(partidas, "santos", "palmeiras") is not None
    assert placar.achar(partidas, "gremio", "inter") is None


def test_resposta_que_nao_e_json_nao_estoura():
    """A ESPN as vezes devolve HTML de erro no lugar do JSON."""
    for lixo in ("", "<html>erro 500</html>", "null", "[]", "{}"):
        assert placar.interpretar(lixo) == []


def test_evento_sem_competidores_e_pulado():
    texto = json.dumps({"events": [{"id": "1", "competitions": [{"competitors": []}]}]})

    assert placar.interpretar(texto) == []


def test_rede_fora_devolve_vazio_em_vez_de_excecao():
    """Quem chama esta gravando: erro de rede aqui nao pode derrubar o jogo."""
    def explode(url):
        raise OSError("sem internet")

    assert placar.buscar("copa-do-brasil", buscar_cru=explode) == []


def test_o_slug_da_copa_do_brasil_e_com_z():
    """`bra.copa_do_brasil` devolve HTTP 400; a ESPN escreve com Z."""
    pedidos = []

    placar.buscar("copa-do-brasil", buscar_cru=lambda u: pedidos.append(u) or "{}")

    assert "bra.copa_do_brazil" in pedidos[0]


def test_slug_desconhecido_passa_direto():
    """Liga que ainda nao esta no mapa deve poder ser usada pelo slug cru."""
    pedidos = []

    placar.buscar("esp.1", buscar_cru=lambda u: pedidos.append(u) or "{}")

    assert "esp.1" in pedidos[0]


def test_gol_novo_e_detectado():
    antes = _partida(gc=0, gf=1)
    agora = _partida(gc=0, gf=2)

    assert placar.gols_novos(antes, agora) == 1


def test_primeira_leitura_nao_dispara_nada():
    """Senao um jogo pego ja 2x0 mandaria cortar dois gols que nao existem."""
    assert placar.gols_novos(None, _partida(gc=2, gf=0)) == 0


def test_placar_parado_nao_dispara():
    assert placar.gols_novos(_partida(gc=1, gf=1), _partida(gc=1, gf=1)) == 0


def test_gol_anulado_pelo_var_nao_vira_numero_negativo():
    antes = _partida(gc=1, gf=0)
    agora = _partida(gc=0, gf=0)

    assert placar.gols_novos(antes, agora) == 0


def test_dois_gols_entre_duas_consultas():
    """Vinte segundos dao para sair gol e replay de outro; nao pode perder um."""
    assert placar.gols_novos(_partida(gc=0, gf=0), _partida(gc=1, gf=1)) == 2


def test_partidas_diferentes_nao_se_comparam():
    antes = _partida(ident="1", gc=0, gf=0)
    agora = _partida(ident="2", gc=3, gf=0)

    assert placar.gols_novos(antes, agora) == 0


def test_estados_que_significam_fim_de_jogo():
    assert _partida(estado="STATUS_FULL_TIME").acabou
    assert _partida(estado="STATUS_POSTPONED").acabou
    assert not _partida(estado="STATUS_SECOND_HALF").acabou
    assert not _partida(estado="STATUS_HALFTIME").acabou
