# Palco e identidade do canal — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dar ao vídeo final a cara do canal — arte de fundo, logo e faixa de redes num palco pré-desenhado, com a janela da reação menor e nítida por cima — sem mudar um pixel do vídeo de hoje enquanto o dono não preencher nada.

**Architecture:** a geometria continua num lugar só (`nucleo/molde.py`), agora em **arranjos nomeados** por formato, com dois ajustes numéricos (`escala`, `deslocamento`). A marca do canal mora num arquivo novo (`dados/identidade.json`, lido por `nucleo/identidade.py`), e campo vazio é camada que **não existe**. O cenário inteiro é composto pelo Pillow num PNG só (`estudio.palco()`), cacheado por assinatura, e entra no ffmpeg como **uma entrada de imagem**, trocando uma linha do `filter_complex`. O painel ganha o cartão MOLDAGEM antes do RENDER FINAL.

**Tech Stack:** Python 3.12, Pillow 12.2.0, pytest 8+, ffmpeg (`C:\yt-dlp\ffmpeg.exe`), HTML/CSS/JS sem framework.

**Spec:** `docs/superpowers/specs/2026-09-05-palco-e-identidade-do-canal-design.md` (aprovado em 05/09/2026). Leia junto: este plano argumenta a partir dele.

**Ponto de partida:** `python -m pytest` na raiz do `PROJETO` — **612 testes passando**. Nenhum pode ficar vermelho ao fim de nenhuma tarefa.

## Global Constraints

- **Só o formato deitado** (1920×1080). O `em-pe` (1080×1920) ganha um arranjo único chamado `quadro-cheio`, com a geometria de hoje, e não muda em mais nada.
- **`drawtext` continua proibido.** Toda letra é desenhada com PIL, num PNG, fora do ffmpeg.
- **O que pode ter letra é o cenário, não o conteúdo.** Os @s das redes e a chamada, que não mudam de jogo para jogo. Nada de placar, cartela de abertura, nome de canal ou qualquer texto específico do jogo.
- **Campo vazio é camada que não existe** — não é camada transparente, não é espaço reservado: o PIL não desenha.
- **`escala` de 0,60 a 1,00**, travada em 1,00. **`deslocamento` de −0,15 a +0,15** (fração de 1080, ou seja 162px para cada lado). Valor fora disso é recusado com mensagem que explica o esticão.
- **Identidade vazia + `quadro-cheio` ⇒ `filter_complex` idêntico ao de hoje, caractere por caractere.** É o teste que importa: enquanto ele passar, ninguém perde o vídeo que já funciona.
- **Uma entrada de imagem só para o palco.** Nem três camadas no ffmpeg, nem filtro que cresce.
- **Teste antes do código**, sem internet e sem arquivo de vídeo grande. Português no código, nos testes, nos commits e na interface.
- **Nada só na memória da página aberta**: toda escolha do operador grava em disco na hora.
- **Nunca sumir calado**: arte que não abre avisa e cai na cor do time; o render não para.
- **Regras de tela** (`DESIGN.md`, travadas em `testes/test_design.py`): sem `box-shadow`, sem gradiente decorativo, raios só 8px/12px/999px/50%, tudo que se aperta é pílula de 999px, **uma** pílula preta por tela (na `edicao.html` é o `button.render`), nenhuma cor crua fora do `:root`, tokens idênticos nas quatro telas — não crie token novo.
- Rodar tudo de `C:\Users\user\Desktop\REACAO DA TORCIDA\PROJETO` com `python -m pytest`.

## File Structure

| Arquivo | Responsabilidade |
| --- | --- |
| `nucleo/identidade.py` **(novo)** | Ler, gravar e conferir `dados/identidade.json`; resolver a moldagem do jogo (padrão do canal + desvio da receita); a trava da escala e do deslocamento. |
| `dados/identidade.exemplo.json` **(novo)** | O arquivo de partida, tudo vazio. Vai para o Git; o pessoal, não. |
| `dados/icones/LEIA-ME.md` **(novo)** | O contrato dos ícones das redes: nome = chave de `redes`, PNG branco com transparência. |
| `nucleo/molde.py` | A tabela de arranjos por formato, as camadas `logo` e `barra`, `escala`/`deslocamento`, e o `palco` como entrada do `para_ffmpeg`. Continua a única fonte da geometria. |
| `nucleo/estudio.py` | `palco()`: compõe o PNG do cenário com PIL e o cacheia por assinatura. Passa a moldagem resolvida ao molde e o palco ao ffmpeg. Ajuste de qualidade do render final. |
| `nucleo/receita.py` | O campo opcional `moldagem` do jogo: gravar, apagar e atravessar o refresh da tela. |
| `nucleo/cortador.py` | O `crf` do corte intermediário. |
| `painel/edicao.py` | As rotas da moldagem, da identidade, do CONFERIR PALCO e do ABRIR A PASTA. |
| `painel/edicao.html` | O cartão MOLDAGEM, com prévia, arranjos, os dois números, os @s e o botão de conferir. |
| `testes/test_identidade.py` **(novo)** | A identidade e a moldagem resolvida. |
| `testes/test_molde.py` | Não-regressão do filtro, arranjos, janela nativa, ajuste fino. |
| `testes/test_estudio.py` | Palco, cache, camadas que existem e as que não existem. |
| `testes/test_painel_edicao.py` | As rotas novas e o que a tela recebe. |
| `testes/test_cortador.py` | O `crf` do corte. |

---

### Task 1: A identidade do canal, a moldagem resolvida e a trava da escala

Passo 1 da seção 10 da spec. Nada muda no vídeo. O teste de não-regressão passa a existir **antes** de qualquer mudança de geometria — é a armadilha montada antes da obra.

**Files:**
- Create: `nucleo/identidade.py`
- Create: `dados/identidade.exemplo.json`
- Modify: `.gitignore` (acrescentar `dados/identidade.json`)
- Modify: `nucleo/receita.py` (`CAMPOS_DA_MOLDAGEM`, `definir_moldagem`, e `casar` preservando o desvio)
- Test: `testes/test_identidade.py` (novo)
- Test: `testes/test_molde.py` (o teste de não-regressão)
- Test: `testes/test_receita.py` (o desvio atravessa o refresh)

**Interfaces:**
- Consumes: nada de tarefa anterior.
- Produces:
  - `identidade.PADROES: dict` — a identidade vazia.
  - `identidade.REDES = ("youtube", "instagram", "tiktok")`, `identidade.CAMPOS_DA_MOLDAGEM = ("arranjo", "escala", "deslocamento")`
  - `identidade.ESCALA_MINIMA = 0.60`, `identidade.ESCALA_MAXIMA = 1.00`, `identidade.DESLOCAMENTO_MAXIMO = 0.15`
  - `identidade.carregar(caminho: Path | None = None) -> dict`
  - `identidade.salvar(valores: dict, caminho: Path | None = None) -> Path`
  - `identidade.mexer(valores: dict, **campos) -> dict`
  - `identidade.conferir(valores: dict) -> None` (levanta `ValueError`)
  - `identidade.moldagem(valores: dict, dados_receita: dict | None = None) -> dict` com as chaves `arranjo`, `escala`, `deslocamento`
  - `identidade.desviou(dados_receita: dict | None) -> bool`
  - `receita.definir_moldagem(dados_receita: dict, valores: dict | None) -> dict`

- [x] **Step 1: Escrever o teste de não-regressão do filtro**

Acrescente ao fim de `testes/test_molde.py`. O literal é a saída de hoje, capturada da própria função em 05/09 — **não** reescreva com f-string: uma f-string monta o esperado com as mesmas contas do código testado, e aí o teste concorda com qualquer erro.

```python
FILTRO_DE_HOJE_DEITADO = (
    "color=c=#101418:s=1920x1080:r=30,vignette=PI/4[fundo];"
    "[0:v]setpts=PTS-STARTPTS,scale=1728:972:force_original_aspect_ratio=increase,"
    "crop=1728:972,setsar=1[recortado];"
    "[1:v]scale=1728:972[cantos];"
    "[recortado][cantos]alphamerge[quadro];"
    "[fundo][quadro]overlay=96:54:shortest=1[com-quadro];"
    "[com-quadro][2:v]overlay=96:54[com-moldura];"
    "[com-moldura]setsar=1[v]"
)


def test_o_quadro_cheio_sai_caractere_por_caractere_igual_ao_de_hoje():
    """A nao-regressao da seccao 7 da spec do palco.

    O palco e a identidade do canal entram por cima de um sistema que ja monta
    video de verdade. O teto do risco e este teste: identidade vazia com
    `quadro-cheio` produz o MESMO filter_complex de antes, caractere por
    caractere. Se ele reprovar, o video mudou sem ninguem ter pedido.
    """
    filtro = molde.para_ffmpeg(
        molde.camadas("deitado"), "deitado", mascara="1:v", moldura="2:v"
    )

    assert filtro == FILTRO_DE_HOJE_DEITADO
```

- [x] **Step 2: Rodar e ver PASSAR (é armadilha, não teste vermelho)**

Run: `python -m pytest testes/test_molde.py -k caractere -v`
Expected: PASS. Aqui a ordem se inverte de propósito: o teste descreve o comportamento **que já existe** e precisa continuar existindo. Verde agora é a prova de que o literal está certo; se reprovar, o literal foi copiado errado — conserte o literal, não o código.

- [x] **Step 3: Escrever os testes da identidade**

Crie `testes/test_identidade.py`:

```python
"""A identidade do canal: um arquivo por instalacao, e campo vazio nao desenha.

O dono ainda nao tem logo, arte nem contas nas redes. O desenho e feito para que
isso nao bloqueie nada: constroi-se agora, preenche-se depois, um campo de cada
vez. O que estes testes cobram e essa promessa - com o arquivo recem-criado, o
video sai identico ao de hoje - e a trava da escala, que e o que impede os
arranjos de palco de perderem a nitidez que sao a razao de existirem.
"""
import json
from pathlib import Path

import pytest

from nucleo import identidade


def test_identidade_recem_criada_nao_desenha_nada(tmp_path: Path):
    """Arquivo que nao existe nao e erro: e a identidade vazia."""
    valores = identidade.carregar(tmp_path / "nao-existe.json")

    assert valores["arranjo"] == "quadro-cheio"
    assert valores["escala"] == 1.0
    assert valores["deslocamento"] == 0.0
    assert valores["arte_de_fundo"] == "" and valores["logo"] == ""
    assert set(valores["redes"]) == set(identidade.REDES)
    assert all(arroba == "" for arroba in valores["redes"].values())


def test_o_arquivo_grava_e_volta_igual(tmp_path: Path):
    arquivo = tmp_path / "identidade.json"
    valores = identidade.mexer(
        identidade.carregar(arquivo), logo=r"C:\arte\logo.png", chamada="SE INSCREVE"
    )

    identidade.salvar(valores, arquivo)

    assert json.loads(arquivo.read_text(encoding="utf-8"))["chamada"] == "SE INSCREVE"
    assert identidade.carregar(arquivo)["logo"] == r"C:\arte\logo.png"


def test_mexer_numa_rede_nao_apaga_as_outras(tmp_path: Path):
    valores = identidade.mexer(
        identidade.carregar(tmp_path / "x.json"), redes={"youtube": "@veia"}
    )

    valores = identidade.mexer(valores, redes={"tiktok": "@veiatk"})

    assert valores["redes"]["youtube"] == "@veia"
    assert valores["redes"]["tiktok"] == "@veiatk"
    assert valores["redes"]["instagram"] == ""


def test_escala_acima_de_um_e_recusada_dizendo_por_que():
    """A trava da seccao 3: escala 1,00 e o 1:1 com a fonte de 720p."""
    with pytest.raises(ValueError) as erro:
        identidade.conferir({"escala": 1.05, "deslocamento": 0.0})

    recado = str(erro.value)
    assert "1280x720" in recado, "o recado tem que dizer QUAL e o limite"
    assert "0.6" in recado or "0,6" in recado


def test_escala_de_um_exato_e_aceita():
    identidade.conferir({"escala": 1.0, "deslocamento": 0.0})
    identidade.conferir({"escala": identidade.ESCALA_MINIMA, "deslocamento": 0.0})


def test_escala_pequena_demais_tambem_e_recusada():
    with pytest.raises(ValueError):
        identidade.conferir({"escala": 0.4, "deslocamento": 0.0})


def test_deslocamento_fora_do_limite_e_recusado():
    with pytest.raises(ValueError) as erro:
        identidade.conferir({"escala": 1.0, "deslocamento": 0.3})

    assert "162" in str(erro.value)


def test_o_jogo_sem_moldagem_usa_o_padrao_do_canal(tmp_path: Path):
    """Ausente - que e o normal - o jogo usa o padrao do canal."""
    do_canal = identidade.mexer(
        identidade.carregar(tmp_path / "x.json"), arranjo="palco-alto", escala=0.9
    )

    resolvida = identidade.moldagem(do_canal, {"formato": "deitado"})

    assert resolvida == {"arranjo": "palco-alto", "escala": 0.9, "deslocamento": 0.0}


def test_o_desvio_do_jogo_sobrepoe_campo_a_campo(tmp_path: Path):
    do_canal = identidade.mexer(
        identidade.carregar(tmp_path / "x.json"), arranjo="palco-alto", escala=0.9
    )

    resolvida = identidade.moldagem(do_canal, {"moldagem": {"escala": 0.8}})

    assert resolvida == {"arranjo": "palco-alto", "escala": 0.8, "deslocamento": 0.0}


def test_o_desvio_fica_marcado():
    """Sair do padrao e permitido, mas nunca por acidente."""
    assert identidade.desviou({"moldagem": {"escala": 0.8}}) is True
    assert identidade.desviou({"formato": "deitado"}) is False
    assert identidade.desviou(None) is False


def test_desvio_com_numero_fora_da_trava_reclama_ao_resolver(tmp_path: Path):
    """Receita editada na mao nao pode furar a trava calada."""
    do_canal = identidade.carregar(tmp_path / "x.json")

    with pytest.raises(ValueError):
        identidade.moldagem(do_canal, {"moldagem": {"escala": 1.4}})
```

- [x] **Step 4: Rodar e ver falhar**

Run: `python -m pytest testes/test_identidade.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'nucleo.identidade'`

- [x] **Step 5: Escrever o `nucleo/identidade.py`**

