# REAÇÃO DA TORCIDA — plano de implementação

> **Para quem executa com agente:** SUB-SKILL OBRIGATÓRIA: use
> `superpowers:subagent-driven-development` (recomendado) ou
> `superpowers:executing-plans` para executar tarefa por tarefa. Os passos usam
> caixinha (`- [ ]`) para acompanhamento.

**Objetivo:** montar a ferramenta que grava lives de torcida, acha o instante da reação ao
gol dentro de cada gravação e entrega os clipes prontos para curadoria e montagem.

**Arquitetura:** esteira de `.bat` numerados chamando um núcleo Python testável, mais um
painel HTML servido localmente. O placar delimita uma janela larga de busca; a energia do
áudio acha o segundo exato dentro de cada gravação, resolvendo o atraso próprio de cada
live.

**Ferramentas:** Python 3.11+, numpy, pytest, `yt-dlp` e `ffmpeg` (já instalados em
`C:\yt-dlp`). Sem GPU, sem modelo de IA.

**Spec:** `docs/superpowers/specs/2026-09-01-reacao-da-torcida-design.md` — leia antes de
começar. O plano argumenta a partir dela.

## Restrições globais

Valem para todas as tarefas, sem exceção:

- **Formato de vídeo travado em 720p** (`altura_maxima: 720`). A 1080p, 13 canais ocupam
  85% dos 100 Mbps da placa de rede e a gravação cai no meio do jogo.
- **Mídia grava no `G:`**, nunca no `C:`. Caminho base: `G:\REACAO DA TORCIDA`.
- **Gravação é `-c copy`.** Nunca recodificar durante a gravação.
- **Gravação em MPEG-TS**, nunca `.mp4` direto — processo morto deixa `.mp4` ilegível.
- **Nenhum teste pode depender de internet** nem de arquivo de vídeo grande. Áudio
  sintético para o detector; `subprocess` de mentira para tudo que chama yt-dlp/ffmpeg.
- **Toda a lógica no núcleo**, nunca nos `.bat`. Os `.bat` são cascas de uma linha.
- **Falha de um canal não derruba os outros.** Canal sem live é resultado normal.
- **Nada some calado.** Clipe sem pico detectado vai marcado, não descartado.
- **Português** em código, commits e interface.
- Windows 10 + PowerShell. Caminhos com `pathlib.Path`, nunca concatenação de string.

## Ordem das tarefas

As tarefas estão ordenadas por risco. As tarefas 2 a 5 são o coração do projeto e a
tarefa 5 já permite rodar o piloto sobre um VOD — ou seja, **a premissa do projeto fica
provada antes de escrever uma linha de gravação ao vivo.** Se a tarefa 5 falhar no critério
de aceite, para tudo e reavalia o detector; não adianta seguir.

| # | Tarefa | Entrega |
|---|---|---|
| 1 | Fundação | projeto de pé, config carregando, pytest rodando |
| 2 | `relogio` | horário de relógio → (arquivo, segundo) |
| 3 | `detector` | energia do áudio → começo do grito |
| 4 | `cortador` | clipe extraído, inclusive atravessando pedaços |
| 5 | **Modo teste** | **a régua: erro em segundos sobre um VOD** |
| 6 | `catalogo` | estado do jogo em disco |
| 7 | `canais` | cadastro e descoberta de live |
| 8 | `gravador` | N gravações em paralelo, com religamento automático de quem cair |
| 9 | `montador` | compilação com cartelas |
| 10 | `painel` | curadoria no navegador |
| 11 | Esteira | os quatro `.bat` |

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `nucleo/config.py` | carregar `dados/config.json` sobre os padrões |
| `nucleo/relogio.py` | aritmética de tempo: horário ↔ (arquivo, segundo) |
| `nucleo/detector.py` | energia do áudio, pico, começo da subida, confiança |
| `nucleo/cortador.py` | montar comandos ffmpeg de extração e corte |
| `nucleo/teste_vod.py` | modo teste: medir erro contra gabarito |
| `nucleo/catalogo.py` | ler e escrever `catalogo.json` |
| `nucleo/canais.py` | cadastro de canais e descoberta de live |
| `nucleo/gravador.py` | iniciar e supervisionar gravações |
| `nucleo/montador.py` | normalizar, cartelar e concatenar clipes |
| `painel/servidor.py` | servidor local e rotas |
| `painel/pagina.html` | página de curadoria |
| `testes/test_*.py` | um arquivo de teste por módulo |

Nenhum módulo do núcleo importa outro além de `config`, `relogio` e `catalogo`. O
`detector` não sabe o que é futebol; o `relogio` não abre arquivo de vídeo; o `cortador`
não sabe o que é gol. Manter essas fronteiras é o que permite testar sem mídia real.

---

### Tarefa 1: Fundação

**Arquivos:**
- Criar: `requisitos.txt`, `pytest.ini`, `nucleo/__init__.py`, `nucleo/config.py`
- Criar: `testes/__init__.py`, `testes/test_config.py`

**Interfaces:**
- Produz: `config.carregar(caminho: Path | None = None) -> dict` — devolve os padrões com
  o arquivo do usuário sobreposto por cima. `config.PADROES: dict`.

- [ ] **Passo 1: criar `requisitos.txt` e `pytest.ini`**

`requisitos.txt`:
```
numpy>=1.26
pytest>=8.0
```

`pytest.ini`:
```ini
[pytest]
testpaths = testes
python_files = test_*.py
addopts = -q
```

- [ ] **Passo 2: escrever o teste que falha**

`testes/test_config.py`:
```python
import json
from pathlib import Path

from nucleo import config


def test_padroes_sao_usados_quando_nao_ha_arquivo():
    c = config.carregar(None)
    assert c["altura_maxima"] == 720
    assert c["biblioteca"].endswith("REACAO DA TORCIDA")
    assert c["segundos_antes"] == 8
    assert c["segundos_depois"] == 12


def test_arquivo_do_usuario_sobrepoe_apenas_o_que_traz(tmp_path: Path):
    arquivo = tmp_path / "config.json"
    arquivo.write_text(json.dumps({"altura_maxima": 480}), encoding="utf-8")

    c = config.carregar(arquivo)

    assert c["altura_maxima"] == 480
    assert c["segundos_antes"] == 8  # continua vindo do padrão
```

- [ ] **Passo 3: rodar e ver falhar**

Rodar: `python -m pytest testes/test_config.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo'`

- [ ] **Passo 4: escrever a implementação mínima**

`nucleo/__init__.py`: arquivo vazio.
`testes/__init__.py`: arquivo vazio.

`nucleo/config.py`:
```python
"""Configuração do projeto: padrões e sobreposição pelo arquivo do usuário."""
import json
from pathlib import Path

PADROES = {
    "biblioteca": r"G:\REACAO DA TORCIDA",
    "altura_maxima": 720,
    "segundos_antes": 8,
    "segundos_depois": 12,
    "janela_antes": 30,
    "janela_depois": 180,
    "limiar_confianca_db": 6.0,
    "duracao_pedaco": 600,
    "teto_canais": 20,
    "disco_minimo_gb": 60,
    "caminho_ytdlp": r"C:\yt-dlp\yt-dlp.exe",
    "caminho_ffmpeg": r"C:\yt-dlp\ffmpeg.exe",
    "caminho_ffprobe": r"C:\ffmpeg\bin\ffprobe.exe",  # conferido: nao existe em C:\yt-dlp
    "fonte_cartela": r"C:\Windows\Fonts\arialbd.ttf",
    "segundos_entre_conferencias": 20,
}

PADRAO_ARQUIVO = Path(__file__).resolve().parent.parent / "dados" / "config.json"


def carregar(caminho: Path | None = PADRAO_ARQUIVO) -> dict:
    """Devolve os padrões com o arquivo do usuário sobreposto por cima."""
    valores = dict(PADROES)
    if caminho is not None and Path(caminho).is_file():
        do_usuario = json.loads(Path(caminho).read_text(encoding="utf-8"))
        valores.update(do_usuario)
    return valores
```

- [ ] **Passo 5: rodar e ver passar**

Rodar: `python -m pytest testes/test_config.py -v`
Esperado: 2 passed

- [ ] **Passo 6: instalar as dependências e criar os arquivos de trabalho**

Os `.exemplo.json` estão versionados; os arquivos reais **não** (o `.gitignore` os exclui,
porque `canais.json` é a lista de trabalho do operador). Sem esta cópia, a etapa 0 quebra
com `FileNotFoundError` na primeira execução.

```powershell
python -m pip install -r requisitos.txt
Copy-Item dados\config.exemplo.json dados\config.json
Copy-Item dados\canais.exemplo.json dados\canais.json
```

Confirme as três ferramentas externas:

```powershell
foreach ($k in "caminho_ytdlp","caminho_ffmpeg","caminho_ffprobe","fonte_cartela") {
  $v = python -c "from nucleo import config; print(config.carregar()['$k'])"
  "$k = $v -> $(Test-Path $v)"
}
```

Todas devem dar `True`. **Atenção:** o `ffmpeg.exe` vive em `C:\yt-dlp`, mas o
`ffprobe.exe` **não** — ele está em `C:\ffmpeg\bin` (conferido em 02/09/2026). Os padrões
já apontam para os lugares certos; se alguma linha der `False`, corrija no
`dados/config.json`. O `ffprobe` é o que mede o pedaço final de uma gravação interrompida
(tarefa 11); sem ele, gol no fim de jogo se perde.

- [ ] **Passo 7: commitar**

```bash
git add requisitos.txt pytest.ini nucleo/ testes/
git commit -m "fundacao: estrutura do projeto e carregamento de configuracao"
```

---

### Tarefa 2: relogio — aritmética de tempo

Esta é a peça central da spec. Ela traduz "o gol foi às 21:37:00" em "segundo 412 do
arquivo `parte-004.ts`". Todo o resto depende dela estar certa.

**Arquivos:**
- Criar: `nucleo/relogio.py`
- Criar: `testes/test_relogio.py`

**Interfaces:**
- Consome: nada.
- Produz:
  - `Pedaco(arquivo: str, inicio: float, fim: float)` — dataclass. `inicio`/`fim` em
    segundos desde o começo da sessão.
  - `Sessao(t0: datetime, pedacos: list[Pedaco])` — dataclass.
  - `ler_segmentos(csv: Path, t0: datetime) -> Sessao`
  - `Localizacao(arquivo: str, segundo: float)` — dataclass.
  - `localizar(sessoes: list[Sessao], momento: datetime) -> Localizacao | None`
  - `Trecho(arquivo: str, inicio: float, fim: float)` — dataclass. Recorte dentro de um
    arquivo, em segundos daquele arquivo.
  - `trechos(sessoes: list[Sessao], inicio: datetime, fim: datetime) -> list[Trecho]`
  - `cobertura(sessoes: list[Sessao]) -> list[tuple[datetime, datetime]]`
  - `janela(momento: datetime, antes: int, depois: int) -> tuple[datetime, datetime]`

**Fora do escopo aqui:** converter "38 do 2º tempo" em horário de relógio. A spec trata
isso como opcional e só é possível com os horários de início de cada tempo registrados —
acréscimo e intervalo tornam a conta impossível sem eles. A entrada do sistema é o
**horário de relógio** do gol.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_relogio.py`:
```python
from datetime import datetime, timedelta
from pathlib import Path

from nucleo import relogio

T0 = datetime(2026, 9, 1, 21, 0, 0)


def sessao_simples() -> relogio.Sessao:
    """Três pedaços: 0-600, 600-1200, 1200-1500 (o último mais curto)."""
    return relogio.Sessao(
        t0=T0,
        pedacos=[
            relogio.Pedaco("parte-000.ts", 0.0, 600.0),
            relogio.Pedaco("parte-001.ts", 600.0, 1200.0),
            relogio.Pedaco("parte-002.ts", 1200.0, 1500.0),
        ],
    )


def test_localiza_dentro_do_primeiro_pedaco():
    achado = relogio.localizar([sessao_simples()], T0 + timedelta(seconds=125))
    assert achado.arquivo == "parte-000.ts"
    assert achado.segundo == 125.0


def test_localiza_no_pedaco_do_meio_descontando_o_offset():
    achado = relogio.localizar([sessao_simples()], T0 + timedelta(seconds=725))
    assert achado.arquivo == "parte-001.ts"
    assert achado.segundo == 125.0


def test_pedaco_final_mais_curto_e_respeitado():
    achado = relogio.localizar([sessao_simples()], T0 + timedelta(seconds=1499))
    assert achado.arquivo == "parte-002.ts"
    assert achado.segundo == 299.0


