# Palco e identidade do canal — desenho

Data: 2026-09-05
Estado: **desenhado, não implementado.** Nenhuma linha de código foi escrita.

O par deste arquivo é o `2026-09-04-estudio-de-edicao-design.md` (o que o
estúdio faz) e o `molde.py` (onde a geometria mora). Este aqui diz **como o
vídeo ganha a cara do canal**.

---

## 1. O que é

Hoje o vídeo final é a cena dentro de um quadro, sobre a cor do time que
perdeu. Funciona, mas não identifica o canal: tirando a cor, um compilado é
igual ao de qualquer outra pessoa.

O palco é a camada de marca. Um fundo com a arte do canal, a logo num canto, e
uma faixa de redes sociais no topo — com a janela da reação **menor**, por
cima, deixando o fundo aparecer.

A referência é o canal **A Voz da Torcida**
(`youtube.com/watch?v=5rpHf5vMufU`): fundo de estádio esverdeado com a marca,
logo em escudo no alto à esquerda, barra de redes no alto à direita, e a live
numa janela emoldurada ocupando cerca de dois terços da largura. Não é pra
copiar — é a estética que o dono quer alcançar.

### O que NÃO é

- **Não é um editor de vídeo.** Não se mexe no conteúdo, não se corta aqui, não
  se sobrepõe nada por cima da cena. O palco é o cenário atrás e ao redor.
- **Não é arrastar na tela.** Nesta rodada você escolhe entre arranjos prontos
  e ajusta dois números. O editor visual está na seção 9, como próximo passo.
- **Não é por vídeo.** É o estilo do canal. Desviar num jogo específico é
  possível e fica marcado na tela — mas o padrão é um só.
- **Não muda o formato em pé.** Nesta rodada, só o deitado (seção 9).

---

## 2. As decisões que geraram este desenho

Todas do dono, em 05/09, na conversa que originou este arquivo:

| Pergunta | Escolha |
| --- | --- |
| A moldagem é fixa ou por vídeo? | **Padrão do canal + desvio pontual marcado** |
| De onde vem a arte? | **PNG pronto de fundo + logo e barra como camadas soltas** |
| Como se mexe nela? | **Arranjos prontos + ajuste fino numérico** |
| Vale pros dois formatos? | **Só deitado, por ora** |
| Como as camadas entram no ffmpeg? | **Palco pré-desenhado com PIL, entrada única** |

### A decisão que este documento revoga em parte

O `molde.py` diz, em 05/09:

> **O vídeo não leva letra nenhuma.** Nem nome de canal, nem placar, nem
> cartela de abertura (...). Foi escolha do dono em 05/09.

Continua valendo para **conteúdo**: nada de placar, cartela de abertura ou
nome de canal escrito sobre a cena. O que muda é que o **cenário** passa a
poder ter letra — os @s das redes na faixa superior, que não tocam a janela da
reação e não mudam de jogo para jogo. O motivo original (quem identifica o
vídeo é a capa e a legenda, que se trocam sem refazer render) continua de pé
para tudo que é específico do jogo.

O `drawtext` permanece proibido. A letra é desenhada com PIL, num PNG, fora do
ffmpeg.

---

## 3. Geometria — os arranjos

A geometria continua morando no `molde.py`, em coordenadas de 0 a 1, com os
dois renderizadores (`para_ffmpeg` e `para_pagina`) saindo dela. Isso não
muda: é o que impede a prévia do navegador de divergir do vídeo gerado.

O que muda é que `_MOLDE["deitado"]` deixa de ser uma lista e passa a ser uma
**tabela de arranjos nomeados**, cada um com suas camadas.

### Os três arranjos

| Arranjo | Janela | Sobra | Para quê |
| --- | --- | --- | --- |
| `quadro-cheio` | 1728×972 em 96,54 | 5% de margem | O de hoje. Padrão até existir arte. |
| `palco-alto` | 1280×720 em 320,280 | 280px em cima, 80 embaixo | Logo e redes na faixa superior |
| `palco-lateral` | 1280×720 em 576,300 | coluna de 576px à esquerda, 64 à direita | O mais próximo da referência |