```python
"""A identidade do canal: o que veste TODO video, e nao um jogo.

Um arquivo por instalacao. O palco e a camada de marca - fundo com a arte do
canal, logo num canto, faixa de redes no alto - e isso e estilo da casa, nao
escolha de jogo.

**Campo vazio e camada que NAO EXISTE.** Nao e camada transparente, nao e
espaco reservado: o PIL simplesmente nao desenha. Com o arquivo recem-criado, o
video sai identico ao de hoje, e e assim que isto entra em producao sem susto.

A moldagem - arranjo, escala e deslocamento - mora aqui porque e do canal. O
jogo pode desviar, num campo `moldagem` opcional da receita, e a tela marca
quando isso acontece: o padrao e um so, e sair dele e permitido, nunca por
acidente.
"""
import json
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "dados" / "identidade.json"

REDES = ("youtube", "instagram", "tiktok")
CAMPOS_DA_MOLDAGEM = ("arranjo", "escala", "deslocamento")

# Acima de 1,00 a janela fica maior que os 1280x720 da fonte e o ffmpeg volta a
# esticar o 720p - o esticao de 1,35x que o palco existe para acabar. Abaixo de
# 0,60 nao se ve mais a cara de ninguem, que e o conteudo do canal.
ESCALA_MINIMA = 0.60
ESCALA_MAXIMA = 1.00
# 0,15 de 1080 = 162px para cada lado. Mais do que isso empurra a janela para
# fora do palco em qualquer arranjo.
DESLOCAMENTO_MAXIMO = 0.15

PADROES = {
    "arranjo": "quadro-cheio",
    "escala": 1.0,
    "deslocamento": 0.0,
    "arte_de_fundo": "",
    "logo": "",
    "redes": {rede: "" for rede in REDES},
    "chamada": "INSCREVA-SE E DEIXE UM LIKE!",
}


def carregar(caminho: Path | None = None) -> dict:
    """Os padroes com o arquivo do usuario sobreposto por cima.

    O caminho e resolvido AQUI, e nao no valor padrao do parametro: valor padrao
    e amarrado na importacao, e ai trocar `ARQUIVO` no teste nao teria efeito -
    a bateria escreveria na identidade real da maquina.
    """
    valores = {**PADROES, "redes": dict(PADROES["redes"])}
    arquivo = Path(ARQUIVO if caminho is None else caminho)
    if not arquivo.is_file():
        return valores
    do_disco = json.loads(arquivo.read_text(encoding="utf-8"))
    valores.update({c: v for c, v in do_disco.items() if c != "redes"})
    valores["redes"] = {**valores["redes"], **(do_disco.get("redes") or {})}
    return valores


def salvar(valores: dict, caminho: Path | None = None) -> Path:
    conferir(valores)
    arquivo = Path(ARQUIVO if caminho is None else caminho)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(
        json.dumps(valores, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return arquivo


def mexer(valores: dict, **campos) -> dict:
    """Sobrepoe campo a campo e confere antes de devolver.

    `redes` se mescla em vez de trocar: gravar o @ do TikTok nao pode apagar o
    do YouTube que ja estava la.
    """
    novas = campos.pop("redes", None) or {}
    novos = {**valores, "redes": {**(valores.get("redes") or {}), **novas}}
    novos.update(campos)
    conferir(novos)
    return novos


def conferir(valores: dict) -> None:
    """A trava da seccao 3 do desenho, com o motivo dentro do recado.

    Recusar sem explicar ensina o operador a tentar numeros ate um passar. O
    recado diz o numero, o limite e por que o limite existe.
    """
    escala = float(valores.get("escala", 1.0))
    if escala > ESCALA_MAXIMA:
        raise ValueError(
            f"escala {escala:g} estica o clipe: a fonte e 720p e na escala 1,00 "
            f"a janela ja mede 1280x720 cravado. Acima disso o ffmpeg reamostra "
            f"e a imagem so borra - use de {ESCALA_MINIMA:g} a {ESCALA_MAXIMA:g}."
        )
    if escala < ESCALA_MINIMA:
        raise ValueError(
            f"escala {escala:g} deixa a janela pequena demais para se ver a cara "
            f"de alguem - use de {ESCALA_MINIMA:g} a {ESCALA_MAXIMA:g}."
        )
    deslocamento = float(valores.get("deslocamento", 0.0))
    if abs(deslocamento) > DESLOCAMENTO_MAXIMO:
        raise ValueError(
            f"deslocamento {deslocamento:g} joga a janela para fora do palco - o "
            f"limite e {DESLOCAMENTO_MAXIMO:g} para cada lado, que da 162px."
        )


def moldagem(valores: dict, dados_receita: dict | None = None) -> dict:
    """Arranjo, escala e deslocamento JA RESOLVIDOS para aquele jogo.

    O desvio da receita sobrepoe campo a campo; ausente - que e o normal - vale
    o padrao do canal. Quem chama isto nao precisa saber de onde veio cada
    numero, e e por isso que a assinatura do palco pode levar o resultado.
    """
    resolvida = {
        campo: valores.get(campo, PADROES[campo]) for campo in CAMPOS_DA_MOLDAGEM
    }
    resolvida.update({
        campo: valor
        for campo, valor in ((dados_receita or {}).get("moldagem") or {}).items()
        if campo in CAMPOS_DA_MOLDAGEM
    })
    resolvida["escala"] = float(resolvida["escala"])
    resolvida["deslocamento"] = float(resolvida["deslocamento"])
    conferir(resolvida)
    return resolvida


def desviou(dados_receita: dict | None) -> bool:
    """Se este jogo sai do padrao do canal. A tela marca quando sai."""
    return bool((dados_receita or {}).get("moldagem"))
```

- [x] **Step 6: Rodar e ver passar**

Run: `python -m pytest testes/test_identidade.py -v`
Expected: 11 PASSED

- [x] **Step 7: Escrever o teste do desvio que atravessa o refresh da tela**

Acrescente ao fim de `testes/test_receita.py`. O helper `_jogo(placar=(3, 1), gols=(1,))` já existe nesse arquivo (linha 29) e roda sem argumento nenhum; `pytest` já está importado lá.

```python
def test_o_desvio_do_jogo_atravessa_o_refresh_da_tela():
    """A tela regrava a receita cada vez que abre; o desvio nao pode sumir ali.

    `casar` re-deriva a receita do catalogo a cada abertura. Sem carregar o
    desvio para a nova, escolher "so neste jogo" duraria ate o proximo refresh -
    e sumiria calado, que e o pior jeito de perder trabalho.
    """
    dados = _jogo()
    velha = receita.definir_moldagem(
        receita.padrao(dados), {"arranjo": "palco-alto", "escala": 0.9}
    )

    nova = receita.casar(velha, dados)

    assert nova["moldagem"] == {"arranjo": "palco-alto", "escala": 0.9}


def test_voltar_ao_padrao_do_canal_apaga_o_desvio():
    dados = _jogo()
    com_desvio = receita.definir_moldagem(receita.padrao(dados), {"escala": 0.8})

    sem_desvio = receita.definir_moldagem(com_desvio, None)

    assert "moldagem" not in sem_desvio


def test_moldagem_com_campo_que_nao_existe_reclama_e_ensina():
    dados = _jogo()

    with pytest.raises(KeyError) as erro:
        receita.definir_moldagem(receita.padrao(dados), {"cor": "#fff"})

    assert "arranjo" in erro.value.args[0]
```

- [x] **Step 8: Rodar e ver falhar**

Run: `python -m pytest testes/test_receita.py -k moldagem -v`
Expected: FAIL com `AttributeError: module 'nucleo.receita' has no attribute 'definir_moldagem'`

- [x] **Step 9: Escrever o campo `moldagem` na receita**

Em `nucleo/receita.py`, depois de `TEXTOS_DO_OPERADOR`:

```python
# O desvio pontual da moldagem: o estilo e do canal, e este campo e a excecao
# marcada. Ausente e o normal.
CAMPOS_DA_MOLDAGEM = ("arranjo", "escala", "deslocamento")
```

Depois de `definir_textos`, acrescente:

```python
def definir_moldagem(dados_receita: dict, valores: dict | None) -> dict:
    """O desvio de moldagem deste jogo, ou `None` para voltar ao padrao do canal.

    A moldagem e do canal e vive no `identidade.json`. Isto aqui e o desvio
    pontual: presente, sobrescreve campo a campo, e a tela marca como "fora do
    padrao"; ausente, o jogo usa o padrao.
    """
    if not valores:
        dados_receita.pop("moldagem", None)
        return dados_receita
    desconhecidos = sorted(set(valores) - set(CAMPOS_DA_MOLDAGEM))
    if desconhecidos:
        raise KeyError(
            f"a moldagem nao tem os campos {', '.join(desconhecidos)} - "
            f"os que existem sao {', '.join(CAMPOS_DA_MOLDAGEM)}"
        )
    dados_receita["moldagem"] = {**(dados_receita.get("moldagem") or {}), **valores}
    return dados_receita
```

E em `casar`, logo depois da linha `nova["textos"] = {...}`:

```python
    # A tela regrava a receita cada vez que abre. Sem trazer o desvio para a
    # receita nova, "so neste jogo" duraria ate o proximo refresh e sumiria
    # calado - e o desvio e justamente o que a tela promete marcar.
    if velha.get("moldagem"):
        nova["moldagem"] = dict(velha["moldagem"])
```

- [x] **Step 10: Rodar e ver passar**

Run: `python -m pytest testes/test_receita.py -v`
Expected: todos PASSED

- [x] **Step 11: Criar o exemplo e ignorar o arquivo pessoal**

`dados/identidade.exemplo.json`:

```json
{
  "arranjo": "quadro-cheio",
  "escala": 1.0,
  "deslocamento": 0.0,
  "arte_de_fundo": "",
  "logo": "",
  "redes": {
    "youtube": "",
    "instagram": "",
    "tiktok": ""
  },
  "chamada": "INSCREVA-SE E DEIXE UM LIKE!"
}
```

Em `.gitignore`, depois da linha `dados/canais.json`:

```
dados/identidade.json
```

- [x] **Step 12: Rodar a bateria inteira**

Run: `python -m pytest`
Expected: 612 + 14 novos PASSED, nenhum falho.

- [x] **Step 13: Commit**

```bash
git add nucleo/identidade.py nucleo/receita.py dados/identidade.exemplo.json .gitignore testes/test_identidade.py testes/test_molde.py testes/test_receita.py
git commit -m "identidade: o arquivo do canal, a moldagem resolvida e a trava da escala"
```

---

### Task 2: Os três arranjos no molde

Passo 2 da seção 10. Nada muda no vídeo: `quadro-cheio` continua o padrão e ninguém consome os arranjos novos ainda.

**Files:**
- Modify: `nucleo/molde.py` (`_ARRANJOS`, `arranjos()`, `camadas()` com ajuste fino, `em_pixels()`, `caixa()`, `para_pagina()`, e a linha das caixas dentro de `para_ffmpeg()`)
- Test: `testes/test_molde.py`

**Interfaces:**
- Consumes: o nome `"quadro-cheio"`, que é o `identidade.PADROES["arranjo"]` da Task 1. O molde não importa a identidade — só usa o mesmo nome.
- Produces:
  - `molde.ARRANJO_PADRAO = "quadro-cheio"`
  - `molde.arranjos(formato: str) -> list[str]`
  - `molde.camadas(formato: str, arranjo: str = ARRANJO_PADRAO, escala: float = 1.0, deslocamento: float = 0.0) -> list[Camada]`
  - `molde.caixa(nome: str, formato: str, arranjo: str = ARRANJO_PADRAO, escala: float = 1.0, deslocamento: float = 0.0) -> dict`
  - `molde.em_pixels(camada: Camada, formato: str) -> dict`
  - `molde.para_pagina(camadas_: list[Camada], formato: str) -> dict` (agora sai das camadas RECEBIDAS)

- [x] **Step 1: Escrever os testes dos arranjos**

Acrescente a `testes/test_molde.py`:

```python
def test_os_tres_arranjos_do_deitado_existem():
    assert molde.arranjos("deitado") == ["quadro-cheio", "palco-alto", "palco-lateral"]


def test_o_em_pe_tem_um_arranjo_so_nesta_rodada():
    """A spec e explicita: nesta rodada, so o deitado ganha palco."""
    assert molde.arranjos("em-pe") == ["quadro-cheio"]


@pytest.mark.parametrize("arranjo", ["palco-alto", "palco-lateral"])
def test_a_janela_do_palco_e_1280x720_cravado(arranjo):
    """A seccao 6: os pixels da fonte caem 1:1, sem reamostrar.

    Se alguem mexer num numero e quebrar o 1:1, a bateria reprova - e nao o olho
    de quem for assistir o proximo compilado.
    """
    quadro = molde.caixa("quadro", "deitado", arranjo)

    assert (quadro["largura"], quadro["altura"]) == (1280, 720)


def test_o_palco_alto_deixa_a_faixa_de_cima_livre():
    """280px em cima, que e onde a logo e a barra moram."""
    quadro = molde.caixa("quadro", "deitado", "palco-alto")

    assert (quadro["esquerda"], quadro["topo"]) == (320, 280)


def test_o_palco_lateral_deixa_a_coluna_da_esquerda_livre():
    quadro = molde.caixa("quadro", "deitado", "palco-lateral")

    assert quadro["esquerda"] == 576
    assert 1920 - (quadro["esquerda"] + quadro["largura"]) == 64


def test_o_quadro_cheio_nao_tem_logo_nem_barra():
    """Sem sobra, nao ha camada: o de hoje continua sendo o de hoje."""
    nomes = [c.nome for c in molde.camadas("deitado", "quadro-cheio")]

    assert nomes == ["fundo", "quadro"]


@pytest.mark.parametrize("arranjo", ["palco-alto", "palco-lateral"])
def test_o_palco_tem_logo_e_barra(arranjo):
    nomes = [c.nome for c in molde.camadas("deitado", arranjo)]

    assert nomes == ["fundo", "logo", "barra", "quadro"]


@pytest.mark.parametrize("arranjo", ["palco-alto", "palco-lateral"])
def test_a_logo_e_a_barra_nao_encostam_na_janela(arranjo):
    """O palco e o cenario ATRAS e AO REDOR: nada se sobrepoe a cena."""
    quadro = molde.caixa("quadro", "deitado", arranjo)
    for nome in ("logo", "barra"):
        caixa = molde.caixa(nome, "deitado", arranjo)
        ao_lado = (
            caixa["esquerda"] + caixa["largura"] <= quadro["esquerda"]
            or caixa["esquerda"] >= quadro["esquerda"] + quadro["largura"]
        )
        acima_ou_abaixo = (
            caixa["topo"] + caixa["altura"] <= quadro["topo"]
            or caixa["topo"] >= quadro["topo"] + quadro["altura"]
        )
        assert ao_lado or acima_ou_abaixo, f"{arranjo}/{nome} invade a janela"


@pytest.mark.parametrize("arranjo", ["palco-alto", "palco-lateral"])
def test_a_logo_e_a_barra_cabem_no_palco(arranjo):
    for nome in ("logo", "barra"):
        caixa = molde.caixa(nome, "deitado", arranjo)
        assert caixa["esquerda"] >= 0 and caixa["topo"] >= 0, f"{arranjo}/{nome}"
        assert caixa["esquerda"] + caixa["largura"] <= 1920, f"{arranjo}/{nome}"
        assert caixa["topo"] + caixa["altura"] <= 1080, f"{arranjo}/{nome}"


def test_a_escala_encolhe_a_janela_em_torno_do_centro():
    """Encolher tem que manter a janela onde estava, e nao empurra-la para um canto."""
    quadro = molde.caixa("quadro", "deitado", "palco-alto", escala=0.75)

    assert (quadro["largura"], quadro["altura"]) == (960, 540)
    assert (quadro["esquerda"], quadro["topo"]) == (480, 370)


def test_o_deslocamento_sobe_a_janela_inteira():
    """0,1 de 1080 = 108px, e so no eixo vertical."""
    quadro = molde.caixa("quadro", "deitado", "palco-alto", deslocamento=-0.1)

    assert (quadro["esquerda"], quadro["largura"]) == (320, 1280)
    assert quadro["topo"] == 172


def test_a_pagina_mostra_a_janela_JA_ajustada():
    """A previa le a mesma geometria; ler a tabela de novo divergiria do render."""
    camadas = molde.camadas("deitado", "palco-alto", escala=0.75)

    pagina = molde.para_pagina(camadas, "deitado")

    quadro = {c["nome"]: c for c in pagina["camadas"]}["quadro"]
    assert (quadro["largura"], quadro["altura"]) == (960, 540)


def test_o_ffmpeg_obedece_a_janela_ajustada():
    filtro = molde.para_ffmpeg(
        molde.camadas("deitado", "palco-alto", escala=0.75), "deitado"
    )

    assert "scale=960:540:force_original_aspect_ratio=increase" in filtro
    assert "overlay=480:370" in filtro


def test_arranjo_que_nao_existe_reclama_e_ensina_os_que_existem():
    with pytest.raises(ValueError) as erro:
        molde.camadas("deitado", "palco-do-mickey")

    assert "palco-alto" in str(erro.value) and "quadro-cheio" in str(erro.value)
```