def test_momento_depois_do_fim_nao_e_coberto():
    assert relogio.localizar([sessao_simples()], T0 + timedelta(seconds=1600)) is None


def test_momento_antes_do_inicio_nao_e_coberto():
    assert relogio.localizar([sessao_simples()], T0 - timedelta(seconds=5)) is None


def test_buraco_entre_sessoes_nao_e_coberto():
    """A gravacao caiu aos 1500s e so religou 120s depois."""
    primeira = sessao_simples()
    segunda = relogio.Sessao(
        t0=T0 + timedelta(seconds=1620),
        pedacos=[relogio.Pedaco("parte-100.ts", 0.0, 600.0)],
    )
    sessoes = [primeira, segunda]

    assert relogio.localizar(sessoes, T0 + timedelta(seconds=1550)) is None

    depois = relogio.localizar(sessoes, T0 + timedelta(seconds=1700))
    assert depois.arquivo == "parte-100.ts"
    assert depois.segundo == 80.0


def test_trechos_dentro_de_um_pedaco_so():
    recortes = relogio.trechos(
        [sessao_simples()],
        T0 + timedelta(seconds=100),
        T0 + timedelta(seconds=120),
    )
    assert recortes == [relogio.Trecho("parte-000.ts", 100.0, 120.0)]


def test_trechos_atravessando_dois_pedacos():
    recortes = relogio.trechos(
        [sessao_simples()],
        T0 + timedelta(seconds=595),
        T0 + timedelta(seconds=615),
    )
    assert recortes == [
        relogio.Trecho("parte-000.ts", 595.0, 600.0),
        relogio.Trecho("parte-001.ts", 0.0, 15.0),
    ]


def test_trechos_pulam_o_buraco_entre_sessoes():
    segunda = relogio.Sessao(
        t0=T0 + timedelta(seconds=1620),
        pedacos=[relogio.Pedaco("parte-100.ts", 0.0, 600.0)],
    )
    recortes = relogio.trechos(
        [sessao_simples(), segunda],
        T0 + timedelta(seconds=1490),
        T0 + timedelta(seconds=1630),
    )
    assert recortes == [
        relogio.Trecho("parte-002.ts", 290.0, 300.0),
        relogio.Trecho("parte-100.ts", 0.0, 10.0),
    ]


def test_le_o_csv_que_o_ffmpeg_escreve(tmp_path: Path):
    csv = tmp_path / "segmentos.csv"
    csv.write_text(
        "parte-000.ts,0.000000,600.000000\n"
        "parte-001.ts,600.000000,1200.000000\n",
        encoding="utf-8",
    )

    sessao = relogio.ler_segmentos(csv, T0)

    assert sessao.t0 == T0
    assert len(sessao.pedacos) == 2
    assert sessao.pedacos[1] == relogio.Pedaco("parte-001.ts", 600.0, 1200.0)


def test_cobertura_lista_os_intervalos_realmente_gravados():
    segunda = relogio.Sessao(
        t0=T0 + timedelta(seconds=1620),
        pedacos=[relogio.Pedaco("parte-100.ts", 0.0, 600.0)],
    )
    intervalos = relogio.cobertura([sessao_simples(), segunda])
    assert intervalos == [
        (T0, T0 + timedelta(seconds=1500)),
        (T0 + timedelta(seconds=1620), T0 + timedelta(seconds=2220)),
    ]
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_relogio.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.relogio'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/relogio.py`:
```python
"""Traduz horario de relogio em posicao dentro dos arquivos gravados.

Uma sessao e um trecho continuo de gravacao. Se a gravacao cai e religa, abre
uma nova sessao com seu proprio t0 — e o buraco entre elas fica visivel, porque
nenhum momento dentro dele e coberto.
"""
import csv as _csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Pedaco:
    arquivo: str
    inicio: float  # segundos desde o comeco da sessao
    fim: float


@dataclass(frozen=True)
class Sessao:
    t0: datetime  # horario de relogio do primeiro frame da sessao
    pedacos: list[Pedaco]


@dataclass(frozen=True)
class Localizacao:
    arquivo: str
    segundo: float  # segundos desde o comeco daquele arquivo


@dataclass(frozen=True)
class Trecho:
    arquivo: str
    inicio: float
    fim: float


def ler_segmentos(csv: Path, t0: datetime) -> Sessao:
    """Le o CSV que o ffmpeg escreve com -segment_list_type csv."""
    pedacos = []
    with Path(csv).open(encoding="utf-8", newline="") as f:
        for linha in _csv.reader(f):
            if len(linha) < 3:
                continue
            pedacos.append(Pedaco(linha[0], float(linha[1]), float(linha[2])))
    return Sessao(t0=t0, pedacos=pedacos)


def _decorridos(sessao: Sessao, momento: datetime) -> float:
    return (momento - sessao.t0).total_seconds()


def localizar(sessoes: list[Sessao], momento: datetime) -> Localizacao | None:
    """Devolve o arquivo e o segundo correspondentes, ou None se nao foi gravado."""
    for sessao in sessoes:
        decorridos = _decorridos(sessao, momento)
        if decorridos < 0:
            continue
        for pedaco in sessao.pedacos:
            if pedaco.inicio <= decorridos < pedaco.fim:
                return Localizacao(pedaco.arquivo, decorridos - pedaco.inicio)
    return None


def trechos(sessoes: list[Sessao], inicio: datetime, fim: datetime) -> list[Trecho]:
    """Recortes que cobrem o intervalo pedido, na ordem, pulando o que nao foi gravado."""
    recortes: list[Trecho] = []
    for sessao in sessoes:
        de = _decorridos(sessao, inicio)
        ate = _decorridos(sessao, fim)
        for pedaco in sessao.pedacos:
            comeco = max(de, pedaco.inicio)
            termino = min(ate, pedaco.fim)
            if termino > comeco:
                recortes.append(
                    Trecho(pedaco.arquivo, comeco - pedaco.inicio, termino - pedaco.inicio)
                )
    return recortes


def cobertura(sessoes: list[Sessao]) -> list[tuple[datetime, datetime]]:
    """Intervalos de relogio realmente gravados. Serve para explicar um 'nao coberto'."""
    intervalos = []
    for sessao in sessoes:
        if not sessao.pedacos:
            continue
        comeco = sessao.t0 + timedelta(seconds=sessao.pedacos[0].inicio)
        termino = sessao.t0 + timedelta(seconds=sessao.pedacos[-1].fim)
        intervalos.append((comeco, termino))
    return intervalos


def janela(momento: datetime, antes: int, depois: int) -> tuple[datetime, datetime]:
    """Janela larga de busca em volta do horario informado do gol."""
    return momento - timedelta(seconds=antes), momento + timedelta(seconds=depois)
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_relogio.py -v`
Esperado: 11 passed

- [ ] **Passo 5: commitar**

```bash
git add nucleo/relogio.py testes/test_relogio.py
git commit -m "relogio: horario de relogio para arquivo e segundo, com buracos entre sessoes"
```

---

### Tarefa 3: detector — achar o começo do grito

**Arquivos:**
- Criar: `nucleo/detector.py`
- Criar: `testes/test_detector.py`

**Interfaces:**
- Consome: nada.
- Produz:
  - `Achado(instante: float, confianca_db: float, tem_pico: bool)` — dataclass. `instante`
    em segundos **relativos ao começo do wav analisado**.
  - `curva_db(amostras: np.ndarray, taxa: int, quadro_s: float = 0.5) -> np.ndarray`
  - `suavizar(curva: np.ndarray, quadros: int) -> np.ndarray`
  - `achar(curva: np.ndarray, quadro_s: float, limiar_db: float) -> Achado`
  - `ler_wav(caminho: Path) -> tuple[np.ndarray, int]`
  - `analisar(caminho_wav: Path, limiar_db: float = 6.0) -> Achado`

**Decisão que precisa ser respeitada:** o instante devolvido é o **começo da subida**, não
o auge do grito. Cortar pelo auge perde o susto, que é a graça do vídeo. O começo da subida
é o último ponto antes do pico em que a curva ainda estava abaixo de
`base + 50% da altura do pico`.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_detector.py`:
```python
import wave
from pathlib import Path

import numpy as np

from nucleo import detector

TAXA = 16000


