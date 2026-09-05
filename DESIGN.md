# DESIGN.md — REAÇÃO DA TORCIDA

O par visual do `AGENTS.md`. Aquele diz **como o código se escreve**; este diz **como a
tela se parece**. Leia antes de mexer em qualquer `.html` do projeto.

O projeto tem quatro telas, e elas não competem:

| Tela | Arquivo | Porta | Quando é usada |
| --- | --- | --- | --- |
| Painel da gravação | `painel/gravacao.html` | 8771 | **Durante** o jogo, de canto de olho |
| Estúdio | `painel/pagina.html` | 8770 | **Depois** do jogo, escolhendo clipe |
| Estúdio de edição | `painel/edicao.html` | 8772 | **Depois** da escolha, montando o vídeo |
| Recepção do estúdio | `painel/recepcao.html` | 8773 | **Antes de tudo**: qual jogo, e por onde continuar |

O estúdio de edição nasceu ao lado do da 8770, e não no lugar dele; a recepção
nasceu ao lado dos dois. Reforma grande não se faz na ferramenta em uso. Os
quatro `:root` têm os mesmos tokens, e a bateria reprova se um divergir.

### A recepção são duas telas no mesmo arquivo

`recepcao.html` mostra uma coisa de cada vez, escolhida pelo endereço:

| Endereço | O que aparece | A pílula preta é |
| --- | --- | --- |
| `#/` | a lista de jogos | o próximo passo do jogo mais novo que pede trabalho (`#continuar`) |
| `#/jogo/<pasta>` | a escolha de clipes daquele jogo | IR PARA A EDIÇÃO (`#editar`) |

As duas nunca aparecem juntas, então continua valendo **uma pílula preta por
tela** — e é por isso que o CSS tem duas regras de pílula preta num arquivo só.
Se um dia as duas visões couberem na mesma dobra, uma delas perde o preto.

O jogo mora no **endereço**, e não na memória da página: recarregar o navegador
volta ao mesmo jogo, e trocar de jogo não reinicia servidor nenhum. É a mesma
regra de sempre, um degrau acima — nada que o operador escolheu pode viver só na
página aberta.

### Prateleira organiza; filtro recorta

Com um jogo, lista basta. Com uma temporada, não: a lista da recepção é
**agrupada** por campeonato, e dentro dele por rodada. São duas coisas
diferentes e a tela não as mistura:

| | O que faz | Onde aparece |
| --- | --- | --- |
| **Prateleira** | organiza o que existe, sem esconder nada | cabeçalho de campeonato + rótulo de rodada |
| **Filtro** | recorta o que aparece (etapa, time) | as pílulas do alto |

Quem decide o rótulo e a ordem é o servidor (`acervo.grupos`), e a página só
desenha o que recebeu: prateleira montada na tela discordaria da contagem do
servidor no dia em que a regra mudasse num dos dois lados.

A ordem, dentro e fora, é a do **jogo mais novo primeiro**. Ordenar rodada por
número deixaria "Semifinal" de fora — fase não é número, e número inventado
ordena errado. Ordenar cada prateleira pelo jogo mais recente que ela tem serve
para os dois casos e não inventa ordem para quem não tem.

Rodada que ninguém preencheu não vira prateleira escondida: aparece como
**"sem rodada"**, e o cartão traz uma pílula azul que preenche dali mesmo — é a
mesma regra do canal sem torcida. Mandar o operador abrir o `catalogo.json` à
mão é o jeito garantido de a gaveta "sem rodada" nunca esvaziar.

**Filtro que cresce troca de forma.** Até oito times, uma fileira de pílulas.
Passando disso, uma lista: uma temporada são vinte clubes, e vinte pílulas viram
uma parede na frente dos jogos. A pílula é o padrão, não uma obrigação de
enfileirar tudo.

---

## 0. O sistema: a folha da Ollama

**Migração encerrada em 04/09/2026.** As três telas seguem o sistema descrito em
<https://getdesign.md/ollama/design-md>: folha de papel branca, preto como única
marca, fio de cabelo no lugar de sombra, pílula para tudo o que se aperta, e
**uma única superfície invertida por tela**.