E troque a parametrização do teste que compara os dois renderizadores, para ele cobrir os arranjos novos:

```python
@pytest.mark.parametrize(
    "formato,arranjo",
    [("deitado", "quadro-cheio"), ("deitado", "palco-alto"),
     ("deitado", "palco-lateral"), ("em-pe", "quadro-cheio")],
)
def test_ffmpeg_e_pagina_concordam_camada_por_camada(formato, arranjo):
    camadas = molde.camadas(formato, arranjo)

    filtro = molde.para_ffmpeg(camadas, formato)
    pagina = molde.para_pagina(camadas, formato)

    do_ffmpeg = _geometria_do_filtro(filtro)
    da_pagina = {c["nome"]: c for c in pagina["camadas"]}
    for nome, caixa in do_ffmpeg.items():
        for campo, valor in caixa.items():
            assert da_pagina[nome][campo] == valor, f"{formato}/{arranjo}/{nome}/{campo}"
```

- [x] **Step 2: Rodar e ver falhar**

Run: `python -m pytest testes/test_molde.py -v`
Expected: FAIL com `AttributeError: module 'nucleo.molde' has no attribute 'arranjos'`

- [x] **Step 3: Escrever a tabela de arranjos**

Em `nucleo/molde.py`, troque a linha do import por:

```python
from dataclasses import dataclass, replace
```

Substitua o bloco `_MOLDE = {...}` inteiro por:

```python
ARRANJO_PADRAO = "quadro-cheio"

# A tabela de arranjos. Cada um e uma pilha de camadas de baixo para cima, e o
# `quadro-cheio` e o de hoje, numero por numero: e o que garante que ninguem
# acorda com o video diferente sem ter pedido.
#
# Nos arranjos de palco a janela e 1280x720 CRAVADO, que e o tamanho da fonte:
# os pixels caem 1:1 no video final, sem reamostrar. A imagem fica mais nitida
# PORQUE a janela e menor - e a sobra e onde a marca do canal aparece.
_ARRANJOS = {
    "deitado": {
        # Quadro de 1728x972 em 96,54 - a margem de 5% e o que deixa o fundo
        # aparecer. Sem ela, um clipe de webcam em tela cheia continua sendo um
        # clipe de webcam, e nao um produto.
        "quadro-cheio": [
            Camada("fundo", 0.0, 0.0, 1.0, 1.0),
            Camada("quadro", 0.05, 0.05, 0.90, 0.90, cantos=_CANTOS, borda=_BORDA),
        ],
        # 280px de sobra em cima: logo no alto a esquerda, redes no alto a
        # direita. 80px embaixo, so de respiro.
        "palco-alto": [
            Camada("fundo", 0.0, 0.0, 1.0, 1.0),
            Camada("logo", 64 / 1920, 48 / 1080, 192 / 1920, 192 / 1080),
            Camada("barra", 1136 / 1920, 88 / 1080, 720 / 1920, 112 / 1080),
            Camada(
                "quadro", 320 / 1920, 280 / 1080, 1280 / 1920, 720 / 1080,
                cantos=_CANTOS, borda=_BORDA,
            ),
        ],
        # O mais proximo da referencia: coluna de 576px a esquerda com a logo
        # centrada nela, barra atravessando o alto, 64px de respiro a direita.
        "palco-lateral": [
            Camada("fundo", 0.0, 0.0, 1.0, 1.0),
            Camada("logo", 128 / 1920, 380 / 1080, 320 / 1920, 320 / 1080),
            Camada("barra", 64 / 1920, 48 / 1080, 1792 / 1920, 96 / 1080),
            Camada(
                "quadro", 576 / 1920, 300 / 1080, 1280 / 1920, 720 / 1080,
                cantos=_CANTOS, borda=_BORDA,
            ),
        ],
    },
    # Em pe: quadro colado na largura, no terco de cima - a altura de 608/1920 e
    # o 16:9 do clipe deitado na tela em pe, sem esticar nada. Nesta rodada o
    # 9:16 nao ganha palco: precisa de outra arte e de outro lugar para a barra,
    # porque ali a faixa de cima e area nobre.
    "em-pe": {
        "quadro-cheio": [
            Camada("fundo", 0.0, 0.0, 1.0, 1.0),
            Camada("quadro", 0.0, 0.25, 1.0, 608 / 1920, cantos=_CANTOS, borda=_BORDA),
        ],
    },
}
```

- [x] **Step 4: Escrever o ajuste fino e os dois renderizadores**

Troque as funções `camadas`, `caixa` e `para_pagina` por:

```python
def arranjos(formato: str) -> list[str]:
    """Os arranjos daquele formato, na ordem em que a tela oferece."""
    _conferir(formato)
    return list(_ARRANJOS[formato])


def camadas(
    formato: str,
    arranjo: str = ARRANJO_PADRAO,
    escala: float = 1.0,
    deslocamento: float = 0.0,
) -> list[Camada]:
    """As camadas daquele arranjo, de baixo para cima, com o ajuste fino aplicado.

    `escala` multiplica a janela do arranjo escolhido e `deslocamento` a sobe ou
    desce; as duas so mexem no `quadro` - logo e barra ficam onde o arranjo
    disse. Quem confere os limites e o `nucleo/identidade.py`, na porta em que o
    numero e digitado.
    """
    _conferir(formato)
    if arranjo not in _ARRANJOS[formato]:
        raise ValueError(
            f"arranjo '{arranjo}' nao existe no {formato} - use "
            f"{' ou '.join(_ARRANJOS[formato])}"
        )
    base = _ARRANJOS[formato][arranjo]
    # Sem ajuste nenhum, devolve a declaracao INTACTA. Nao e economia de
    # processador: conta com float nao volta no mesmo numero (0,05 + 0,45 - 0,45
    # nao devolve 0,05), e o `quadro-cheio` sem ajuste tem que sair caractere
    # por caractere igual ao de hoje.
    if escala == 1.0 and deslocamento == 0.0:
        return list(base)
    return [
        _ajustada(c, escala, deslocamento) if c.nome == "quadro" else c for c in base
    ]


def _ajustada(quadro: Camada, escala: float, deslocamento: float) -> Camada:
    """A janela cresce e encolhe em torno do proprio centro, e sobe e desce inteira.

    Em torno do centro porque encolher empurrando para um canto nao e ajuste
    fino: e outra composicao, e ai o arranjo escolhido nao quer dizer mais nada.
    """
    centro_x = quadro.x + quadro.largura / 2
    centro_y = quadro.y + quadro.altura / 2
    largura = quadro.largura * escala
    altura = quadro.altura * escala
    return replace(
        quadro,
        x=centro_x - largura / 2,
        y=centro_y - altura / 2 + deslocamento,
        largura=largura,
        altura=altura,
    )


def em_pixels(camada: Camada, formato: str) -> dict:
    """Aquela camada em pixels daquele formato, arredondada uma vez so."""
    largura, altura = tamanho(formato)
    return {
        "nome": camada.nome,
        "esquerda": round(camada.x * largura),
        "topo": round(camada.y * altura),
        "largura": round(camada.largura * largura),
        "altura": round(camada.altura * altura),
        "cantos": round(camada.cantos * largura),
        "borda": round(camada.borda * largura),
    }


def caixa(
    nome: str,
    formato: str,
    arranjo: str = ARRANJO_PADRAO,
    escala: float = 1.0,
    deslocamento: float = 0.0,
) -> dict:
    for camada in camadas(formato, arranjo, escala, deslocamento):
        if camada.nome == nome:
            return em_pixels(camada, formato)
    raise KeyError(f"o arranjo '{arranjo}' do {formato} nao tem camada '{nome}'")


def para_pagina(camadas_: list[Camada], formato: str) -> dict:
    """O JSON que a previa usa para posicionar em CSS. Tudo ja em pixels.

    Sai das camadas RECEBIDAS, e nao da tabela: com escala e deslocamento, ler a
    tabela de novo devolveria a janela sem ajuste - a previa mostraria uma coisa
    e o ffmpeg faria outra, que e exatamente o que este modulo existe para
    impedir.
    """
    largura, altura = tamanho(formato)
    return {
        "formato": formato,
        "largura": largura,
        "altura": altura,
        "camadas": [em_pixels(c, formato) for c in camadas_],
    }
```

E dentro de `para_ffmpeg`, troque a linha que monta as caixas:

```python
    # `em_pixels` e nao `caixa`: as camadas chegam aqui JA ajustadas, e reler a
    # tabela pelo nome desfaria a escala e o deslocamento em silencio.
    caixas = {c.nome: em_pixels(c, formato) for c in camadas_}
```

- [x] **Step 5: Atualizar o cabeçalho do módulo**

No docstring de `nucleo/molde.py`, troque o parágrafo que começa em **"O vídeo não leva letra nenhuma"** por:

```
**O video nao leva letra nenhuma SOBRE A CENA.** Nem placar, nem cartela de
abertura, nem nome de canal escrito por cima do que foi gravado: quem identifica
o video e a capa e a legenda do post, que sao fora do mp4 e podem ser trocadas
sem refazer render nenhum. Foi escolha do dono em 05/09.

O que o desenho do palco (05/09) liberou e o CENARIO: os @s das redes e a
chamada, na faixa que sobra ao redor da janela, que nao tocam a cena e nao mudam
de jogo para jogo. Eles sao desenhados com PIL, num PNG, fora do ffmpeg - o
`drawtext` continua proibido, e e por isso que aqui nao ha nenhum.

A geometria mora em ARRANJOS nomeados, um por composicao, e cada formato tem os
seus. `quadro-cheio` e o de hoje e o padrao; os `palco-*` deixam sobra para a
marca do canal e poem a janela em 1280x720 cravado, que e o tamanho da fonte.
```

- [x] **Step 6: Rodar e ver passar, inclusive a não-regressão**

Run: `python -m pytest testes/test_molde.py -v`
Expected: todos PASSED, `test_o_quadro_cheio_sai_caractere_por_caractere_igual_ao_de_hoje` incluído.

- [x] **Step 7: Rodar a bateria inteira**

Run: `python -m pytest`
Expected: nenhum falho. Se `test_estudio.py` ou `test_painel_edicao.py` reprovarem, é porque alguma chamada a `molde.caixa`/`para_pagina` mudou de comportamento — conserte antes de commitar.

- [x] **Step 8: Commit**

```bash
git add nucleo/molde.py testes/test_molde.py
git commit -m "molde: tres arranjos no deitado, com escala e deslocamento"
```

---

### Task 3: A moldagem escolhida chega ao vídeo e ao cache

O elo que faltava entre a Task 1 e a Task 2: com identidade vazia nada muda; escolhendo `palco-alto`, a janela do render encolhe para 1280×720 e a máscara acompanha.

**Files:**
- Modify: `nucleo/estudio.py` (renomear `identidade` → `chave_da_peca`; `mascaras`, `filtro_do_item`, `planejar`, `assinatura`, `montar` e `espiar` recebendo a identidade)
- Test: `testes/test_estudio.py`

**Interfaces:**
- Consumes: `identidade.carregar()`, `identidade.PADROES`, `identidade.moldagem(ident, dados_receita)` (Task 1); `molde.camadas(formato, arranjo, escala, deslocamento)` e `molde.caixa(...)` (Task 2).
- Produces:
  - `estudio.chave_da_peca(origem: str, de: float, ate: float, filtro: str) -> str` (era `estudio.identidade`)
  - `estudio.mascaras(pasta_jogo: Path, formato: str, moldagem: dict | None = None) -> tuple[Path, Path]`
  - `estudio.filtro_do_item(dados_receita: dict, ident: dict | None = None, com_mascaras: bool = True) -> tuple[str, str]`
  - `estudio.planejar(dados, dados_receita, avisar=None, ident: dict | None = None) -> list[dict]`
  - `estudio.assinatura(dados, dados_receita, ident: dict | None = None) -> str`
  - `estudio.montar(..., tentativas=TENTATIVAS, ident: dict | None = None) -> Path`
  - `estudio.espiar(..., executar=None, ident: dict | None = None) -> Path`

- [x] **Step 1: Escrever os testes**

No topo de `testes/test_estudio.py`, acrescente `identidade` ao import do núcleo:

```python
from nucleo import catalogo, cortador, estudio, identidade, molde, receita
```

Acrescente ao fim do arquivo:

```python
def test_com_identidade_vazia_o_filtro_e_o_de_hoje(tmp_path: Path):
    """A nao-regressao vista do estudio: sem marca nenhuma, nada mudou."""
    from testes.test_molde import FILTRO_DE_HOJE_DEITADO

    dados = _jogo(tmp_path)

    filtro, rotulo = estudio.filtro_do_item(receita.padrao(dados), identidade.PADROES)

    assert filtro == FILTRO_DE_HOJE_DEITADO
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
```

E no teste que já existe por volta da linha 484, troque `estudio.identidade(` por `estudio.chave_da_peca(`.

- [x] **Step 2: Rodar e ver falhar**

Run: `python -m pytest testes/test_estudio.py -k "identidade_vazia or arranjo or mascara_segue or desvio or assinatura_do_video" -v`
Expected: FAIL com `TypeError: filtro_do_item() takes from 1 to 2 positional arguments but 3 were given`

- [x] **Step 3: Renomear a chave da peça e importar a identidade**

Em `nucleo/estudio.py`, na linha do import:

```python
from nucleo import cortador, identidade, molde, receita, times as mod_times
```

Renomeie `def identidade(origem, de, ate, filtro)` para `def chave_da_peca(origem, de, ate, filtro)` e acrescente ao docstring dela:

```
    O nome era `identidade`, e virou `chave_da_peca` quando a identidade DO
    CANAL passou a ser um modulo: duas coisas com o mesmo nome no mesmo arquivo
    e defeito esperando hora.
```

Troque as duas chamadas internas (em `planejar` e em `previa`) para `chave_da_peca(...)`.

- [x] **Step 4: A moldagem chega às máscaras e ao filtro**

Troque a assinatura de `mascaras` e a primeira linha do corpo:

```python
def mascaras(
    pasta_jogo: Path, formato: str, moldagem: dict | None = None
) -> tuple[Path, Path]:
```
```python
    quadro = molde.caixa("quadro", formato, **(moldagem or {}))
```

O nome do arquivo já leva largura, altura e canto, então cada arranjo ganha a sua máscara sem precisar de versão nenhuma.

Troque `filtro_do_item` por:

```python
def filtro_do_item(
    dados_receita: dict, ident: dict | None = None, com_mascaras: bool = True
) -> tuple[str, str]:
    """O filter_complex do item e o rotulo da saida dele.

    Nao depende do clipe nem do jogo porque nao ha nada de individual para
    desenhar: o mesmo filtro serve a todos os itens daquela receita. O que muda
    de um para o outro e o corte, que mora no comando.

    A moldagem vem RESOLVIDA - padrao do canal com o desvio do jogo por cima - e
    e ela que decide o tamanho e a posicao da janela.
    """
    ident = identidade.carregar() if ident is None else ident
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    moldagem = identidade.moldagem(ident, dados_receita)
    filtro = molde.para_ffmpeg(
        molde.camadas(formato, **moldagem),
        formato,
        cor_fundo=cor_do_fundo(dados_receita),
        mascara="1:v" if com_mascaras else None,
        moldura="2:v" if com_mascaras else None,
    )
    return filtro, "v"
```

- [x] **Step 5: A identidade atravessa `planejar`, `assinatura`, `montar` e `espiar`**

`planejar` — acrescente o parâmetro e troque a linha do filtro:

```python
def planejar(
    dados: dict,
    dados_receita: dict,
    avisar: Callable[[str], None] | None = None,
    ident: dict | None = None,
) -> list[dict]:
```
```python
    ident = identidade.carregar() if ident is None else ident
    filtro, rotulo = filtro_do_item(dados_receita, ident)
```

`assinatura`:

```python
def assinatura(dados: dict, dados_receita: dict, ident: dict | None = None) -> str:
```
```python
    nomes = [peca["nome"] for peca in planejar(dados, dados_receita, ident=ident)]
```

`montar` — acrescente `ident: dict | None = None` como **último** parâmetro (o `esteira.py` chama por palavra-chave, e o último lugar não desloca ninguém) e troque, no corpo:

```python
    ident = identidade.carregar() if ident is None else ident
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    moldagem = identidade.moldagem(ident, dados_receita)
    mascara, moldura = mascaras(pasta_jogo, formato, moldagem)
```
```python
    for peca in planejar(dados, dados_receita, avisar, ident):
```
```python
           saida=str(saida), mensagem="pronto",
           assinatura=assinatura(dados, dados_receita, ident))
```

`espiar` — acrescente `ident: dict | None = None` como último parâmetro e troque:

```python
    ident = identidade.carregar() if ident is None else ident
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    mascara, moldura = mascaras(
        pasta_jogo, formato, identidade.moldagem(ident, dados_receita)
    )
    filtro, rotulo = filtro_do_item(dados_receita, ident)
```

- [x] **Step 6: Rodar e ver passar**

Run: `python -m pytest testes/test_estudio.py -v`
Expected: todos PASSED

- [x] **Step 7: Rodar a bateria inteira**

Run: `python -m pytest`
Expected: nenhum falho (`test_acervo.py` chama `estudio.assinatura(dados, edicao)` — o parâmetro novo é opcional, e com identidade vazia o comportamento é o de antes).

- [x] **Step 8: Commit**

```bash
git add nucleo/estudio.py testes/test_estudio.py
git commit -m "estudio: o arranjo escolhido chega ao video e ao cache"
```

---

### Task 4: O palco pré-desenhado, com a arte de fundo

Passo 3 da seção 10: `estudio.palco()` desenhando só a arte de fundo, e a troca de uma linha no `filter_complex`.

**Files:**
- Modify: `nucleo/molde.py` (`para_ffmpeg(..., palco=None)`)
- Modify: `nucleo/estudio.py` (`palco()`, `camadas_do_palco()`, `tem_o_que_desenhar()`, `assinatura_do_palco()`, o palco na chave da peça, a quarta entrada no `comando_item` e no `espiar`)
- Test: `testes/test_molde.py`, `testes/test_estudio.py`

**Interfaces:**
- Consumes: Task 3 inteira.
- Produces:
  - `molde.para_ffmpeg(camadas_, formato, cor_fundo=COR_FUNDO, entrada="0:v", mascara=None, moldura=None, fps=FPS, palco: str | None = None) -> str`
  - `estudio.PASTA_FORMAS = "formas"`, `estudio.VAO_DO_PALCO = 16`
  - `estudio.camadas_do_palco(ident: dict, formato: str, moldagem: dict) -> list[str]`
  - `estudio.tem_o_que_desenhar(ident: dict, formato: str, moldagem: dict) -> bool`
  - `estudio.assinatura_do_palco(formato: str, ident: dict, moldagem: dict, cor_fundo: str) -> str`
  - `estudio.palco(pasta_jogo: Path, formato: str, ident: dict, moldagem: dict, cor_fundo: str, avisar: Callable[[str], None] | None = None) -> Path | None`
  - `estudio.chave_da_peca(origem, de, ate, filtro, palco: str = "") -> str`
  - `estudio.comando_item(..., video=None, palco: Path | None = None) -> list[str]`

- [x] **Step 1: Escrever o teste do filtro com palco**

Acrescente a `testes/test_molde.py`:

```python
def test_com_palco_o_fundo_vira_uma_entrada_de_imagem():
    """A seccao 5 da spec: UMA linha muda, e o resto do filtro fica intacto."""
    filtro = molde.para_ffmpeg(
        molde.camadas("deitado", "palco-alto"), "deitado",
        mascara="1:v", moldura="2:v", palco="3:v",
    )

    assert "[3:v]scale=1920:1080,setsar=1,fps=30[fundo]" in filtro
    assert "color=c=" not in filtro, "com palco nao ha cor chapada"
    assert "vignette" not in filtro, "a vinheta agora vem desenhada no PNG"
    # O recorte, a mascara, a sobreposicao e a moldura seguem iguais.
    assert "alphamerge[quadro]" in filtro
    assert "[fundo][quadro]overlay=320:280:shortest=1[com-quadro]" in filtro


def test_sem_palco_o_filtro_e_a_cor_chapada_de_sempre():
    filtro = molde.para_ffmpeg(molde.camadas("deitado"), "deitado")

    assert "color=c=#101418:s=1920x1080:r=30,vignette=PI/4[fundo]" in filtro
    assert "[3:v]" not in filtro


def test_o_palco_entra_com_a_taxa_de_quadros_declarada():
    """Imagem nao tem relogio: sem `fps`, a base do overlay chega com a taxa que
    o ffmpeg inventa para um `-loop 1` e o tempo do video sai torto."""
    filtro = molde.para_ffmpeg(molde.camadas("deitado"), "deitado", palco="3:v")

    assert f"fps={molde.FPS}[fundo]" in filtro
```

- [x] **Step 2: Rodar e ver falhar**

Run: `python -m pytest testes/test_molde.py -k palco -v`
Expected: FAIL com `TypeError: para_ffmpeg() got an unexpected keyword argument 'palco'`

- [x] **Step 3: O palco como entrada do `para_ffmpeg`**

Em `nucleo/molde.py`, acrescente o parâmetro ao fim da assinatura de `para_ffmpeg`:

```python
def para_ffmpeg(
    camadas_: list[Camada],
    formato: str,
    cor_fundo: str = COR_FUNDO,
    entrada: str = "0:v",
    mascara: str | None = None,
    moldura: str | None = None,
    fps: int = FPS,
    palco: str | None = None,
) -> str:
```

Acrescente ao docstring dela:

```
    `palco` e a entrada de imagem do cenario do canal, um PNG so, ja com arte de
    fundo, logo e barra compostos pelo PIL. Com ele, a linha do fundo troca cor
    chapada por imagem - e e a UNICA linha que muda. Sem ele, o filtro sai
    identico ao de antes de o palco existir.
```

E troque a linha que monta `partes` por:

```python
    if palco:
        # Imagem nao tem relogio. Sem o `fps`, a base do overlay chega com a
        # taxa que o ffmpeg inventa para um `-loop 1` e o tempo do video sai
        # torto. A vinheta, que era do ffmpeg, agora vem desenhada no PNG.
        partes = [f"[{palco}]scale={largura}:{altura},setsar=1,fps={fps}[fundo]"]
    else:
        partes = [
            f"color=c={cor_fundo}:s={largura}x{altura}:r={fps},vignette=PI/4[fundo]"
        ]
```

- [x] **Step 4: Rodar e ver passar**

Run: `python -m pytest testes/test_molde.py -v`
Expected: todos PASSED, a não-regressão inclusive.

- [x] **Step 5: Escrever os testes do palco**

Acrescente a `testes/test_estudio.py`:

```python
def _arte(caminho: Path, tamanho=(1920, 1080), cor=(12, 90, 40)) -> Path:
    """Uma arte de fundo de mentira: PNG chapado, sem texto, como a do Canva."""
    from PIL import Image

    caminho.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", tamanho, cor).save(caminho)
    return caminho


def _com_arte(tmp_path: Path, **campos) -> dict:
    return {
        **identidade.PADROES,
        "arte_de_fundo": str(_arte(tmp_path / "arte.png")),
        **campos,
    }


def test_sem_arte_nenhuma_o_palco_nao_existe(tmp_path: Path):
    """Campo vazio e camada que nao existe - e sem camada nenhuma, sem PNG."""
    moldagem = identidade.moldagem(identidade.PADROES)

    assert estudio.camadas_do_palco(identidade.PADROES, "deitado", moldagem) == []
    assert estudio.palco(
        tmp_path, "deitado", identidade.PADROES, moldagem, "#101418"
    ) is None


def test_com_arte_o_palco_sai_do_tamanho_do_formato(tmp_path: Path):
    from PIL import Image

    ident = _com_arte(tmp_path)
    moldagem = identidade.moldagem(ident)

    png = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418")

    assert Image.open(png).size == (1920, 1080)
    assert png.parent.name == estudio.PASTA_FORMAS


def test_a_arte_de_outro_tamanho_cobre_o_palco_sem_deformar(tmp_path: Path):
    """Redimensiona cobrindo e corta o excesso: arte esticada tem cara de erro."""
    from PIL import Image

    ident = {
        **identidade.PADROES,
        "arte_de_fundo": str(_arte(tmp_path / "quadrada.png", (800, 800))),
    }

    png = estudio.palco(
        tmp_path, "deitado", ident, identidade.moldagem(ident), "#101418"
    )

    imagem = Image.open(png).convert("RGB")
    assert imagem.size == (1920, 1080)
    assert imagem.getpixel((960, 540)) == (12, 90, 40), "a arte cobriu o meio"


def test_arte_que_nao_abre_avisa_e_cai_na_cor_do_time(tmp_path: Path):
    """O render nao para por causa de um PNG quebrado - so avisa."""
    from PIL import Image

    quebrada = tmp_path / "quebrada.png"
    quebrada.write_bytes(b"isto nao e um png")
    ident = {**identidade.PADROES, "arte_de_fundo": str(quebrada)}
    recados = []

    png = estudio.palco(
        tmp_path, "deitado", ident, identidade.moldagem(ident), "#c8102e",
        avisar=recados.append,
    )

    assert png is not None
    assert any("arte" in r.lower() for r in recados), "nunca sumir calado"
    # No meio, onde a vinheta e mais fraca, sobra a cor do time.
    assert Image.open(png).convert("RGB").getpixel((960, 540)) == (200, 16, 46)


def test_o_fundo_da_cor_do_time_tem_as_pontas_mais_escuras_que_o_meio(tmp_path: Path):
    """A vinheta era do ffmpeg e passou a ser do PIL: o efeito e que continua.

    O caminho da cor chapada e o mesmo da arte que nao abre, e e por ele que se
    mede - com arte de verdade a vinheta nao aparece, porque a arte cobre tudo.
    """
    from PIL import Image

    quebrada = tmp_path / "sem-vinheta.png"
    quebrada.write_bytes(b"isto nao e um png")
    ident = {**identidade.PADROES, "arte_de_fundo": str(quebrada)}

    png = estudio.palco(
        tmp_path, "deitado", ident, identidade.moldagem(ident), "#c8102e"
    )

    imagem = Image.open(png).convert("RGB")
    assert sum(imagem.getpixel((5, 5))) < sum(imagem.getpixel((960, 540)))


def test_o_palco_pronto_nao_e_desenhado_de_novo(tmp_path: Path):
    ident = _com_arte(tmp_path)
    moldagem = identidade.moldagem(ident)
    primeiro = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418")
    quando = primeiro.stat().st_mtime_ns

    segundo = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418")

    assert segundo == primeiro
    assert segundo.stat().st_mtime_ns == quando, "reaproveitou em vez de redesenhar"


def test_trocar_a_arte_gera_outro_palco(tmp_path: Path):
    """Mesmo nome de arquivo, outro conteudo: o cache tem que perceber."""
    ident = _com_arte(tmp_path)
    moldagem = identidade.moldagem(ident)
    primeiro = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418")

    _arte(tmp_path / "arte.png", (1920, 1080), (200, 16, 46))
    segundo = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418")

    assert segundo != primeiro


def test_a_cor_do_time_entra_na_assinatura_do_palco():
    ident = identidade.PADROES
    moldagem = identidade.moldagem(ident)

    um = estudio.assinatura_do_palco("deitado", ident, moldagem, "#c8102e")
    outro = estudio.assinatura_do_palco("deitado", ident, moldagem, "#101418")

    assert um != outro


def test_o_palco_entra_como_a_quarta_entrada_do_ffmpeg(tmp_path: Path):
    """Depois da mascara e da moldura: assim 1:v e 2:v continuam sendo elas."""
    dados = _jogo(tmp_path)
    ident = _com_arte(tmp_path)
    executor = Executor()

    estudio.montar(tmp_path, dados, receita.padrao(dados), CFG,
                   executar=executor, ident=ident)

    comando = executor.comandos[0]
    entradas = [comando[i + 1] for i, arg in enumerate(comando) if arg == "-i"]
    assert len(entradas) == 4
    assert "palco-deitado-" in entradas[3] and entradas[3].endswith(".png")
    assert "[3:v]scale=1920:1080" in " ".join(comando)


def test_trocar_a_arte_refaz_as_pecas(tmp_path: Path):
    """A arte muda a imagem da peca; o cache por item tem que perceber sozinho."""
    dados = _jogo(tmp_path)
    feita = receita.padrao(dados)
    estudio.montar(tmp_path, dados, feita, CFG, executar=Executor(),
                   ident=identidade.PADROES)

    depois = Executor()
    estudio.montar(tmp_path, dados, feita, CFG, executar=depois,
                   ident=_com_arte(tmp_path))

    assert len(depois.comandos) == 3, "os dois clipes e a emenda"


def test_a_previa_continua_com_a_mesma_chave_de_cache():
    """O palco entra na chave so quando existe: acrescentar o campo sempre
    renomearia de uma vez todo o cache que ja esta no disco."""
    antes = estudio.chave_da_peca("clipes/x.mp4", 10.0, 70.0, "crua")

    assert estudio.chave_da_peca("clipes/x.mp4", 10.0, 70.0, "crua", "") == antes
    assert estudio.chave_da_peca("clipes/x.mp4", 10.0, 70.0, "crua", "abc") != antes
```

- [x] **Step 6: Rodar e ver falhar**

Run: `python -m pytest testes/test_estudio.py -k palco -v`
Expected: FAIL com `AttributeError: module 'nucleo.estudio' has no attribute 'camadas_do_palco'`

- [x] **Step 7: Escrever o palco no estúdio**

Em `nucleo/estudio.py`, acrescente ao lado de `PASTA_PECAS`:

```python
# O cenario do canal mora numa prateleira propria do cache: e forma, e nao peca
# de video, e da para abrir no visualizador e conferir antes de gastar treze
# minutos de render.
PASTA_FORMAS = "formas"
# O ar entre a arte e a marca, medido no palco de 1920x1080.
VAO_DO_PALCO = 16
```