def gravar_wav(caminho: Path, amostras: np.ndarray, taxa: int = TAXA) -> Path:
    inteiros = np.clip(amostras, -1.0, 1.0)
    inteiros = (inteiros * 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(inteiros.tobytes())
    return caminho


def audio_com_grito(duracao_s: int = 60, comeco_do_grito: float = 40.0) -> np.ndarray:
    """Ruido baixo constante e, a partir de `comeco_do_grito`, um trecho bem mais alto."""
    gerador = np.random.default_rng(42)
    sinal = gerador.normal(0.0, 0.02, duracao_s * TAXA)
    de = int(comeco_do_grito * TAXA)
    ate = int((comeco_do_grito + 8) * TAXA)
    subida = np.linspace(0.0, 1.0, int(0.5 * TAXA))
    sinal[de : de + len(subida)] += gerador.normal(0.0, 0.5, len(subida)) * subida
    sinal[de + len(subida) : ate] += gerador.normal(0.0, 0.5, ate - de - len(subida))
    return sinal


def test_acha_o_comeco_da_subida_e_nao_o_auge(tmp_path: Path):
    arquivo = gravar_wav(tmp_path / "grito.wav", audio_com_grito())

    achado = detector.analisar(arquivo, limiar_db=6.0)

    assert achado.tem_pico
    assert abs(achado.instante - 40.0) <= 1.5, f"achou em {achado.instante}"
    assert achado.confianca_db > 10


def test_ruido_constante_nao_tem_pico(tmp_path: Path):
    gerador = np.random.default_rng(7)
    arquivo = gravar_wav(tmp_path / "plano.wav", gerador.normal(0.0, 0.05, 60 * TAXA))

    achado = detector.analisar(arquivo, limiar_db=6.0)

    assert not achado.tem_pico


def test_sem_pico_ainda_devolve_um_instante_utilizavel(tmp_path: Path):
    """Nada some calado: mesmo sem pico, ha um instante para cortar e conferir."""
    gerador = np.random.default_rng(7)
    arquivo = gravar_wav(tmp_path / "plano.wav", gerador.normal(0.0, 0.05, 60 * TAXA))

    achado = detector.analisar(arquivo, limiar_db=6.0)

    assert 0.0 <= achado.instante <= 60.0


def test_grito_no_comeco_do_trecho_nao_estoura(tmp_path: Path):
    arquivo = gravar_wav(tmp_path / "cedo.wav", audio_com_grito(comeco_do_grito=0.5))
    achado = detector.analisar(arquivo, limiar_db=6.0)
    assert achado.instante >= 0.0


def test_curva_em_db_tem_um_valor_por_quadro():
    amostras = np.zeros(TAXA * 10) + 0.1
    curva = detector.curva_db(amostras, TAXA, quadro_s=0.5)
    assert len(curva) == 20
    assert np.all(np.isfinite(curva))
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_detector.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.detector'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/detector.py`:
```python
"""Acha o comeco da explosao de audio dentro de um trecho.

Nao sabe o que e futebol: recebe um wav, devolve um instante e uma confianca.
Aritmetica simples de propósito — a maquina nao tem GPU.
"""
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

QUADRO_S = 0.5
SUAVIZACAO_S = 3.0
FRACAO_DA_SUBIDA = 0.5


@dataclass(frozen=True)
class Achado:
    instante: float  # segundos desde o comeco do wav analisado
    confianca_db: float
    tem_pico: bool


def ler_wav(caminho: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(caminho), "rb") as w:
        taxa = w.getframerate()
        canais = w.getnchannels()
        bruto = w.readframes(w.getnframes())
    amostras = np.frombuffer(bruto, dtype="<i2").astype(np.float32) / 32768.0
    if canais > 1:
        amostras = amostras.reshape(-1, canais).mean(axis=1)
    return amostras, taxa


def curva_db(amostras: np.ndarray, taxa: int, quadro_s: float = QUADRO_S) -> np.ndarray:
    """Energia RMS por quadro, em decibeis."""
    por_quadro = max(1, int(taxa * quadro_s))
    inteiros = len(amostras) // por_quadro
    if inteiros == 0:
        return np.array([-120.0])
    blocos = amostras[: inteiros * por_quadro].reshape(inteiros, por_quadro)
    rms = np.sqrt(np.mean(blocos.astype(np.float64) ** 2, axis=1))
    return 20.0 * np.log10(rms + 1e-9)


def suavizar(curva: np.ndarray, quadros: int) -> np.ndarray:
    if quadros <= 1 or len(curva) < quadros:
        return curva
    nucleo = np.ones(quadros) / quadros
    return np.convolve(curva, nucleo, mode="same")


def achar(curva: np.ndarray, quadro_s: float, limiar_db: float) -> Achado:
    """Pico, linha de base e o ponto em que a subida comeca."""
    base = float(np.median(curva))
    indice_pico = int(np.argmax(curva))
    pico = float(curva[indice_pico])
    altura = pico - base

    corte = base + FRACAO_DA_SUBIDA * altura
    indice_subida = indice_pico
    while indice_subida > 0 and curva[indice_subida - 1] >= corte:
        indice_subida -= 1

    return Achado(
        instante=indice_subida * quadro_s,
        confianca_db=altura,
        tem_pico=altura >= limiar_db,
    )


def analisar(caminho_wav: Path, limiar_db: float = 6.0) -> Achado:
    amostras, taxa = ler_wav(Path(caminho_wav))
    curva = curva_db(amostras, taxa)
    quadros = max(1, int(SUAVIZACAO_S / QUADRO_S))
    return achar(suavizar(curva, quadros), QUADRO_S, limiar_db)
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_detector.py -v`
Esperado: 5 passed

Se `test_acha_o_comeco_da_subida_e_nao_o_auge` falhar por pouco, o suspeito é a suavização
de 3 s empurrando o começo para trás. Ajuste `SUAVIZACAO_S` ou `FRACAO_DA_SUBIDA` — **não**
afrouxe a tolerância do teste, que é o que garante o critério de aceite do piloto.

- [ ] **Passo 5: commitar**

```bash
git add nucleo/detector.py testes/test_detector.py
git commit -m "detector: acha o comeco da explosao de audio por energia em db"
```

---

### Tarefa 4: cortador — extrair o clipe

**Arquivos:**
- Criar: `nucleo/cortador.py`
- Criar: `testes/test_cortador.py`

**Interfaces:**
- Consome: `relogio.Trecho`.
- Produz:
  - `comando_audio(fonte: Path, inicio: float, duracao: float, saida: Path, ffmpeg: str) -> list[str]`
  - `comando_corte(fonte: Path, inicio: float, duracao: float, saida: Path, ffmpeg: str) -> list[str]`
  - `comando_juntar(lista: Path, saida: Path, ffmpeg: str) -> list[str]`
  - `escrever_lista_concat(trechos: list[relogio.Trecho], pasta: Path, destino: Path) -> Path`
  - `preparar_fonte(trechos, pasta, temporaria, ffmpeg, executar) -> tuple[Path, float]` —
    devolve o arquivo de onde cortar e o deslocamento a somar. Um trecho só: devolve o
    próprio arquivo e o deslocamento dele. Vários trechos: junta antes e devolve
    deslocamento `0.0`.
  - `executar(comando: list[str]) -> None` — invólucro de `subprocess.run` com
    `check=True`. Existe para ser substituído nos testes.
  - `duracao(arquivo: Path, ffprobe: str, rodar=_rodar_texto) -> float` — duração em
    segundos via ffprobe. Serve para medir o pedaço final de uma gravação que foi
    interrompida e por isso não entrou no CSV de segmentos (ver tarefa 11).
  - `_rodar_texto(comando: list[str]) -> str` — invólucro substituível nos testes.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_cortador.py`:
```python
from pathlib import Path

from nucleo import cortador, relogio

FFMPEG = r"C:\yt-dlp\ffmpeg.exe"


def test_comando_de_corte_recodifica_para_ser_preciso():
    cmd = cortador.comando_corte(Path("a.ts"), 100.0, 20.0, Path("saida.mp4"), FFMPEG)
    texto = " ".join(cmd)
    assert cmd[0] == FFMPEG
    assert "-ss" in cmd and "100.0" in cmd
    assert "-t" in cmd and "20.0" in cmd
    assert "libx264" in texto, "corte precisa recodificar, senao pula para o keyframe"
    assert "-c copy" not in texto


def test_comando_de_audio_pede_mono_16k_wav():
    cmd = cortador.comando_audio(Path("a.ts"), 10.0, 30.0, Path("t.wav"), FFMPEG)
    texto = " ".join(cmd)
    assert "-vn" in cmd
    assert "16000" in texto
    assert "-ac" in cmd and "1" in cmd


def test_um_trecho_so_usa_o_arquivo_direto(tmp_path: Path):
    trechos = [relogio.Trecho("parte-000.ts", 100.0, 120.0)]
    chamadas = []

    fonte, deslocamento = cortador.preparar_fonte(
        trechos, tmp_path, tmp_path / "junto.ts", FFMPEG, executar=chamadas.append
    )

    assert fonte == tmp_path / "parte-000.ts"
    assert deslocamento == 100.0
    assert chamadas == [], "com um trecho so nao ha nada a juntar"


def test_dois_trechos_sao_juntados_antes_do_corte(tmp_path: Path):
    trechos = [
        relogio.Trecho("parte-000.ts", 595.0, 600.0),
        relogio.Trecho("parte-001.ts", 0.0, 15.0),
    ]
    chamadas = []

    fonte, deslocamento = cortador.preparar_fonte(
        trechos, tmp_path, tmp_path / "junto.ts", FFMPEG, executar=chamadas.append
    )

    assert fonte == tmp_path / "junto.ts"
    assert deslocamento == 0.0
    assert len(chamadas) == 1
    assert "concat" in " ".join(chamadas[0])


def test_duracao_le_o_numero_que_o_ffprobe_devolve():
    def rodar_falso(comando):
        assert "ffprobe" in comando[0]
        return "  412.480000\n"

    assert cortador.duracao(Path("a.ts"), "ffprobe", rodar=rodar_falso) == 412.48


def test_duracao_de_arquivo_ilegivel_devolve_zero():
    """Pedaco truncado no fim da gravacao: nao pode estourar."""
    assert cortador.duracao(Path("a.ts"), "ffprobe", rodar=lambda c: "N/A\n") == 0.0


def test_lista_de_concat_nomeia_os_arquivos_na_ordem(tmp_path: Path):
    trechos = [
        relogio.Trecho("parte-000.ts", 595.0, 600.0),
        relogio.Trecho("parte-001.ts", 0.0, 15.0),
    ]
    lista = cortador.escrever_lista_concat(trechos, tmp_path, tmp_path / "lista.txt")
    conteudo = lista.read_text(encoding="utf-8")
    assert conteudo.index("parte-000.ts") < conteudo.index("parte-001.ts")
    assert conteudo.count("file ") == 2
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_cortador.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.cortador'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/cortador.py`:
```python
"""Monta e executa os comandos ffmpeg de extracao de audio e de corte de clipe.

Nao sabe o que e gol: recebe inicio e duracao.
"""
import subprocess
from pathlib import Path
from typing import Callable

from nucleo import relogio


def executar(comando: list[str]) -> None:
    subprocess.run(comando, check=True, capture_output=True)


def _rodar_texto(comando: list[str]) -> str:
    return subprocess.run(comando, capture_output=True, text=True).stdout


def duracao(
    arquivo: Path, ffprobe: str, rodar: Callable[[list[str]], str] = _rodar_texto
) -> float:
    """Duracao em segundos. Devolve 0.0 se o arquivo estiver truncado ou ilegivel."""
    saida = rodar([
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(arquivo),
    ])
    try:
        return float(saida.strip())
    except (TypeError, ValueError):
        return 0.0


def comando_audio(
    fonte: Path, inicio: float, duracao: float, saida: Path, ffmpeg: str
) -> list[str]:
    return [
        ffmpeg, "-y",
        "-ss", str(inicio),
        "-i", str(fonte),
        "-t", str(duracao),
        "-vn", "-ac", "1", "-ar", "16000",
        str(saida),
    ]


def comando_corte(
    fonte: Path, inicio: float, duracao: float, saida: Path, ffmpeg: str
) -> list[str]:
    # Recodifica de proposito: com -c copy o corte pula para o keyframe anterior
    # e a reacao comeca fora de hora. Sao 20 segundos, custa quase nada.
    return [
        ffmpeg, "-y",
        "-ss", str(inicio),
        "-i", str(fonte),
        "-t", str(duracao),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(saida),
    ]


def comando_juntar(lista: Path, saida: Path, ffmpeg: str) -> list[str]:
    return [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(lista),
        "-c", "copy",
        str(saida),
    ]


def escrever_lista_concat(
    trechos: list[relogio.Trecho], pasta: Path, destino: Path
) -> Path:
    linhas = [f"file '{(pasta / t.arquivo).as_posix()}'" for t in trechos]
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return destino


def preparar_fonte(
    trechos: list[relogio.Trecho],
    pasta: Path,
    temporaria: Path,
    ffmpeg: str,
    executar: Callable[[list[str]], None] = executar,
) -> tuple[Path, float]:
    """Devolve (arquivo de onde cortar, deslocamento a somar ao instante)."""
    if not trechos:
        raise ValueError("sem trecho gravado para esse intervalo")
    if len(trechos) == 1:
        return pasta / trechos[0].arquivo, trechos[0].inicio

    lista = escrever_lista_concat(trechos, pasta, temporaria.with_suffix(".txt"))
    executar(comando_juntar(lista, temporaria, ffmpeg))
    return temporaria, 0.0
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_cortador.py -v`
Esperado: 7 passed

- [ ] **Passo 5: commitar**

```bash
git add nucleo/cortador.py testes/test_cortador.py
git commit -m "cortador: comandos de audio e corte preciso, com juncao entre pedacos"
```

---

### Tarefa 5: modo teste — a régua do projeto

**Esta é a tarefa que decide se o projeto funciona.** Ela roda sobre um VOD já baixado,
com gols de posição conhecida, e informa de quantos segundos o detector errou. Só depois
de o resultado ser aceitável é que vale a pena escrever gravação ao vivo.

**Critério de aceite:** erro de no máximo 3 segundos em pelo menos 80% dos gols.

**Arquivos:**
- Criar: `nucleo/teste_vod.py`
- Criar: `testes/test_teste_vod.py`

**Interfaces:**
- Consome: `detector.analisar`, `cortador.comando_audio`, `cortador.executar`,
  `config.carregar`.
- Produz:
  - `Medida(gol: int, esperado: float, achado: float, erro: float, confianca_db: float, tem_pico: bool)`
  - `medir(vod: Path, gabarito: list[float], cfg: dict, pasta_temp: Path, executar=cortador.executar) -> list[Medida]`
  - `resumir(medidas: list[Medida], tolerancia: float = 3.0) -> dict` — devolve
    `{"total", "dentro", "fracao", "aprovado", "erro_medio"}`.
  - `principal(argv: list[str] | None = None) -> int` — entrada de linha de comando.

Como o VOD é um arquivo só, aqui **não se usa `relogio`**: a posição do gol já vem em
segundos do arquivo. É de propósito — isola o detector para poder medi-lo sozinho.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_teste_vod.py`:
```python
from pathlib import Path

from nucleo import teste_vod


def test_resumo_aprova_quando_a_maioria_esta_dentro_da_tolerancia():
    medidas = [
        teste_vod.Medida(1, 100.0, 101.0, 1.0, 14.0, True),
        teste_vod.Medida(2, 200.0, 201.5, 1.5, 12.0, True),
        teste_vod.Medida(3, 300.0, 290.0, 10.0, 4.0, False),
        teste_vod.Medida(4, 400.0, 400.5, 0.5, 20.0, True),
        teste_vod.Medida(5, 500.0, 502.0, 2.0, 9.0, True),
    ]
    resumo = teste_vod.resumir(medidas, tolerancia=3.0)
    assert resumo["total"] == 5
    assert resumo["dentro"] == 4
    assert resumo["fracao"] == 0.8
    assert resumo["aprovado"] is True


def test_resumo_reprova_abaixo_de_oitenta_por_cento():
    medidas = [
        teste_vod.Medida(1, 100.0, 130.0, 30.0, 3.0, False),
        teste_vod.Medida(2, 200.0, 201.0, 1.0, 12.0, True),
    ]
    assert teste_vod.resumir(medidas, tolerancia=3.0)["aprovado"] is False


def test_medir_abre_uma_janela_por_gol_e_soma_o_offset(tmp_path: Path, monkeypatch):
    """A janela comeca antes do gol, entao o instante achado precisa voltar
    para a escala do arquivo somando o comeco da janela."""
    chamadas = []

    def executar_falso(comando):
        chamadas.append(comando)
        # o proximo passo do medir vai ler este wav; cria um vazio valido
        Path(comando[-1]).write_bytes(b"")

    def analisar_falso(caminho, limiar_db):
        # o detector diz "a subida comecou 35s depois do inicio da janela"
        from nucleo import detector
        return detector.Achado(instante=35.0, confianca_db=15.0, tem_pico=True)

    monkeypatch.setattr(teste_vod.detector, "analisar", analisar_falso)

    cfg = {"janela_antes": 30, "janela_depois": 180, "limiar_confianca_db": 6.0,
           "caminho_ffmpeg": "ffmpeg"}

    medidas = teste_vod.medir(
        Path("jogo.mp4"), [1000.0], cfg, tmp_path, executar=executar_falso
    )

    assert len(medidas) == 1
    # janela comecou em 1000-30 = 970; 970 + 35 = 1005
    assert medidas[0].achado == 1005.0
    assert medidas[0].erro == 5.0
    assert len(chamadas) == 1


def test_janela_nao_comeca_antes_do_inicio_do_arquivo(tmp_path: Path, monkeypatch):
    def executar_falso(comando):
        Path(comando[-1]).write_bytes(b"")

    def analisar_falso(caminho, limiar_db):
        from nucleo import detector
        return detector.Achado(instante=0.0, confianca_db=15.0, tem_pico=True)

    monkeypatch.setattr(teste_vod.detector, "analisar", analisar_falso)
    cfg = {"janela_antes": 30, "janela_depois": 180, "limiar_confianca_db": 6.0,
           "caminho_ffmpeg": "ffmpeg"}

    medidas = teste_vod.medir(Path("j.mp4"), [10.0], cfg, tmp_path, executar=executar_falso)

    assert medidas[0].achado == 0.0, "janela travada em zero, nao em -20"
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_teste_vod.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.teste_vod'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/teste_vod.py`:
```python
"""Modo teste: mede o erro do detector contra um gabarito conhecido.

E a regua do projeto. Sem essa medida nao existe base para dizer que funciona.
"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nucleo import config, cortador, detector

TOLERANCIA_S = 3.0
FRACAO_MINIMA = 0.8


@dataclass(frozen=True)
class Medida:
    gol: int
    esperado: float
    achado: float
    erro: float
    confianca_db: float
    tem_pico: bool


def medir(
    vod: Path,
    gabarito: list[float],
    cfg: dict,
    pasta_temp: Path,
    executar: Callable[[list[str]], None] = cortador.executar,
) -> list[Medida]:
    pasta_temp.mkdir(parents=True, exist_ok=True)
    medidas = []
    for numero, esperado in enumerate(gabarito, start=1):
        inicio = max(0.0, esperado - cfg["janela_antes"])
        duracao = cfg["janela_antes"] + cfg["janela_depois"]
        wav = pasta_temp / f"janela-{numero:02d}.wav"
        executar(cortador.comando_audio(vod, inicio, duracao, wav, cfg["caminho_ffmpeg"]))

        achado = detector.analisar(wav, limiar_db=cfg["limiar_confianca_db"])
        posicao = inicio + achado.instante
        medidas.append(
            Medida(
                gol=numero,
                esperado=esperado,
                achado=posicao,
                erro=abs(posicao - esperado),
                confianca_db=achado.confianca_db,
                tem_pico=achado.tem_pico,
            )
        )
    return medidas


def resumir(medidas: list[Medida], tolerancia: float = TOLERANCIA_S) -> dict:
    total = len(medidas)
    dentro = sum(1 for m in medidas if m.erro <= tolerancia)
    fracao = dentro / total if total else 0.0
    erros = [m.erro for m in medidas]
    return {
        "total": total,
        "dentro": dentro,
        "fracao": fracao,
        "aprovado": total > 0 and fracao >= FRACAO_MINIMA,
        "erro_medio": sum(erros) / total if total else 0.0,
    }


def principal(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Mede o erro do detector sobre um VOD.")
    p.add_argument("vod", type=Path, help="arquivo de video ja baixado")
    p.add_argument(
        "--gols", type=float, nargs="+", required=True,
        help="posicao real de cada gol, em segundos do arquivo",
    )
    p.add_argument("--temp", type=Path, default=Path("temp-teste"))
    args = p.parse_args(argv)

    cfg = config.carregar()
    medidas = medir(args.vod, args.gols, cfg, args.temp)

    print(f"{'gol':>4} {'esperado':>10} {'achado':>10} {'erro':>7} {'conf dB':>8}  pico")
    for m in medidas:
        marca = "sim" if m.tem_pico else "NAO"
        print(
            f"{m.gol:>4} {m.esperado:>10.1f} {m.achado:>10.1f} "
            f"{m.erro:>7.1f} {m.confianca_db:>8.1f}  {marca}"
        )

    r = resumir(medidas)
    print(
        f"\n{r['dentro']}/{r['total']} dentro de {TOLERANCIA_S:.0f}s "
        f"({r['fracao']:.0%}), erro medio {r['erro_medio']:.1f}s"
    )
    print("APROVADO" if r["aprovado"] else "REPROVADO — nao siga para a gravacao ao vivo")
    return 0 if r["aprovado"] else 1


if __name__ == "__main__":
    sys.exit(principal())
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_teste_vod.py -v`
Esperado: 4 passed

- [ ] **Passo 5: rodar o piloto de verdade**

Baixe um VOD de live de torcida já encerrada, anote a posição em segundos de cada gol
assistindo, e rode:

```powershell
python -m nucleo.teste_vod "G:\REACAO DA TORCIDA\vod-teste.mp4" --gols 1234 2890 4412
```

Anote o resultado. **Se sair REPROVADO, pare o plano aqui** e reavalie o detector antes
de seguir — o resto das tarefas não conserta um detector que erra.

- [ ] **Passo 6: commitar**

```bash
git add nucleo/teste_vod.py testes/test_teste_vod.py
git commit -m "modo teste: mede o erro do detector contra gabarito de VOD"
```

---

### Tarefa 6: catalogo — o estado do jogo em disco

**Arquivos:**
- Criar: `nucleo/catalogo.py`
- Criar: `testes/test_catalogo.py`

**Interfaces:**
- Consome: nada.
- Produz:
  - `caminho(pasta_jogo: Path) -> Path` — `pasta_jogo / "catalogo.json"`
  - `novo(jogo: str) -> dict`
  - `carregar(pasta_jogo: Path) -> dict`
  - `salvar(pasta_jogo: Path, dados: dict) -> None`
  - `registrar_gol(dados: dict, numero: int, horario: str, descricao: str) -> dict`
  - `registrar_clipe(dados: dict, gol: int, canal: str, arquivo: str, instante: float, confianca_db: float, tem_pico: bool) -> dict`
  - `marcar_escolha(dados: dict, gol: int, canal: str, escolhido: bool) -> dict`
  - `escolhidos(dados: dict) -> list[dict]` — na ordem: por gol, depois por canal.

Formato de `catalogo.json`:
```json
{
  "jogo": "2026-09-01 atletico-mg x cruzeiro",
  "gols": [{"numero": 1, "horario": "2026-09-01T21:37:00", "descricao": "1x0"}],
  "clipes": [
    {"gol": 1, "canal": "canal-exemplo", "arquivo": "clipes/gol-01/canal-exemplo.mp4",
     "instante": 4412.5, "confianca_db": 14.2, "tem_pico": true, "escolhido": null}
  ]
}
```

`escolhido: null` significa "ainda não olhei". `true`/`false` são decisões do operador.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_catalogo.py`:
```python
from pathlib import Path

from nucleo import catalogo


def test_ida_e_volta_no_disco_preserva_escolhas(tmp_path: Path):
    dados = catalogo.novo("2026-09-01 atletico-mg x cruzeiro")
    dados = catalogo.registrar_gol(dados, 1, "2026-09-01T21:37:00", "1x0")
    dados = catalogo.registrar_clipe(
        dados, 1, "canal-a", "clipes/gol-01/canal-a.mp4", 4412.5, 14.2, True
    )
    dados = catalogo.marcar_escolha(dados, 1, "canal-a", True)

    catalogo.salvar(tmp_path, dados)
    relido = catalogo.carregar(tmp_path)

    assert relido["clipes"][0]["escolhido"] is True
    assert relido["gols"][0]["descricao"] == "1x0"


def test_clipe_novo_comeca_sem_decisao(tmp_path: Path):
    dados = catalogo.registrar_clipe(
        catalogo.novo("j"), 1, "canal-a", "x.mp4", 10.0, 3.0, False
    )
    assert dados["clipes"][0]["escolhido"] is None
    assert dados["clipes"][0]["tem_pico"] is False


def test_registrar_o_mesmo_clipe_duas_vezes_atualiza_em_vez_de_duplicar():
    dados = catalogo.novo("j")
    dados = catalogo.registrar_clipe(dados, 1, "canal-a", "x.mp4", 10.0, 3.0, False)
    dados = catalogo.registrar_clipe(dados, 1, "canal-a", "x.mp4", 12.0, 9.0, True)
    assert len(dados["clipes"]) == 1
    assert dados["clipes"][0]["instante"] == 12.0


def test_escolhidos_saem_na_ordem_dos_gols():
    dados = catalogo.novo("j")
    dados = catalogo.registrar_clipe(dados, 2, "canal-b", "b.mp4", 1.0, 9.0, True)
    dados = catalogo.registrar_clipe(dados, 1, "canal-a", "a.mp4", 1.0, 9.0, True)
    dados = catalogo.registrar_clipe(dados, 1, "canal-z", "z.mp4", 1.0, 9.0, True)
    for gol, canal in [(2, "canal-b"), (1, "canal-a"), (1, "canal-z")]:
        dados = catalogo.marcar_escolha(dados, gol, canal, True)

    ordem = [(c["gol"], c["canal"]) for c in catalogo.escolhidos(dados)]
    assert ordem == [(1, "canal-a"), (1, "canal-z"), (2, "canal-b")]


def test_carregar_pasta_sem_catalogo_devolve_estrutura_vazia(tmp_path: Path):
    dados = catalogo.carregar(tmp_path)
    assert dados["gols"] == []
    assert dados["clipes"] == []
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_catalogo.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.catalogo'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/catalogo.py`:
```python
"""Estado do jogo em disco. Nada vive so na memoria da pagina aberta."""
import json
from pathlib import Path

NOME = "catalogo.json"


def caminho(pasta_jogo: Path) -> Path:
    return Path(pasta_jogo) / NOME


def novo(jogo: str) -> dict:
    return {"jogo": jogo, "gols": [], "clipes": []}


def carregar(pasta_jogo: Path) -> dict:
    arquivo = caminho(pasta_jogo)
    if not arquivo.is_file():
        return novo(Path(pasta_jogo).name)
    return json.loads(arquivo.read_text(encoding="utf-8"))


def salvar(pasta_jogo: Path, dados: dict) -> None:
    Path(pasta_jogo).mkdir(parents=True, exist_ok=True)
    caminho(pasta_jogo).write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def registrar_gol(dados: dict, numero: int, horario: str, descricao: str) -> dict:
    dados["gols"] = [g for g in dados["gols"] if g["numero"] != numero]
    dados["gols"].append({"numero": numero, "horario": horario, "descricao": descricao})
    dados["gols"].sort(key=lambda g: g["numero"])
    return dados


def _achar_clipe(dados: dict, gol: int, canal: str) -> dict | None:
    for clipe in dados["clipes"]:
        if clipe["gol"] == gol and clipe["canal"] == canal:
            return clipe
    return None


def registrar_clipe(
    dados: dict, gol: int, canal: str, arquivo: str,
    instante: float, confianca_db: float, tem_pico: bool,
) -> dict:
    existente = _achar_clipe(dados, gol, canal)
    campos = {
        "gol": gol, "canal": canal, "arquivo": arquivo,
        "instante": instante, "confianca_db": confianca_db, "tem_pico": tem_pico,
    }
    if existente is not None:
        existente.update(campos)
    else:
        dados["clipes"].append({**campos, "escolhido": None})
    return dados


def marcar_escolha(dados: dict, gol: int, canal: str, escolhido: bool) -> dict:
    clipe = _achar_clipe(dados, gol, canal)
    if clipe is None:
        raise KeyError(f"clipe do gol {gol} no canal {canal} nao existe")
    clipe["escolhido"] = escolhido
    return dados


def escolhidos(dados: dict) -> list[dict]:
    marcados = [c for c in dados["clipes"] if c.get("escolhido") is True]
    return sorted(marcados, key=lambda c: (c["gol"], c["canal"]))
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_catalogo.py -v`
Esperado: 5 passed

- [ ] **Passo 5: commitar**

```bash
git add nucleo/catalogo.py testes/test_catalogo.py
git commit -m "catalogo: estado do jogo em disco, com escolhas do operador"
```

---

### Tarefa 7: canais — cadastro e descoberta de live

**Arquivos:**
- Criar: `nucleo/canais.py`
- Criar: `testes/test_canais.py`

**Interfaces:**
- Consome: `config`.
- Produz:
  - `Canal(nome: str, url: str, ativo: bool)` — dataclass.
  - `carregar(caminho: Path) -> dict[str, list[Canal]]`
  - `url_live(url_canal: str) -> str` — acrescenta `/live`, sem duplicar barra.
  - `esta_ao_vivo(canal: Canal, ytdlp: str, rodar=_rodar) -> str | None` — devolve a URL do
    vídeo ao vivo, ou `None`. Canal sem live é resultado normal, **nunca exceção**.
  - `ao_vivo_do_time(time: str, cadastro: dict, ytdlp: str, rodar=_rodar) -> list[tuple[Canal, str]]`
  - `_rodar(comando: list[str]) -> tuple[int, str]` — invólucro substituível nos testes.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_canais.py`:
```python
import json
from pathlib import Path

from nucleo import canais


def test_url_live_nao_duplica_barra():
    assert canais.url_live("https://youtube.com/@x") == "https://youtube.com/@x/live"
    assert canais.url_live("https://youtube.com/@x/") == "https://youtube.com/@x/live"


def test_canal_ao_vivo_devolve_a_url_do_video():
    def rodar_falso(comando):
        return 0, "https://www.youtube.com/watch?v=abc123\n"

    canal = canais.Canal("Exemplo", "https://youtube.com/@x", True)
    assert canais.esta_ao_vivo(canal, "yt-dlp", rodar=rodar_falso) == \
        "https://www.youtube.com/watch?v=abc123"


def test_canal_sem_live_devolve_none_sem_estourar():
    def rodar_falso(comando):
        return 1, "ERROR: This live event will begin in 2 hours"

    canal = canais.Canal("Exemplo", "https://youtube.com/@x", True)
    assert canais.esta_ao_vivo(canal, "yt-dlp", rodar=rodar_falso) is None


def test_um_canal_fora_do_ar_nao_derruba_os_outros():
    chamadas = []

    def rodar_falso(comando):
        chamadas.append(comando)
        if "@ruim" in " ".join(comando):
            return 1, "ERROR: not live"
        return 0, "https://www.youtube.com/watch?v=ok\n"

    cadastro = {
        "cruzeiro": [
            canais.Canal("Ruim", "https://youtube.com/@ruim", True),
            canais.Canal("Bom", "https://youtube.com/@bom", True),
        ]
    }
    vivos = canais.ao_vivo_do_time("cruzeiro", cadastro, "yt-dlp", rodar=rodar_falso)

    assert len(chamadas) == 2, "tentou os dois"
    assert [c.nome for c, _ in vivos] == ["Bom"]


def test_canal_inativo_nao_e_consultado():
    chamadas = []

    def rodar_falso(comando):
        chamadas.append(comando)
        return 0, "https://x\n"

    cadastro = {"t": [canais.Canal("Desligado", "https://youtube.com/@d", False)]}
    assert canais.ao_vivo_do_time("t", cadastro, "yt-dlp", rodar=rodar_falso) == []
    assert chamadas == []


def test_carrega_o_cadastro_do_json(tmp_path: Path):
    arquivo = tmp_path / "canais.json"
    arquivo.write_text(
        json.dumps({"cruzeiro": [
            {"nome": "A", "url": "https://youtube.com/@a", "ativo": True}
        ]}),
        encoding="utf-8",
    )
    cadastro = canais.carregar(arquivo)
    assert cadastro["cruzeiro"][0] == canais.Canal("A", "https://youtube.com/@a", True)


def test_cadastro_ausente_ensina_como_criar(tmp_path: Path):
    try:
        canais.carregar(tmp_path / "canais.json")
    except FileNotFoundError as erro:
        assert "canais.exemplo.json" in str(erro), "o recado precisa dizer o que fazer"
    else:
        raise AssertionError("deveria ter reclamado")
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_canais.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.canais'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/canais.py`:
```python
"""Cadastro de canais por time e descoberta de quem esta ao vivo."""
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Canal:
    nome: str
    url: str
    ativo: bool = True


def carregar(caminho: Path) -> dict[str, list[Canal]]:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise FileNotFoundError(
            f"{caminho} nao existe. Copie o exemplo: "
            f"Copy-Item {caminho.with_name('canais.exemplo.json')} {caminho}"
        )
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    return {
        time: [Canal(c["nome"], c["url"], c.get("ativo", True)) for c in lista]
        for time, lista in bruto.items()
    }


def url_live(url_canal: str) -> str:
    return url_canal.rstrip("/") + "/live"


def _rodar(comando: list[str]) -> tuple[int, str]:
    p = subprocess.run(comando, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def esta_ao_vivo(
    canal: Canal, ytdlp: str, rodar: Callable[[list[str]], tuple[int, str]] = _rodar
) -> str | None:
    """URL do video ao vivo, ou None. Canal fora do ar e resultado normal."""
    codigo, saida = rodar([ytdlp, "--no-warnings", "--print", "webpage_url",
                           url_live(canal.url)])
    if codigo != 0:
        return None
    linha = saida.strip().splitlines()[0].strip() if saida.strip() else ""
    return linha or None


def ao_vivo_do_time(
    time: str,
    cadastro: dict[str, list[Canal]],
    ytdlp: str,
    rodar: Callable[[list[str]], tuple[int, str]] = _rodar,
) -> list[tuple[Canal, str]]:
    vivos = []
    for canal in cadastro.get(time, []):
        if not canal.ativo:
            continue
        url = esta_ao_vivo(canal, ytdlp, rodar=rodar)
        if url:
            vivos.append((canal, url))
    return vivos
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_canais.py -v`
Esperado: 7 passed

- [ ] **Passo 5: commitar**

```bash
git add nucleo/canais.py testes/test_canais.py
git commit -m "canais: cadastro por time e descoberta de live sem derrubar o lote"
```

---

### Tarefa 8: gravador — N gravações em paralelo

**Arquivos:**
- Criar: `nucleo/gravador.py`
- Criar: `testes/test_gravador.py`

**Interfaces:**
- Consome: `canais.Canal`, `config`.
- Produz:
  - `pasta_do_canal(biblioteca: Path, jogo: str, canal: Canal) -> Path`
  - `apelido(nome: str) -> str` — nome de pasta seguro: minúsculas, sem acento, espaços
    viram hífen.
  - `comando(url: str, pasta: Path, sessao: int, cfg: dict) -> str` — devolve **uma string**
    de shell, porque é um cano de dois processos.
  - `espaco_livre_gb(caminho: Path) -> float`
  - `verificar_espaco(caminho: Path, minimo_gb: float) -> None` — levanta `RuntimeError`.
  - `avaliar_banda(quantidade: int, teto: int) -> str | None` — aviso ou `None`.
  - `escrever_gravacao(pasta: Path, url: str, sessao: int, t0: datetime) -> Path` — grava
    `gravacao.json`.
  - `iniciar(vivos, biblioteca, jogo, cfg, abrir=_abrir) -> list[Processo]`
  - `Processo(canal: Canal, url: str, pasta: Path, sessao: int, processo: object, tentativas: int = 0)` —
    **mutável**, o supervisor atualiza `sessao`, `processo` e `tentativas`.
  - `supervisionar(processos, cfg, abrir=_abrir, dormir=time.sleep, agora=datetime.now, voltas=None) -> None`
  - `MAX_TENTATIVAS = 5`

**Isto é o que cumpre a promessa "gravação cai → religa em nova sessão" da spec.** Sem o
supervisor, uma queda de conexão aos 20 minutos significa perder o resto do jogo naquele
canal, calada. O `voltas` existe só para o teste poder rodar um número finito de conferências.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_gravador.py`:
```python
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


class ProcessoFalso:
    """Devolve None enquanto vivo; um codigo de saida depois de `vive_por` conferencias."""

    def __init__(self, vive_por: int = 999):
        self.vive_por = vive_por
        self.conferencias = 0

    def poll(self):
        self.conferencias += 1
        return None if self.conferencias <= self.vive_por else 1


def test_processo_vivo_nao_e_reiniciado(tmp_path: Path):
    abertos = []
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso()
    )

    gravador.supervisionar(
        [pr], {**CFG, "segundos_entre_conferencias": 0},
        abrir=lambda c, p: abertos.append(c), dormir=lambda s: None, voltas=3,
    )

    assert abertos == []
    assert pr.sessao == 1


