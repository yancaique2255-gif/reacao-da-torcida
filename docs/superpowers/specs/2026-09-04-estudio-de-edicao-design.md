# Estúdio de edição — desenho

Data: 2026-09-04
Estado: **passos 1 a 5 da seção 14 aplicados** (`torcida` obrigatória;
`perdedor` e `melhor`; `molde` e `receita`; `estudio`; painel 8772). O vídeo
longo já sai. Do passo 6 em diante, nada deste documento está no código ainda.

O par deste arquivo é o `DESIGN.md` (como a tela se parece) e o `AGENTS.md`
(como o código se escreve). Este aqui diz **o que o estúdio faz**.

---

## 1. O que é

Hoje a esteira termina com clipes soltos numa pasta. O estúdio de edição pega
esses clipes e entrega **um vídeo pronto para subir**, com a cara do canal, mais
a capa e o texto da publicação.

Duas peças saem de cada jogo:

| Peça | Formato | Duração | Onde vai |
| --- | --- | --- | --- |
| **Vídeo longo** | 16:9, 1920×1080 | 12 a 20 min | YouTube |
| **Vídeo curto** | 9:16, 1080×1920 | ~2 min, 20s por canal | Shorts, Reels, TikTok |

Mais **`capa.jpg`** e **`publicar.md`** (título, descrição, tags) na mesma pasta.

### O que NÃO é

- **Não tem quadro de reação.** O apresentador não entra nesta rodada. Foi
  decisão do operador e é o que mais separa este trabalho do canal de referência.
- **Não é um editor livre.** Não tem pista, não tem arrastar clipe pra qualquer
  lugar, não tem sobreposição arbitrária. O molde é fixo; o que você escolhe é
  o que entra, em que ordem e onde corta.
- **Não decide sozinho o que publicar.** Ele propõe; o operador confirma. Como
  no resto do projeto, quem manda é quem está olhando.

---

## 2. A regra editorial: só quem perdeu

Esta é a decisão que organiza tudo o mais, e ela não estava escrita em lugar
nenhum do projeto até agora.

**Gravamos os dois lados. Publicamos só o lado que perdeu.** O canal de
referência vive disso: "VAMOS RIR DO INTER". A graça é a reação de quem se
frustrou, e reação de vencedor não rende.

Então o estúdio precisa saber, para cada canal, **de que torcida ele é**. E
precisa saber quem perdeu.

### Quem perdeu sai do placar

O `catalogo.json` já guarda `partida.mandante` e `partida.visitante`, e a ESPN
já entrega o placar. Grêmio 3 x 1 Internacional → perdedor é o Internacional →
entram os canais com `torcida: "inter"`.

Três casos, e os três precisam de resposta:

| Caso | Regra |
| --- | --- |
| Um time perdeu | Entram os canais da torcida dele |
| Empate | Não há perdedor: o operador escolhe de que lado quer rir |
| Operador discorda | Ele troca no painel, e a escolha grava em disco na hora |

O padrão é o perdedor. A troca é sempre possível — é uma sugestão, não uma
trava.

### O buraco: metade dos canais não tem torcida

**Consertado em 04/09/2026** — o diagnóstico abaixo fica registrado porque é o
que motivou a mudança; o estado atual está no fim desta seção.

Conferi o jogo de ontem. Dos seis canais gravados, **três estão com `torcida`
em branco**:

```
bage-tv                  torcida: ''        <- em branco
baldasso-tv              torcida: ''        <- em branco, e é o principal canal do Inter
farid-germano-filho      torcida: 'inter'
gaucha-esportes          torcida: ''        <- em branco
paulo-brito              torcida: 'inter'
radio-imortal            torcida: 'gremio'
```

O `baldasso-tv` é o caso que dói: é o canal que o próprio vídeo de referência
credita como reação do Inter, e para nós ele é um canal sem torcida. Com a
regra editorial ligada, ele **ficaria de fora do vídeo** — o melhor material
perdido por um campo vazio.