`quadro-cheio` fica byte a byte igual ao molde atual. É o que garante que
ninguém acorda com o vídeo diferente sem ter pedido.

### As camadas novas

Além de `fundo` e `quadro`, que já existem:

- **`logo`** — caixa definida pelo arranjo. Em `palco-alto`, no alto à
  esquerda; em `palco-lateral`, centrada na coluna esquerda.
- **`barra`** — faixa de redes. Em `palco-alto`, no alto à direita; em
  `palco-lateral`, no alto, atravessando.

`quadro-cheio` não tem `logo` nem `barra`: não há sobra onde pôr.

### O ajuste fino

Dois números, e só:

- **`escala`** (0,60 a 1,00) — multiplica a janela **do arranjo escolhido**.
  **Trava em 1,00.**
- **`deslocamento`** (−0,15 a +0,15) — sobe ou desce a janela, em fração da
  altura do palco (1080), ou seja no máximo 162px para cada lado.

O teto de 1,00 é a seção 6: nos arranjos de palco, escala 1,00 é o 1:1 com a
fonte, e passar disso volta a esticar o 720p. O campo recusa o valor e diz por
quê.

Uma ressalva honesta: em `quadro-cheio` a janela **já** é maior que a fonte, e
escala 1,00 ali continua sendo o esticão de 1,35× de hoje. A trava não conserta
o `quadro-cheio` — ela só impede que os arranjos de palco percam a vantagem que
têm. Quem quer nitidez usa um arranjo de palco.

### Onde esses números moram

`escala`, `deslocamento` e `arranjo` são **do canal**: vivem no
`identidade.json` e valem para todo jogo.

O desvio pontual (a decisão da seção 2) mora no `receita.json` do jogo, num
campo `moldagem` **opcional**:

```json
"moldagem": { "arranjo": "palco-alto", "escala": 0.9, "deslocamento": 0.0 }
```

Ausente — que é o normal — o jogo usa o padrão do canal. Presente, sobrescreve
campo a campo, e é isso que a tela marca como "fora do padrão". A assinatura do
palco (seção 5) leva os valores já resolvidos, então trocar o desvio invalida o
cache e regenera sozinho.

---

## 4. Identidade — `dados/identidade.json`

Arquivo novo, um por instalação (não por jogo):

```json
{
  "arranjo": "quadro-cheio",
  "escala": 1.0,
  "deslocamento": 0.0,
  "arte_de_fundo": "",
  "logo": "",
  "redes": { "youtube": "", "instagram": "", "tiktok": "" },
  "chamada": "INSCREVA-SE E DEIXE UM LIKE!"
}
```

**Regra central: campo vazio é camada que não existe.** Não é camada
transparente, não é espaço reservado — o PIL simplesmente não desenha.

| Campo | Vazio significa |
| --- | --- |
| `arte_de_fundo` | Fundo continua sendo a cor do time perdedor, com vinheta |
| `logo` | Nenhuma logo desenhada |
| `redes.*` | Aquela rede some da barra |
| todas as `redes` | A barra inteira não é desenhada |

Com o arquivo recém-criado — tudo vazio, `arranjo: "quadro-cheio"` — o vídeo
sai **idêntico** ao de hoje. É assim que isso entra em produção sem sustos, e
é o que o teste de não-regressão da seção 7 verifica.

O dono ainda não tem logo, arte nem contas nas redes. O desenho é feito para
que isso não bloqueie nada: constrói-se agora, preenche-se depois, um campo de
cada vez.

### A arte de fundo

PNG de 1920×1080, **sem texto**. Cenário e cor, feitos no Canva. Texto na arte
obrigaria a refazer a imagem inteira no dia que um @ mudasse — é justamente o
que a barra como camada separada evita.

Se o PNG vier em outro tamanho, é redimensionado cobrindo o palco (sem
deformar) e o excesso é cortado. Se não abrir, o render não para: avisa e cai
na cor do time.

