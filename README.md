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

As duas telas podem ficar abertas ao mesmo tempo: moram em portas diferentes.

O detector de pico não decide mais sozinho onde está o gol — quem marca é o
operador, ou o placar da ESPN. Ele é usado para duas coisas: medir a força da
reação de cada clipe (para o estúdio mostrar os mais explosivos primeiro) e
descobrir quanto cada canal atrasa em relação aos outros. A descoberta automática de lives também foi removida: a decisão
dos canais é sempre do operador.

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