def test_gravacao_que_cai_volta_em_nova_sessao(tmp_path: Path):
    import json

    gravador.escrever_gravacao(tmp_path, "https://x", 1, datetime(2026, 9, 1, 21, 0, 0))
    abertos = []
    pr = gravador.Processo(
        canais.Canal("A", "u", True), "https://x", tmp_path, 1, ProcessoFalso(vive_por=1)
    )

    gravador.supervisionar(
        [pr], {**CFG, "segundos_entre_conferencias": 0},
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
        lista, {**CFG, "segundos_entre_conferencias": 0},
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
        lista, {**CFG, "segundos_entre_conferencias": 0},
        abrir=lambda c, p: ProcessoFalso(vive_por=0),
        dormir=lambda s: None, voltas=20,
    )

    assert [p.canal.nome for p in lista] == ["Bom"]


def test_iniciar_abre_um_processo_por_canal_vivo(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(gravador, "espaco_livre_gb", lambda caminho: 300.0)
    abertos = []

    def abrir_falso(comando, pasta):
        abertos.append(comando)
        return object()

    vivos = [
        (canais.Canal("A", "https://youtube.com/@a", True), "https://x/watch?v=1"),
        (canais.Canal("B", "https://youtube.com/@b", True), "https://x/watch?v=2"),
    ]
    processos = gravador.iniciar(vivos, tmp_path, "jogo-teste", CFG, abrir=abrir_falso)

    assert len(processos) == 2
    assert len(abertos) == 2
    assert (tmp_path / "jogo-teste" / "bruto" / "a" / "gravacao.json").is_file()
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_gravador.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.gravador'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/gravador.py`:
```python
"""Sobe e acompanha as gravacoes ao vivo, uma por canal.

O comando e um cano: yt-dlp entrega o stream, ffmpeg fatia em pedacos de
MPEG-TS sem recodificar. TS sobrevive a processo morto; mp4 nao.
"""
import json
import re
import shutil
import subprocess
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from nucleo import canais as mod_canais


MAX_TENTATIVAS = 5


@dataclass
class Processo:
    canal: mod_canais.Canal
    url: str
    pasta: Path
    sessao: int
    processo: object
    tentativas: int = 0


def apelido(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-")
    return limpo.lower()


def pasta_do_canal(biblioteca: Path, jogo: str, canal: mod_canais.Canal) -> Path:
    return Path(biblioteca) / jogo / "bruto" / apelido(canal.nome)


def comando(url: str, pasta: Path, sessao: int, cfg: dict) -> str:
    formato = (
        f'bv*[height<={cfg["altura_maxima"]}]+ba/'
        f'b[height<={cfg["altura_maxima"]}]'
    )
    # Nomes relativos de proposito: _abrir roda com cwd=pasta. Se fossem absolutos,
    # o ffmpeg escreveria o caminho absoluto dentro do CSV de segmentos e o relogio
    # passaria a carregar caminho em vez de nome de arquivo.
    saida = f"s{sessao:02d}-parte-%03d.ts"
    lista = f"s{sessao:02d}-segmentos.csv"
    return (
        f'"{cfg["caminho_ytdlp"]}" -f "{formato}" --no-part -o - "{url}"'
        f' | "{cfg["caminho_ffmpeg"]}" -y -i pipe: -c copy'
        f' -f segment -segment_time {cfg["duracao_pedaco"]}'
        f" -segment_format mpegts -reset_timestamps 1"
        f' -segment_list "{lista}" -segment_list_type csv'
        f' "{saida}"'
    )


def espaco_livre_gb(caminho: Path) -> float:
    return shutil.disk_usage(Path(caminho)).free / (1024**3)


def verificar_espaco(caminho: Path, minimo_gb: float) -> None:
    livre = espaco_livre_gb(caminho)
    if livre < minimo_gb:
        raise RuntimeError(
            f"disco com {livre:.0f} GB livres, minimo exigido {minimo_gb:.0f} GB. "
            "Libere espaco antes de comecar — nao no meio do jogo."
        )


def avaliar_banda(quantidade: int, teto: int) -> str | None:
    if quantidade <= teto:
        return None
    return (
        f"{quantidade} canais passa do teto de {teto} da placa de 100 Mbps. "
        "Gravacao pode cair no meio do jogo."
    )


def escrever_gravacao(pasta: Path, url: str, sessao: int, t0: datetime) -> Path:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "gravacao.json"
    if arquivo.is_file():
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    else:
        dados = {"url": url, "sessoes": []}
    dados["sessoes"].append({"numero": sessao, "t0": t0.isoformat()})
    arquivo.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return arquivo


def _abrir(comando_shell: str, pasta: Path):
    return subprocess.Popen(comando_shell, shell=True, cwd=str(pasta))


def iniciar(
    vivos: list[tuple[mod_canais.Canal, str]],
    biblioteca: Path,
    jogo: str,
    cfg: dict,
    abrir: Callable[[str, Path], object] = _abrir,
) -> list[Processo]:
    Path(biblioteca).mkdir(parents=True, exist_ok=True)
    verificar_espaco(biblioteca, cfg["disco_minimo_gb"])

    aviso = avaliar_banda(len(vivos), cfg["teto_canais"])
    if aviso:
        print(f"AVISO: {aviso}")

    processos = []
    for canal, url in vivos:
        pasta = pasta_do_canal(biblioteca, jogo, canal)
        pasta.mkdir(parents=True, exist_ok=True)
        sessao = 1
        escrever_gravacao(pasta, url, sessao, datetime.now())
        processos.append(
            Processo(
                canal, url, pasta, sessao,
                abrir(comando(url, pasta, sessao, cfg), pasta),
            )
        )
    return processos


def supervisionar(
    processos: list[Processo],
    cfg: dict,
    abrir: Callable[[str, Path], object] = _abrir,
    dormir: Callable[[float], None] = time.sleep,
    agora: Callable[[], datetime] = datetime.now,
    voltas: int | None = None,
) -> None:
    """Fica de olho nas gravacoes: quem cair volta em nova sessao.

    Sem isto, uma queda de conexao aos 20 minutos perde o resto do jogo naquele
    canal, calada. Quem cai varias vezes seguidas teve a live encerrada de
    verdade — ai desiste, em vez de religar para sempre.
    """
    feitas = 0
    while processos and (voltas is None or feitas < voltas):
        dormir(cfg["segundos_entre_conferencias"])
        feitas += 1
        for pr in list(processos):
            if pr.processo.poll() is None:
                continue

            pr.tentativas += 1
            if pr.tentativas > MAX_TENTATIVAS:
                print(f"{pr.canal.nome}: caiu {MAX_TENTATIVAS}x seguidas — desistindo")
                processos.remove(pr)
                continue

            pr.sessao += 1
            escrever_gravacao(pr.pasta, pr.url, pr.sessao, agora())
            pr.processo = abrir(comando(pr.url, pr.pasta, pr.sessao, cfg), pr.pasta)
            print(f"{pr.canal.nome}: caiu, religando na sessao {pr.sessao}")
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_gravador.py -v`
Esperado: 12 passed

- [ ] **Passo 5: commitar**

```bash
git add nucleo/gravador.py testes/test_gravador.py
git commit -m "gravador: gravacao em mpegts fatiado, com religamento e travas de banda"
```

---

### Tarefa 9: montador — a compilação

**Arquivos:**
- Criar: `nucleo/montador.py`
- Criar: `testes/test_montador.py`

**Interfaces:**
- Consome: `catalogo.escolhidos`.
- Produz:
  - `comando_cartela(clipe: Path, nome_canal: str, saida: Path, ffmpeg: str, fonte: str) -> list[str]` —
    normaliza para 1280x720 a 30 fps e escreve o nome do canal nos 3 primeiros segundos.
    **`fonte` e obrigatorio**: no Windows o `drawtext` falha com "Cannot find a valid font"
    sem um `fontfile=` explicito, e o caminho precisa de escape proprio (`C\:/Windows/...`).
  - `caminho_de_fonte(fonte: str) -> str` — escapa o caminho para o filtro.
  - `comando_concat(lista: Path, saida: Path, ffmpeg: str) -> list[str]`
  - `escrever_lista(arquivos: list[Path], destino: Path) -> Path`
  - `montar(escolhidos: list[dict], pasta_jogo: Path, cfg: dict, executar=cortador.executar) -> Path`

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_montador.py`:
```python
from pathlib import Path

from nucleo import montador

FFMPEG = "ffmpeg"
FONTE = r"C:\Windows\Fonts\arialbd.ttf"


def test_cartela_normaliza_e_escreve_o_nome_do_canal():
    cmd = montador.comando_cartela(
        Path("a.mp4"), "Canal do Zé", Path("b.mp4"), FFMPEG, FONTE
    )
    texto = " ".join(cmd)
    assert "1280" in texto and "720" in texto, "canais entregam formatos diferentes"
    assert "fps=30" in texto
    assert "drawtext" in texto
    assert "Canal do" in texto


def test_cartela_leva_fontfile_escapado():
    """Sem fontfile o drawtext falha no Windows; com dois-pontos cru, o filtro quebra."""
    cmd = montador.comando_cartela(Path("a.mp4"), "X", Path("b.mp4"), FFMPEG, FONTE)
    texto = " ".join(cmd)
    assert "fontfile=" in texto
    assert "C\\:/Windows/Fonts/arialbd.ttf" in texto


def test_nome_com_aspas_nao_quebra_o_filtro():
    cmd = montador.comando_cartela(
        Path("a.mp4"), "Canal 'X': o melhor", Path("b.mp4"), FFMPEG, FONTE
    )
    texto = " ".join(cmd)
    assert "\\:" in texto or "\\'" in texto, "dois-pontos e aspas precisam de escape"


def test_montar_gera_um_intermediario_por_clipe_e_um_concat(tmp_path: Path):
    chamadas = []
    escolhidos = [
        {"gol": 1, "canal": "canal-a", "arquivo": "clipes/gol-01/canal-a.mp4"},
        {"gol": 1, "canal": "canal-b", "arquivo": "clipes/gol-01/canal-b.mp4"},
    ]
    cfg = {"caminho_ffmpeg": FFMPEG, "fonte_cartela": FONTE}

    saida = montador.montar(escolhidos, tmp_path, cfg, executar=chamadas.append)

    assert len(chamadas) == 3, "duas cartelas e uma juncao"
    assert "concat" in " ".join(chamadas[-1])
    assert saida == tmp_path / "saida" / "compilacao.mp4"


def test_montar_sem_escolhidos_avisa_em_vez_de_gerar_vazio(tmp_path: Path):
    try:
        montador.montar(
            [], tmp_path,
            {"caminho_ffmpeg": FFMPEG, "fonte_cartela": FONTE},
            executar=lambda c: None,
        )
    except ValueError as erro:
        assert "nenhum" in str(erro).lower()
    else:
        raise AssertionError("deveria ter recusado montar do nada")
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_montador.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.montador'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/montador.py`:
```python
"""Junta os clipes escolhidos numa compilacao, com o nome do canal na tela."""
from pathlib import Path
from typing import Callable

from nucleo import cortador

LARGURA, ALTURA, FPS = 1280, 720, 30
SEGUNDOS_DE_CARTELA = 3


def _escapar(texto: str) -> str:
    """drawtext trata : ' \\ e % como sintaxe."""
    for de, para in [("\\", "\\\\"), (":", "\\:"), ("'", "\\'"), ("%", "\\%")]:
        texto = texto.replace(de, para)
    return texto


def caminho_de_fonte(fonte: str) -> str:
    """C:\Windows\Fonts\x.ttf -> C\:/Windows/Fonts/x.ttf (exigencia do drawtext)."""
    return str(fonte).replace("\\", "/").replace(":", "\:", 1)


def comando_cartela(
    clipe: Path, nome_canal: str, saida: Path, ffmpeg: str, fonte: str
) -> list[str]:
    filtro = (
        f"scale={LARGURA}:{ALTURA}:force_original_aspect_ratio=decrease,"
        f"pad={LARGURA}:{ALTURA}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},"
        f"drawtext=fontfile='{caminho_de_fonte(fonte)}':"
        f"text='{_escapar(nome_canal)}':x=40:y=h-90:fontsize=42:"
        f"fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=12:"
        f"enable='lt(t,{SEGUNDOS_DE_CARTELA})'"
    )
    return [
        ffmpeg, "-y", "-i", str(clipe),
        "-vf", filtro,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        str(saida),
    ]


def comando_concat(lista: Path, saida: Path, ffmpeg: str) -> list[str]:
    return [
        ffmpeg, "-y", "-f", "concat", "-safe", "0",
        "-i", str(lista), "-c", "copy", str(saida),
    ]


def escrever_lista(arquivos: list[Path], destino: Path) -> Path:
    destino.write_text(
        "\n".join(f"file '{a.as_posix()}'" for a in arquivos) + "\n", encoding="utf-8"
    )
    return destino


def montar(
    escolhidos: list[dict],
    pasta_jogo: Path,
    cfg: dict,
    executar: Callable[[list[str]], None] = cortador.executar,
) -> Path:
    if not escolhidos:
        raise ValueError("nenhum clipe escolhido — marque as reacoes no painel primeiro")

    pasta_jogo = Path(pasta_jogo)
    temp = pasta_jogo / "temp-montagem"
    temp.mkdir(parents=True, exist_ok=True)
    saida_pasta = pasta_jogo / "saida"
    saida_pasta.mkdir(parents=True, exist_ok=True)

    intermediarios = []
    for indice, clipe in enumerate(escolhidos, start=1):
        origem = pasta_jogo / clipe["arquivo"]
        destino = temp / f"{indice:03d}.mp4"
        executar(
            comando_cartela(
                origem, clipe["canal"], destino,
                cfg["caminho_ffmpeg"], cfg["fonte_cartela"],
            )
        )
        intermediarios.append(destino)

    lista = escrever_lista(intermediarios, temp / "lista.txt")
    saida = saida_pasta / "compilacao.mp4"
    executar(comando_concat(lista, saida, cfg["caminho_ffmpeg"]))
    return saida
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_montador.py -v`
Esperado: 5 passed

- [ ] **Passo 5: commitar**

```bash
git add nucleo/montador.py testes/test_montador.py
git commit -m "montador: normaliza, cartela e junta os clipes escolhidos"
```

---

### Tarefa 10: painel — curadoria no navegador

**Arquivos:**
- Criar: `painel/__init__.py`, `painel/servidor.py`, `painel/pagina.html`
- Criar: `testes/test_servidor.py`

**Interfaces:**
- Consome: `catalogo`, `montador`, `config`.
- Produz:
  - `montar_resposta(rota: str, corpo: dict, pasta_jogo: Path, cfg: dict) -> tuple[int, dict]` —
    a lógica das rotas, separada do `http.server` para poder ser testada sem abrir porta.
  - `servir(pasta_jogo: Path, cfg: dict, porta: int = 8770) -> None`

Rotas:

| Método | Rota | O que faz |
|---|---|---|
| GET | `/` | a página |
| GET | `/api/catalogo` | o `catalogo.json` inteiro |
| POST | `/api/escolha` | `{gol, canal, escolhido}` → grava na hora |
| POST | `/api/montar` | monta a compilação a partir dos escolhidos |
| GET | `/midia/<caminho>` | serve os clipes para o `<video>` |

**Regra da spec que precisa valer aqui:** toda marcação grava em disco no ato. Recarregar
a página não pode perder trabalho.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_servidor.py`:
```python
from pathlib import Path

from nucleo import catalogo
from painel import servidor

CFG = {"caminho_ffmpeg": "ffmpeg"}


def preparar(tmp_path: Path) -> Path:
    dados = catalogo.novo("jogo")
    dados = catalogo.registrar_clipe(dados, 1, "canal-a", "clipes/gol-01/a.mp4",
                                     10.0, 12.0, True)
    catalogo.salvar(tmp_path, dados)
    return tmp_path


def test_get_catalogo_devolve_os_clipes(tmp_path: Path):
    pasta = preparar(tmp_path)
    codigo, corpo = servidor.montar_resposta("GET /api/catalogo", {}, pasta, CFG)
    assert codigo == 200
    assert corpo["clipes"][0]["canal"] == "canal-a"


def test_escolha_grava_no_disco_na_hora(tmp_path: Path):
    pasta = preparar(tmp_path)

    codigo, _ = servidor.montar_resposta(
        "POST /api/escolha", {"gol": 1, "canal": "canal-a", "escolhido": True}, pasta, CFG
    )

    assert codigo == 200
    relido = catalogo.carregar(pasta)
    assert relido["clipes"][0]["escolhido"] is True


def test_escolha_de_clipe_inexistente_devolve_404(tmp_path: Path):
    pasta = preparar(tmp_path)
    codigo, corpo = servidor.montar_resposta(
        "POST /api/escolha", {"gol": 9, "canal": "fantasma", "escolhido": True}, pasta, CFG
    )
    assert codigo == 404
    assert "erro" in corpo


def test_montar_sem_escolhidos_devolve_400_com_recado(tmp_path: Path):
    pasta = preparar(tmp_path)
    codigo, corpo = servidor.montar_resposta("POST /api/montar", {}, pasta, CFG)
    assert codigo == 400
    assert "nenhum" in corpo["erro"].lower()


def test_rota_desconhecida_devolve_404(tmp_path: Path):
    codigo, _ = servidor.montar_resposta("GET /api/nada", {}, tmp_path, CFG)
    assert codigo == 404
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_servidor.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'painel'`

- [ ] **Passo 3: escrever a lógica das rotas**

`painel/__init__.py`: arquivo vazio.

`painel/servidor.py`:
```python
"""Painel de curadoria: servidor local e rotas.

A logica das rotas fica em montar_resposta, separada do http.server, para
poder ser testada sem abrir porta.
"""
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nucleo import catalogo, montador

PAGINA = Path(__file__).resolve().parent / "pagina.html"


def montar_resposta(rota: str, corpo: dict, pasta_jogo: Path, cfg: dict) -> tuple[int, dict]:
    if rota == "GET /api/catalogo":
        return 200, catalogo.carregar(pasta_jogo)

    if rota == "POST /api/escolha":
        dados = catalogo.carregar(pasta_jogo)
        try:
            dados = catalogo.marcar_escolha(
                dados, corpo["gol"], corpo["canal"], bool(corpo["escolhido"])
            )
        except KeyError as erro:
            return 404, {"erro": str(erro)}
        catalogo.salvar(pasta_jogo, dados)  # grava na hora, sempre
        return 200, {"ok": True}

    if rota == "POST /api/montar":
        dados = catalogo.carregar(pasta_jogo)
        try:
            saida = montador.montar(catalogo.escolhidos(dados), pasta_jogo, cfg)
        except ValueError as erro:
            return 400, {"erro": str(erro)}
        return 200, {"ok": True, "arquivo": str(saida)}

    return 404, {"erro": f"rota desconhecida: {rota}"}


class _Manipulador(SimpleHTTPRequestHandler):
    def __init__(self, *args, pasta_jogo: Path, cfg: dict, **kwargs):
        self.pasta_jogo = pasta_jogo
        self.cfg = cfg
        super().__init__(*args, directory=str(pasta_jogo), **kwargs)

    def _responder(self, codigo: int, corpo: dict) -> None:
        dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            pagina = PAGINA.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(pagina)))
            self.end_headers()
            self.wfile.write(pagina)
            return
        if self.path.startswith("/api/"):
            codigo, corpo = montar_resposta(f"GET {self.path}", {}, self.pasta_jogo, self.cfg)
            self._responder(codigo, corpo)
            return
        super().do_GET()  # serve os clipes para o <video>

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        codigo, resposta = montar_resposta(
            f"POST {self.path}", corpo, self.pasta_jogo, self.cfg
        )
        self._responder(codigo, resposta)


