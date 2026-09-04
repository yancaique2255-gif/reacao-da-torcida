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
import subprocess
from pathlib import Path

import pytest

from nucleo import catalogo, cortador, estudio, molde, receita

CFG = {
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
    "fonte_display": r"C:\Windows\Fonts\bahnschrift.ttf",
    "fonte_sans": r"C:\Windows\Fonts\segoeuib.ttf",
    "fonte_mono": r"C:\Windows\Fonts\consolab.ttf",
    "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
}
TIMES = {
    "gremio": {
        "nome": "Grêmio", "torcida": "gremio", "apelido": "GREMISTAS",
        "adjetivo": "GREMISTAS", "curto": "GRÊMIO", "cor": "#0d80bf", "escudo": "",
    },
    "internacional": {
        "nome": "Internacional", "torcida": "inter", "apelido": "COLORADOS",
        "adjetivo": "COLORADAS", "curto": "INTER", "cor": "#c8102e", "escudo": "",
    },
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


class Morrendo(Executor):
    """ffmpeg que morre no item `em`, deixando o arquivo pela metade.

    E o que aconteceu de verdade: saida congelada nos 48 bytes do cabecalho.
    """

    def __init__(self, em: int):
        super().__init__()
        self.em = em

    def __call__(self, comando):
        self.comandos.append(comando)
        destino = Path(comando[-1])
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"\x00" * 48)
        if len(self.comandos) >= self.em:
            raise subprocess.CalledProcessError(1, comando, stderr=b"morri no meio")


class Tropecando(Executor):
    """ffmpeg que falha nas chamadas listadas e vai bem nas outras.

    O travamento medido em 03/09 e intermitente - o mesmo item passou em 1 de
    cada 3 tentativas. Refazer resolve; desistir na primeira, nao.
    """

    def __init__(self, falha_em=(), como=None):
        super().__init__()
        self.falha_em = set(falha_em)
        self.como = como

    def __call__(self, comando):
        self.comandos.append(comando)
        destino = Path(comando[-1])
        destino.parent.mkdir(parents=True, exist_ok=True)
        if len(self.comandos) in self.falha_em:
            destino.write_bytes(b"\x00" * 48)
            raise self.como or subprocess.CalledProcessError(
                1, comando, stderr=b"tropecei"
            )
        destino.write_bytes(b"video de mentira")


