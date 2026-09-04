"""O estudio executa a receita: espiar, previa, final, cache e fila.

A maquina e modesta - seis nucleos, sem placa de video dedicada - e um video de
20 minutos em 1080p leva minutos. Fingir que e instantaneo seria mentir para o
operador. Por isso sao tres velocidades declaradas e um cache por item: mexer no
item 5 nao pode refazer os itens 1 a 4.

O que estes testes travam e exatamente isso, mais o que a emenda promete: todo
clipe no mesmo volume, cartela abrindo cada gol, e o progresso em disco para o
painel poder ser fechado e reaberto sem matar o render.
"""
import json
from pathlib import Path

import pytest

from nucleo import catalogo, estudio, molde, receita

CFG = {
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
    "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
}


class Executor:
    """ffmpeg de mentira: anota o comando e cria o arquivo de saida."""

    def __init__(self):
        self.comandos = []

    def __call__(self, comando):
        self.comandos.append(comando)
        destino = Path(comando[-1])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"video de mentira")

    def texto(self) -> str:
        return " ".join(" ".join(c) for c in self.comandos)


def _jogo(pasta: Path, gols=(1,)) -> dict:
    dados = catalogo.registrar_partida(
        catalogo.novo(pasta.name), "copa-do-brasil", "Grêmio", "Internacional"
    )
    dados = catalogo.registrar_placar(dados, 3, 1)
    for numero in gols:
        dados = catalogo.registrar_gol(dados, numero, f"2026-09-03T20:1{numero}:00", "")
        for gol in dados["gols"]:
            if gol["numero"] == numero:
                gol["placar"] = [numero, 0]
        for canal, db in [("farid-germano-filho", 15.2), ("paulo-brito", 7.8)]:
            dados = catalogo.registrar_clipe(
                dados, numero, canal, f"clipes/gol-0{numero}/{canal}.mp4",
                100.0, db, True, "inter", 175.0,
            )
    catalogo.salvar(pasta, dados)
    return dados


def test_cada_item_vira_um_arquivo_proprio_no_cache(tmp_path: Path):
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    pedacos = sorted(estudio.pasta_cache(tmp_path).glob("*.mp4"))
    assert len(pedacos) == 3, "uma cartela e dois clipes"