def servir(pasta_jogo: Path, cfg: dict, porta: int = 8770) -> None:
    manipulador = partial(_Manipulador, pasta_jogo=Path(pasta_jogo), cfg=cfg)
    with ThreadingHTTPServer(("127.0.0.1", porta), manipulador) as servidor_http:
        print(f"Painel em http://127.0.0.1:{porta}  (Ctrl+C para parar)")
        servidor_http.serve_forever()
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_servidor.py -v`
Esperado: 5 passed

- [ ] **Passo 5: escrever a página**

`painel/pagina.html` — um bloco por gol, os canais lado a lado, `<video>` por clipe,
✓/✗ que chama `POST /api/escolha` no ato, e botão MONTAR. Clipe com `tem_pico: false`
recebe borda vermelha e o aviso "conferir na mão".

```html
<!doctype html>
<meta charset="utf-8">
<title>Reação da Torcida</title>
<style>
  body { font-family: system-ui, sans-serif; background:#111; color:#eee; margin:24px; }
  h2 { border-bottom:1px solid #333; padding-bottom:6px; }
  .gol { margin-bottom:32px; }
  .canais { display:flex; flex-wrap:wrap; gap:16px; }
  .clipe { width:320px; border:2px solid #333; border-radius:8px; padding:8px; }
  .clipe.suspeito { border-color:#c0392b; }
  .clipe.escolhido { border-color:#27ae60; }
  video { width:100%; border-radius:4px; }
  .nome { font-weight:600; margin:6px 0; }
  .aviso { color:#e74c3c; font-size:13px; }
  button { cursor:pointer; padding:6px 12px; border:0; border-radius:4px; }
  .sim { background:#27ae60; color:#fff; } .nao { background:#555; color:#fff; }
  #montar { background:#f1c40f; font-weight:700; padding:12px 24px; font-size:16px; }
</style>
<h1>Reação da Torcida</h1>
<div id="gols"></div>
<button id="montar">MONTAR COMPILAÇÃO</button>
<p id="recado"></p>
<script>
async function carregar() {
  const dados = await (await fetch('/api/catalogo')).json();
  const alvo = document.getElementById('gols');
  alvo.innerHTML = '';
  for (const gol of dados.gols) {
    const bloco = document.createElement('div');
    bloco.className = 'gol';
    bloco.innerHTML = `<h2>Gol ${gol.numero} — ${gol.descricao || ''}</h2>`;
    const linha = document.createElement('div');
    linha.className = 'canais';
    for (const c of dados.clipes.filter(c => c.gol === gol.numero)) {
      const caixa = document.createElement('div');
      caixa.className = 'clipe' + (c.tem_pico ? '' : ' suspeito')
                                + (c.escolhido ? ' escolhido' : '');
      caixa.innerHTML = `
        <video controls preload="metadata" src="/${c.arquivo}"></video>
        <div class="nome">${c.canal}</div>
        ${c.tem_pico ? '' : '<div class="aviso">sem pico — conferir na mão</div>'}
        <button class="sim">✓ usar</button> <button class="nao">✗ descartar</button>`;
      caixa.querySelector('.sim').onclick = () => escolher(c.gol, c.canal, true);
      caixa.querySelector('.nao').onclick = () => escolher(c.gol, c.canal, false);
      linha.appendChild(caixa);
    }
    bloco.appendChild(linha);
    alvo.appendChild(bloco);
  }
}
async function escolher(gol, canal, escolhido) {
  await fetch('/api/escolha', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({gol, canal, escolhido})
  });
  carregar();
}
document.getElementById('montar').onclick = async () => {
  const r = await (await fetch('/api/montar', {method: 'POST'})).json();
  document.getElementById('recado').textContent = r.erro || ('Pronto: ' + r.arquivo);
};
carregar();
</script>
```

- [ ] **Passo 6: conferir na mão**

Rodar `python -c "from pathlib import Path; from nucleo import config; from painel import servidor; servidor.servir(Path(r'G:\REACAO DA TORCIDA\jogo-teste'), config.carregar())"`,
abrir `http://127.0.0.1:8770`, marcar um clipe, **recarregar a página** e confirmar que a
marcação continua lá.

- [ ] **Passo 7: commitar**

```bash
git add painel/ testes/test_servidor.py
git commit -m "painel: curadoria no navegador, com escolha gravada em disco na hora"
```

---

### Tarefa 11: a esteira — os quatro `.bat`

**Arquivos:**
- Criar: `0 - CANAIS.bat`, `1 - GRAVAR.bat`, `2 - CORTAR.bat`, `3 - ESTUDIO.bat`
- Criar: `nucleo/esteira.py`
- Criar: `testes/test_esteira.py`

**Interfaces:**
- Consome: todos os módulos anteriores.
- Produz:
  - `nome_do_jogo(mandante: str, visitante: str, data=None) -> str` — `"2026-09-01 mandante x visitante"`
  - `resolver_horario(texto: str, sessoes: list[relogio.Sessao]) -> datetime` — escolhe o
    dia certo para o `HH:MM:SS` informado.
  - `_completar_pedaco_final(sessao, pasta, cfg, prefixo) -> relogio.Sessao`
  - `_sessoes_do_canal(pasta: Path, cfg: dict) -> list[relogio.Sessao]`
  - `etapa_canais(argv) -> int`, `etapa_gravar(argv) -> int`, `etapa_cortar(argv) -> int`,
    `etapa_estudio(argv) -> int`

**Duas armadilhas que estas funções existem para desarmar:**

*A virada da meia-noite.* Jogo de Copa do Brasil começa 21:30 e termina depois da
meia-noite. Colar a hora do gol na data de hoje poria um gol de 00:15 doze horas **antes**
do início da gravação, e todo canal responderia "não coberto". `resolver_horario` escolhe
entre o dia do início e o seguinte, pelo que a gravação realmente cobre.

*O pedaço final que não entrou no CSV.* O ffmpeg só escreve a linha do CSV quando o pedaço
de 10 minutos fecha. Fechar a janela da gravação mata o processo no meio de um pedaço: o
`.ts` está no disco, mas o relógio não sabe dele. Sem `_completar_pedaco_final`, **um gol
nos últimos minutos — o material mais valioso — apareceria como "não coberto"**.

`etapa_cortar` é a que costura tudo: lê `gravacao.json` e os CSVs de cada canal, monta as
sessões com `relogio.ler_segmentos`, abre a janela por gol, extrai o áudio, chama o
`detector`, corta com o `cortador` e registra no `catalogo`. Quando um canal não cobre o
horário do gol, registra o motivo e segue para o próximo — **não derruba o lote**.

- [ ] **Passo 1: escrever o teste que falha**

`testes/test_esteira.py`:
```python
from datetime import datetime
from pathlib import Path

from nucleo import esteira, relogio


def test_nome_do_jogo_usa_data_e_apelidos():
    nome = esteira.nome_do_jogo("Atlético-MG", "Cruzeiro", datetime(2026, 9, 1))
    assert nome == "2026-09-01 atletico-mg x cruzeiro"


def test_nome_do_jogo_serve_como_pasta():
    nome = esteira.nome_do_jogo("São Paulo", "Grêmio", datetime(2026, 9, 1))
    assert ":" not in nome and "?" not in nome
    assert nome == "2026-09-01 sao-paulo x gremio"


def sessao_da_noite() -> relogio.Sessao:
    """Gravacao das 21:30 as 00:10 do dia seguinte."""
    return relogio.Sessao(
        t0=datetime(2026, 9, 1, 21, 30, 0),
        pedacos=[relogio.Pedaco(f"s01-parte-{i:03d}.ts", i * 600.0, (i + 1) * 600.0)
                 for i in range(16)],
    )


def test_horario_do_primeiro_tempo_fica_no_dia_do_jogo():
    momento = esteira.resolver_horario("21:47:00", [sessao_da_noite()])
    assert momento == datetime(2026, 9, 1, 21, 47, 0)


def test_gol_depois_da_meia_noite_cai_no_dia_seguinte():
    """Copa do Brasil comeca 21:30; gol aos 50 do segundo tempo passa da meia-noite."""
    momento = esteira.resolver_horario("00:05:00", [sessao_da_noite()])
    assert momento == datetime(2026, 9, 2, 0, 5, 0), "nao pode voltar 12h para 01/09"


def test_sem_gravacao_nenhuma_nao_estoura():
    momento = esteira.resolver_horario("21:47:00", [])
    assert momento.hour == 21 and momento.minute == 47


def test_pedaco_final_fora_do_csv_e_recuperado(tmp_path: Path):
    """Fechar a janela mata o ffmpeg no meio do pedaco: o .ts existe, o CSV nao o cita."""
    (tmp_path / "s01-parte-000.ts").write_bytes(b"x")
    (tmp_path / "s01-parte-001.ts").write_bytes(b"x")  # o que ficou de fora
    sessao = relogio.Sessao(
        t0=datetime(2026, 9, 1, 21, 0, 0),
        pedacos=[relogio.Pedaco("s01-parte-000.ts", 0.0, 600.0)],
    )
    cfg = {"caminho_ffprobe": "ffprobe"}
    monkey = esteira.cortador.duracao
    esteira.cortador.duracao = lambda arquivo, ffprobe: 137.0
    try:
        completada = esteira._completar_pedaco_final(sessao, tmp_path, cfg, "s01")
    finally:
        esteira.cortador.duracao = monkey

    assert [p.arquivo for p in completada.pedacos] == [
        "s01-parte-000.ts", "s01-parte-001.ts"
    ]
    assert completada.pedacos[1] == relogio.Pedaco("s01-parte-001.ts", 600.0, 737.0)


def test_pedaco_final_ilegivel_e_ignorado(tmp_path: Path):
    (tmp_path / "s01-parte-001.ts").write_bytes(b"")
    sessao = relogio.Sessao(datetime(2026, 9, 1, 21, 0, 0), [])
    monkey = esteira.cortador.duracao
    esteira.cortador.duracao = lambda arquivo, ffprobe: 0.0
    try:
        completada = esteira._completar_pedaco_final(
            sessao, tmp_path, {"caminho_ffprobe": "ffprobe"}, "s01"
        )
    finally:
        esteira.cortador.duracao = monkey

    assert completada.pedacos == []
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `python -m pytest testes/test_esteira.py -v`
Esperado: FALHA com `ModuleNotFoundError: No module named 'nucleo.esteira'`

- [ ] **Passo 3: escrever a implementação**

`nucleo/esteira.py`:
```python
"""As quatro etapas da esteira. Os .bat sao cascas de uma linha em volta daqui."""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from nucleo import canais as mod_canais
from nucleo import catalogo, config, cortador, detector, gravador, relogio


def nome_do_jogo(mandante: str, visitante: str, data: datetime | None = None) -> str:
    data = data or datetime.now()
    return (
        f"{data:%Y-%m-%d} {gravador.apelido(mandante)} x {gravador.apelido(visitante)}"
    )


def _cadastro(cfg: dict):
    arquivo = Path(__file__).resolve().parent.parent / "dados" / "canais.json"
    return mod_canais.carregar(arquivo)


def etapa_canais(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("time")
    args = p.parse_args(argv)
    cfg = config.carregar()

    vivos = mod_canais.ao_vivo_do_time(args.time, _cadastro(cfg), cfg["caminho_ytdlp"])
    for canal, url in vivos:
        print(f"AO VIVO  {canal.nome}  {url}")
    print(f"\n{len(vivos)} canal(is) ao vivo.")
    aviso = gravador.avaliar_banda(len(vivos), cfg["teto_canais"])
    if aviso:
        print(f"AVISO: {aviso}")
    return 0


def etapa_gravar(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("time")
    p.add_argument("mandante")
    p.add_argument("visitante")
    args = p.parse_args(argv)
    cfg = config.carregar()

    jogo = nome_do_jogo(args.mandante, args.visitante)
    vivos = mod_canais.ao_vivo_do_time(args.time, _cadastro(cfg), cfg["caminho_ytdlp"])
    if not vivos:
        print("Nenhum canal ao vivo. Nada a gravar.")
        return 1

    processos = gravador.iniciar(vivos, Path(cfg["biblioteca"]), jogo, cfg)
    print(f"Gravando {len(processos)} canal(is) em {cfg['biblioteca']}\\{jogo}")
    print("Feche esta janela para parar.")
    gravador.supervisionar(processos, cfg)  # religa quem cair
    return 0


def _completar_pedaco_final(sessao: relogio.Sessao, pasta: Path, cfg: dict, prefixo: str):
    """Acrescenta o pedaco que ficou de fora do CSV.

    O ffmpeg so escreve a linha do CSV quando o pedaco fecha. Fechar a janela da
    gravacao mata o processo no meio de um pedaco de 10 minutos: o .ts esta no
    disco, mas o relogio nao sabe dele — e um gol nos ultimos minutos, que e
    justamente o material bom, apareceria como "nao coberto".
    """
    conhecidos = {p.arquivo for p in sessao.pedacos}
    orfaos = sorted(
        a.name for a in pasta.glob(f"{prefixo}-parte-*.ts") if a.name not in conhecidos
    )
    pedacos = list(sessao.pedacos)
    fim = pedacos[-1].fim if pedacos else 0.0
    for nome in orfaos:
        medida = cortador.duracao(pasta / nome, cfg["caminho_ffprobe"])
        if medida <= 0:
            continue
        pedacos.append(relogio.Pedaco(nome, fim, fim + medida))
        fim += medida
    return relogio.Sessao(t0=sessao.t0, pedacos=pedacos)


def _sessoes_do_canal(pasta: Path, cfg: dict) -> list[relogio.Sessao]:
    import json

    dados = json.loads((pasta / "gravacao.json").read_text(encoding="utf-8"))
    sessoes = []
    for s in dados["sessoes"]:
        prefixo = f"s{s['numero']:02d}"
        csv = pasta / f"{prefixo}-segmentos.csv"
        t0 = datetime.fromisoformat(s["t0"])
        sessao = (
            relogio.ler_segmentos(csv, t0)
            if csv.is_file()
            else relogio.Sessao(t0=t0, pedacos=[])
        )
        sessao = _completar_pedaco_final(sessao, pasta, cfg, prefixo)
        if sessao.pedacos:
            sessoes.append(sessao)
    return sessoes


def resolver_horario(texto: str, sessoes: list[relogio.Sessao]) -> datetime:
    """HH:MM:SS -> datetime, escolhendo o dia que cai dentro do que foi gravado.

    Jogo de Copa do Brasil comeca 21:30 e termina depois da meia-noite. Colar a
    hora do gol na data de hoje poria um gol de 00:15 doze horas antes do t0.
    """
    hora = datetime.strptime(texto, "%H:%M:%S").time()
    intervalos = relogio.cobertura(sessoes)
    if not intervalos:
        return datetime.combine(datetime.now().date(), hora)

    inicio = intervalos[0][0]
    for dia in (inicio.date(), inicio.date() + timedelta(days=1)):
        candidato = datetime.combine(dia, hora)
        if any(de <= candidato <= ate for de, ate in intervalos):
            return candidato
    return datetime.combine(inicio.date(), hora)


def etapa_cortar(argv=None) -> int:
    p = argparse.ArgumentParser(description="Gera os clipes a partir dos horarios dos gols.")
    p.add_argument("jogo", help="nome da pasta do jogo")
    p.add_argument("--gols", nargs="+", required=True,
                   help="horarios de relogio, ex: 21:37:00 22:05:30")
    args = p.parse_args(argv)
    cfg = config.carregar()

    pasta_jogo = Path(cfg["biblioteca"]) / args.jogo
    dados = catalogo.carregar(pasta_jogo)

    # Le as sessoes de todos os canais uma vez so: alem de evitar reler o disco
    # por gol, e o que permite resolver a data do horario informado.
    por_canal = {
        pasta.name: _sessoes_do_canal(pasta, cfg)
        for pasta in sorted((pasta_jogo / "bruto").iterdir())
        if (pasta / "gravacao.json").is_file()
    }
    if not por_canal:
        print(f"Nenhuma gravacao em {pasta_jogo / 'bruto'}")
        return 1
    qualquer = next(iter(por_canal.values()))

    for numero, texto in enumerate(args.gols, start=1):
        momento = resolver_horario(texto, qualquer)
        dados = catalogo.registrar_gol(dados, numero, momento.isoformat(), "")
        inicio, fim = relogio.janela(momento, cfg["janela_antes"], cfg["janela_depois"])
        destino = pasta_jogo / "clipes" / f"gol-{numero:02d}"
        destino.mkdir(parents=True, exist_ok=True)

        for nome, sessoes in por_canal.items():
            pasta_canal = pasta_jogo / "bruto" / nome
            recortes = relogio.trechos(sessoes, inicio, fim)
            if not recortes:
                gravado = ", ".join(
                    f"{de:%H:%M:%S}-{ate:%H:%M:%S}"
                    for de, ate in relogio.cobertura(sessoes)
                ) or "nada"
                print(
                    f"gol {numero}: {nome} nao cobre {momento:%H:%M:%S} "
                    f"— gravado: {gravado}"
                )
                continue

            temp = pasta_canal / f"janela-{numero:02d}.ts"
            fonte, deslocamento = cortador.preparar_fonte(
                recortes, pasta_canal, temp, cfg["caminho_ffmpeg"]
            )
            wav = pasta_canal / f"janela-{numero:02d}.wav"
            duracao = sum(t.fim - t.inicio for t in recortes)
            cortador.executar(
                cortador.comando_audio(fonte, deslocamento, duracao, wav,
                                       cfg["caminho_ffmpeg"])
            )
            achado = detector.analisar(wav, limiar_db=cfg["limiar_confianca_db"])

            comeco = max(0.0, deslocamento + achado.instante - cfg["segundos_antes"])
            tamanho = cfg["segundos_antes"] + cfg["segundos_depois"]
            saida = destino / f"{nome}.mp4"
            cortador.executar(
                cortador.comando_corte(fonte, comeco, tamanho, saida, cfg["caminho_ffmpeg"])
            )
            dados = catalogo.registrar_clipe(
                dados, numero, nome,
                str(saida.relative_to(pasta_jogo)).replace("\\", "/"),
                comeco, achado.confianca_db, achado.tem_pico,
            )
            marca = "" if achado.tem_pico else "  (SEM PICO — conferir)"
            print(f"gol {numero}: {nome} -> {saida.name}{marca}")
            wav.unlink(missing_ok=True)
            temp.unlink(missing_ok=True)  # a juncao temporaria, quando houve
            temp.with_suffix(".txt").unlink(missing_ok=True)

    catalogo.salvar(pasta_jogo, dados)
    return 0


def etapa_estudio(argv=None) -> int:
    from painel import servidor

    p = argparse.ArgumentParser()
    p.add_argument("jogo")
    p.add_argument("--porta", type=int, default=8770)
    args = p.parse_args(argv)
    cfg = config.carregar()
    servidor.servir(Path(cfg["biblioteca"]) / args.jogo, cfg, args.porta)
    return 0


if __name__ == "__main__":
    etapas = {
        "canais": etapa_canais, "gravar": etapa_gravar,
        "cortar": etapa_cortar, "estudio": etapa_estudio,
    }
    sys.exit(etapas[sys.argv[1]](sys.argv[2:]))
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `python -m pytest testes/test_esteira.py -v`
Esperado: 7 passed

- [ ] **Passo 5: escrever os quatro `.bat`**

`0 - CANAIS.bat`:
```bat
@echo off
cd /d "%~dp0"
set /p TIME_=Time (ex: cruzeiro):
python -m nucleo.esteira canais %TIME_%
pause
```

`1 - GRAVAR.bat`:
```bat
@echo off
cd /d "%~dp0"
set /p TIME_=Time da torcida a gravar:
set /p MANDANTE=Mandante:
set /p VISITANTE=Visitante:
python -m nucleo.esteira gravar %TIME_% "%MANDANTE%" "%VISITANTE%"
pause
```

`2 - CORTAR.bat`:
```bat
@echo off
cd /d "%~dp0"
set /p JOGO=Pasta do jogo:
set /p GOLS=Horarios dos gols separados por espaco (ex: 21:37:00 22:05:30):
python -m nucleo.esteira cortar "%JOGO%" --gols %GOLS%
pause
```

`3 - ESTUDIO.bat`:
```bat
@echo off
cd /d "%~dp0"
set /p JOGO=Pasta do jogo:
start "" http://127.0.0.1:8770
python -m nucleo.esteira estudio "%JOGO%"
```

- [ ] **Passo 6: rodar a bateria inteira**

Rodar: `python -m pytest -v`
Esperado: todos passando, ~62 testes.

- [ ] **Passo 7: commitar**

```bash
git add "0 - CANAIS.bat" "1 - GRAVAR.bat" "2 - CORTAR.bat" "3 - ESTUDIO.bat" nucleo/esteira.py testes/test_esteira.py
git commit -m "esteira: as quatro etapas e os .bat de entrada"
```

---

## Conferência final

Depois da tarefa 11, antes de dizer que está pronto:

- [ ] `python -m pytest -v` com tudo verde. Cole a saída.
- [ ] `python -m nucleo.teste_vod <vod> --gols ...` sobre o VOD de referência, e o resultado
      é APROVADO (≥80% dentro de 3 s). **Esse é o critério que importa.** Cole a saída.
- [ ] Um jogo de verdade gravado com **um canal**, cortado e curado no painel do começo ao
      fim.
- [ ] **Matar a gravação na marra** (fechar a janela) e conferir que um gol dos últimos
      minutos ainda é cortado — é o teste do pedaço órfão que não entrou no CSV.
- [ ] **Derrubar a internet por uns segundos** durante uma gravação e conferir que ela
      volta sozinha numa sessão 2, e que o `gravacao.json` registrou as duas.
- [ ] Se o jogo passou da meia-noite, conferir que um gol de `00:0x` foi localizado — e não
      reportado como "não coberto".
- [ ] Conferir que a mídia foi para o `G:` e não para o `C:`.
- [ ] Conferir que nenhum arquivo de vídeo entrou no repositório (`git status` limpo).
- [ ] Apagar a pasta `bruto/` do jogo depois de montar a compilação. São ~44 GB por jogo e
      a limpeza ainda é manual, de propósito.