def _jogo(pasta: Path, gols=(1,)) -> dict:
    # Nome de pasta como o de verdade: a data da cartela sai dele.
    dados = catalogo.registrar_partida(
        catalogo.novo("2026-09-03 gremio x internacional"),
        "copa-do-brasil", "Grêmio", "Internacional",
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

    pedacos = sorted(estudio.pasta_das_pecas(tmp_path).glob("*.mp4"))
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

    assert executor.texto().count("GOL 01") == 1
    assert executor.texto().count("GOL 02") == 1


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


def test_as_formas_do_quadro_saem_do_tamanho_do_quadro(tmp_path: Path):
    """Os cantos arredondados e a borda saem do molde, e nao de um numero solto."""
    from PIL import Image

    formas = estudio.formas_do_molde(tmp_path, "deitado")

    assert Image.open(formas["mascara"]).size == (1728, 972)
    assert Image.open(formas["moldura"]).size == (1728, 972)


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
    assert "GRÊMIO" not in dos_quadros and "INTER " not in dos_quadros
    assert dos_quadros.count("1 x 0") == 2, "um em cada quadro"
    # Na cartela, que e tela cheia, o placar por extenso cabe e fica - com o
    # nome `curto` do time, que e o que define o corpo do display.
    assert "GRÊMIO 1 x 0 INTER" in executor.texto()


def test_nome_de_canal_gigante_nao_estoura_a_etiqueta():
    """Cortar o nome e feio; deixar vazar por cima do video e pior."""
    curto = estudio.titulo_do_canal("baldasso-tv")
    gigante = estudio.titulo_do_canal("canal-do-torcedor-que-nunca-cala-a-boca")

    assert curto == "BALDASSO TV"
    assert len(gigante) <= molde.MAXIMO_DO_CANAL


def test_a_previa_nao_manda_preset_de_libx264_para_a_apu(tmp_path: Path):
    """Medido: o h264_amf recusa `-preset veryfast` e `-crf`, e a previa morria.

    "Unable to parse preset option value veryfast" - os presets dele sao outros.
    Taxa de bits em vez de crf serve aos dois, e a previa nao precisa de mais.
    """
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.previa(
        tmp_path, dados, receita.padrao(dados), 1, "paulo-brito",
        {**CFG, "codec_previa": "h264_amf"}, executar=executor,
    )

    comando = executor.comandos[0]
    assert "h264_amf" in comando
    assert "veryfast" not in comando
    assert "-crf" not in comando
    assert "-b:v" in comando


def test_previa_recusada_pela_apu_sai_pelo_libx264(tmp_path: Path):
    """A APU pode estar ocupada. Ficar sem previa por isso seria bobagem."""
    dados = _jogo(tmp_path)
    tentativas = []

    def apu_ocupada(comando):
        tentativas.append(comando)
        if "h264_amf" in comando:
            raise subprocess.CalledProcessError(1, comando)
        Path(comando[-1]).write_bytes(b"video de mentira")

    saida = estudio.previa(
        tmp_path, dados, receita.padrao(dados), 1, "paulo-brito",
        {**CFG, "codec_previa": "h264_amf"}, executar=apu_ocupada,
    )

    assert len(tentativas) == 2
    assert "libx264" in tentativas[1]
    assert saida.is_file()


def test_render_que_morreu_no_meio_nao_fica_rodando_para_sempre(tmp_path: Path):
    """Estado travado que nunca resolve e pior que erro: o operador espera um
    arquivo que nunca vem. Se o processo do render sumiu, a tela tem que dizer."""
    # `pid_em` no passado: PID recem-criado tem carencia, porque o `tasklist`
    # nao o enxerga na hora. O que este teste cobra e o depois da carencia.
    estudio.anotar(tmp_path, rodando=True, feito=1, total=5, pid=999999, pid_em=0.0)

    estado = estudio.estado(tmp_path, vivo=lambda pid: False)

    assert estado["rodando"] is False
    assert "parou" in estado["mensagem"]


def test_render_vivo_continua_rodando(tmp_path: Path):
    estudio.anotar(tmp_path, rodando=True, feito=1, total=5, pid=4242)

    assert estudio.estado(tmp_path, vivo=lambda pid: True)["rodando"] is True


def test_o_fundo_do_video_e_a_cor_da_torcida_que_perdeu(tmp_path: Path):
    """Sem o fundo com a cara do time, um clipe de webcam continua um clipe de webcam."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)

    cor = estudio.cor_do_fundo(feita, {"internacional": {
        "nome": "Internacional", "torcida": "inter", "cor": "#c8102e",
    }})

    assert cor == "#c8102e"


def test_torcida_sem_cor_cadastrada_usa_a_do_molde(tmp_path: Path):
    dados = _jogo(tmp_path)

    assert estudio.cor_do_fundo(receita.padrao(dados), {}) == molde.COR_FUNDO


# ------------------------------------------------- o cache nao engole lixo

def test_peca_que_ficou_pela_metade_nao_e_reaproveitada(tmp_path: Path):
    """O defeito que sumiu com um clipe do video de 03/09 sem avisar nada.

    ffmpeg que morre no meio deixa um .mp4 de 48 bytes - so o `ftyp`, sem
    `moov`. O render seguinte reaproveitava esse arquivo, o `concat` engolia, e
    a compilacao saia 60s mais curta em silencio. Mandar RENDER de novo nao
    consertava: o lixo tem nome, tamanho e data de peca boa.
    """
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    morreu = Morrendo(em=2)
    with pytest.raises(subprocess.CalledProcessError):
        estudio.montar(tmp_path, dados, feita, CFG, executar=morreu)

    depois = Executor()
    estudio.montar(tmp_path, dados, feita, CFG, executar=depois)

    assert len(depois.comandos) == 3, (
        "a peca que morreu tem de ser refeita, mais a emenda; "
        f"rodou {len(depois.comandos)}"
    )


def test_a_peca_que_morreu_nao_fica_no_disco(tmp_path: Path):
    dados = _jogo(tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        estudio.montar(
            tmp_path, dados, receita.padrao(dados), CFG, executar=Morrendo(em=1)
        )

    sobras = list(estudio.pasta_cache(tmp_path).rglob("*.mp4"))
    assert sobras == [], f"sobrou lixo no cache: {sobras}"


def test_a_peca_boa_fica_com_o_nome_final_e_e_reaproveitada(tmp_path: Path):
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    estudio.montar(tmp_path, dados, feita, CFG, executar=Executor())

    prontas = sorted(estudio.pasta_das_pecas(tmp_path).glob("*.mp4"))
    assert len(prontas) == 3, "uma cartela e dois clipes, todos batizados"
    assert not list(estudio.pasta_cache(tmp_path).glob("parcial-*"))


def test_lixo_do_render_antigo_no_cache_nao_conta_como_peca(tmp_path: Path):
    """Os jogos rodados antes deste conserto tem os .mp4 na raiz do cache.

    Nada ali passou por batismo nenhum, entao nada ali e confiavel: o cache novo
    mora em `pecas/` e nem olha para tras.
    """
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    cache = estudio.pasta_cache(tmp_path)
    cache.mkdir(parents=True, exist_ok=True)
    for item in receita.itens_do_video(feita):
        clipe = estudio._clipe_de(dados, item["gol"], item["canal"])
        filtro, _ = estudio.filtro_do_item(clipe, dados, feita, CFG)
        nome = estudio.identidade(clipe["arquivo"], item["de"], item["ate"], filtro)
        (cache / f"{nome}.mp4").write_bytes(b"\x00" * 48)  # so o ftyp

    executor = Executor()
    estudio.montar(tmp_path, dados, feita, CFG, executar=executor)

    assert len(executor.comandos) == 4, "cartela, dois clipes e a emenda"


# ------------------------------------------------- o item que falha e refeito

def test_o_item_que_falha_e_tentado_de_novo(tmp_path: Path):
    """O travamento do ffmpeg e intermitente: 2 de cada 3 no mesmo item.

    Com uma tentativa so, um travamento derrubava o render inteiro. Refazer o
    item transforma "painel morto" em "item X falhou, refazendo".
    """
    dados = _jogo(tmp_path)
    tropeco = Tropecando(falha_em=(2,))

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=tropeco)

    assert len(tropeco.comandos) == 5, "cartela, clipe que tropecou, ele de novo, clipe 2, emenda"
    assert len(list(estudio.pasta_das_pecas(tmp_path).glob("*.mp4"))) == 3


def test_o_item_que_nao_volta_derruba_o_render_dizendo_por_que(tmp_path: Path):
    dados = _jogo(tmp_path)
    ditos = []

    with pytest.raises(cortador.FALHAS):
        estudio.montar(
            tmp_path, dados, receita.padrao(dados), CFG,
            executar=Morrendo(em=1), avisar=ditos.append,
        )

    recado = "\n".join(ditos)
    assert recado.count("refazendo") == estudio.TENTATIVAS - 1
    assert "morri no meio" in recado, "as ultimas linhas do ffmpeg tem de aparecer"


def test_render_que_falha_nao_deixa_o_disco_dizendo_que_esta_rodando(tmp_path: Path):
    """Estado travado que nunca resolve e pior do que erro."""
    dados = _jogo(tmp_path)

    with pytest.raises(cortador.FALHAS):
        estudio.montar(
            tmp_path, dados, receita.padrao(dados), CFG,
            executar=Morrendo(em=1), avisar=lambda t: None,
        )

    guardado = json.loads((tmp_path / estudio.NOME_ESTADO).read_text(encoding="utf-8"))
    assert guardado["rodando"] is False
    assert "morri no meio" in guardado["mensagem"]


def test_o_travamento_tambem_e_tentado_de_novo(tmp_path: Path):
    dados = _jogo(tmp_path)
    tropeco = Tropecando(falha_em=(1,), como=subprocess.TimeoutExpired(["ffmpeg"], 900))

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=tropeco)

    assert len(list(estudio.pasta_das_pecas(tmp_path).glob("*.mp4"))) == 3


def test_previa_que_TRAVA_na_apu_tambem_cai_para_o_libx264(tmp_path: Path):
    """Encoder de APU nao falha so com codigo de erro - ele tambem trava.

    Ficar sem previa por isso seria bobagem: o libx264 sempre existe e em
    640x360 da conta.
    """
    dados = _jogo(tmp_path)
    tentados = []

    def executar(comando):
        tentados.append(comando)
        if "h264_amf" in comando:
            raise subprocess.TimeoutExpired(comando, 900)
        Path(comando[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(comando[-1]).write_bytes(b"previa")

    estudio.previa(
        tmp_path, dados, receita.padrao(dados), 1, "farid-germano-filho",
        {**CFG, "codec_previa": "h264_amf"}, executar=executar,
    )

    assert len(tentados) == 2
    assert "libx264" in tentados[-1]


# --------------------------------------------- o PID que acabou de nascer

def test_pid_recem_nascido_nao_e_dado_por_morto(tmp_path: Path):
    """O `tasklist` ainda nao enxerga o PID recem-criado.

    Ao clicar RENDER, a resposta imediata dizia "o render parou sozinho antes de
    terminar" - era a primeira coisa que o operador lia. Sumia no refresh
    seguinte, o que e pior: ensina a ignorar o aviso que um dia sera verdade.
    """
    estudio.anotar(tmp_path, rodando=True, pid=4242)

    assert estudio.estado(tmp_path, vivo=lambda p: False)["rodando"] is True


def _render_no_disco(pasta: Path, **campos) -> None:
    """Escreve o `render.json` na mao, sem passar pelo `anotar`.

    E preciso: o `anotar` le o estado antes de gravar, e essa leitura ja
    corrige. Para provar que a LEITURA grava a correcao, o arquivo tem de
    chegar sujo ate ela.
    """
    (pasta / estudio.NOME_ESTADO).write_text(
        json.dumps({"rodando": True, "feito": 3, "total": 16, "mensagem": "3 de 16",
                    "saida": "", "pid": 4242, **campos}),
        encoding="utf-8",
    )


def test_pid_que_sumiu_depois_da_carencia_e_dado_por_morto(tmp_path: Path):
    _render_no_disco(tmp_path, pid_em=0.0)  # como se tivesse nascido em 1970

    estado = estudio.estado(tmp_path, vivo=lambda p: False)

    assert estado["rodando"] is False and "parou sozinho" in estado["mensagem"]


def test_render_morto_para_de_dizer_rodando_no_disco_tambem(tmp_path: Path):
    """Quem corrigia isso era so a leitura; o disco continuava mentindo."""
    _render_no_disco(tmp_path, pid_em=0.0)

    estudio.estado(tmp_path, vivo=lambda p: False)

    guardado = json.loads((tmp_path / estudio.NOME_ESTADO).read_text(encoding="utf-8"))
    assert guardado["rodando"] is False
    assert "parou sozinho" in guardado["mensagem"]


# ------------------------------------------- o design do produto publicado

def test_a_cartela_diz_o_placar_por_extenso_com_o_nome_curto(tmp_path: Path):
    """A cartela saia escrita so "GOL 3". Agora ela e um bloco de quatro papeis.

    O nome que vai nela e o `curto` do dados/times.json - "GRÊMIO 3 x 0 INTER" -
    e nao o nome por extenso, que estoura a linha no pior caso.
    """
    dados = _jogo(tmp_path)

    peca = estudio.cartela_do_gol(dados, 1, TIMES)

    assert peca["marca"] == "GOL 01"
    assert peca["titulo"] == "GRÊMIO 1 x 0 INTER"
    assert "COPA DO BRASIL" in peca["meta"]
    assert "03/09/2026" in peca["meta"]


def test_a_cartela_sem_placar_anotado_mostra_os_times_sem_numero(tmp_path: Path):
    """Dizer o que se sabe, e nunca inventar um numero na tela."""
    dados = _jogo(tmp_path)
    for gol in dados["gols"]:
        gol.pop("placar", None)

    peca = estudio.cartela_do_gol(dados, 1, TIMES)

    assert peca["titulo"] == "GRÊMIO x INTER"
    assert "0" not in peca["titulo"]


def test_a_marca_do_gol_tem_sempre_dois_digitos(tmp_path: Path):
    """`GOL 03` e nao `GOL 3`: mono com largura fixa nao pode dancar na tela."""
    dados = _jogo(tmp_path, gols=(1, 2))

    assert estudio.cartela_do_gol(dados, 2, TIMES)["marca"] == "GOL 02"


def test_as_tres_letras_saem_da_configuracao():
    letras = estudio.fontes_de(CFG)

    assert set(letras) == set(molde.LETRAS)
    assert letras["display"].name == "bahnschrift.ttf"
    assert letras["sans"].name == "segoeuib.ttf"
    assert letras["mono"].name == "consolab.ttf"


def test_a_letra_que_falta_cai_para_a_herdada():
    """Fonte que nao existe na maquina nao pode custar o render."""
    letras = estudio.fontes_de({"fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf"})

    assert {p.name for p in letras.values()} == {"arialbd.ttf"}


def test_as_formas_do_molde_saem_uma_vez_e_sao_reaproveitadas(tmp_path: Path):
    """Canto arredondado no ffmpeg puro daria um `geq` caro e ilegivel."""
    primeiras = estudio.formas_do_molde(tmp_path, "deitado")

    assert set(primeiras) >= {"mascara", "moldura", "etiqueta", "torcida", "placar"}
    for arquivo in primeiras.values():
        assert arquivo.is_file(), arquivo
    assert estudio.formas_do_molde(tmp_path, "deitado") == primeiras


def test_a_pilula_do_png_e_branca_no_meio_e_vazia_no_canto(tmp_path: Path):
    """`rounded.full` de verdade: o canto da pilula tem de estar transparente."""
    from PIL import Image

    formas = estudio.formas_do_molde(tmp_path, "deitado")
    pilula = Image.open(formas["etiqueta"]).convert("RGBA")
    caixa = molde.caixa("etiqueta", "deitado")

    assert pilula.size == (caixa["largura"], caixa["altura"])
    assert pilula.getpixel((caixa["largura"] // 2, caixa["altura"] // 2)) == (
        255, 255, 255, 255
    )
    assert pilula.getpixel((0, 0))[3] == 0, "o canto da pilula tem de ser vazio"


def test_a_pilula_tem_fio_de_contorno_para_nao_sumir_no_branco(tmp_path: Path):
    """Transmissao tem cromado branco proprio, e pilula branca sobre ele nao aparece.

    Visto na primeira prova no jogo de verdade: a pilula do placar caiu em cima
    da barra de patrocinadores do canal, que e branca, e sumiu. O sistema de
    origem ja tem a resposta - o `button-secondary` dele e branco com fio de
    `{colors.hairline-strong}`, que e justamente uma superficie branca que
    precisa se destacar de outra branca.
    """
    from PIL import Image

    formas = estudio.formas_do_molde(tmp_path, "deitado")
    pilula = Image.open(formas["placar"]).convert("RGBA")
    caixa = molde.caixa("placar", "deitado")

    meio = pilula.getpixel((caixa["largura"] // 2, caixa["altura"] // 2))
    borda = pilula.getpixel((caixa["largura"] // 2, 1))
    assert meio == (255, 255, 255, 255)
    assert borda[3] == 255 and borda[0] < 240, f"o fio da pilula nao apareceu: {borda}"


def test_o_item_manda_uma_entrada_de_imagem_por_forma(tmp_path: Path):
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    do_clipe = executor.comandos[1]
    assert do_clipe.count("-loop") == len(estudio.ORDEM_DAS_FORMAS)


def test_as_entradas_de_imagem_vao_limitadas_por_tempo(tmp_path: Path):
    """Medido em 03/09: limitar as entradas de imagem com `-t` fez 3 de 4
    passarem, contra 1 de 3 sem isso. E a mitigacao do travamento do ffmpeg."""
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    do_clipe = executor.comandos[1]
    posicoes = [i for i, arg in enumerate(do_clipe) if arg == "-loop"]
    for posicao in posicoes:
        assert "-t" in do_clipe[posicao:posicao + 4], do_clipe[posicao:posicao + 5]


def test_o_nome_do_canal_e_a_torcida_vao_em_pilulas_separadas(tmp_path: Path):
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    texto = executor.texto()
    assert "FARID GERMANO FILHO" in texto
    assert "TORCIDA DO INTER" in texto
    assert "torcida do inter" not in texto, "a segunda linha da tarja velha saiu"


def test_estado_de_render_vivo_nao_reescreve_o_disco(tmp_path: Path):
    """Ler nao pode escrever a toa: o render em andamento escreve o tempo todo."""
    _render_no_disco(tmp_path, pid_em=0.0)
    antes = (tmp_path / estudio.NOME_ESTADO).read_text(encoding="utf-8")

    estudio.estado(tmp_path, vivo=lambda p: True)

    assert (tmp_path / estudio.NOME_ESTADO).read_text(encoding="utf-8") == antes
