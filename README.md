# REAÇÃO DA TORCIDA

Ferramenta local para gravar lives escolhidas pelo operador, recortar reações
em horários informados manualmente, selecionar os melhores clipes e gerar uma
compilação.

## Fluxo atual

1. **0 - CANAIS.bat** — escolha no YouTube as lives com mais visualizações e
   cole as URLs exatas em dados/canais.json.
2. **1 - GRAVAR.bat** — grave simultaneamente todos os canais marcados como
   ativos, em até 720p e em segmentos MPEG-TS.
3. **2 - CORTAR.bat** — informe o horário exato em que a reação aparece na
   gravação. Cada clipe terá 8 segundos antes e 12 segundos depois.
4. **3 - ESTUDIO.bat** — assista aos clipes no painel local, escolha quais
   usar e monte a compilação.

Durante o jogo, o **PAINEL DA GRAVACAO.bat** (porta 8771) mostra o que cada canal
está gravando, com um quadro recente de cada um, e traz o botão MARCAR GOL. Se
você informar a liga no passo 1, o placar da ESPN marca os gols sozinho.

O detector de pico não decide mais sozinho onde está o gol — quem marca é o
operador, ou o placar da ESPN. Ele é usado para duas coisas: medir a força da
reação de cada clipe (para o estúdio mostrar os mais explosivos primeiro) e
descobrir quanto cada canal atrasa em relação aos outros. A descoberta automática de lives também foi removida: a decisão
dos canais é sempre do operador.

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

## Testes

Execute: python -m pytest -v

As decisões feitas no painel são gravadas imediatamente em catalogo.json.