Portanto, faz parte desta rodada:

1. `0 - CADASTRAR CANAIS` passa a **exigir** a torcida ao cadastrar. Sem ela não
   grava o canal.
2. O estúdio mostra, em vermelho, todo canal sem torcida, e deixa preencher ali
   mesmo. **Não some com ele da lista** — a regra do `DESIGN.md` seção 7 vale:
   o que está errado aparece marcado, não desaparece.
3. Um comando conserta os jogos velhos preenchendo o que faltar.

Os três já estão preenchidos: `bage-tv` gremio, `baldasso-tv` inter,
`gaucha-esportes` neutro. E `neutro` virou uma resposta por extenso — vazio
agora quer dizer só uma coisa, "ninguém preencheu", e é recusado no cadastro.

---

## 3. O molde

O molde é o formato do canal, e ele **não muda de jogo para jogo**. É o que faz
os vídeos parecerem da mesma casa.

### Camadas, de baixo para cima

1. **Fundo** — cor da torcida perdedora, em degradê radial escuro nas bordas,
   com o escudo do time em marca-d'água bem fraca. É o "fundo atrás" que o
   operador pediu: sem ele, um clipe de webcam em tela cheia é um clipe de
   webcam, não é um produto.
2. **Quadro do clipe** — o vídeo da reação, cantos arredondados, borda clara
   fina. Ocupa a maior parte da tela mas **deixa margem**, senão o fundo não
   aparece e a marca some.
3. **Etiqueta** — nome do canal e a torcida, canto inferior esquerdo.
4. **Placar** — escudos e o placar naquele momento do jogo, canto superior
   direito. O placar é o **do gol que está passando**, não o final: no gol 1 o
   quadro diz `1 x 0`.
5. **Cartela de gol** — 2 segundos anunciando `GOL 1 · GRÊMIO 1 x 0 INTER`
   antes da primeira reação de cada gol.

### Geometria

**Deitado (16:9), 1920×1080:**

```
┌──────────────────────────────────────────────────────────┐  fundo: cor do
│  ┌────────────────────────────────────────┐  ╔════════╗  │  time perdedor
│  │                                        │  ║ (esc)  ║  │
│  │                                        │  ║  1x0   ║  │  quadro: 1728×972
│  │            reação em vídeo             │  ╚════════╝  │  em x=96, y=54
│  │                                        │              │  (margem de 5%)
│  │                                        │              │
│  │  ┌───────────────────┐                 │              │  cantos 24px
│  │  │ BALDASSO TV       │                 │              │  borda 3px clara
│  │  │ torcida do INTER  │                 │              │
│  │  └───────────────────┘                 │              │
│  └────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────┘
```

**Em pé (9:16), 1080×1920:**

```
┌──────────────────┐
│   GRÊMIO 1x0     │   ← placar grande em cima
│   INTERNACIONAL  │
│                  │
│ ┌──────────────┐ │   quadro: 1080×608, colado na
│ │              │ │   largura, no terço de cima
│ │   reação     │ │
│ │              │ │
│ └──────────────┘ │
│                  │
│  BALDASSO TV     │   ← etiqueta grande embaixo,
│  torcida do INTER│     onde o dedo não tapa
│                  │
│      GOL 1       │
└──────────────────┘
```

### Uma declaração, dois renderizadores

Aqui está o ponto que decide se este painel é profissional ou é um brinquedo.

A prévia mora no navegador (HTML/CSS) e o vídeo final sai do ffmpeg. **São dois
renderizadores diferentes.** Se cada um tiver sua própria cópia da geometria,
eles divergem — e divergem justamente quando ninguém está olhando, que é
depois de alguém mexer num número num dos dois lados. Aí a prévia mente, e uma
prévia que mente é pior que não ter prévia.

A saída é declarar o molde **uma vez só**, em coordenadas normalizadas
(0 a 1), e gerar os dois a partir dela:

```
molde.camadas(formato)     -> [Camada(nome, x, y, largura, altura, ...), ...]
molde.para_ffmpeg(camadas) -> o filter_complex
molde.para_pagina(camadas) -> o JSON que a prévia usa pra posicionar em CSS
```

E um teste que **compara as duas saídas camada por camada**. Se alguém mexer
na geometria de um lado só, a bateria reprova. É o mesmo remédio que já usamos
para os tokens de cor das duas telas.

---

## 4. O cortador — a peça nova que o operador pediu

Os clipes têm cerca de **175 segundos cada**. Seis canais e quatro gols dão 70
minutos de material; só os canais do Inter dão 35. O vídeo longo tem que ter
entre 12 e 20 minutos. **Cortar não é enfeite do vídeo curto: é obrigatório
nos dois.**

O detector já faz metade do trabalho: `nucleo/detector.py` devolve o instante
em que a explosão começa e a força dela em decibéis. Esses números já estão
gravados em cada clipe do catálogo (`instante`, `confianca_db`, `tem_pico`).

Falta a outra metade: **dado um clipe e uma duração alvo, qual é a melhor
janela?**

### `nucleo/melhor.py`

```
janela(curva_db, quadro_s, duracao_alvo, tem_pico) -> (inicio, fim)
```

Duas estratégias, escolhidas pelo `tem_pico` que o detector já decidiu:

**Com pico** — a reação existe e sabemos onde. A janela é posicionada de modo
que o pico caia a **35% do começo dela**. Não no meio, e muito menos no
começo: você precisa ver a cara do sujeito *antes* da explosão, senão a
explosão não tem graça. Um terço de subida, dois terços de reação.

**Sem pico** — não houve grito. Aí a janela é a de **maior energia média**,
deslizando quadro a quadro. É o melhor palpite disponível, e o painel marca
esse clipe como fraco para o operador decidir se vale.

Nos dois casos a janela é presa dentro do clipe: nunca começa antes de zero,
nunca termina depois do fim.

### Por que isso é uma função pura

`janela` recebe uma curva de números e devolve dois números. Não abre vídeo,
não chama ffmpeg, não toca em disco. Dá para testar com curvas inventadas —
um pico no meio, um pico no começo, um clipe todo plano, um clipe mais curto
que a janela pedida — e cada caso vira um teste de duas linhas.

A curva vem do `detector.curva_db`, que já existe e já é testado.

### Onde entra em cada formato

| Formato | Duração por clipe | Quantos clipes |
| --- | --- | --- |
| Longo | 45 a 90s (o operador ajusta) | todos os escolhidos |
| Curto | **20s** | quantos couberem em ~2 min |

O corte que o cortador propõe é **um ponto de partida**, não uma sentença: ele
chega no painel como duas alças que o operador arrasta. É a diferença entre
uma máquina que ajuda e uma máquina que decide.

---

## 5. A receita

Tudo o que o operador escolhe mora num arquivo, na pasta do jogo:
**`receita.json`**.

```json
{
  "formato": "deitado",
  "torcida_alvo": "inter",
  "molde": { "margem": 0.05, "duracao_por_clipe": 60 },
  "itens": [
    { "gol": 1, "canal": "farid-germano-filho",
      "entra": true,  "de": 71.2, "ate": 131.2, "ordem": 1 },
    { "gol": 1, "canal": "paulo-brito",
      "entra": true,  "de": 88.0, "ate": 148.0, "ordem": 2 },
    { "gol": 1, "canal": "radio-imortal",
      "entra": false, "de": 0.0,  "ate": 60.0,  "ordem": 3 }
  ],
  "textos": {
    "titulo": "REAÇÕES dos COLORADOS - GRÊMIO 3x1 INTERNACIONAL - ...",
    "gancho": "ELIMINADO DA COPA DO BRASIL",
    "frase_da_capa": "VERGONHA! INTER ELIMINADO DA COPA DO BRASIL!"
  }
}
```

Três propriedades que ela precisa ter:

1. **Nasce sozinha.** Na primeira vez, é derivada do catálogo: entram os canais
   da torcida perdedora, na ordem da força da reação, com o corte que o
   cortador propôs. O operador abre o painel e já tem um vídeo montável.
2. **A escolha do operador ganha.** Recortar o jogo de novo não desfaz o que
   ele mexeu. O que ele tocou fica marcado como tocado.
3. **Grava na hora.** Cada clique escreve o arquivo antes de a tela mudar.
   Regra do `DESIGN.md` seção 7, e a mesma do catálogo.

Apagar a `receita.json` é seguro: ela volta ao padrão derivado. Não se perde
gravação, só se perde a edição.

---

## 6. O render

Esta é a parte onde a máquina manda, e a máquina é modesta: **Ryzen 5 5600G,
6 núcleos, sem placa de vídeo dedicada**. O `h264_amf` existe (a APU encoda),
mas a qualidade dele não serve para o arquivo final.

Um vídeo de 20 minutos em 1080p com sobreposições leva **minutos** de CPU
nesta máquina. Fingir que é instantâneo seria mentir para o operador, e o
`DESIGN.md` proíbe exatamente isso.

Três velocidades, de propósito:

| | O que faz | Quanto demora | Para quê |
| --- | --- | --- | --- |
| **Espiar** | um quadro parado, com todas as camadas | instantâneo | ver se a etiqueta cobriu o rosto |
| **Prévia** | 640×360, `h264_amf`, só o trecho que você está olhando | segundos | conferir movimento e som |
| **Final** | 1920×1080, `libx264`, o vídeo inteiro | minutos, em fila | subir |

### O cache por item é o que torna isso usável

Cada clipe vira um arquivo intermediário próprio, com nome derivado de um
**hash de tudo o que afeta a imagem dele**: arquivo de origem, corte, molde,
textos, formato. Mexer no item 5 não re-renderiza os itens 1 a 4 — só o 5, e
depois a emenda, que é cópia de fluxo e é instantânea.

O `montador.py` de hoje já monta por intermediários, mas **apaga a pasta
temporária no fim**. A mudança é guardar, com nome de hash, e limpar por
comando.

Custo: os intermediários são uma cópia inteira do vídeo, uns 1 a 2 GB por
jogo. Cabe, mas precisa de um `estudio limpar` e de um aviso no painel quando
passar de um teto.

### A fila

O render final roda em outro processo, com progresso. O painel pode ser
fechado e reaberto sem matar o render — o mesmo desenho do supervisor de
gravação, que já funciona assim. O estado da fila mora em disco, não na
página.

---

## 7. A capa

A capa é metade do clique no YouTube. Um vídeo bom com capa fraca rende menos
que um vídeo médio com capa forte, e por isso ela entra nesta rodada e não na
seguinte.

A anatomia foi tirada da capa do vídeo de referência do jogo de ontem:

```
┌────────────────────────────────────────────────┐
│ ┌──────────────────┐      (escudo A)  3x1      │
│ │ REAÇÕES          │      (escudo B)           │
│ │ COLORADAS        │                           │
│ └──────────────────┘   ┌───────┬───────┐       │
│   ┌────────────────┐   │ rosto │ rosto │       │
│   │                │   ├───────┼───────┤       │
│   │  rosto grande  │   │ rosto │ rosto │       │
│   │                │   └───────┴───────┘       │
│   └────────────────┘                           │
│  "VERGONHA! INTER ELIMINADO DA COPA DO BRASIL!"│
└────────────────────────────────────────────────┘
```

**Os rostos saem dos próprios clipes.** O quadro escolhido é o do instante do
pico — que é o momento em que a cara está mais expressiva, e é justamente o
número que o detector já guardou. O operador troca o quadro arrastando um
seletor, e a capa regera.

O resto (fundo, escudos, placar, título, frase) é composição.

**Ferramenta: Pillow**, que já está instalado (12.2.0) mas **não está no
`requisitos.txt`** — entra. Compor uma capa em camadas com PIL é direto;
fazer o mesmo com `drawtext` do ffmpeg é sofrimento e fica pior.