Troque a assinatura e o JSON de `chave_da_peca`:

```python
def chave_da_peca(
    origem: str, de: float, ate: float, filtro: str, palco: str = ""
) -> str:
```
```python
    crua = json.dumps(
        [origem, round(float(de), 3), round(float(ate), 3), filtro]
        + ([palco] if palco else []),
        ensure_ascii=False,
    )
```

e acrescente ao docstring dela:

```
    O `palco` e a assinatura do cenario, e entra na chave SO QUANDO EXISTE: o
    filtro nomeia a entrada do palco ([3:v]), mas nao diz qual PNG e - trocar a
    arte mudaria a imagem sem mudar a chave. Acrescentar o campo sempre, mesmo
    vazio, renomearia de uma vez todo o cache que ja esta no disco.
```

Acrescente, depois de `mascaras`:

```python
def camadas_do_palco(ident: dict, formato: str, moldagem: dict) -> list[str]:
    """Quais camadas de marca este palco desenha, na ordem em que vao ao PNG.

    E a regra central da identidade num lugar so: **campo vazio e camada que NAO
    EXISTE** - nao e camada transparente, nao e espaco reservado.
    """
    desenhar = []
    if _arquivo_de(ident.get("arte_de_fundo")):
        desenhar.append("arte_de_fundo")
    return desenhar


def tem_o_que_desenhar(ident: dict, formato: str, moldagem: dict) -> bool:
    """Sem nada de marca, o palco nem existe - e o filtro e o de sempre."""
    return bool(camadas_do_palco(ident, formato, moldagem))


def assinatura_do_palco(
    formato: str, ident: dict, moldagem: dict, cor_fundo: str
) -> str:
    """Impressao digital do cenario: identidade, moldagem e cor do time.

    Mudou qualquer um, gera outro arquivo; nao mudou nada, reaproveita - o mesmo
    mecanismo do `mascaras()`. O relogio e o tamanho dos arquivos de arte vao
    junto: trocar o PNG por outro com o MESMO nome tem que gerar outro palco,
    senao o cache serve o cenario velho para sempre.
    """
    crua = json.dumps(
        [
            formato,
            {c: ident.get(c, "") for c in ("arte_de_fundo", "logo", "chamada")},
            ident.get("redes") or {},
            moldagem,
            cor_fundo,
            [_relogio_do_arquivo(ident.get(c)) for c in ("arte_de_fundo", "logo")],
        ],
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha1(crua.encode("utf-8")).hexdigest()[:16]


def palco(
    pasta_jogo: Path,
    formato: str,
    ident: dict,
    moldagem: dict,
    cor_fundo: str,
    avisar: Callable[[str], None] | None = None,
) -> Path | None:
    """O PNG do cenario do canal: arte de fundo, logo e barra ja compostos.

    `None` quando nao ha nada de marca para desenhar, e ai o render segue com a
    cor do time e a vinheta do ffmpeg, como antes de o palco existir.

    Um PNG so, e nao tres entradas de imagem: o filtro nao cresce, o numero de
    entradas do ffmpeg nao muda, e o palco vira um arquivo que se abre no
    visualizador e se confere antes de gastar treze minutos de render.
    """
    if not tem_o_que_desenhar(ident, formato, moldagem):
        return None
    marca = assinatura_do_palco(formato, ident, moldagem, cor_fundo)
    destino = pasta_cache(pasta_jogo) / PASTA_FORMAS / f"palco-{formato}-{marca}.png"
    if destino.is_file():
        return destino

    destino.parent.mkdir(parents=True, exist_ok=True)
    tela = _fundo_do_palco(ident, molde.tamanho(formato), cor_fundo, avisar)
    # Nome provisorio ate o arquivo estar inteiro, como as pecas de video: PNG
    # truncado tem nome, tamanho e data de arquivo bom, e o render seguinte o
    # reaproveitaria como cenario pronto.
    meio = destino.with_name(f"parcial-{destino.name}")
    tela.convert("RGB").save(meio)
    os.replace(meio, destino)
    return destino


def _arquivo_de(caminho) -> Path | None:
    """O caminho que existe no disco, ou `None`. Campo vazio nao desenha."""
    if not caminho:
        return None
    arquivo = Path(str(caminho))
    return arquivo if arquivo.is_file() else None


def _relogio_do_arquivo(caminho) -> list:
    arquivo = _arquivo_de(caminho)
    if arquivo is None:
        return []
    ficha = arquivo.stat()
    return [ficha.st_mtime_ns, ficha.st_size]


def _fundo_do_palco(ident: dict, tamanho: tuple[int, int], cor_fundo: str, avisar):
    from PIL import Image

    arte = _arquivo_de(ident.get("arte_de_fundo"))
    if arte:
        try:
            return _cobrindo(Image.open(arte).convert("RGB"), tamanho)
        except OSError as erro:
            # Arte que nao abre nao para um render de treze minutos: avisa e cai
            # na cor do time. Nunca sumir calado vale aqui tambem.
            if avisar:
                avisar(f"a arte de fundo nao abriu ({erro}) - fica a cor do time")
    return _vinheta(Image.new("RGB", tamanho, _rgb_do_palco(cor_fundo)))


def _cobrindo(imagem, tamanho: tuple[int, int]):
    """Redimensiona cobrindo o palco, sem deformar, e corta o excesso."""
    largura, altura = tamanho
    proporcao = max(largura / imagem.width, altura / imagem.height)
    imagem = imagem.resize((
        max(1, round(imagem.width * proporcao)),
        max(1, round(imagem.height * proporcao)),
    ))
    esquerda = (imagem.width - largura) // 2
    topo = (imagem.height - altura) // 2
    return imagem.crop((esquerda, topo, esquerda + largura, topo + altura))


def _vinheta(tela):
    """Escurece as pontas, como o `vignette=PI/4` fazia no fundo chapado.

    E aproximacao, e nao a mesma conta: o filtro do ffmpeg e otica de lente. O
    que importa e o efeito - meio claro, pontas escuras, para a janela ter
    contra o que aparecer. Sem marca nenhuma o palco nem existe, e ai o render
    continua usando a vinheta do proprio ffmpeg.
    """
    from PIL import Image

    escuro = Image.radial_gradient("L").resize(tela.size)
    escuro = escuro.point(lambda valor: int(210 * (valor / 255) ** 2))
    tela.paste(Image.new("RGB", tela.size, (0, 0, 0)), (0, 0), escuro)
    return tela


def _rgb_do_palco(cor: str) -> tuple[int, int, int]:
    cor = (cor or molde.COR_FUNDO).lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))
```

- [x] **Step 8: Ligar o palco ao plano, ao comando e ao espiar**

Em `planejar`, troque o bloco do filtro por:

```python
    ident = identidade.carregar() if ident is None else ident
    formato = dados_receita.get("formato", FORMATO_PADRAO)
    moldagem = identidade.moldagem(ident, dados_receita)
    # A assinatura do palco entra na chave das pecas: o filtro nomeia a entrada
    # ([3:v]) mas nao diz qual PNG e. Sem isto, trocar a arte deixaria o cache
    # servindo pecas com o cenario velho.
    marca = (
        assinatura_do_palco(formato, ident, moldagem, cor_do_fundo(dados_receita))
        if tem_o_que_desenhar(ident, formato, moldagem) else ""
    )
    filtro, rotulo = filtro_do_item(dados_receita, ident)
```
e, na montagem de cada peça:

```python
            "nome": chave_da_peca(
                clipe["arquivo"], item["de"], item["ate"], filtro, marca
            ),
```

Em `filtro_do_item`, passe o palco ao molde — quem cria o arquivo é `montar`/`espiar`, e as duas usam o MESMO `tem_o_que_desenhar`, então nunca discordam do filtro:

```python
    moldagem = identidade.moldagem(ident, dados_receita)
    filtro = molde.para_ffmpeg(
        molde.camadas(formato, **moldagem),
        formato,
        cor_fundo=cor_do_fundo(dados_receita),
        mascara="1:v" if com_mascaras else None,
        moldura="2:v" if com_mascaras else None,
        palco="3:v" if (
            com_mascaras and tem_o_que_desenhar(ident, formato, moldagem)
        ) else None,
    )
```

Em `comando_item`, acrescente `palco: Path | None = None` ao fim da assinatura e a entrada depois da moldura:

```python
        "-loop", "1", "-t", str(duracao), "-i", str(moldura),
        # O palco e a QUARTA entrada, depois da mascara e da moldura: assim 1:v
        # e 2:v continuam sendo elas, e o filtro de hoje nao se mexe.
        *(["-loop", "1", "-t", str(duracao), "-i", str(palco)] if palco else []),
```

Em `montar`, depois da linha das máscaras:

```python
    cenario = palco(
        pasta_jogo, formato, ident, moldagem, cor_do_fundo(dados_receita), avisar
    )
```
e no `comando_de`:

```python
        comando_de = (
            lambda destino, p=peca: comando_item(
                pasta_jogo / p["clipe"]["arquivo"], p["item"], p["filtro"],
                p["rotulo"], mascara, moldura, destino, cfg["caminho_ffmpeg"],
                palco=cenario,
            )
        )
```

Em `espiar`, depois das máscaras:

```python
    cenario = palco(
        pasta_jogo, formato, ident, identidade.moldagem(ident, dados_receita),
        cor_do_fundo(dados_receita),
    )
```
e no comando, depois da moldura:

```python
        "-loop", "1", "-i", str(moldura),
        *(["-loop", "1", "-i", str(cenario)] if cenario else []),
```

- [x] **Step 9: Rodar e ver passar**

Run: `python -m pytest testes/test_estudio.py -v`
Expected: todos PASSED

- [x] **Step 10: Rodar a bateria inteira**

Run: `python -m pytest`
Expected: nenhum falho.

- [x] **Step 11: Commit**

```bash
git add nucleo/molde.py nucleo/estudio.py testes/test_molde.py testes/test_estudio.py
git commit -m "estudio: o palco pre-desenhado entra como fundo do video"
```

---

### Task 5: A logo e a barra de redes no palco

Passo 4 da seção 10. É aqui que o cenário passa a identificar o canal.

**Files:**
- Modify: `nucleo/estudio.py` (`camadas_do_palco` completo, `arrobas`, `icone`, `_desenhar_logo`, `_desenhar_barra`, a fonte na assinatura e nos chamadores)
- Create: `dados/icones/LEIA-ME.md`
- Test: `testes/test_estudio.py`

**Interfaces:**
- Consumes: Task 4 inteira; `molde.caixa(nome, formato, arranjo, escala, deslocamento)` com as camadas `logo` e `barra` (Task 2); `estudio.fonte_de(cfg)` (já existe).
- Produces:
  - `estudio.PASTA_DOS_ICONES: Path`
  - `estudio.arrobas(ident: dict) -> list[tuple[str, str]]`
  - `estudio.icone(rede: str, corpo: int)` → imagem PIL ou `None`
  - `estudio.assinatura_do_palco(formato, ident, moldagem, cor_fundo, fonte: Path | None = None) -> str`
  - `estudio.palco(pasta_jogo, formato, ident, moldagem, cor_fundo, fonte: Path | None = None, avisar=None) -> Path | None`
  - `estudio.planejar(dados, dados_receita, avisar=None, ident=None, fonte: Path | None = None) -> list[dict]`
  - `estudio.assinatura(dados, dados_receita, ident=None, fonte: Path | None = None) -> str`

- [x] **Step 1: Escrever os testes**

Acrescente a `testes/test_estudio.py`:

```python
FONTE = Path(CFG["fonte_cartela"])


def _logo(caminho: Path, tamanho=(400, 400)) -> Path:
    from PIL import Image

    Image.new("RGBA", tamanho, (255, 0, 0, 255)).save(caminho)
    return caminho


def _quantos_claros(imagem, caixa) -> int:
    """Pixels quase brancos dentro da caixa: e a letra e o icone desenhados."""
    recorte = imagem.crop((
        caixa["esquerda"], caixa["topo"],
        caixa["esquerda"] + caixa["largura"], caixa["topo"] + caixa["altura"],
    )).convert("L")
    return sum(1 for valor in recorte.getdata() if valor > 200)


def test_sem_logo_nao_ha_camada_de_logo(tmp_path: Path):
    ident = {**identidade.PADROES, "arranjo": "palco-alto",
             "redes": {**identidade.PADROES["redes"], "youtube": "@veiabanguela"}}

    camadas = estudio.camadas_do_palco(ident, "deitado", identidade.moldagem(ident))

    assert "logo" not in camadas and "barra" in camadas


def test_todas_as_redes_em_branco_nao_desenham_barra(tmp_path: Path):
    ident = {**identidade.PADROES, "arranjo": "palco-alto",
             "logo": str(_logo(tmp_path / "logo.png"))}

    camadas = estudio.camadas_do_palco(ident, "deitado", identidade.moldagem(ident))

    assert camadas == ["logo"]


def test_rede_em_branco_nao_ocupa_espaco_na_barra():
    """Instagram vazio nao aparece; a barra se monta com o que existir."""
    ident = {**identidade.PADROES, "redes": {
        "youtube": "@veiabanguela", "instagram": "", "tiktok": "@veiatk"
    }}

    assert estudio.arrobas(ident) == [
        ("youtube", "@veiabanguela"), ("tiktok", "@veiatk")
    ]


def test_o_quadro_cheio_nao_tem_onde_por_logo_nem_barra(tmp_path: Path):
    """Sem sobra nao ha camada, mesmo com tudo preenchido - e sem camada, sem PNG."""
    ident = {**identidade.PADROES, "logo": str(_logo(tmp_path / "logo.png")),
             "redes": {**identidade.PADROES["redes"], "youtube": "@veiabanguela"}}
    moldagem = identidade.moldagem(ident)

    assert estudio.camadas_do_palco(ident, "deitado", moldagem) == []
    assert estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418") is None


def test_a_logo_cai_exatamente_na_caixa_que_a_pagina_promete(tmp_path: Path):
    """O terceiro renderizador: o PIL desenha nas caixas do MESMO molde.

    A previa da tela e o palco do render leem a mesma geometria. Este teste e o
    que impede as duas de divergirem depois de alguem mexer num numero de um
    lado so - o mesmo papel do `test_ffmpeg_e_pagina_concordam`.
    """
    from PIL import Image

    ident = {**identidade.PADROES, "arranjo": "palco-alto",
             "logo": str(_logo(tmp_path / "logo.png"))}
    moldagem = identidade.moldagem(ident)

    png = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418")

    caixa = molde.caixa("logo", "deitado", **moldagem)
    imagem = Image.open(png).convert("RGB")
    assert imagem.getpixel((caixa["esquerda"], caixa["topo"])) == (255, 0, 0)
    assert imagem.getpixel((
        caixa["esquerda"] + caixa["largura"] - 1,
        caixa["topo"] + caixa["altura"] - 1,
    )) == (255, 0, 0)
    assert imagem.getpixel((caixa["esquerda"] - 3, caixa["topo"] - 3)) != (255, 0, 0)


def test_a_logo_cabe_inteira_na_caixa_sem_ser_cortada(tmp_path: Path):
    """Logo cortada nao e logo: cabe dentro, e nao cobre a caixa a forca."""
    from PIL import Image

    ident = {**identidade.PADROES, "arranjo": "palco-lateral",
             "logo": str(_logo(tmp_path / "comprida.png", (600, 200)))}
    moldagem = identidade.moldagem(ident)

    png = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418")

    caixa = molde.caixa("logo", "deitado", **moldagem)
    imagem = Image.open(png).convert("RGB")
    # 600x200 numa caixa de 320x320: a logo fica 320x107, centrada - e as quinas
    # de cima da caixa continuam sendo cenario, nao logo.
    assert imagem.getpixel((caixa["esquerda"], caixa["topo"])) != (255, 0, 0)
    assert imagem.getpixel((
        caixa["esquerda"] + caixa["largura"] // 2,
        caixa["topo"] + caixa["altura"] // 2,
    )) == (255, 0, 0)


def test_a_barra_desenha_o_arroba_de_cada_rede(tmp_path: Path):
    from PIL import Image

    ident = {**identidade.PADROES, "arranjo": "palco-alto", "chamada": "",
             "redes": {"youtube": "@veiabanguela", "instagram": "", "tiktok": ""}}
    moldagem = identidade.moldagem(ident)

    png = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418", fonte=FONTE)

    claros = _quantos_claros(
        Image.open(png), molde.caixa("barra", "deitado", **moldagem)
    )
    assert claros > 100, "a barra saiu vazia"


def test_a_chamada_grande_demais_nao_sai_cortada_na_borda(tmp_path: Path):
    """O PIL sabe MEDIR texto: o que nao cabe nao entra, em vez de estourar a caixa."""
    from PIL import Image

    ident = {**identidade.PADROES, "arranjo": "palco-alto",
             "chamada": "SE INSCREVE NO CANAL " * 12,
             "redes": {"youtube": "@veiabanguela", "instagram": "", "tiktok": ""}}
    moldagem = identidade.moldagem(ident)

    png = estudio.palco(tmp_path, "deitado", ident, moldagem, "#101418", fonte=FONTE)

    caixa = molde.caixa("barra", "deitado", **moldagem)
    quarto_da_esquerda = {**caixa, "largura": caixa["largura"] // 4}
    assert _quantos_claros(Image.open(png), quarto_da_esquerda) == 0


def test_sem_icone_no_disco_a_barra_sai_so_com_texto():
    """O dono ainda vai por os PNGs la; esperar por eles nao pode travar o palco."""
    assert estudio.icone("orkut", 32) is None


def test_o_icone_do_disco_entra_no_tamanho_da_letra(tmp_path: Path, monkeypatch):
    from PIL import Image

    monkeypatch.setattr(estudio, "PASTA_DOS_ICONES", tmp_path)
    Image.new("RGBA", (512, 512), (255, 255, 255, 255)).save(tmp_path / "youtube.png")

    desenhado = estudio.icone("youtube", 40)

    assert desenhado is not None and desenhado.size == (40, 40)


def test_trocar_o_arroba_gera_outro_palco(tmp_path: Path):
    ident = {**identidade.PADROES, "arranjo": "palco-alto",
             "redes": {**identidade.PADROES["redes"], "youtube": "@um"}}
    moldagem = identidade.moldagem(ident)
    primeiro = estudio.palco(
        tmp_path, "deitado", ident, moldagem, "#101418", fonte=FONTE
    )

    outro = {**ident, "redes": {**ident["redes"], "youtube": "@outro"}}
    segundo = estudio.palco(
        tmp_path, "deitado", outro, moldagem, "#101418", fonte=FONTE
    )

    assert segundo != primeiro
```