O arquivo cru daquele sistema está em
`https://raw.githubusercontent.com/VoltAgent/awesome-design-md/HEAD/design-md/ollama/DESIGN.md`
— a página do site é aplicação JS e não serve para ler.

O que a migração trocou, para quem for ler código antigo e estranhar:

- Fundo chapado branco nas três telas; saiu o degradê radial, saiu o rodapé em
  degradê do estúdio.
- Saíram **todas** as `box-shadow`, e com elas o brilho da bolinha viva.
- A letra passou a ser a do sistema (`ui-sans-serif`), sem a Inter na frente.
- Tudo o que se aperta virou pílula de 999px — botão, `select`, campo de digitar,
  selo de estado, chip de marca de gol.
- Cartão foi de 16/18px para 12px.
- A ação principal de cada tela virou a pílula preta: MARCAR GOL na gravação,
  MONTAR no estúdio, RENDER FINAL na edição. Saíram o âmbar e o `--gol`.
- Os fundos escuros herdados da paleta anterior (o vinho do apagar, o azul-noite
  do abrir pasta, o `#344353` do descartar) viraram tinta da cor de estado sobre
  o papel, com o fio na mesma cor.
- As cores de estado escureceram para passar em contraste sobre branco, e a
  tinta de fundo caiu de 16% para 12% (a conta está na seção 2).

---

## 1. Tema visual e atmosfera

Sala escura, jogo na TV, painel num monitor lateral. Quem olha não está lendo: está
**conferindo**. A tela tem que responder de relance, a dois metros de distância, com o
rabo do olho.

Até a migração, a resposta a isso era "escuro sempre". Deixou de ser: o vocabulário
agora é a folha branca da Ollama, e o que faz o trabalho de ser lido de relance não é
mais o fundo escuro, são três coisas mais baratas:

- **Uma pílula preta por tela.** É o objeto mais escuro da página e a única coisa que
  chama para clicar. Numa tela branca ela se acha sem procurar. Preto é escasso de
  propósito: duas pílulas pretas na mesma dobra e nenhuma das duas é a principal.
- **Fio de cabelo no lugar de sombra.** Quem separa cartão de página é `--linha`, não
  profundidade. Nada levanta do papel.
- **Cor é estado, nunca enfeite.** Se uma cor aparece, ela quer dizer alguma coisa. Um
  botão azul e um botão verde são coisas diferentes, e não duas opções de gosto.

Os dois compromissos que atravessaram a migração inteira:

- **Nada pisca à toa.** Movimento é caro: só o que mudou tem direito a se mexer. A
  única animação do projeto é o alarme de canal caído, e ela existe porque perder um
  canal no meio do jogo custa a partida.
- **Estado tem que estar escrito, não só colorido.** Verde e vermelho são as duas
  cores mais usadas aqui, e são exatamente as duas que mais gente não distingue.

O estúdio é mais espaçoso e pode respirar — ninguém escolhe clipe com pressa. O painel
da gravação é apertado de propósito: cabe tudo sem rolar a página.

---

## 2. Paleta e o papel de cada cor

Os tokens vivem no `:root` de cada tela e têm **o mesmo nome e o mesmo valor nas três**.
Se você precisar de uma cor que não está aqui, o problema é o estado que você está
inventando, não a paleta.

