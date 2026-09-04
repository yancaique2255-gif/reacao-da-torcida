---
version: 1
name: reacao-da-torcida-video
base: https://getdesign.md/ollama/design-md
description: |
  O produto publicado - o video, a cartela e a capa - vestido com o sistema da
  Ollama: superficie chapada sem degrade nenhum, estrutura por fio de cabelo,
  pilula para tudo o que e etiqueta, e a tipografia do sistema em tres papeis
  (display, sans, mono). A unica inversao de superficie, aquele "olhe aqui" que
  a Ollama gasta uma vez por pagina, aqui e a propria tela: o fundo e a cor do
  time que perdeu, e todo o cromado por cima dele e pilula branca com texto
  preto. Nada levanta, nada flutua, nada tem sombra.

# A cor do fundo NAO mora aqui: ela e a do time que perdeu, e sai do
# dados/times.json. O que mora aqui e o cromado que vai por cima dela.
colors:
  canvas: "#ffffff"
  ink: "black"
  on-dark: "white"
  on-dark-mute: "white@0.72"
  hairline: "white@0.22"
  hairline-strong: "#d4d4d4"

typography:
  display: bahnschrift.ttf
  sans: segoeuib.ttf
  mono: consolab.ttf

rounded:
  lg: 0.0125
  full: metade da altura da camada

spacing:
  recuo: 0.04

molde:
  deitado:
    fundo: 0.0 0.0 1.0 1.0
    quadro: 0.05 0.05 0.9 0.9
    etiqueta: 0.09 0.804 0.34 0.075
    torcida: 0.442 0.804 0.24 0.075
    placar: 0.76 0.121 0.15 0.075
    cartela: 0.0 0.0 1.0 1.0
    cartela-marca: 0.09 0.315 0.125 0.075
    cartela-titulo: 0.09 0.425 0.82 0.13
    cartela-regra: 0.09 0.6 0.5 0.002778
    cartela-meta: 0.09 0.635 0.82 0.05
  em-pe:
    fundo: 0.0 0.0 1.0 1.0
    quadro: 0.0 0.25 1.0 0.316667
    etiqueta: 0.06 0.6 0.62 0.048
    torcida: 0.06 0.658 0.5 0.038
    placar: 0.06 0.075 0.42 0.048
    cartela: 0.0 0.0 1.0 1.0
    cartela-marca: 0.06 0.36 0.24 0.042
    cartela-titulo: 0.06 0.425 0.88 0.05
    cartela-regra: 0.06 0.5 0.5 0.0015625
    cartela-meta: 0.06 0.525 0.88 0.03

capa:
  tamanho: 1280 720
  regiao: 40 232 1200 384
  vao: 12
---

# DESIGN DO VÍDEO — REAÇÃO DA TORCIDA

O `DESIGN.md` da raiz cobre as **telas do painel**. Este cobre o **produto
publicado**: o vídeo longo, o curto, a cartela que abre cada gol e a capa do
YouTube. São coisas diferentes e não se misturam — o painel é ferramenta de
trabalho num quarto escuro, o vídeo é o que o público vê no celular.

**Base:** <https://getdesign.md/ollama/design-md>. Este documento é a tradução
daquele sistema para uma superfície que não é uma página web: 1920×1080 a 30
quadros, sem interação, sem hover, sem responsivo — só dois formatos fixos.

**Onde isto vive em código:** `nucleo/molde.py` (a geometria, em coordenadas de
0 a 1), `nucleo/estudio.py` (os textos e as peças) e `nucleo/capa.py` (a capa).
A regra dura do molde continua valendo: **a geometria mora no `molde.py` e os
dois renderizadores saem dela** — `para_ffmpeg` para o vídeo, `para_pagina` para
a prévia em CSS. O `testes/test_molde.py` lê a geometria de volta do
`filter_complex`, como o ffmpeg leria, e compara camada por camada com o que a
página recebe. Mexer num lado só reprova a bateria.

---

## 1. Por que este sistema, e não outro

O vídeo estava com cara de template: degradê vermelho liso de cima a baixo,
Arial do Windows em tudo, tarja preta translúcida atrás do nome do canal,
cartela escrita só `GOL 3` no meio da tela e capa com dois buracos.

O sistema da Ollama é o antídoto exato disso. Ele é, nas palavras do próprio
documento, "a superfície de marketing mais agressivamente sub-desenhada do
espaço de ferramentas de IA, e esse é todo o ponto": tela de papel chapada,
zero degradê, zero sombra, estrutura por fio de 1 px, e **uma única inversão de
superfície por página** — o cartão escuro do plano "Max", que é o único "olhe
aqui" de todo o site.