### A fonte

A capa e as etiquetas pedem uma condensada pesada. A máquina tem **só Impact,
Bahnschrift e Arial Bold** — nenhuma delas é a cara certa.

Então **entra uma fonte no repositório** (Anton ou Bebas Neue, as duas com
licença SIL Open Font, que permite redistribuir). Uma fonte que não carrega
deixa a tela em Times New Roman, e o `DESIGN.md` já cuida disso para as telas;
aqui vale para o vídeo.

---

## 8. A publicação

Esta parte sai quase de graça, porque **os dados já estão no disco**.

O `JOGO.md` já guarda, para cada live, o canal, a torcida e o link. A descrição
do canal de referência tem exatamente esse bloco:

```
Créditos do vídeo:
🔗 Baldasso TV https://www.youtube.com/@BaldassoTV
🔗 Gigante Colorado https://www.youtube.com/@gigantecoloradors
...
```

Ou seja: **o bloco de créditos é um `for` em cima do que a ficha já tem.**
Nada de novo precisa ser anotado.

O título segue um padrão rígido, tirado de vinte vídeos do canal:

```
REAÇÕES {TORCIDA} - {MANDANTE} {A}x{B} {VISITANTE} - {GANCHO} - VAMOS RIR DO {TIME}!
```

`{GANCHO}` é a única parte que muda de verdade: `ELIMINADO DA COPA DO BRASIL`,
`EMPATE FRUSTRANTE`, `OITAVO JOGO SEM VITÓRIA`. O painel oferece uma lista e o
operador escreve o dele.

Sai um **`publicar.md`** na pasta de saída, com título, descrição e tags,
pronto para copiar e colar. Não sobe nada sozinho: publicar é ação de fora, e
ação de fora se confirma.

### `dados/times.json`

Precisa de um dicionário por time: nome, apelido da torcida (`colorados`),
adjetivo da capa (`COLORADAS`), cor de fundo, arquivo do escudo. Começa com os
times que o operador grava e cresce conforme aparecem.

---

## 9. Os módulos

Módulos pequenos, cada um com um assunto, testáveis sem abrir vídeo — como o
resto do `nucleo/`.

| Módulo | Faz | Testável sem vídeo? |
| --- | --- | --- |
| `nucleo/melhor.py` | acha a melhor janela de N segundos | sim, curva inventada |
| `nucleo/molde.py` | declara as camadas; emite ffmpeg e CSS | sim, compara as duas saídas |
| `nucleo/receita.py` | deriva do catálogo, guarda a edição | sim |
| `nucleo/perdedor.py` | quem perdeu, quais canais entram | sim |
| `nucleo/capa.py` | compõe a capa com PIL | sim, confere tamanho e camadas |
| `nucleo/publicacao.py` | título, descrição, tags | sim, texto puro |
| `nucleo/estudio.py` | executa a receita, cache, fila | parcial, com `executar` falso |

O `montador.py` de hoje é absorvido pelo `estudio.py`. Ele já tem duas coisas
boas que ficam: o `loudnorm` em `-16 LUFS` (sem isso, um canal berra e o outro
sussurra na mesma compilação) e a emenda por `concat` com cópia de fluxo.

---

## 10. O painel

**Porta 8772, arquivo novo, ao lado do estúdio de hoje.**

Isso é deliberado. O estúdio da porta 8770 é o que o operador usa para
trabalhar. Reforma grande não se faz na ferramenta que está em uso — o novo
nasce ao lado, prova que funciona num jogo de verdade, e só então o velho sai.

Segue o `DESIGN.md`: os mesmos onze tokens, o mesmo escuro, estado repetido em
texto além da cor.

