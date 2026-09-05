"""O estudio executa a receita: espiar, previa, final, cache e fila.

A maquina e modesta - seis nucleos, sem placa de video dedicada - e um video de
20 minutos em 1080p leva minutos. Fingir que e instantaneo seria mentir para o
operador. Por isso sao tres velocidades declaradas e um cache por item: mexer no
item 5 nao pode refazer os itens 1 a 4.

O que estes testes travam e exatamente isso, mais o que a emenda promete: todo
clipe no mesmo volume, nenhuma letra dentro do video, e o progresso em disco
para o painel poder ser fechado e reaberto sem matar o render.
"""
import json
import subprocess
from pathlib import Path

import pytest

from nucleo import catalogo, cortador, estudio, identidade, molde, receita

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

    pedacos = sorted(estudio.pasta_das_pecas(tmp_path).glob("*.mp4"))
    assert len(pedacos) == 2, "um pedaco por trecho marcado, e nada mais"


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

    assert len(depois.comandos) == 3, "os dois clipes e a emenda"


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


def test_o_video_montado_nao_escreve_nada_na_tela(tmp_path: Path):
    """O dono pediu o video limpo em 05/09. O molde ja garante isso camada por
    camada; aqui o que se cobra e a montagem inteira, que e onde a cartela
    entrava por fora do molde - um pedaco a mais na frente de cada gol.
    """
    dados = _jogo(tmp_path, gols=(1, 2))
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    texto = executor.texto()
    assert "drawtext" not in texto
    assert "GOL 1" not in texto and "GOL 2" not in texto
    assert "Grêmio" not in texto and "Internacional" not in texto
    assert "PAULO BRITO" not in texto.upper()


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


def test_espiar_sai_um_quadro_so(tmp_path: Path):
    """Instantaneo, para ver como a cena fica dentro do molde."""
    dados = _jogo(tmp_path)
    executor = Executor()

    quadro = estudio.espiar(
        tmp_path, dados, receita.padrao(dados), 1, "paulo-brito", CFG, executar=executor
    )

    assert quadro.suffix == ".png"
    assert "-frames:v" in executor.comandos[0]
    assert len(executor.comandos) == 1


def test_a_previa_e_so_o_corte_cru_sem_as_camadas(tmp_path: Path):
    """A previa responde UMA pergunta: o corte pegou o que tinha que pegar?

    Compor fundo, quadro, etiqueta e placar em 1080p para so entao encolher
    para 640 custava 25 s no trecho de 60 s do gol 1 (medido em 05/09, e 48 s
    no laudo do jogo real). O mesmo trecho cortado cru sai em 2,2 s, e o que o
    operador ve e exatamente o mesmo: onde comeca, onde termina, se o grito
    caiu dentro. Quem confere as camadas e o ESPIAR, que ja e instantaneo.
    """
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.previa(
        tmp_path, dados, receita.padrao(dados), 1, "paulo-brito", CFG, executar=executor
    )

    comando = executor.comandos[0]
    texto = executor.texto()
    assert len(executor.comandos) == 1
    assert "scale=640" in texto
    assert "-filter_complex" not in comando, "compor camadas e o que custava caro"
    assert "drawtext" not in texto
    assert "loudnorm" not in texto, "nivelar volume e coisa do render, nao da previa"
    # `-ss` ANTES do `-i`: assim o ffmpeg pula pelo indice em vez de decodificar
    # o clipe inteiro ate o ponto do corte.
    assert comando.index("-ss") < comando.index("-i")