Num vídeo de reação de torcida essa inversão já existe e é obrigatória: **o
fundo é a cor do time que perdeu**. Sem esse fundo, um clipe de webcam em tela
cheia continua sendo um clipe de webcam. Então a tradução é direta:

| No sistema da Ollama | Aqui |
| --- | --- |
| `{colors.canvas}` — a folha de papel branca | O cromado: pílula, régua, moldura |
| `{colors.surface-dark}` — a única superfície invertida | **A tela inteira**, na cor do time |
| `{component.button-pill-on-dark}` — pílula branca sobre escuro | Toda etiqueta do vídeo |
| `{colors.on-dark}` / `{colors.on-dark-mute}` | O texto da cartela |
| `{colors.hairline}` — o fio de 1 px | A borda do quadro e a régua da cartela |
| `{component.command-tag}` — chip de comando em mono | Placar, torcida, marca do gol |

O que o sistema **proíbe** é exatamente o que estava errado:

- *"Don't introduce gradients, drop shadows, or atmospheric backgrounds."* →
  o `vignette=PI/4` sai do fundo e da cartela. A cor do time fica chapada.
- *"Don't lift cards with shadows. Use a 1px hairline border."* → a moldura do
  quadro deixa de ser branco quase sólido e passa a ser `{colors.hairline}` —
  fio, e não caixilho.
- *"Don't soften pills or sharpen cards."* → etiqueta, torcida e placar viram
  `{rounded.full}`; o quadro fica em `{rounded.lg}`. Nada de meio-termo.
- *"Don't replace ui-sans-serif with a branded display body face."* → o texto
  miúdo é a sans do sistema, que no Windows é a Segoe UI.
- *"Code is a first-class component."* → todo número e toda etiqueta técnica
  (placar, torcida, liga, data) vão em mono.

## 2. Cor

`{colors.canvas}` e `{colors.ink}` são o par de todo o cromado: pílula branca,
texto preto dentro. Não existe terceira cor de marca — a cor de marca é a do
time, e ela é o **fundo**, nunca o texto.

| Papel | Valor | Onde |
| --- | --- | --- |
| `{colors.canvas}` | `#ffffff` | Fundo da pílula (etiqueta, torcida, placar, marca da cartela) |
| `{colors.ink}` | `black` | Texto dentro da pílula |
| `{colors.on-dark}` | `white` | Título da cartela, sobre a cor do time |
| `{colors.on-dark-mute}` | `white@0.72` | Linha de meta da cartela |
| `{colors.hairline}` | `white@0.22` | Borda do quadro, régua da cartela |
| `{colors.hairline-strong}` | `#d4d4d4` | O fio de contorno de toda pílula |
| fundo | `dados/times.json` | A tela inteira |

**A cor do fundo não está neste documento de propósito.** Ela é um fato do jogo
e mora no cadastro dos times; escrevê-la aqui criaria a segunda cópia que o
`DESIGN.md` do painel já aprendeu a não ter.

Sem semântica de erro/sucesso/aviso: o vídeo não tem estado, não tem validação
e não tem banner. Isso é o próprio sistema de origem — *"the system has
effectively no error/success/warning palette"*.

## 3. Tipografia

Três papéis, e nenhum deles é uma fonte de marca. É a decisão de **não ter uma
decisão de tipografia**, que é o que faz o sistema da Ollama parecer nativo.

| Papel | Arquivo | Substitui | Onde |
| --- | --- | --- | --- |
| `display` | `bahnschrift.ttf` | SF Pro Rounded | Título da cartela, e só ele |
| `sans` | `segoeuib.ttf` | `ui-sans-serif` | Nome do canal, frase da capa |
| `mono` | `consolab.ttf` | `ui-monospace` | Placar, torcida, marca do gol, meta |

