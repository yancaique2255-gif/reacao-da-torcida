# REAÇÃO DA TORCIDA

Ferramenta local para gravar lives escolhidas pelo operador, recortar reações
em horários informados manualmente, selecionar os melhores clipes e gerar uma
compilação.

## Fluxo atual

Os atalhos numerados na raiz da pasta são a ordem de uso, e cada um chama o
`.bat` de mesmo número dentro de `PROJETO\`:

1. **0 - CADASTRAR CANAIS** — escolha no YouTube as lives com mais visualizações
   e cole as URLs exatas. O nome do canal vem do próprio YouTube.
2. **1 - GRAVAR** — grava simultaneamente todos os canais marcados como ativos,
   em até 720p e em segmentos MPEG-TS. Informe a liga aqui e o placar da ESPN
   passa a marcar e cortar os gols sozinho.
3. **2 - PAINEL DO JOGO** (porta 8771) — a tela do *durante*. Mostra o que cada
   canal está gravando com um quadro recente, traz o botão MARCAR GOL, e diz em
   que pé está o corte de cada gol: aguardando, cortando 3/6, 6/6 cortado, ou
   parou no meio. O botão **abrir clipes** abre a pasta no Explorador.
4. **3 - CORTAR NA MÃO** — para o que o placar não pegou: informe o horário
   exato em que a reação aparece na gravação.
5. **4 - ESTUDIO** (porta 8770) — a tela do *depois*. Assista aos clipes, escolha
   quais usar e monte a compilação.
6. **5 - EDICAO** (porta 8772) — o estúdio de edição: monta o vídeo com a cara do
   canal. Ele já abre decidido — entram os canais da torcida que **perdeu**, na
   ordem da reação mais forte, com o corte proposto —, e tudo ali é ajustável:
   marcar e desmarcar, arrastar as alças do corte, trocar de que torcida se ri,
   virar o vídeo em pé. Cada clique grava em disco na hora. ESPIAR mostra um
   quadro pronto na hora; PRÉVIA renderiza o trecho pequeno; RENDER FINAL vai
   para a fila em outro processo, e você pode fechar a tela sem matar o render.

As telas podem ficar abertas ao mesmo tempo: moram em portas diferentes. A 8770
continua sendo a de trabalhar; a 8772 nasceu ao lado dela, e não no lugar.

O detector de pico não decide mais sozinho onde está o gol — quem marca é o
operador, ou o placar da ESPN. Ele é usado para duas coisas: medir a força da
reação de cada clipe (para o estúdio mostrar os mais explosivos primeiro) e
descobrir quanto cada canal atrasa em relação aos outros. A descoberta automática de lives também foi removida: a decisão
dos canais é sempre do operador.

## De que torcida é cada canal

O estúdio de edição publica **só o lado que perdeu** — é a regra editorial do
canal. Por isso todo canal precisa dizer de que torcida é, e o cadastro passou
a **exigir** isso: sem torcida ele não grava a live. Canal de narração, sem
lado, se cadastra como `neutro` — que é uma resposta, diferente de campo vazio.

Vazio é caro e é calado: o canal grava, corta, aparece no painel, e só some lá
na frente, quando o estúdio filtrar pelo perdedor. Foi o que quase aconteceu com
o `baldasso-tv` no primeiro jogo, que era o melhor material da noite.

Para os jogos gravados antes disso:

```
python -m nucleo.esteira torcida "2026-09-03 gremio x internacional"
```

Sem argumentos ele lista os canais e preenche sozinho o que o cadastro já sabe.
O que ele não souber, você diz — e ele grava nos três lugares (cadastro,
gravação e catálogo):

```
python -m nucleo.esteira torcida "2026-09-03 gremio x internacional" ^
  --definir baldasso-tv=inter gaucha-esportes=neutro
```

No **4 - ESTUDIO** dá para fazer o mesmo sem sair da tela: o canal sem torcida
aparece marcado em vermelho, com a lista de escolha logo abaixo. Ele nunca some
da lista.

## A ficha de cada jogo

Cada pasta de jogo ganha um **`JOGO.md`**: os times, a competição, a data e —
o motivo de ele existir — **o link de cada live gravada**, com o canal e a
torcida. Embaixo, os gols anotados e quantos clipes saíram de cada um. Um mês
depois ninguém lembra quais lives entraram num jogo, e a informação estava
espalhada por um `gravacao.json` dentro de cada canal.

Na raiz da biblioteca fica o **`JOGOS.md`**, um jogo por linha, do mais novo para
o mais velho.

As duas fichas são derivadas: `python -m nucleo.esteira ficha` refaz idênticas a
partir do disco. Apagar não perde nada.

## Onde ficam as coisas

Tudo mora em `Desktop\REACAO DA TORCIDA`, com os atalhos numerados na raiz e o
material em `MIDIA\`. A biblioteca é sempre disco local — nunca o `G:`, que é
o Google Drive e disputaria banda com a gravação.

## Configuração

Copie dados/config.exemplo.json para dados/config.json e ajuste os caminhos se
necessário. O arquivo pessoal não entra no Git.

A biblioteca tem que ficar em **disco local** (`C:\REACAO DA TORCIDA`). O `G:` é o
Google Drive: gravar lá dispara upload durante o jogo e o upload disputa a mesma
banda que baixa as lives. Só a compilação pronta sobe para o Drive.

Vídeos, áudios e segmentos são ignorados pelo repositório.

## Como a interface é escrita

`DESIGN.md`, na raiz do repositório, é o par visual do `AGENTS.md`: aquele diz
como o código se escreve, este diz como a tela se parece. Os tokens de cor, a
tipografia e o que cada cor significa moram lá, e as duas telas usam o mesmo
vocabulário. Leia antes de mexer em qualquer `.html`.

## Testes

Execute: python -m pytest -v

As decisões feitas no painel são gravadas imediatamente em catalogo.json.