def test_previa_ja_feita_nao_chama_o_ffmpeg_de_novo(tmp_path: Path):
    """Clicar PREVIA duas vezes no mesmo trecho tem que ser instantaneo."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    primeira = estudio.previa(
        tmp_path, dados, feita, 1, "paulo-brito", CFG, executar=Executor()
    )

    depois = Executor()
    segunda = estudio.previa(
        tmp_path, dados, feita, 1, "paulo-brito", CFG, executar=depois
    )

    assert segunda == primeira
    assert depois.comandos == [], "o cache tinha que ter respondido sozinho"


def test_mexer_no_trecho_refaz_a_previa(tmp_path: Path):
    """Cache que nao percebe o corte novo vira previa que mente."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    antes = estudio.previa(
        tmp_path, dados, feita, 1, "paulo-brito", CFG, executar=Executor()
    )

    for item in feita["itens"]:
        if item["canal"] == "paulo-brito" and item["gol"] == 1:
            item["ate"] = float(item["ate"]) - 10
    depois = Executor()
    nova = estudio.previa(
        tmp_path, dados, feita, 1, "paulo-brito", CFG, executar=depois
    )

    assert nova != antes
    assert len(depois.comandos) == 1


def test_previa_morta_no_meio_nao_fica_no_cache(tmp_path: Path):
    """Foi o que aconteceu com as pecas em 03/09: 48 bytes viraram peca boa.

    Com cache, o estrago dura para sempre - todo clique seguinte serve o
    arquivo quebrado sem nunca mais chamar o ffmpeg.
    """
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)

    with pytest.raises(cortador.FALHAS):
        estudio.previa(
            tmp_path, dados, feita, 1, "paulo-brito", CFG,
            executar=Morrendo(em=1),
        )

    assert list(estudio.pasta_cache(tmp_path).glob("previa-*.mp4")) == []


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
    assert estado["feito"] == estado["total"] == 2
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

    assert len(depois.comandos) == 2, (
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
    assert len(prontas) == 2, "os dois clipes, ambos batizados"
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
        filtro, _ = estudio.filtro_do_item(feita)
        nome = estudio.chave_da_peca(clipe["arquivo"], item["de"], item["ate"], filtro)
        (cache / f"{nome}.mp4").write_bytes(b"\x00" * 48)  # so o ftyp

    executor = Executor()
    estudio.montar(tmp_path, dados, feita, CFG, executar=executor)

    assert len(executor.comandos) == 3, "os dois clipes e a emenda"


# ------------------------------------------------- o item que falha e refeito

def test_o_item_que_falha_e_tentado_de_novo(tmp_path: Path):
    """O travamento do ffmpeg e intermitente: 2 de cada 3 no mesmo item.

    Com uma tentativa so, um travamento derrubava o render inteiro. Refazer o
    item transforma "painel morto" em "item X falhou, refazendo".
    """
    dados = _jogo(tmp_path)
    tropeco = Tropecando(falha_em=(2,))

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=tropeco)

    assert len(tropeco.comandos) == 4, "clipe que tropecou, ele de novo, clipe 2, emenda"
    assert len(list(estudio.pasta_das_pecas(tmp_path).glob("*.mp4"))) == 2


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

    assert len(list(estudio.pasta_das_pecas(tmp_path).glob("*.mp4"))) == 2


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


def test_as_entradas_de_imagem_vao_limitadas_por_tempo(tmp_path: Path):
    """Medido em 03/09: limitar as entradas de imagem com `-t` fez 3 de 4
    renders passarem, contra 1 de 3 sem isso. E a mitigacao barata do
    travamento do ffmpeg que o laudo mediu."""
    dados = _jogo(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG, executar=executor)

    do_clipe = executor.comandos[1]
    posicoes = [i for i, arg in enumerate(do_clipe) if arg == "-loop"]
    assert posicoes, "o clipe tem de mandar as mascaras como entrada de imagem"
    for posicao in posicoes:
        assert "-t" in do_clipe[posicao:posicao + 4], do_clipe[posicao:posicao + 5]


def test_anotar_um_pid_novo_nao_herda_a_morte_do_pid_velho(tmp_path: Path):
    """Achado na prova no jogo de verdade: o aviso falso voltou pelos fundos.

    O `anotar` le o estado antes de gravar, e essa leitura CORRIGE - se o PID
    que estava no arquivo tinha morrido, ela devolve `rodando: false`. Anotar o
    PID novo por cima disso gravava um render que acabou de nascer como render
    que ja morreu, e a primeira coisa que o operador lia ao clicar RENDER era
    "o render parou sozinho antes de terminar".
    """
    _render_no_disco(tmp_path, pid=111, pid_em=0.0)  # o render de ontem, morto

    estudio.anotar(tmp_path, rodando=True, feito=0, total=16, mensagem="na fila")
    depois = estudio.anotar(tmp_path, pid=222)

    assert depois["rodando"] is True
    assert depois["pid"] == 222
    assert estudio.estado(tmp_path, vivo=lambda p: False)["rodando"] is True