- [x] **Step 2: Rodar e ver falhar**

Run: `python -m pytest testes/test_estudio.py -k "logo or barra or arroba or icone" -v`
Expected: FAIL com `AttributeError: module 'nucleo.estudio' has no attribute 'arrobas'`

- [x] **Step 3: Escrever a logo, a barra e os ícones**

Em `nucleo/estudio.py`, ao lado de `PASTA_FORMAS`:

```python
# Os icones das redes vao versionados no repositorio, em PNG branco com
# transparencia, com o nome da chave em `identidade.redes`.
PASTA_DOS_ICONES = Path(__file__).resolve().parent.parent / "dados" / "icones"
```

Complete `camadas_do_palco`:

```python
def camadas_do_palco(ident: dict, formato: str, moldagem: dict) -> list[str]:
    """Quais camadas de marca este palco desenha, na ordem em que vao ao PNG.

    E a regra central da identidade num lugar so: **campo vazio e camada que NAO
    EXISTE** - nao e camada transparente, nao e espaco reservado. Arranjo sem
    sobra tambem nao tem onde por logo nem barra, e ai elas nao entram nem com
    os campos preenchidos.
    """
    tem = {c.nome for c in molde.camadas(formato, **moldagem)}
    desenhar = []
    if _arquivo_de(ident.get("arte_de_fundo")):
        desenhar.append("arte_de_fundo")
    if "logo" in tem and _arquivo_de(ident.get("logo")):
        desenhar.append("logo")
    if "barra" in tem and arrobas(ident):
        desenhar.append("barra")
    return desenhar


def arrobas(ident: dict) -> list[tuple[str, str]]:
    """As redes preenchidas, na ordem do arquivo. Rede vazia nao ocupa espaco."""
    return [
        (rede, str(arroba).strip())
        for rede, arroba in (ident.get("redes") or {}).items()
        if str(arroba).strip()
    ]


def icone(rede: str, corpo: int):
    """O PNG branco de `dados/icones/<rede>.png`, no tamanho da letra.

    Sem icone no disco, a barra sai so com texto: o dono ainda vai por os
    arquivos la, e esperar por eles nao pode travar o palco.
    """
    arquivo = PASTA_DOS_ICONES / f"{rede}.png"
    if not arquivo.is_file():
        return None
    from PIL import Image

    desenhado = Image.open(arquivo).convert("RGBA")
    desenhado.thumbnail((corpo, corpo))
    return desenhado
```

Acrescente as duas camadas ao corpo de `palco`, entre o fundo e o batismo do arquivo:

```python
    tela = _fundo_do_palco(ident, molde.tamanho(formato), cor_fundo, avisar)
    _desenhar_logo(tela, ident, formato, moldagem)
    _desenhar_barra(tela, ident, formato, moldagem, fonte)
```

E os desenhistas, depois de `_vinheta`:

```python
def _desenhar_logo(tela, ident: dict, formato: str, moldagem: dict) -> None:
    arquivo = _arquivo_de(ident.get("logo"))
    caixa = _caixa_ou_nada("logo", formato, moldagem)
    if not (arquivo and caixa):
        return
    from PIL import Image

    desenhada = Image.open(arquivo).convert("RGBA")
    # `thumbnail` e nao `resize`: a logo cabe INTEIRA na caixa, sem deformar e
    # sem ser cortada. Logo cortada nao e logo.
    desenhada.thumbnail((caixa["largura"], caixa["altura"]))
    tela.paste(
        desenhada,
        (
            caixa["esquerda"] + (caixa["largura"] - desenhada.width) // 2,
            caixa["topo"] + (caixa["altura"] - desenhada.height) // 2,
        ),
        desenhada,
    )


def _desenhar_barra(
    tela, ident: dict, formato: str, moldagem: dict, fonte: Path | None
) -> None:
    """A faixa de redes: um par icone + arroba por rede que existir.

    Monta da DIREITA para a esquerda, com o que existir: rede vazia nao deixa
    buraco. A chamada entra no que sobrar a esquerda, e so se couber - o PIL
    sabe medir texto, e texto cortado na borda e pior do que texto ausente.
    """
    caixa = _caixa_ou_nada("barra", formato, moldagem)
    escritas = arrobas(ident)
    if not (caixa and escritas):
        return
    from PIL import ImageDraw

    desenho = ImageDraw.Draw(tela)
    corpo = max(14, caixa["altura"] // 3)
    letra = _letra_do_palco(fonte, corpo)
    meio = caixa["topo"] + caixa["altura"] // 2
    direita = caixa["esquerda"] + caixa["largura"]

    for rede, arroba in reversed(escritas):
        _texto_do_palco(desenho, arroba, (direita, meio), letra, "rm")
        direita -= round(desenho.textlength(arroba, font=letra)) + VAO_DO_PALCO
        marca = icone(rede, corpo)
        if marca:
            tela.paste(marca, (direita - marca.width, meio - marca.height // 2), marca)
            direita -= marca.width + VAO_DO_PALCO

    chamada = str(ident.get("chamada") or "").strip()
    livre = direita - caixa["esquerda"] - VAO_DO_PALCO
    if chamada and desenho.textlength(chamada, font=letra) <= livre:
        _texto_do_palco(desenho, chamada, (caixa["esquerda"], meio), letra, "lm")


def _caixa_ou_nada(nome: str, formato: str, moldagem: dict) -> dict | None:
    """A caixa daquela camada, ou `None` se o arranjo nao tiver onde por."""
    try:
        return molde.caixa(nome, formato, **moldagem)
    except KeyError:
        return None


def _letra_do_palco(fonte: Path | None, corpo: int):
    """A fonte da barra. Sem arquivo, a letra do sistema: feia, mas legivel.

    Nao se importa do `capa.py` porque o `capa` importa o estudio - importar de
    volta fecharia o ciclo. Sao seis linhas; o ciclo custaria mais.
    """
    from PIL import ImageFont

    if fonte and Path(fonte).is_file():
        return ImageFont.truetype(str(fonte), corpo)
    return ImageFont.load_default()


def _texto_do_palco(desenho, texto: str, posicao, letra, ancora: str) -> None:
    """Letra branca com sombra dura atras: a barra vai sobre arte clara e escura."""
    x, y = posicao
    desenho.text((x + 2, y + 2), texto, font=letra, fill=(0, 0, 0), anchor=ancora)
    desenho.text((x, y), texto, font=letra, fill=(255, 255, 255), anchor=ancora)
```

- [x] **Step 4: A fonte entra na assinatura e nos chamadores**

A fonte muda o desenho da barra, então ela é parte da imagem — tem que entrar na assinatura do palco e, por ela, na chave da peça.

`assinatura_do_palco`:

```python
def assinatura_do_palco(
    formato: str, ident: dict, moldagem: dict, cor_fundo: str,
    fonte: Path | None = None,
) -> str:
```
e no JSON, depois da linha dos relógios:

```python
            str(fonte or ""),
```

`palco` — `fonte` entra **antes** de `avisar`:

```python
def palco(
    pasta_jogo: Path,
    formato: str,
    ident: dict,
    moldagem: dict,
    cor_fundo: str,
    fonte: Path | None = None,
    avisar: Callable[[str], None] | None = None,
) -> Path | None:
```
```python
    marca = assinatura_do_palco(formato, ident, moldagem, cor_fundo, fonte)
```

`planejar` e `assinatura` ganham `fonte` ao fim da assinatura:

```python
def planejar(
    dados: dict,
    dados_receita: dict,
    avisar: Callable[[str], None] | None = None,
    ident: dict | None = None,
    fonte: Path | None = None,
) -> list[dict]:
```
```python
    marca = (
        assinatura_do_palco(
            formato, ident, moldagem, cor_do_fundo(dados_receita), fonte
        )
        if tem_o_que_desenhar(ident, formato, moldagem) else ""
    )
```
```python
def assinatura(
    dados: dict, dados_receita: dict, ident: dict | None = None,
    fonte: Path | None = None,
) -> str:
```
```python
    nomes = [
        peca["nome"]
        for peca in planejar(dados, dados_receita, ident=ident, fonte=fonte)
    ]
```

`montar` — a fonte sai do `cfg` e vai aos três lugares:

```python
    fonte = fonte_de(cfg)
    cenario = palco(
        pasta_jogo, formato, ident, moldagem, cor_do_fundo(dados_receita),
        fonte, avisar,
    )
```
```python
    for peca in planejar(dados, dados_receita, avisar, ident, fonte):
```
```python
           assinatura=assinatura(dados, dados_receita, ident, fonte))
```

`espiar`:

```python
    cenario = palco(
        pasta_jogo, formato, ident, identidade.moldagem(ident, dados_receita),
        cor_do_fundo(dados_receita), fonte_de(cfg),
    )
```

- [x] **Step 5: O contrato dos ícones**

Crie `dados/icones/LEIA-ME.md`:

~~~markdown
# Ícones das redes

Um PNG por rede, com o **nome da chave** que aparece em `redes`, no
`dados/identidade.json`:

```
youtube.png    instagram.png    tiktok.png
```

- **PNG branco com transparência.** O palco desenha por cima de arte clara e
  escura, e o branco com sombra é o que lê nas duas.
- Quadrado, e de pelo menos 256×256. O estúdio reduz para a altura da letra da
  barra; ampliar um ícone pequeno serrilha.
- **Sem ícone no disco, a barra sai só com o texto.** Nada quebra, nada avisa: é
  o comportamento normal enquanto os arquivos não estiverem aqui.

Estes arquivos vão para o Git — são identidade do canal, não configuração de
máquina.
~~~

- [x] **Step 6: Rodar e ver passar**

Run: `python -m pytest testes/test_estudio.py -v`
Expected: todos PASSED

- [x] **Step 7: Rodar a bateria inteira**

Run: `python -m pytest`
Expected: nenhum falho.

- [x] **Step 8: Commit**

```bash
git add nucleo/estudio.py dados/icones/LEIA-ME.md testes/test_estudio.py
git commit -m "estudio: a logo e a barra de redes entram no palco"
```

---

### Task 6: O cartão MOLDAGEM no painel

Passo 5 da seção 10, e o conserto do caminho que o dono não conseguiu abrir.

**Files:**
- Modify: `painel/edicao.py` (a identidade na `tela`, `abrir_no_explorador`, e as rotas `/api/moldagem`, `/api/identidade`, `/api/palco`, `/api/abrir-pasta`)
- Modify: `painel/edicao.html` (o cartão MOLDAGEM antes do RENDER FINAL e o botão ABRIR A PASTA)
- Modify: `DESIGN.md` (o parágrafo do cartão MOLDAGEM)
- Test: `testes/test_painel_edicao.py`

**Interfaces:**
- Consumes: tudo das tarefas 1 a 5 — `identidade.carregar/salvar/mexer/conferir/moldagem/desviou`, `identidade.CAMPOS_DA_MOLDAGEM`, `identidade.REDES`, `molde.arranjos`, `molde.camadas`, `molde.para_pagina`, `receita.definir_moldagem`, `estudio.palco`, `estudio.camadas_do_palco`, `estudio.fonte_de`, `estudio.cor_do_fundo`.
- Produces:
  - `edicao.montar_resposta(rota, corpo, pasta_jogo, cfg, executar=None, lancar=None, abrir=None) -> tuple[int, dict]`
  - `edicao.abrir_no_explorador(saida: Path) -> None`
  - Campos novos em `tela()`: `arranjos`, `moldagem`, `identidade`, `fora_do_padrao`, `palco_desenha`, `recado_da_moldagem`

- [x] **Step 1: Escrever os testes**

No topo de `testes/test_painel_edicao.py`, acrescente `pytest` e `identidade`:

```python
import pytest

from nucleo import catalogo, estudio, identidade, receita
```

Acrescente ao fim do arquivo:

```python
@pytest.fixture(autouse=True)
def identidade_isolada(tmp_path: Path, monkeypatch):
    """Nenhum teste escreve na identidade real da maquina.

    As rotas gravam com `identidade.salvar()` sem caminho, e ele resolve o
    `ARQUIVO` do modulo na hora - trocar o atributo aqui basta.
    """
    monkeypatch.setattr(identidade, "ARQUIVO", tmp_path / "dados" / "identidade.json")


def test_a_tela_traz_a_moldagem_do_canal_ja_resolvida(tmp_path: Path):
    _jogo(tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert corpo["moldagem"] == {
        "arranjo": "quadro-cheio", "escala": 1.0, "deslocamento": 0.0
    }
    assert corpo["arranjos"] == ["quadro-cheio", "palco-alto", "palco-lateral"]
    assert corpo["fora_do_padrao"] is False
    assert corpo["palco_desenha"] == [], "identidade vazia nao desenha nada"


def test_escolher_o_arranjo_grava_na_identidade_do_canal(tmp_path: Path):
    """O palco e o estilo da casa: escolher aqui vale para todo jogo."""
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/moldagem", {"arranjo": "palco-alto"}, tmp_path)

    assert codigo == 200
    assert corpo["moldagem"]["arranjo"] == "palco-alto"
    assert identidade.carregar()["arranjo"] == "palco-alto"
    assert corpo["fora_do_padrao"] is False


def test_so_neste_jogo_grava_o_desvio_na_receita_e_marca(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/moldagem",
        {"arranjo": "palco-lateral", "so_neste_jogo": True},
        tmp_path,
    )

    assert codigo == 200
    assert corpo["fora_do_padrao"] is True
    assert corpo["moldagem"]["arranjo"] == "palco-lateral"
    gravada = json.loads((tmp_path / receita.NOME).read_text(encoding="utf-8"))
    assert gravada["moldagem"]["arranjo"] == "palco-lateral"
    assert identidade.carregar()["arranjo"] == "quadro-cheio", "o canal nao mudou"


def test_mexer_no_padrao_do_canal_apaga_o_desvio_do_jogo(tmp_path: Path):
    _jogo(tmp_path)
    _pedir("POST /api/moldagem", {"escala": 0.8, "so_neste_jogo": True}, tmp_path)

    _, corpo = _pedir("POST /api/moldagem", {"escala": 0.9}, tmp_path)

    assert corpo["fora_do_padrao"] is False
    assert corpo["moldagem"]["escala"] == 0.9


def test_escala_acima_de_um_e_recusada_pela_rota(tmp_path: Path):
    """O navegador ja prende o campo; quem garante e este lado."""
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/moldagem", {"escala": 1.5}, tmp_path)

    assert codigo == 400
    assert "1280x720" in corpo["erro"]
    assert identidade.carregar()["escala"] == 1.0, "nada mudou no disco"


def test_arranjo_que_nao_existe_e_recusado_pela_rota(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/moldagem", {"arranjo": "palco-do-mickey"}, tmp_path
    )

    assert codigo == 400
    assert "palco-alto" in corpo["erro"]


def test_os_arrobas_gravam_na_hora(tmp_path: Path):
    """Nada so na memoria da pagina aberta."""
    _jogo(tmp_path)

    codigo, corpo = _pedir(
        "POST /api/identidade", {"redes": {"youtube": "@veiabanguela"}}, tmp_path
    )

    assert codigo == 200
    assert corpo["identidade"]["redes"]["youtube"] == "@veiabanguela"
    assert identidade.carregar()["redes"]["youtube"] == "@veiabanguela"


def test_conferir_palco_sem_marca_nenhuma_diz_que_nao_ha_o_que_desenhar(tmp_path: Path):
    _jogo(tmp_path)

    codigo, corpo = _pedir("POST /api/palco", {}, tmp_path)

    assert codigo == 200
    assert corpo["arquivo"] == ""
    assert "arte" in corpo["recado"].lower()


def test_conferir_palco_devolve_o_png_para_a_tela(tmp_path: Path):
    from PIL import Image

    _jogo(tmp_path)
    arte = tmp_path / "arte.png"
    Image.new("RGB", (1920, 1080), (12, 90, 40)).save(arte)
    _pedir("POST /api/identidade", {"arte_de_fundo": str(arte)}, tmp_path)

    codigo, corpo = _pedir("POST /api/palco", {}, tmp_path)

    assert codigo == 200
    assert corpo["arquivo"].startswith("/midia/intermediarios/formas/palco-deitado-")
    assert "?v=" in corpo["arquivo"], "sem contador o navegador mostra o palco velho"


def test_a_tela_diz_o_que_o_palco_vai_desenhar(tmp_path: Path):
    from PIL import Image

    _jogo(tmp_path)
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (400, 400), (255, 0, 0, 255)).save(logo)
    _pedir("POST /api/moldagem", {"arranjo": "palco-alto"}, tmp_path)
    _pedir("POST /api/identidade", {"logo": str(logo)}, tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert corpo["palco_desenha"] == ["logo"]


def test_a_previa_da_tela_traz_as_caixas_do_arranjo_escolhido(tmp_path: Path):
    """A previa usa `para_pagina`, que ja devolve as caixas em pixels."""
    _jogo(tmp_path)
    _pedir("POST /api/moldagem", {"arranjo": "palco-alto"}, tmp_path)

    _, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    caixas = {c["nome"]: c for c in corpo["molde"]["camadas"]}
    assert (caixas["quadro"]["largura"], caixas["quadro"]["altura"]) == (1280, 720)
    assert "logo" in caixas and "barra" in caixas


def test_abrir_a_pasta_chama_o_explorador_com_o_caminho_inteiro(tmp_path: Path):
    """O nome do jogo tem espacos: o caminho vai como ARGUMENTO, nunca como
    texto para o operador copiar."""
    _jogo(tmp_path)
    saida = tmp_path / "saida" / "compilacao-deitado.mp4"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_bytes(b"video de mentira")
    estudio.anotar(tmp_path, rodando=False, saida=str(saida))
    abertos = []

    codigo, _ = _pedir("POST /api/abrir-pasta", {}, tmp_path, abrir=abertos.append)

    assert codigo == 200
    assert abertos == [saida]


def test_abrir_a_pasta_sem_video_pronto_diz_que_nao_tem(tmp_path: Path):
    _jogo(tmp_path)
    abertos = []

    codigo, corpo = _pedir("POST /api/abrir-pasta", {}, tmp_path, abrir=abertos.append)

    assert codigo == 404
    assert abertos == []
    assert "video" in corpo["erro"].lower()


def test_receita_editada_na_mao_fora_da_trava_ainda_abre_a_tela(tmp_path: Path):
    """Tela que nao abre e pior do que tela com recado."""
    dados = _jogo(tmp_path)
    edicao_ruim = receita.padrao(dados)
    edicao_ruim["moldagem"] = {"escala": 1.9}
    receita.salvar(tmp_path, edicao_ruim)

    codigo, corpo = _pedir("GET /api/edicao", {}, tmp_path)

    assert codigo == 200
    assert corpo["moldagem"]["escala"] == 1.0, "caiu no padrao do canal"
    assert "1280x720" in corpo["recado_da_moldagem"]


def test_a_tela_tem_o_cartao_da_moldagem_antes_do_render():
    """A seccao 8: o lugar que faltava e depois de escolher os clipes, antes de gerar."""
    pagina = edicao.PAGINA.read_text(encoding="utf-8")

    assert 'id="moldagem"' in pagina
    assert 'id="botao-palco"' in pagina
    assert 'id="abrir-pasta"' in pagina
    assert pagina.index('id="moldagem"') < pagina.index('id="render"')
```

- [x] **Step 2: Rodar e ver falhar**

Run: `python -m pytest testes/test_painel_edicao.py -v`
Expected: FAIL com `KeyError: 'moldagem'` no primeiro teste novo.

- [x] **Step 3: A identidade chega à `tela()`**

Em `painel/edicao.py`, na linha do import:

```python
from nucleo import canais, capa, catalogo, cortador, estudio, identidade, melhor, molde
from nucleo import perdedor, publicacao, receita, torcidas
```

No começo de `tela()`, troque a primeira linha por:

```python
    formato = edicao.get("formato", receita.FORMATO_PADRAO)
    ident = identidade.carregar()
    try:
        moldagem = identidade.moldagem(ident, edicao)
        recado_da_moldagem = ""
    except ValueError as erro:
        # Receita editada na mao com numero fora da trava: a tela abre no padrao
        # do canal e DIZ por que. Tela que nao abre e pior do que tela com
        # recado - o operador fica sem lugar nenhum para consertar.
        moldagem = identidade.moldagem(ident)
        recado_da_moldagem = str(erro)
```

No dicionário devolvido, troque a linha do molde e acrescente os campos:

```python
        "molde": molde.para_pagina(molde.camadas(formato, **moldagem), formato),
        "arranjos": molde.arranjos(formato),
        "moldagem": moldagem,
        "identidade": {**ident, "redes": dict(ident.get("redes") or {})},
        "fora_do_padrao": identidade.desviou(edicao),
        "palco_desenha": estudio.camadas_do_palco(ident, formato, moldagem),
        "recado_da_moldagem": recado_da_moldagem,
```

- [x] **Step 4: O explorador e as rotas novas**

Ao lado de `lancar_render`, acrescente:

```python
def abrir_no_explorador(saida: Path) -> None:
    """`explorer /select,<arquivo>`: a pasta abre com o video ja selecionado.

    O caminho vai como ARGUMENTO, e nao como texto na tela para o operador
    copiar: o nome do jogo tem espacos e, colado sem aspas, o Windows nao
    encontra - foi o que travou o dono em 05/09, com o video pronto no disco.

    `Popen` e nao `run`: o `explorer` sai com codigo 1 mesmo quando abre a
    janela.
    """
    subprocess.Popen(["explorer", f"/select,{saida}"])
```

Em `montar_resposta`, acrescente `abrir=None` ao fim da assinatura:

```python
def montar_resposta(
    rota: str,
    corpo: dict,
    pasta_jogo: Path,
    cfg: dict,
    executar=None,
    lancar=None,
    abrir=None,
) -> tuple[int, dict]:
```

E os blocos, antes do `if rota == "POST /api/render":`:

```python
    if rota == "POST /api/moldagem":
        edicao = receita.carregar(pasta_jogo, dados)
        formato = edicao.get("formato", receita.FORMATO_PADRAO)
        valores = {}
        for campo in identidade.CAMPOS_DA_MOLDAGEM:
            if campo not in corpo:
                continue
            if campo == "arranjo":
                if corpo[campo] not in molde.arranjos(formato):
                    return 400, {
                        "erro": f"arranjo '{corpo[campo]}' nao existe no "
                                f"{formato} - use "
                                f"{' ou '.join(molde.arranjos(formato))}"
                    }
                valores[campo] = corpo[campo]
                continue
            try:
                valores[campo] = float(corpo[campo])
            except (TypeError, ValueError):
                return 400, {"erro": f"{campo} precisa ser um numero"}
        try:
            if corpo.get("so_neste_jogo"):
                # A trava vale nos dois caminhos: desvio de jogo tambem nao
                # pode furar o teto de 1,00.
                identidade.conferir({
                    **identidade.moldagem(identidade.carregar(), edicao), **valores
                })
                edicao = receita.definir_moldagem(edicao, valores)
            else:
                identidade.salvar(identidade.mexer(identidade.carregar(), **valores))
                # Mexer no padrao do canal apaga o desvio deste jogo: senao o
                # operador mexe no numero e a tela nao muda, porque o desvio
                # continua ganhando, calado.
                edicao = receita.definir_moldagem(edicao, None)
        except ValueError as erro:
            return 400, {"erro": str(erro)}
        receita.salvar(pasta_jogo, edicao)
        return 200, tela(pasta_jogo, dados, edicao, cfg)

    if rota == "POST /api/identidade":
        campos = {
            campo: corpo[campo]
            for campo in ("arte_de_fundo", "logo", "chamada")
            if campo in corpo
        }
        if "redes" in corpo:
            campos["redes"] = {
                rede: str(arroba).strip()
                for rede, arroba in (corpo["redes"] or {}).items()
                if rede in identidade.REDES
            }
        try:
            identidade.salvar(identidade.mexer(identidade.carregar(), **campos))
        except ValueError as erro:
            return 400, {"erro": str(erro)}
        return 200, tela(pasta_jogo, dados, receita.carregar(pasta_jogo, dados), cfg)

    if rota == "POST /api/palco":
        edicao = receita.carregar(pasta_jogo, dados)
        formato = edicao.get("formato", receita.FORMATO_PADRAO)
        ident = identidade.carregar()
        try:
            moldagem = identidade.moldagem(ident, edicao)
        except ValueError as erro:
            return 400, {"erro": str(erro)}
        recados = []
        cenario = estudio.palco(
            pasta_jogo, formato, ident, moldagem, estudio.cor_do_fundo(edicao),
            estudio.fonte_de(cfg), recados.append,
        )
        if cenario is None:
            return 200, {
                "arquivo": "",
                "recado": "nada de marca para desenhar - preencha a arte de "
                          "fundo, a logo ou um @ das redes",
            }
        relativo = cenario.relative_to(pasta_jogo).as_posix()
        return 200, {
            "arquivo": f"/midia/{relativo}?v={cenario.stat().st_mtime_ns}",
            "recado": " ".join(recados),
        }

    if rota == "POST /api/abrir-pasta":
        saida = estudio.estado(pasta_jogo).get("saida") or ""
        if not saida or not Path(saida).exists():
            return 404, {"erro": "ainda nao ha video pronto neste jogo"}
        (abrir or abrir_no_explorador)(Path(saida))
        return 200, {"abriu": saida}
```

E no `POST /api/render`, logo depois da conferência de itens marcados:

```python
        try:
            identidade.moldagem(identidade.carregar(), edicao)
        except ValueError as erro:
            # Melhor recusar aqui do que deixar o render morrer num processo
            # separado, onde a mensagem nao chega a tela.
            return 400, {"erro": str(erro)}
```

- [x] **Step 5: Rodar e ver os testes de rota passarem**

Run: `python -m pytest testes/test_painel_edicao.py -v`
Expected: só `test_a_tela_tem_o_cartao_da_moldagem_antes_do_render` ainda FAIL — a página é o passo seguinte.

- [x] **Step 6: O cartão MOLDAGEM na página**

Em `painel/edicao.html`, no `<style>`, depois do bloco do `#publicar-texto`:

```css
    #moldagem .previa-palco { position: relative; width: 100%; background: var(--caixa-2);
                              border: 1px solid var(--linha); border-radius: 8px;
                              aspect-ratio: 16/9; margin-bottom: 12px; }
    #moldagem .previa-palco > div { position: absolute; border: 1px solid var(--fio-forte);
                                    border-radius: 8px; font-size: 11px; color: var(--fraco);
                                    display: flex; align-items: center;
                                    justify-content: center; overflow: hidden; }
    #moldagem .previa-palco > div.quadro { border-color: var(--viva); color: var(--viva);
                                           background: color-mix(in srgb, var(--viva) 12%, var(--caixa)); }
    #moldagem .arranjos { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
    #moldagem .numeros { display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
                         margin-bottom: 8px; }
    #moldagem .numeros label { color: var(--fraco); font-size: 12px; font-weight: 600;
                               text-transform: uppercase; letter-spacing: .5px; }
    #moldagem .so-neste-jogo { display: flex; align-items: center; gap: 8px;
                               margin-bottom: 12px; color: var(--fraco); font-size: 12px;
                               font-weight: 600; text-transform: uppercase;
                               letter-spacing: .5px; }
    input.numero { width: 100%; background: var(--caixa-2); color: var(--texto);
                   border: 1px solid var(--fio-forte); border-radius: 999px;
                   padding: 6px 12px; font: inherit; font-weight: 700;
                   font-variant-numeric: tabular-nums; }
    #palco { width: 100%; border-radius: 12px; display: none; margin-top: 8px; }
```