def test_mexer_num_item_so_refaz_aquele_item(tmp_path: Path):
    """O cache por item e o que torna o painel usavel numa maquina sem GPU."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    estudio.montar(tmp_path, dados, feita, CFG, executar=Executor())

    depois = Executor()
    estudio.montar(
        tmp_path, dados, receita.mexer(feita, 1, "paulo-brito", de=20.0, ate=80.0),
        CFG, executar=depois,
    )

    assert len(depois.comandos) == 2, "so o item mexido e a emenda"


def test_o_mesmo_item_sem_mexer_nao_roda_de_novo(tmp_path: Path):
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    estudio.montar(tmp_path, dados, feita, CFG, executar=Executor())

    depois = Executor()
    estudio.montar(tmp_path, dados, feita, CFG, executar=depois)

    assert len(depois.comandos) == 1, "so a emenda, que e copia de fluxo"


def test_trocar_o_formato_refaz_tudo(tmp_path: Path):
    """Outro molde, outra imagem: o hash tem que perceber isso sozinho."""
    dados = _jogo(tmp_path)
    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=Executor())

    depois = Executor()
    estudio.montar(
        tmp_path, dados, receita.padrao(dados, formato="em-pe", duracao_por_clipe=20),
        CFG, executar=depois,
    )

    assert len(depois.comandos) == 4, "cartela, dois clipes e a emenda"


def test_a_emenda_e_copia_de_fluxo(tmp_path: Path):
    """Recodificar de novo na emenda seria jogar minutos fora por nada."""
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    emenda = executor.comandos[-1]
    assert "concat" in emenda and "copy" in emenda


def test_todo_clipe_passa_pelo_mesmo_alvo_de_volume(tmp_path: Path):
    """Um canal berra e o outro sussurra: na mesma compilacao isso e insuportavel."""
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    assert executor.texto().count("loudnorm=I=-16") == 2


def test_a_cartela_abre_cada_gol(tmp_path: Path):
    dados = _jogo(tmp_path, gols=(1, 2))
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    assert executor.texto().count("GOL 1") == 1
    assert executor.texto().count("GOL 2") == 1


def test_o_placar_do_quadro_e_o_do_gol_que_esta_passando(tmp_path: Path):
    """No gol 1 o quadro diz 1x0, e nao o placar final."""
    dados = _jogo(tmp_path, gols=(1, 2))

    assert estudio.placar_do_gol(dados, 1) == "Grêmio 1 x 0 Internacional"
    assert estudio.placar_do_gol(dados, 2) == "Grêmio 2 x 0 Internacional"


def test_gol_sem_placar_anotado_nao_inventa_um(tmp_path: Path):
    """Jogo gravado antes de o placar do gol existir: diz o que sabe, so isso."""
    dados = _jogo(tmp_path)
    for gol in dados["gols"]:
        gol.pop("placar")

    assert estudio.placar_do_gol(dados, 1) == ""
    assert estudio.texto_da_cartela(dados, 1) == "GOL 1"


def test_espiar_sai_um_quadro_so(tmp_path: Path):
    """Instantaneo, para ver se a etiqueta cobriu o rosto."""
    dados = _jogo(tmp_path)
    executor = Executor()

    quadro = estudio.espiar(
        tmp_path, dados, receita.padrao(dados), 1, "paulo-brito", CFG, executar=executor
    )

    assert quadro.suffix == ".png"
    assert "-frames:v" in executor.comandos[0]
    assert len(executor.comandos) == 1


def test_a_previa_e_pequena_e_so_do_trecho(tmp_path: Path):
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.previa(
        tmp_path, dados, receita.padrao(dados), 1, "paulo-brito", CFG, executar=executor
    )

    assert "scale=640:360" in executor.texto()
    assert len(executor.comandos) == 1


def test_sem_nada_marcado_o_estudio_reclama_e_ensina_a_saida(tmp_path: Path):
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    for item in feita["itens"]:
        item["entra"] = False

    with pytest.raises(ValueError) as erro:
        estudio.montar(tmp_path, dados, feita, CFG, executar=Executor())

    assert "marque" in str(erro.value).lower()


def test_o_progresso_fica_no_disco(tmp_path: Path):
    """O painel pode ser fechado e reaberto sem matar o render."""
    dados = _jogo(tmp_path)

    saida = estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=Executor())

    estado = estudio.estado(tmp_path)
    assert estado["rodando"] is False
    assert estado["feito"] == estado["total"] == 3
    assert estado["saida"] == str(saida)


def test_o_progresso_anda_peca_por_peca(tmp_path: Path):
    dados = _jogo(tmp_path)
    andou = []
    executor = Executor()

    def espiando(comando):
        andou.append(estudio.estado(tmp_path)["feito"])
        executor(comando)

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=espiando)

    assert andou[:3] == [0, 1, 2]


def test_limpar_devolve_o_espaco(tmp_path: Path):
    """Os intermediarios sao uma copia inteira do video: 1 a 2 GB por jogo."""
    dados = _jogo(tmp_path)
    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=Executor())
    antes = estudio.tamanho_do_cache(tmp_path)

    liberado = estudio.limpar(tmp_path)

    assert antes > 0 and liberado == antes
    assert estudio.tamanho_do_cache(tmp_path) == 0


def test_as_mascaras_saem_do_tamanho_do_quadro(tmp_path: Path):
    """Os cantos arredondados e a borda saem do molde, e nao de um numero solto."""
    from PIL import Image

    mascara, moldura = estudio.mascaras(tmp_path, "deitado")

    assert Image.open(mascara).size == (1728, 972)
    assert Image.open(moldura).size == (1728, 972)


def test_o_render_avisa_quando_o_cache_passa_do_teto(tmp_path: Path):
    dados = _jogo(tmp_path)
    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=Executor())

    assert estudio.passou_do_teto(tmp_path, {**CFG, "teto_cache_gb": 0}) is True
    assert estudio.passou_do_teto(tmp_path, {**CFG, "teto_cache_gb": 5}) is False


def test_o_estado_de_um_jogo_que_nunca_renderizou_nao_quebra(tmp_path: Path):
    assert estudio.estado(tmp_path)["rodando"] is False
    assert estudio.estado(tmp_path)["total"] == 0


def test_o_arquivo_de_estado_e_json_de_verdade(tmp_path: Path):
    dados = _jogo(tmp_path)

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=Executor())

    lido = json.loads((tmp_path / estudio.NOME_ESTADO).read_text(encoding="utf-8"))
    assert lido["mensagem"]


def test_o_quadro_mostra_so_os_numeros_do_placar(tmp_path: Path):
    """Nome de time por extenso nao cabe na caixa: transborda e sai da tela.

    Medido no primeiro render de verdade - "Grêmio 1 x 0 Internacional" saiu
    cortado pela borda direita. Quem identifica os times e o escudo, e a cartela
    de tela cheia, onde ha espaco. No quadro ficam os numeros.
    """
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    dos_quadros = " ".join(
        " ".join(c) for c in executor.comandos if "alphamerge" in " ".join(c)
    )
    assert estudio.numeros_do_gol(dados, 1) == "1 x 0"
    assert "Internacional" not in dos_quadros
    assert dos_quadros.count("1 x 0") == 2, "um em cada quadro"
    # Na cartela, que e tela cheia, o nome por extenso cabe e fica.
    assert "Internacional" in executor.texto()


def test_nome_de_canal_gigante_nao_estoura_a_etiqueta():
    """Cortar o nome e feio; deixar vazar por cima do video e pior."""
    curto = estudio.titulo_do_canal("baldasso-tv")
    gigante = estudio.titulo_do_canal("canal-do-torcedor-que-nunca-cala-a-boca")

    assert curto == "BALDASSO TV"
    assert len(gigante) <= molde.MAXIMO_DO_CANAL