| Token | Valor | Papel |
| --- | --- | --- |
| `--fundo` | `#ffffff` | A folha de papel. A página inteira, sem alternância de superfície. |
| `--caixa` | `#ffffff` | Cartão, tabela, quadro. É a mesma folha: quem separa é o fio, não a cor. |
| `--caixa-2` | `#fafafa` | Superfície suave: campo, pílula de controle, cabeçalho de tabela. |
| `--linha` | `#e5e5e5` | O fio de cabelo. Toda borda e todo divisor. |
| `--fio-forte` | `#d4d4d4` | O fio um pouco mais forte: contorno de botão e de campo. |
| `--texto` | `#000000` | Tinta. Título, texto normal, rótulo de botão, **fundo da pílula principal**. |
| `--fraco` | `#737373` | Rótulo, unidade, legenda, texto secundário. |
| `--escuro` | `#171717` | **A única superfície invertida.** Uma por tela, e nada mais. |
| `--viva` | `#027a48` | **Está funcionando**: canal gravando, corte pronto. |
| `--morta` | `#b42318` | **Parou**: canal caído, corte que morreu no meio. |
| `--alerta` | `#b54708` | **Anda, mas confira**: cortando agora, cobertura parcial, medida que discordou. |
| `--info` | `#1849a9` | Ação neutra que abre outra coisa (abrir pasta, ver quadro, alinhar). |

### Fundo colorido é a cor a 12% sobre a caixa

Nunca a cor cheia. Cor cheia com texto por cima não passa em contraste e grita mais
alto que o gol.

```css
background: color-mix(in srgb, var(--viva) 12%, var(--caixa));
color: var(--viva);
border-color: color-mix(in srgb, var(--viva) 40%, var(--caixa));  /* só quando levar fio */
```

**Eram 16% e não davam conta.** Medido: `--viva` e `--alerta` sobre a própria tinta a
16% ficavam em 4,3:1, abaixo do 4,5:1 que a AA pede para texto de 12px. A 12% passam
folgado, e o desenho não perdeu nada — a tinta continua se lendo como selo.

| Cor | sobre `#ffffff` | sobre `#fafafa` | sobre a própria tinta a 12% |
| --- | --- | --- | --- |
| `--viva` | 5,41 | 5,19 | 4,57 |
| `--morta` | 6,57 | 6,30 | 5,40 |
| `--alerta` | 5,43 | 5,20 | 4,56 |
| `--info` | 8,19 | 7,84 | 6,72 |
| `--fraco` | 4,74 | 4,54 | — não use `--fraco` sobre tinta: cai para 3,9 |

Duas consequências práticas dessa tabela, e as duas já estão no código:

- **Hover não escurece o fundo, firma o fio.** Escurecer a tinta no hover devolvia o
  problema de contraste. Botão de estado no hover troca `border-color` pela cor cheia.
- **Cartão não ganha tinta de estado.** O clipe escolhido no estúdio tem fio verde e
  selo escrito "✓ no vídeo" — não fundo verde, porque o `12,4 dB` em `--fraco` dentro
  dele cairia para 4,2:1.

### O que cada cor NÃO pode fazer

- Verde não quer dizer "bom", quer dizer **vivo**. Um clipe ruim de um canal que gravou
  direito continua verde.
- Vermelho não quer dizer "erro do usuário", quer dizer **parou**. Erro de digitação é
  âmbar.
- Nenhuma cor de estado carrega ação principal. Quem chama para clicar é a pílula
  preta; verde, vermelho e âmbar só informam. Foi por isso que o `--gol` saiu: MARCAR
  GOL era vermelho e disputava atenção com "canal caiu".

---

## 3. Tipografia

Uma família só, do sistema, sem baixar nada — a máquina é offline durante o jogo e uma
fonte que não carrega deixa a tela em Times New Roman no meio da partida.

```css
font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
```

| Papel | Tamanho | Peso | Observação |
| --- | --- | --- | --- |
| Título da página | `clamp(30px, 5vw, 54px)` | 700 | `letter-spacing: -.04em` |
| Nome do jogo (`h2`) | 22px | 700 | |
| Texto normal | 14px | 400 | |
| Rótulo de botão | 14px | 600 | nunca 800: no papel branco pesa demais |
| Rótulo, legenda, unidade | 12px | 600 | `--fraco`, `text-transform: uppercase`, `letter-spacing: .5px` |
| Número grande de resumo | 26px | 700 | `font-variant-numeric: tabular-nums` |

**Todo número que muda sozinho leva `tabular-nums`.** Sem isso o "12,4 MB" vira "9,8 MB" e
a coluna inteira dança a cada 3 segundos — o olho persegue o movimento e não lê o valor.

---