---

## 5. O palco — `estudio.palco()`

Vizinho de `estudio.mascaras()`, mesma prateleira de cache
(`intermediarios/formas/`). Desenha **um PNG só**, de 1920×1080, com arte de
fundo, logo e barra já compostos.

```
palco-deitado-<assinatura>.png
```

A assinatura é a impressão digital de: identidade + arranjo + escala +
deslocamento + cor do time perdedor. Mudou qualquer um, gera outro arquivo;
não mudou nada, reaproveita. É o mesmo mecanismo do `mascaras()`.

### O que muda no ffmpeg

Uma linha. Hoje:

```
color=c=<cor>:s=1920x1080:r=30,vignette=PI/4[fundo]
```

Com palco:

```
[<entrada do palco>]scale=1920:1080,setsar=1[fundo]
```

O resto do `filter_complex` — recorte da cena, máscara de cantos, sobreposição,
moldura — fica intacto. `para_ffmpeg` ganha um parâmetro `palco: str | None`;
com `None`, gera exatamente o filtro de hoje.

Por que um PNG só, e não três entradas de imagem: o filtro não cresce, o número
de entradas do ffmpeg não muda, e o palco vira um arquivo que se abre no
visualizador e se confere antes de gastar treze minutos de render.

### A barra de redes

Desenhada pelo PIL a partir de `redes` e `chamada`, com a fonte de
`config.fonte_cartela`. Cada rede vira um par ícone + arroba. As redes vazias
não ocupam espaço: a barra é montada da direita para a esquerda com o que
existir, e some inteira se não existir nada.

Os ícones vão versionados no repositório, em `dados/icones/`, em PNG branco com
transparência. Sem ícone no disco, desenha só o texto.

---

## 6. Qualidade — o que se ganha de graça

Medido no jogo `2026-09-03 gremio x internacional`:

| Etapa | Resolução | Taxa | Recodifica |
| --- | --- | --- | --- |
| `bruto/*.ts` | 1280×720 | 2,27 Mbps | não (cópia) |
| `clipes/*.mp4` | 1280×720 | 1,22 Mbps | **sim** |
| `compilacao-deitado.mp4` | 1920×1080 | 1,84 Mbps | **sim** |
| YouTube | — | — | **sim** |

Dois defeitos aparecem nessa tabela, e os dois se corrigem nesta rodada.

### O esticão

A fonte é 1280×720 e o `quadro-cheio` a joga num quadro de 1728×972 — um
esticão de 1,35× que não inventa detalhe nenhum, só borra e gasta bitrate.

Nos arranjos de palco a janela é **1280×720 cravado**, dentro de um palco de
1920×1080. Os pixels da fonte caem 1:1 no vídeo final, sem reamostrar. A
imagem fica mais nítida **porque** a janela é menor.

É também o que legitima manter a saída em 1080p: o palco é 1080p de verdade,
com conteúdo nativo dentro, em vez de 720p inflado. E o YouTube distribui
upload 1080p melhor que 720p.

### O intermediário espremido

O corte sai a 1,22 Mbps de uma fonte de 2,27 — perde 46% antes de a montagem
começar, e não volta. O clipe é descartável (existe para revisão e para a
montagem consumir), então comprimi-lo é a perda mais barata de evitar que
existe.

| Onde | Hoje | Passa a ser | Custo |
| --- | --- | --- | --- |
| `cortador.comando_corte` | `veryfast` / `crf 20` | `veryfast` / **`crf 16`** | clipe ~2× no disco, temporário |
| `estudio._VIDEO_FINAL` | `veryfast` / `crf 20` | **`slow`** / **`crf 18`** | alguns minutos a mais, uma vez por jogo |

### O teto que não se fura

A fonte é 720p porque a placa de rede de 100 Mbps não aguenta baixar 1080p de
vários canais ao mesmo tempo (`altura_maxima: 720`, e o motivo está no
`AGENTS.md`). Enquanto a internet for essa, 720p nativo bem tratado é o melhor
resultado possível. Este desenho não promete 1080p real — promete parar de
estragar o 720p que se tem.