def test_estado_de_render_vivo_nao_reescreve_o_disco(tmp_path: Path):
    """Ler nao pode escrever a toa: o render em andamento escreve o tempo todo."""
    _render_no_disco(tmp_path, pid_em=0.0)
    antes = (tmp_path / estudio.NOME_ESTADO).read_text(encoding="utf-8")

    estudio.estado(tmp_path, vivo=lambda p: True)

    assert (tmp_path / estudio.NOME_ESTADO).read_text(encoding="utf-8") == antes


def test_com_identidade_vazia_o_filtro_e_o_de_hoje(tmp_path: Path):
    """A nao-regressao vista do estudio: sem marca nenhuma, nada mudou."""
    from testes.test_molde import FILTRO_DE_HOJE_DEITADO

    dados = _jogo(tmp_path)

    feita = receita.padrao(dados)
    filtro, rotulo = estudio.filtro_do_item(feita, identidade.PADROES)

    # A cor do fundo e a da torcida deste jogo; a geometria e que tem de ser
    # caractere por caractere a de hoje.
    esperado = FILTRO_DE_HOJE_DEITADO.replace(
        molde.COR_FUNDO, estudio.cor_do_fundo(feita)
    )
    assert filtro == esperado
    assert rotulo == "v"


def test_o_arranjo_de_palco_encolhe_a_janela_no_render(tmp_path: Path):
    """1280x720 cravado, na posicao do arranjo: e o 1:1 com a fonte."""
    dados = _jogo(tmp_path)
    ident = {**identidade.PADROES, "arranjo": "palco-alto"}

    filtro, _ = estudio.filtro_do_item(receita.padrao(dados), ident)

    assert "scale=1280:720:force_original_aspect_ratio=increase" in filtro
    assert "overlay=320:280" in filtro


def test_a_mascara_segue_a_janela_do_arranjo(tmp_path: Path):
    """Mascara do tamanho errado arredondaria canto onde nao tem canto."""
    from PIL import Image

    mascara, moldura = estudio.mascaras(
        tmp_path, "deitado",
        {"arranjo": "palco-alto", "escala": 1.0, "deslocamento": 0.0},
    )

    assert Image.open(mascara).size == (1280, 720)
    assert Image.open(moldura).size == (1280, 720)


def test_trocar_o_arranjo_refaz_as_pecas(tmp_path: Path):
    """Outra janela, outra imagem: o hash tem que perceber isso sozinho."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    estudio.montar(tmp_path, dados, feita, CFG, executar=Executor(),
                   ident=identidade.PADROES)

    depois = Executor()
    estudio.montar(
        tmp_path, dados, feita, CFG, executar=depois,
        ident={**identidade.PADROES, "arranjo": "palco-lateral"},
    )

    assert len(depois.comandos) == 3, "os dois clipes e a emenda"


def test_o_desvio_do_jogo_muda_so_aquele_jogo(tmp_path: Path):
    """O padrao do canal continua o padrao; este jogo sai dele, marcado."""
    dados = _jogo(tmp_path)
    com_desvio = receita.definir_moldagem(
        receita.padrao(dados), {"arranjo": "palco-alto"}
    )

    filtro, _ = estudio.filtro_do_item(com_desvio, identidade.PADROES)

    assert "overlay=320:280" in filtro


def test_a_assinatura_do_video_muda_quando_a_moldagem_muda(tmp_path: Path):
    """A recepcao compara assinaturas para saber se o mp4 do disco envelheceu."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)

    antes = estudio.assinatura(dados, feita, identidade.PADROES)
    depois = estudio.assinatura(
        dados, feita, {**identidade.PADROES, "arranjo": "palco-alto"}
    )

    assert antes != depois