## 4. Componentes

### Botão

Todos são pílula (`border-radius: 999px`), todos com `min-height` de 28px no compacto e
36px no normal, `padding: 6px 14px` e `9px 18px`.

| Variante | Fundo | Texto | Fio | Onde |
| --- | --- | --- | --- | --- |
| normal | `--caixa` | `--texto` | `--fio-forte` | ações comuns |
| principal | `--texto` | `--fundo` | `--texto` | **uma por tela**: MARCAR GOL, MONTAR, RENDER FINAL |
| perigo | `--morta` a 12% | `--morta` | `--morta` a 40% | apagar marca, parar gravação |
| abrir | `--caixa` | `--info` | `--fio-forte` | abrir pasta, ver quadro, alinhar |
| apagado | `--caixa` | `--fraco` | `--fio-forte` | descartar, filtro desligado |

Hover do normal é `background: var(--caixa-2)`; hover do perigo é o fio na cor cheia.
**Ação irreversível no meio do jogo pede `confirm()`** — parar a gravação por clique sem
querer custa o resto da partida.

### Selo de estado (pílula)

`border-radius: 999px`, 12px, peso 600, fundo a 12%, texto na cor cheia. É a forma padrão
de dizer em que pé está alguma coisa: corte, alinhamento, cobertura, clipe escolhido.
Selo diz o estado **por escrito** — `✓ 6/6 cortado`, `sem torcida`, `✓ no vídeo`.

### Cartão

`background: var(--caixa)`, `border: 1px solid var(--linha)`, `border-radius: 12px`.
**Sem sombra, em nenhuma tela.** Cartão dentro de cartão usa a mídia a 8px, para o
canto de dentro não competir com o de fora.

### Tabela

Cabeçalho em `--fraco` 12px maiúsculo. Linha divisória `1px solid var(--linha)`.
Coluna numérica alinhada à direita com `tabular-nums`.

---

## 5. Layout

- **Escala de espaço: 4 / 8 / 16 / 24 / 32.** Nada de 5, 7, 13, 18.
- **Escala de raio: 8 (mídia dentro de cartão, trilho) / 12 (cartão, mídia, faixa) /
  999 (tudo o que se aperta).** Três valores, mais o `50%` da bolinha de canal vivo.
- Largura máxima `min(1400px, calc(100% - 32px))`, centralizada.
- O painel da gravação **não rola horizontalmente**. Nunca. Se não coube, encolhe.
- Grade de quadros: `repeat(auto-fill, minmax(210px, 1fr))`.

---

## 6. Profundidade

Quase nenhuma, e nenhuma feita de sombra. Três camadas e acabou:

1. `--fundo` — a página
2. `--caixa` — o cartão, separado por fio
3. `--caixa-2` — o controle dentro do cartão

Separação por **borda**, sempre. `box-shadow` não aparece em nenhuma das três telas, e a
bateria reprova se voltar. Nada de gradiente decorativo: o rodapé grudado do estúdio, que
era um degradê para o conteúdo sumir por baixo, hoje é fundo chapado com fio em cima.

A única exceção é a **superfície invertida**: uma por tela, `--escuro` ou a pílula preta.
Na gravação são a pílula MARCAR GOL e a faixa do recado que aparece e sai; no estúdio, a
pílula MONTAR; na edição, a pílula RENDER FINAL; na recepção, o próximo passo do jogo que
pede trabalho — e, dentro de um jogo, IR PARA A EDIÇÃO. Botão dentro de superfície invertida é
pílula branca (`--fundo` com `--texto`).

**O preto atrás de foto e de vídeo não conta como superfície**: é passe-partout. O `#000`
do `<video>`, do quadro do canal e do fundo da lupa existe para a imagem ter contra o que
aparecer, e por isso o texto que fica sobre ele vai em `--fundo`, não em `--texto`.

---

## 7. Pode e não pode

**Pode**

- Deixar o estado óbvio pela cor e **repetido em texto**. Cor sozinha exclui quem não
  distingue verde de vermelho, e são exatamente as duas cores mais usadas aqui.