```
┌──────────────────────────────────────────────────────────────────────┐
│ GRÊMIO 3 x 1 INTERNACIONAL · Copa do Brasil · 03/09        [DEITADO] │
│ rindo do: INTERNACIONAL ▾          12:08 de vídeo · 12 clipes        │
├───────────────────────────────────┬──────────────────────────────────┤
│ GOL 1 · 1x0                       │                                  │
│  ☑ farid-germano-filho  15.2 dB   │        ESPIAR                    │
│    ├──[====|=========]──┤  60s    │   ┌────────────────────────┐     │
│  ☑ paulo-brito           7.8 dB   │   │                        │     │
│    ├────[====|======]───┤  60s    │   │   quadro com todas     │     │
│  ☐ baldasso-tv        sem torcida │   │   as camadas           │     │
│    └ preencher torcida ▾          │   │                        │     │
│                                   │   └────────────────────────┘     │
│ GOL 2 · 2x0                       │                                  │
│  ☑ paulo-brito          11.4 dB   │   [ PRÉVIA 640p ]  [ CAPA ]      │
│    ├──[===|========]────┤  60s    │                                  │
├───────────────────────────────────┴──────────────────────────────────┤
│  [ RENDER FINAL ]   fila: nada rodando         [ PUBLICAR.MD ]       │
└──────────────────────────────────────────────────────────────────────┘
```

O que cada coisa faz:

- **`☑`** — entra ou não. Grava na hora.
- **A barra** — o corte. As alças arrastam; o `|` é onde o detector achou o
  pico. Grava ao soltar.
- **`15.2 dB`** — a força da reação. Ordena a lista sozinha, do mais explosivo
  para o mais morno.
- **`sem torcida`** em vermelho — o canal aparece marcado, não some.
- **`rindo do: ▾`** — a torcida alvo, com o perdedor já escolhido.
- **`DEITADO`/`EM PÉ`** — troca o formato. A mesma receita, outro molde.

---

## 11. Testes

O projeto tem 327 testes e a regra é que defeito consertado vira teste. Os
novos:

- **`melhor`** — pico no meio, pico no começo, pico no fim, curva plana, clipe
  mais curto que a janela. A janela nunca sai do clipe.
- **`molde`** — ffmpeg e CSS concordam em toda camada, nos dois formatos. É o
  teste que impede a prévia de mentir.
- **`receita`** — deriva do catálogo; a edição do operador sobrevive a um novo
  corte; apagar volta ao padrão.
- **`perdedor`** — vitória do mandante, vitória do visitante, empate, e a troca
  manual.
- **`publicacao`** — o título segue o padrão; o bloco de créditos traz todas as
  lives com link.
- **`estudio`** — o cache reaproveita item não mexido e refaz o mexido.

---

## 12. O que fica de fora desta rodada

Escrito para não virar surpresa depois:

- **Quadro de reação do apresentador.** Decisão do operador.
- **Legenda automática.** Existe projeto separado para isso (`LEGENDAR VIDEO`).
- **Subir sozinho para o YouTube.** Sai o `publicar.md`; o envio é do operador.
- **Música e efeitos.** O áudio é o das reações.
- **Mosaico das lives juntas.** Foi considerado e descartado nesta rodada: o
  operador escolheu um a um. A capa continua com a grade de rostos, que é
  outra coisa.

---

## 13. Riscos

**O campo `torcida` vazio.** Já está errado hoje, em três dos seis canais, e
com a regra editorial ligada isso deixa o melhor material de fora. É o primeiro
item a consertar, e é barato.

**A prévia divergir do render.** É o risco clássico deste tipo de painel e a
razão de o molde ser declarado uma vez só, com teste comparando as duas
saídas.

**O tempo de render assustar.** Minutos numa máquina sem placa de vídeo. O
remédio é o cache por item e a fila com progresso — e dizer a verdade sobre o
tempo, em vez de girar uma rodinha.

**O disco encher.** Intermediários somam 1 a 2 GB por jogo, e a biblioteca é
disco local. Precisa de comando de limpeza e de aviso no painel.

**Publicar reação de terceiro.** O canal de referência credita cada live na
descrição, com link. Fazemos o mesmo, e é por isso que o bloco de créditos é
gerado automático e não é opcional.