---

## 7. Testes

O teste que hoje compara `para_ffmpeg` com `para_pagina` camada por camada
passa a cobrir `logo` e `barra`. Continua sendo o que impede a prévia de
divergir do render.

Mais quatro, todos escritos antes do código:

1. **Não-regressão.** Identidade vazia com `quadro-cheio` produz o mesmo
   `filter_complex` de hoje, caractere por caractere. Este é o teste que
   importa: enquanto ele passar, ninguém perde o vídeo que já funciona.
2. **Campo vazio some.** Instagram em branco não aparece na barra; todas as
   redes em branco não desenham barra nenhuma; sem logo não há camada de logo.
3. **Escala travada.** `escala > 1,0` é recusada com mensagem que explica o
   esticão. `1,0` exato é aceito.
4. **Janela nativa.** Nos arranjos de palco com escala 1,0, a caixa do quadro
   mede 1280×720 exatos — se alguém mexer num número e quebrar o 1:1, a bateria
   reprova.

---

## 8. Painel — a aba MOLDAGEM

Entra na tela do estúdio, **antes** do RENDER FINAL. É o lugar que faltava:
depois de escolher os clipes e montar o compilado, antes de gerar o final.

Tem:

- **Escolha do arranjo**, com prévia. A prévia usa o `para_pagina`, que já
  existe e já devolve as caixas em pixels.
- **Escala e deslocamento**, dois campos, com a trava da seção 3.
- **Os @s**, um campo por rede, que gravam no `identidade.json`.
- **Conferir palco** — gera o PNG e abre no visualizador. Confere-se a estética
  sem renderizar vídeo nenhum.

Quando um jogo desvia do padrão do canal, a tela marca. O padrão é um só; sair
dele é permitido, mas nunca por acidente.

Vale corrigir aqui o que atrapalhou hoje: o fim do RENDER FINAL mostra o
caminho do arquivo como texto, e o dono não conseguiu abrir (o nome do jogo tem
espaços, e colado sem aspas o Windows não encontra). Troca-se por um botão
**abrir a pasta**, que chama `explorer /select,<saida>`.

---

## 9. Fora de escopo — os próximos passos

Nada disto entra nesta rodada. Está aqui para não se perder.

- **Editor de arrastar na tela.** Pedido explicitamente pelo dono em 05/09,
  para depois: arrastar a janela, puxar o canto, posicionar a logo com o mouse.
  Só faz sentido depois de rodar alguns jogos com arranjo pronto — aí se sabe
  o que faltou. O obstáculo real está registrado: geometria arrastada com o
  mouse não é comparável por teste, e é assim que a prévia e o ffmpeg passam a
  divergir sem ninguém ver.
- **Formato em pé.** O `molde.py` guarda arranjo por formato, então acrescentar
  o 9:16 depois é somar entradas na tabela. Precisa de uma segunda arte
  (1080×1920) e de um lugar melhor para a barra — no 9:16 a faixa de cima é
  área nobre.
- **Animação das camadas.** Logo entrando, barra deslizando. Exigiria as
  camadas como entradas separadas no ffmpeg (a abordagem descartada na seção
  2), então é reversão de decisão, não acréscimo.

---

## 10. Ordem de construção

Cada passo deixa o sistema funcionando:

1. `identidade.json` e sua leitura, com todos os campos vazios. Nada muda no
   vídeo. Teste de não-regressão passa a existir.
2. Arranjos no `molde.py`, com `quadro-cheio` como padrão. Nada muda no vídeo.
3. `estudio.palco()` desenhando só a arte de fundo (sem logo, sem barra).
4. Logo e barra no palco.
5. Aba MOLDAGEM no painel.
6. Ajustes de qualidade da seção 6.

Os passos 1 e 2 são os que mais podem quebrar coisa que já funciona, e são os
que saem primeiro — enquanto o vídeo gerado ainda tem que ser idêntico ao de
hoje, e portanto qualquer quebra aparece na hora.