- Mostrar o que falhou, marcado. Clipe que o detector não achou vai em vermelho na tela.
- Guardar em disco na hora do clique.
- Piscar o alarme de canal caído. É a única animação do projeto, e é para ser vista de
  costas.

**Não pode**

- **Sumir com o que deu errado.** É a regra mais forte do projeto. Canal sem material
  aparece marcado, não some da lista. Vale para a lista de jogos também: jogo cujo
  `catalogo.json` não deu para ler aparece com o selo `não deu para ler`, e não sai da
  tela levando os outros seis com ele.
- **Avisar o que não é verdade.** Aviso falso ensina o operador a ignorar o aviso que um
  dia será verdade. Foi o que derrubou a primeira versão do "renderize de novo": ela
  comparava a hora dos arquivos, e a tela de edição regrava a receita a cada abertura —
  todo vídeo parecia velho um minuto depois de sair. Hoje quem responde é a assinatura
  que o render gravou, e render antigo, sem assinatura, não afirma nada.
- **Fingir que ainda está trabalhando.** Estado travado que nunca resolve é pior que erro:
  o operador espera por um arquivo que nunca vem.
- Guardar escolha do operador só na página aberta. Recarregar não pode perder trabalho.
- Inventar cor nova para um estado novo. Se não cabe em vivo / parou / confira / neutro,
  o estado está mal pensado.
- **Cor cheia atrás de texto**, sombra, gradiente decorativo, e mais de uma pílula preta
  por tela.
- Deixar valor cru de cor no CSS. Só `#000` de passe-partout e o branco a 70% sobre ele.
- Animação de entrada, transição acima de 120ms, spinner girando sem fim.

---

## 8. Responsivo

Alvo é monitor de desktop, 1366px para cima. Não há versão de celular e não vai haver —
esta ferramenta roda na máquina que está gravando.

O que precisa aguentar: janela dividida ao meio (≈960px) e monitor grande (2560px).
Grade fluida com `auto-fill` resolve os dois sem media query. Abaixo de 900px a tabela
de canais pode rolar dentro do próprio contêiner (`overflow-x: auto`) — a página, não.

---

## 9. Guia rápido para agentes

Ao gerar ou mexer em interface deste projeto:

1. **Leia o `:root` da tela antes de escrever CSS.** Os tokens já existem; usar valor cru
   em vez de token é o erro mais comum e o mais chato de desfazer.
2. **Pergunte que estado a cor representa.** Não existe "um verde mais bonito": existe
   `--viva`, e ele quer dizer que está funcionando.
3. **Pílula para tudo o que se aperta**, 12px para o cartão, e o preto só na ação
   principal — que já existe em cada tela, então não crie a segunda.
4. **Repita o estado em texto.** `✓ 6/6 cortado` ao lado do verde, não só o verde.
5. **Português na interface**, como no resto do projeto.
6. **Toda escolha do operador grava em disco na hora**, antes de a tela mudar.
7. **Não mude a tela do jogo com jogo rolando.** O painel da gravação pode ser reiniciado
   sem risco, mas a gravação em si, não — e as duas coisas moram em processos diferentes.

### Prompts prontos

> "Acrescente um selo de estado no painel da gravação seguindo o DESIGN.md: pílula, fundo
> a 12%, texto na cor cheia, com o estado repetido por escrito."

> "Unifique os tokens desta tela com o DESIGN.md, sem mudar o layout."

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

### O arranjo `palco-largo`

Desenhado pelo dono em 05/09, por cima de um quadro do `palco-alto`: a logo desce
para o meio da coluna da esquerda, a janela cresce e cola na direita, e o vão que
sobrava em cima vira a faixa das redes.

É o único arranjo que **amplia** a fonte — 1472×828 contra os 1280×720 do clipe,
15% a mais. Os outros três mantêm o 1:1. A troca foi escolhida olhando o
resultado renderizado, e não no papel: o vão vazio incomodava mais do que a perda
de definição. Quem for medir nitidez depois encontra o número no
`testes/test_molde.py`, não escondido.