Duas das três escolhas são **exatamente** o que o documento da Ollama manda:
`ui-sans-serif` no Windows *é* a Segoe UI, e a Consolas está nomeada na própria
cadeia de fallback do `ui-monospace` (*"SFMono-Regular → Menlo → Monaco →
Consolas"*). Não são substitutos: são o valor do token nesta máquina.

O `display` é a única troca deliberada. A SF Pro Rounded é licenciada pela
Apple, e o documento aponta a **Nunito** como substituto aberto — que não está
instalada aqui, e baixar fonte para dentro do repositório é dependência nova
por decoração. Ficou a **Bahnschrift** (a DIN 1451 que acompanha o Windows 10),
que é geométrica como a SF Pro Rounded mas não é arredondada. A troca é
proposital e melhora o produto: DIN é a letra de placar de estádio e de placa
de sinalização, e este vídeo é de futebol. O documento de origem declara a
mesma tolerância para si mesmo — *"Ollama explicitly accepts that the heading
face will look slightly different on Windows/Linux"*.

A hierarquia é comprimida como a de lá (36 → 30 → 24 → 20 → 16 numa coluna de
720 px), traduzida para fração da **altura** da tela:

| Camada | Fração (deitado / em pé) | Deitado | Em pé | Papel |
| --- | --- | --- | --- | --- |
| `cartela-titulo` | 0,090 / 0,028 | 97 px | 54 px | O único display do sistema |
| `placar` | 0,050 / 0,032 | 54 px | 61 px | Mono |
| `etiqueta` | 0,042 / 0,024 | 45 px | 46 px | Sans |
| `cartela-marca` | 0,038 / 0,021 | 41 px | 40 px | Mono |
| `torcida` | 0,026 / 0,016 | 28 px | 31 px | Mono |
| `cartela-meta` | 0,028 / 0,016 | 30 px | 31 px | Mono |

**O `drawtext` do ffmpeg não sabe encolher texto: o que não cabe vaza por cima
do vídeo.** Quem garante que cabe é o `molde.cabe`, e o `test_molde.py` cobra
isso para o nome de canal mais longo, para a torcida mais longa e para o pior
placar possível — em cada camada e em cada formato. É por isso que os tamanhos
acima são o que são: são o maior corpo em que o pior texto ainda cabe.

## 4. Forma

Duas formas, como no sistema de origem — *"the dominant shape vocabulary is
just two values"*.

| Token | Valor | Onde |
| --- | --- | --- |
| `{rounded.full}` | metade da altura da camada | Etiqueta, torcida, placar, marca da cartela |
| `{rounded.lg}` | 0,0125 da largura (24 px no deitado) | O quadro do clipe, e as fotos da capa |

Canto arredondado no ffmpeg puro daria um `geq` caro e ilegível. Os cantos do
quadro e as pílulas saem do Pillow, uma imagem por formato, feita uma vez e
reaproveitada — o mesmo caminho que os cantos do quadro já usavam. **A pílula é
só a forma: o texto vai por cima, com `drawtext`, nas coordenadas que saem do
molde.** É o que mantém a geometria num lugar só e legível de volta a partir do
`filter_complex`.

O fio (`{colors.hairline}`) tem **3 px** no deitado e 2 px no em pé, e não 1 px:
1 px desaparece na compressão H.264 do YouTube. É a única medida deste
documento que não é a do sistema de origem, e o motivo é o meio, não o gosto.

## 5. Espaço

`{spacing.recuo}` = **0,04 da largura da tela** (77 px no deitado, 43 px no em
pé). É o recuo de toda pílula para dentro da borda do quadro, nos quatro lados,
e é o mesmo número que posiciona o trilho esquerdo da cartela.

Um número só, aplicado em tudo — o equivalente ao `{spacing.section}` de 88 px
que a Ollama usa "liberalmente" entre todos os blocos da página. O ar é o
layout: a cartela não tem caixa, não tem divisória decorativa e não tem coluna;
tem uma régua de fio e ar.

## 6. As três peças

### 6.1 O molde do clipe

```
+-----------------------------------------------------------+  cor do time, chapada
|   +-----------------------------------------------+       |  quadro, rounded.lg
|   |                                    ( 3 x 0 )  |       |  pilula mono, topo-direita
|   |                                               |       |
|   |                    a live                     |       |
|   |                                               |       |
|   |  ( BALDASSO TV )  ( TORCIDA DO INTER )        |       |  pilula sans + pilula mono
|   +-----------------------------------------------+       |  borda: fio white@0.22
+-----------------------------------------------------------+
```

O nome do canal deixa de dividir tarja com a torcida: são **duas pílulas lado a
lado**, cada uma na sua caixa e na sua letra, como uma fileira de
`{component.command-tag}`. No em pé elas empilham, porque 1080 px de largura não
comportam as duas em linha.

A tarja `black@0.55` que ficava atrás das duas sai inteira. Ela existia para dar
legibilidade sobre qualquer cena — a pílula branca faz o mesmo trabalho e é
forma, não fundo sujo.

### 6.2 A cartela

Saía `GOL 3` centralizado no meio da tela. Passa a ser um bloco alinhado à
esquerda, no trilho de `{spacing.recuo}`, lido de cima para baixo como uma seção
de documento — que é a ideia inteira do sistema de origem (*"the system is the
documentation, and the documentation is the system"*).

```
+-----------------------------------------------------------+
|                                                           |
|   ( GOL 03 )                                              |  pilula mono
|                                                           |
|   GREMIO 3 x 0 INTER                                      |  display, on-dark
|   -------------------------                               |  regua de fio
|   COPA DO BRASIL - 03/09/2026                             |  mono, on-dark-mute
|                                                           |
+-----------------------------------------------------------+
```

Quatro camadas, quatro papéis: **onde estamos** (a marca do gol), **o que
mudou** (o placar por extenso, que é a informação do lance), **a régua** e **de
que jogo se trata**.

O placar da cartela usa o nome `curto` do `dados/times.json` (`GRÊMIO`, `INTER`)
e não o nome por extenso: `PALMEIRAS 10 x 10 PALMEIRAS`, o pior caso possível, é
o que define o corpo do display. Sem placar anotado, a cartela mostra os dois
times sem número — **dizer o que se sabe, e nunca inventar um número na tela**.

### 6.3 A capa

1280×720, a mesma gramática, com uma diferença: aqui existe foto (os rostos
extraídos dos clipes), e a Ollama não tem fotografia nenhuma. A regra que se
importa é a de geometria — foto em `{rounded.lg}` com fio, e nunca levantada por
sombra.

```
+-----------------------------------------------------------+  cor do time, chapada
|  REACOES                                       ( 3 x 1 )  |  sans + pilula mono
|  COLORADAS                                                |  display
|  +-----------------+--------------+--------------+        |
|  |                 |              |              |        |  rostos: 1 a 5,
|  |      rosto      |    rosto     |    rosto     |        |  sem buraco nunca
|  |                 |              |              |        |
|  +-----------------+--------------+--------------+        |
|  ( VERGONHA! INTER ELIMINADO EM CASA )                    |  pilula sans
+-----------------------------------------------------------+
```

O degradê preto de baixo para cima **sai**. Ele existia para dar legibilidade à
frase por cima da foto; a frase passa a morar numa pílula branca abaixo da faixa
de rostos, onde não há foto para competir. É a mesma troca do vídeo: forma em
vez de fundo sujo.

A grade de rostos se deriva de uma região só (`capa.regiao`) e se adapta a 1, 2,
3, 4 ou 5 — quantidade ímpar ganha um rosto grande à esquerda, quantidade par
divide igual. O layout fixo de 1 grande + 4 pequenos deixava um quadrante vazio
quando entravam três canais, que é como a capa de 03/09 saiu.

## 7. Pode e não pode

### Pode
- Superfície chapada. A cor do time cobre a tela e não tem degradê, vinheta nem
  atmosfera.
- Pílula branca com texto preto para toda etiqueta. É o único cromado do
  sistema.
- Mono para todo número e toda etiqueta técnica.
- `display` só no título da cartela e no adjetivo da capa. Um por peça.
- Fio de cabelo para separar: régua, borda de quadro, borda de foto.

### Não pode
- Degradê, vinheta, sombra, brilho, atmosfera. Nada.
- Cor de marca no texto. O texto é branco sobre a cor do time, ou preto sobre a
  pílula. Não há terceira opção.
- Caixa translúcida atrás de texto. Se precisa de fundo, é pílula branca.
- Fonte de marca no texto miúdo. Abaixo do título da cartela é a sans do
  sistema.
- Pílula com canto médio, ou quadro com canto de pílula. As duas formas são
  fechadas.
- Número inventado. Placar que não foi anotado não aparece.

## 8. Como mexer nisto

1. **A geometria só se mexe no `molde.py`**, em fração de 0 a 1. `para_ffmpeg` e
   `para_pagina` saem da mesma declaração, e o `test_molde.py` compara as duas
   camada por camada. Editar um lado só reprova a bateria.
2. **Este documento não pode mentir.** O `testes/test_design_do_video.py` lê o
   bloco de metadados do topo daqui e compara com o que o `molde.py` e o
   `capa.py` declaram. Documento que mente é pior que documento que falta.
3. **Texto novo pede prova de que cabe.** Toda camada de texto tem um teste com
   o pior texto possível. O `drawtext` não encolhe nada.
4. Antes de somar token, pergunte se a peça nova não se escreve com pílula,
   quadro chapado e régua de fio. O sistema quase nunca precisa de token novo —
   é a força dele.