No `<aside>`, **antes** do cartão do RENDER FINAL:

```html
    <div class="cartao" id="moldagem">
      <div class="rotulo">moldagem <span class="aviso" id="desvio"></span></div>
      <div class="previa-palco" id="previa-palco"></div>
      <div class="arranjos" id="arranjos"></div>
      <div class="numeros">
        <label>escala
          <input type="number" id="escala" class="numero" min="0.6" max="1" step="0.05">
        </label>
        <label>deslocamento
          <input type="number" id="deslocamento" class="numero" min="-0.15" max="0.15" step="0.01">
        </label>
      </div>
      <label class="so-neste-jogo">
        <input type="checkbox" id="so-neste-jogo"> só neste jogo
      </label>
      <input type="text" id="youtube" placeholder="@ do YouTube">
      <input type="text" id="instagram" placeholder="@ do Instagram">
      <input type="text" id="tiktok" placeholder="@ do TikTok">
      <button class="abrir" id="botao-palco">CONFERIR PALCO</button>
      <img id="palco" alt="palco do canal">
      <p class="recado" id="recado-moldagem"></p>
    </div>
```

No cartão do RENDER FINAL, depois do `<p class="recado" id="recado-render">`:

```html
      <button class="abrir" id="abrir-pasta" style="display:none">ABRIR A PASTA</button>
```

- [x] **Step 7: O JS do cartão**

No `<script>`, depois de `desenharGol`:

```js
function desenharMoldagem(dados) {
  const arranjos = $("arranjos");
  arranjos.innerHTML = "";
  for (const nome of dados.arranjos) {
    const botao = document.createElement("button");
    botao.textContent = nome.toUpperCase();
    botao.classList.toggle("ativo", nome === dados.moldagem.arranjo);
    botao.onclick = () => mandarMoldagem({ arranjo: nome });
    arranjos.append(botao);
  }
  $("escala").value = dados.moldagem.escala;
  $("deslocamento").value = dados.moldagem.deslocamento;
  // Sair do padrão do canal é permitido, mas nunca por acidente: a tela marca.
  $("desvio").textContent = dados.fora_do_padrao ? "fora do padrão do canal" : "";
  $("so-neste-jogo").checked = dados.fora_do_padrao;
  const redes = (dados.identidade || {}).redes || {};
  for (const rede of ["youtube", "instagram", "tiktok"]) {
    $(rede).value = redes[rede] || "";
  }
  if (dados.recado_da_moldagem) {
    avisar("recado-moldagem", dados.recado_da_moldagem, "erro");
  } else if (!dados.palco_desenha.length) {
    avisar("recado-moldagem", "sem arte, logo ou @: o vídeo sai como hoje");
  } else {
    avisar("recado-moldagem", `o palco desenha: ${dados.palco_desenha.join(", ")}`);
  }
  desenharPreviaDoPalco(dados.molde);
}

function desenharPreviaDoPalco(molde) {
  const tela = $("previa-palco");
  tela.innerHTML = "";
  tela.style.aspectRatio = `${molde.largura} / ${molde.altura}`;
  for (const caixa of molde.camadas) {
    if (caixa.nome === "fundo") continue;
    const bloco = document.createElement("div");
    bloco.className = caixa.nome;
    bloco.style.left = `${(caixa.esquerda / molde.largura) * 100}%`;
    bloco.style.top = `${(caixa.topo / molde.altura) * 100}%`;
    bloco.style.width = `${(caixa.largura / molde.largura) * 100}%`;
    bloco.style.height = `${(caixa.altura / molde.altura) * 100}%`;
    bloco.textContent = caixa.nome === "quadro"
      ? `${caixa.largura}×${caixa.altura}` : caixa.nome;
    tela.append(bloco);
  }
}

const mandarMoldagem = (campos) => mandar("/api/moldagem", {
  ...campos, so_neste_jogo: $("so-neste-jogo").checked,
}, "recado-moldagem");
```

Em `desenhar(dados)`, antes de `mostrarRender(dados.render)`:

```js
  desenharMoldagem(dados);
```

Em `mostrarRender`, troque o ramo do vídeo pronto — o caminho como texto era o que o dono não conseguia abrir:

```js
  $("abrir-pasta").style.display = estado.saida ? "block" : "none";
  if (estado.rodando) {
    avisar("recado-render", `rodando: ${estado.mensagem || "…"}`);
    vigiar();
  } else if (estado.saida) {
    // O caminho vai no título do botão, e não como texto para copiar: o nome do
    // jogo tem espaços e, colado sem aspas, o Windows não encontra.
    $("abrir-pasta").title = estado.saida;
    avisar("recado-render", "pronto — abra a pasta para ver o vídeo", "ok");
  } else {
    avisar("recado-render", estado.mensagem || "fila: nada rodando");
  }
```

E os ganchos, junto dos outros, antes da última linha do arquivo:

```js
$("escala").onchange = () => mandarMoldagem({ escala: Number($("escala").value) });
$("deslocamento").onchange = () =>
  mandarMoldagem({ deslocamento: Number($("deslocamento").value) });
// Grava ao sair do campo, e não a cada tecla: uma escrita por @ escrito.
const gravarRedes = () => mandar("/api/identidade", {
  redes: {
    youtube: $("youtube").value.trim(),
    instagram: $("instagram").value.trim(),
    tiktok: $("tiktok").value.trim(),
  },
}, "recado-moldagem");
for (const rede of ["youtube", "instagram", "tiktok"]) $(rede).onchange = gravarRedes;

$("botao-palco").onclick = async () => {
  $("botao-palco").disabled = true;
  avisar("recado-moldagem", "desenhando o palco…");
  try {
    const resposta = await pedir("/api/palco", {});
    if (!resposta.arquivo) {
      $("palco").style.display = "none";
      avisar("recado-moldagem", resposta.recado);
    } else {
      $("palco").src = resposta.arquivo;
      $("palco").style.display = "block";
      avisar("recado-moldagem",
             resposta.recado || "palco pronto — confira antes do render", "ok");
    }
  } catch (erro) {
    avisar("recado-moldagem", erro.message, "erro");
  }
  $("botao-palco").disabled = false;
};

$("abrir-pasta").onclick = async () => {
  try {
    await pedir("/api/abrir-pasta", {});
  } catch (erro) {
    avisar("recado-render", erro.message, "erro");
  }
};
```

- [x] **Step 8: Rodar os testes da página e do design**

Run: `python -m pytest testes/test_painel_edicao.py testes/test_design.py -v`
Expected: todos PASSED. Se `test_design.py` reprovar, o conserto é na CSS que você acabou de escrever: raio fora da escala 8/12/999, cor crua fora do `:root`, sombra, gradiente, ou um `input` que não ficou pílula.

- [x] **Step 9: Um parágrafo no DESIGN.md**

Acrescente ao `DESIGN.md`:

```markdown
## O cartão MOLDAGEM

Fica no `aside` da `edicao.html`, entre a capa e o RENDER FINAL — depois de
escolher os clipes, antes de gerar o vídeo.

A prévia do palco é um retângulo `16/9` em `--caixa-2` com uma caixa
absolutamente posicionada por camada, em porcentagem: a janela da reação em
`--viva` com a tinta de estado a 12%, a logo e a barra em `--fio-forte` com
rótulo em `--fraco`. As medidas vêm do `molde.para_pagina`, as mesmas que o
ffmpeg obedece — nenhuma constante de geometria mora no HTML.

Os arranjos são pílulas comuns com `.ativo` no escolhido; a pílula preta da tela
continua sendo uma só, o RENDER FINAL. `input.numero` é a pílula dos dois
ajustes, com `tabular-nums` porque são números que se comparam.
```

- [x] **Step 10: Rodar a bateria inteira**

Run: `python -m pytest`
Expected: nenhum falho.

- [x] **Step 11: Commit**

```bash
git add painel/edicao.py painel/edicao.html DESIGN.md testes/test_painel_edicao.py
git commit -m "painel: o cartao MOLDAGEM e o botao que abre a pasta do video"
```

---

### Task 7: Os ajustes de qualidade

Passo 6 da seção 10. Dois números, medidos no jogo de 03/09, e a documentação que os explica.

**Files:**
- Modify: `nucleo/cortador.py` (`comando_corte`: `crf 20` → `crf 16`)
- Modify: `nucleo/estudio.py` (`_VIDEO_FINAL`: `veryfast`/`crf 20` → `slow`/`crf 18`)
- Modify: `AGENTS.md`, `README.md`
- Test: `testes/test_cortador.py`, `testes/test_estudio.py`

**Interfaces:**
- Consumes: nada das tarefas anteriores — é independente e pode ser revisada sozinha.
- Produces: nenhuma função nova.

- [x] **Step 1: Escrever os testes**

Acrescente a `testes/test_cortador.py`. A ordem dos argumentos é a que os testes vizinhos já usam — `comando_corte(fonte, inicio, duracao, saida, ffmpeg)`:

```python
def test_o_clipe_intermediario_nao_e_espremido(tmp_path: Path):
    """O corte sai a 1,22 Mbps de uma fonte de 2,27, e nao volta mais.

    Medido no jogo de 03/09: 46% perdidos antes de a montagem comecar. O clipe e
    descartavel - existe para revisao e para a montagem consumir - entao
    comprimi-lo e a perda mais barata de evitar que existe. O preco e o dobro de
    disco, temporario.
    """
    comando = cortador.comando_corte(
        tmp_path / "bruto.ts", 10.0, 60.0, tmp_path / "clipe.mp4", "ffmpeg.exe"
    )

    assert comando[comando.index("-crf") + 1] == "16"
```

Acrescente a `testes/test_estudio.py`:

```python
def test_o_video_final_nao_e_comprimido_a_toa():
    """A compilacao sai UMA vez por jogo e vai para o YouTube, que recodifica.

    `veryfast`/`crf 20` economizava minutos numa etapa que roda uma vez e gasta
    banda para sempre.
    """
    argumentos = estudio._VIDEO_FINAL

    assert argumentos[argumentos.index("-preset") + 1] == "slow"
    assert argumentos[argumentos.index("-crf") + 1] == "18"


def test_a_previa_continua_rapida_e_descartavel(tmp_path: Path):
    """O ajuste de qualidade e do CORTE e do FINAL - a previa mede relogio."""
    comando = estudio.comando_previa(
        tmp_path / "clipe.mp4", {"de": 10.0, "ate": 70.0},
        tmp_path / "previa.mp4", "ffmpeg.exe",
    )

    assert "ultrafast" in comando
    assert comando[comando.index("-crf") + 1] == "30"
```

- [x] **Step 2: Rodar e ver falhar**

Run: `python -m pytest testes/test_cortador.py -k espremido testes/test_estudio.py -k comprimido -v`
Expected: FAIL com `AssertionError: assert '20' == '16'`

- [x] **Step 3: Trocar os dois números**

Em `nucleo/cortador.py`, dentro de `comando_corte`, acrescente ao comentário que já existe e troque o valor:

```python
    # Recodifica de proposito: com -c copy o corte pula para o keyframe anterior
    # e a reacao comeca fora de hora. Sao 20 segundos, custa quase nada.
    #
    # `crf 16` e nao 20: medido em 03/09, o clipe saia a 1,22 Mbps de uma fonte
    # de 2,27 - 46% perdidos antes de a montagem comecar, e nao volta. O clipe e
    # descartavel e mora no cache do jogo; o dobro de disco por algumas horas e
    # mais barato do que perder metade da imagem para sempre.
```
```python
        "-crf",
        "16",
```

Em `nucleo/estudio.py`, troque `_VIDEO_FINAL`:

```python
# `slow`/`crf 18` e nao `veryfast`/`crf 20`: esta etapa roda UMA vez por jogo e
# produz o arquivo que sobe para o YouTube, que recodifica de novo por cima.
# Alguns minutos a mais de CPU aqui valem mais do que bitrate economizado no
# unico lugar onde ele nao volta.
_VIDEO_FINAL = [
    "-c:v", "libx264", "-preset", "slow", "-crf", "18",
    "-pix_fmt", "yuv420p", "-r", str(molde.FPS),
]
```

- [x] **Step 4: Rodar e ver passar**

Run: `python -m pytest testes/test_cortador.py testes/test_estudio.py -v`
Expected: todos PASSED

- [x] **Step 5: Documentar o que passou a existir**

Em `AGENTS.md`, na seção **"Onde começar"**, depois do item 3:

```markdown
4. `docs/superpowers/specs/2026-09-05-palco-e-identidade-do-canal-design.md` — o
   palco: como o vídeo ganha a cara do canal.
5. `docs/superpowers/plans/2026-09-05-palco-e-identidade-do-canal-plan.md` — as
   tarefas do palco, em ordem.
```

E na seção **"O que não fazer"**:

```markdown
- Voltar `drawtext` ao molde. O cenário pode ter letra — os @s das redes, na faixa
  que sobra —, mas ela é desenhada com PIL num PNG, fora do ffmpeg. Sobre a cena
  não vai letra nenhuma: nem placar, nem cartela, nem nome de canal.
- Passar de `escala 1,00` nos arranjos de palco. A fonte é 720p e a janela já é
  1280×720 cravada nessa escala; acima disso o ffmpeg volta a esticar.
```

Em `README.md`, na seção **"Configuração"**, depois do parágrafo do `config.json`:

```markdown
Copie `dados/identidade.exemplo.json` para `dados/identidade.json` para vestir os
vídeos com a marca do canal: arte de fundo, logo, os @s das redes e o arranjo do
palco. **Campo vazio é camada que não existe** — com o arquivo recém-criado o
vídeo sai exatamente como antes, e cada campo preenchido acrescenta uma camada.
Os ajustes ficam no cartão MOLDAGEM do estúdio, que também gera o PNG do palco
para conferir antes de renderizar. O arquivo pessoal não entra no Git; os ícones
das redes, em `dados/icones/`, entram.
```

- [x] **Step 6: Rodar a bateria inteira**

Run: `python -m pytest`
Expected: nenhum falho.

- [x] **Step 7: Commit**

```bash
git add nucleo/cortador.py nucleo/estudio.py AGENTS.md README.md testes/test_cortador.py testes/test_estudio.py
git commit -m "qualidade: clipe em crf 16 e compilacao em slow/crf 18"
```

---

## Prova no jogo de verdade (depois da Task 7)

O plano acima é testado por bateria; o desenho é sobre estética, e estética não se prova em `pytest`. Antes de dizer que funcionou, com um jogo já gravado na biblioteca:

1. Abra o estúdio (`4 - ESTUDIO.bat`), escolha `palco-alto` e clique **CONFERIR PALCO**. Sem arte nenhuma, tem que dizer que não há o que desenhar.
2. Ponha um PNG de 1920×1080 qualquer em `arte_de_fundo` e confira de novo: a arte aparece inteira, sem deformar.
3. Escreva um @ no YouTube e confira: a barra aparece no alto à direita, sem tocar a janela.
4. **RENDER FINAL** e abra o mp4. O que se mede: a janela tem 1280×720 dentro de um quadro de 1920×1080 (confira com `ffprobe`), e a imagem dentro da janela está mais nítida do que a do compilado anterior.
5. Confirme que o botão **ABRIR A PASTA** abre a pasta com o vídeo selecionado — é o defeito de 05/09.

Se qualquer um dos cinco falhar, o conserto é código, não documentação.