---

## 14. Ordem de construção

Cada passo entrega algo que funciona sozinho:

1. ~~**`torcida` obrigatória**~~ — **feito.** O cadastro exige (`0 - CANAIS`
   não grava sem), o estúdio da 8770 marca em vermelho e deixa preencher ali,
   e `python -m nucleo.esteira torcida <jogo>` conserta os jogos velhos. Os
   três canais em branco do jogo de 03/09 foram preenchidos: `bage-tv` gremio,
   `baldasso-tv` inter, `gaucha-esportes` neutro. `nucleo/torcidas.py`.
2. ~~**`perdedor` + `melhor`**~~ — **feito.** `nucleo/perdedor.py` (quem
   perdeu, quais clipes entram, a troca do operador gravada em `rindo_de`) e
   `nucleo/melhor.py` (a janela de N segundos, com pico e sem pico). Nenhum
   dos dois abre vídeo: 26 testes novos, 378 no total. O placar final passou a
   caber no catálogo (`catalogo.registrar_placar`), porque a ESPN só responde
   enquanto o jogo está no ar e o estúdio edita dias depois — **falta quem
   escreva esse placar**, e isso vem com o painel do passo 5.
3. ~~**`molde` + `receita`**~~ — **feito.** `nucleo/molde.py` declara as cinco
   camadas em coordenadas de 0 a 1 e emite o `filter_complex` e o JSON da
   página; o teste lê a geometria de volta do filtro e compara com o da página,
   camada por camada, nos dois formatos. `nucleo/receita.py` nasce derivada do
   catálogo, guarda o que o operador tocou e sobrevive a um corte novo.
4. ~~**`estudio` render**~~ — **feito.** `nucleo/estudio.py` com as três
   velocidades, cache por item (hash do filtro inteiro: mudou a imagem, mudou o
   nome do arquivo), progresso em `render.json` e `python -m nucleo.esteira
   render|limpar`. Renderizado de verdade nesta máquina: saiu 1920×1080 com
   cantos arredondados, borda, etiqueta e placar. Dois defeitos achados no
   primeiro quadro e corrigidos — o placar por extenso saía cortado pela borda
   (no quadro vão só os números; o nome por extenso ficou na cartela) e o nome
   do canal vazava da tarja (o molde agora garante que cabe).
5. ~~**Painel 8772**~~ — **feito.** `painel/edicao.py` + `painel/edicao.html`,
   abertos pelo `5 - EDICAO.bat`. Provado por HTTP de ponta a ponta nesta
   máquina: página serve, edição já vem derivada, arrastar alça grava, espiar
   0,3s, prévia 2,0s, render em outro processo termina e volta `pronto`.
   Dois defeitos que só a prova real acharia foram corrigidos — o `h264_amf`
   recusa `-preset veryfast`/`-crf` (a prévia morria), e um render que morre no
   meio deixava a tela dizendo "rodando" para sempre (agora o PID é conferido).
6. **`capa` + `publicacao`** — as duas peças que acompanham o vídeo.
7. **Formato em pé** — o curto de 2 min, mesmo molde, outro enquadramento.

O vídeo longo fica pronto no passo 5. O curto, no 7.

---

## 15. Decisões ainda abertas

| # | Pergunta | Padrão que vou seguir se não houver resposta |
| --- | --- | --- |
| 1 | A capa entra nesta rodada? | **Sim.** É metade do clique. |
| 2 | O curto de 2 min é 9:16 ou 16:9? | **9:16.** Shorts aceita até 3 min desde 2024. Se for para o feed, é um sinalizador. |
| 3 | Margem do quadro no deitado | **5%.** Fundo precisa aparecer, senão a marca some. A conferir na primeira prévia. |
| 4 | Duração por clipe no longo | **60s**, ajustável. 12 clipes (3 canais do Inter × 4 gols) dão 12:08 com as cartelas — dentro da faixa do canal. |
