# Alinhamento dos canais e gatilho automático de gol

Especificação escrita em 02/09/2026, depois da primeira transmissão de verdade
(Santos 0x0 Palmeiras e Vitória 0x2 Vasco, 11 canais, 11,9 GB gravados).

Este documento é para ser executado por outra IA, sem acesso à conversa em que
nasceu. Tudo o que é afirmação de fato aqui foi **medido**, e a medição está
descrita junto — não confie em nenhum número sem refazer a medida se algo
parecer estranho.

---

## 1. O problema, em uma frase

O operador sabe **que** houve gol (ele viu), mas o sistema não sabe **em que
segundo, em cada canal**, a reação daquele gol aparece — porque cada live tem
um atraso próprio em relação ao evento real.

Hoje o corte usa um único horário de relógio para todos os canais. Isso funciona
quando os canais estão todos colados no ao vivo, e falha quando não estão.

## 2. O que já existe e funciona (não reescrever)

Leia `AGENTS.md` antes de qualquer coisa. Em resumo do que interessa aqui:

- **`nucleo/relogio.py`** traduz horário de relógio → posição dentro dos `.ts`
  gravados. É a peça central. `Sessao(t0, pedacos)`, `trechos()`, `cobertura()`.
- **`esteira.ancorar_t0()`** já corrige o t0 pelo relógio do disco. Sem isso o
  erro era de meio minuto. **Isto resolve o atraso da GRAVAÇÃO, não o da LIVE.**
- **`nucleo/detector.py`** mede energia RMS em dB por quadro de 0,5 s e devolve
  `Achado(instante, confianca_db, tem_pico)`. `confianca_db` é `pico − mediana`.
- **`esteira.medir_reacao()`** já roda o detector em cada clipe cortado e grava
  `confianca_db` no catálogo.
- **`painel/gravacao.py`** (porta 8771) é o painel do *durante*: miniaturas,
  botão MARCAR GOL, PARAR, alarme de queda.
- **`gravador.ficou_para_tras()`** derruba e recomeça canal que está baixando
  mais devagar que o jogo.

## 3. Duas coisas que parecem a mesma e não são

Esta é **a distinção que mais importa** nesta especificação. Confundir as duas
leva a construir a coisa errada.

### 3.1 Atraso de download (JÁ RESOLVIDO)

O ffmpeg entra na playlist HLS atrás da ponta e baixa **abaixo do tempo real**.
O canal escreve bytes o tempo todo — passa por saudável em qualquer teste de
crescimento — e mesmo assim o trecho do gol ainda não existe no disco.

**Medido em 02/09/2026, com as duas partidas gravando:**

```
saudáveis     atraso de 0,1 a 0,2 min
quebrados     atraso de 60 a 62 min   ← CINCO canais de onze
```

Resolvido por `gravador.atraso_do_ao_vivo()`: compara quanto de vídeo existe no
disco contra quanto tempo passou desde o início da sessão. Passou de 5 min,
derruba e recomeça na ponta. **Não mexer nisto.**

### 3.2 Atraso da transmissão (O PROBLEMA DESTA SPEC)

Mesmo com o download em dia, cada canal transmite o jogo com o seu próprio
atraso: encoder, plataforma, o quanto o apresentador demora para reagir. Um
canal mostra o gol às 23:12:40 e o outro às 23:13:25, e **os dois estão
gravando perfeitamente**.

Isto é invisível para qualquer medida de disco. Só o **conteúdo** revela.

## 4. O que o operador pediu, e o que muda no pedido

Pedido literal: *"criar um atrasador de canal, algo que eu consiga atrasar os
segundos da live, assim consigo ter lives igual"*.

A intuição está certa: **existe um deslocamento por canal, e alinhar por ele é
o que resolve.** O que muda é onde aplicar:

- ❌ **Não atrase a gravação.** Segurar bytes na entrada só gastaria memória e
  criaria um jeito novo de perder o começo de um lance.
- ✅ **Aplique o deslocamento no corte.** A gravação continua crua e completa;
  cada canal é cortado no horário dele.

O resultado que o operador quer — "lives iguais" — aparece no clipe, que é onde
ele importa. E fica reversível: mudou a estimativa, corta de novo, sem regravar.

## 5. Desenho

### 5.1 Deslocamento por canal

Novo campo por canal, em `gravacao.json` (que já existe por canal):

```json
{
  "url": "...",
  "torcida": "vasco",
  "deslocamento": 12.5,
  "deslocamento_de": "consenso",
  "sessoes": [...]
}
```

- `deslocamento`: segundos a **somar** ao horário do gol para achar a reação
  neste canal. Positivo = este canal está atrasado em relação à referência.
- `deslocamento_de`: `"manual"` (o operador digitou) ou `"consenso"` (medido).
  **Manual sempre vence consenso** — o operador viu, o algoritmo estimou.

### 5.2 Auto-calibração pelo consenso (o coração)

**A ideia:** quando um gol acontece, todos os canais que o transmitem explodem.
A diferença entre os instantes de pico **é** o atraso relativo entre eles.

Isto se auto-calibra: o primeiro gol mede os deslocamentos, e os gols seguintes
já saem alinhados — e refinam a estimativa.

```
Para um gol marcado no horário H:
  1. Para cada canal, extraia o áudio da janela [H − 90s, H + 120s].
     Janela larga de propósito: ela precisa conter o pico mesmo com o canal
     dessincronizado. É busca, não é o corte.
  2. Rode detector.analisar() e guarde (instante_do_pico, confianca_db).
  3. Descarte quem ficou abaixo de `limiar_confianca_db` (padrão 6 dB):
     canal que não explodiu não tem opinião sobre quando foi o gol.
  4. Se sobraram MENOS DE 2 canais → não há consenso. Não invente
     deslocamento; deixe como está e registre no catálogo que não deu.
  5. A referência é a MEDIANA dos instantes (não a média: um canal muito
     fora estragaria a média, e a mediana ignora).
  6. deslocamento_do_canal = instante_do_canal − mediana
  7. Guarde. Se o canal já tinha deslocamento de consenso, faça média com o
     anterior — cada gol melhora a estimativa.
```

**Dado real para testar contra** (Vitória x Vasco, gol 1, marcado 23:12:36):

```
arena-rubro-negra    pico 23:11:49   15.9 dB
ateno-vascanos       pico 23:12:45   11.4 dB
fantico-vascano      pico 23:12:47    8.3 dB
mediana = 23:12:45  →  espalhamento entre os dois mais próximos: 2s
```

Note que `arena-rubro-negra` ficou 56 s fora dos outros dois. **Este é
exatamente o caso que a mediana existe para tratar** — e é também um alerta:
se o espalhamento for muito grande, provavelmente o pico daquele canal é outra
coisa (um quase-gol, um grito de revolta, um anúncio). Registre o espalhamento
para o operador ver.

### 5.3 Gatilho automático pela ESPN

Endpoint público, sem chave, conferido em 02/09/2026 (veja
`nucleo/placar.py` se já existir, senão crie):

```
https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard
```

- Slug da Copa do Brasil: **`bra.copa_do_brazil`** (com **Z**;
  `bra.copa_do_brasil` devolve HTTP 400). Brasileirão: `bra.1`.
- Lista completa: `https://sports.core.api.espn.com/v2/sports/soccer/leagues?limit=800`
- **Exige `User-Agent` de navegador**, senão a ESPN recusa.
- Campos úteis: `events[].competitions[0].competitors[].score`,
  `.status.type.name` (`STATUS_SECOND_HALF`, `STATUS_FULL_TIME`),
  `.status.displayClock` (`81'`), e `.details[]` com os gols e seus autores.

**O papel de cada fonte, e por que são duas:**

| fonte | responde | não responde |
|---|---|---|
| ESPN | **QUE** houve gol (zero falso positivo) | em que segundo a reação sai em cada canal |
| áudio | **QUANDO** cada canal reagiu | se aquilo foi gol ou quase-gol |

Uma cobre o buraco da outra. **Não tente usar só uma.**

O laço: pergunta à ESPN de 20 em 20 segundos (educado; a API não é sua). Placar
mudou → marca o gol no catálogo com o horário **do momento da detecção**, marcado
como `origem: "espn"` e `confirmado: false`. Depois roda o consenso de áudio para
achar o instante verdadeiro, e aí sim `confirmado: true`.

**Importante:** a ESPN tem atraso próprio, e ele varia. Ela é o **gatilho**, não
o relógio. Nunca corte usando o horário em que a ESPN avisou.

### 5.4 Regra do corte, canal a canal

O pedido original era: *"se tiver dois ou mais canais acusando, acusa nos outros
também, porém esse com um tempo maior de corte em caso de delay"*.

A primeira metade fica. A segunda vira quatro casos, porque "janela maior" só
ajuda em um deles:

| situação do canal | o que fazer |
|---|---|
| explodiu, e tem o trecho | corta na janela normal, no instante dele |
| **não** explodiu, mas tem o trecho | corta com **janela maior** ← aqui o pedido está certo |
| tem deslocamento conhecido de gols anteriores | usa o deslocamento, janela normal |
| **ainda não baixou** o trecho | **não corta.** Fica pendente |

O último caso é a razão de a segunda metade do pedido não funcionar sozinha:
quando o canal está 60 minutos atrás, **janela maior não adianta — o vídeo não
existe no disco**. Não é cortar mais; é não ter o que cortar.

Para esse caso: marque o clipe como `pendente` no catálogo e permita rodar o
corte de novo depois. O painel do estúdio deve mostrar "aguardando download"
em vez de esconder o canal — a regra do projeto é **nunca sumir calado**.

## 6. Plano de implementação

Cada tarefa entrega algo que roda e é testado. Ordem importa.

### Tarefa 1 — `nucleo/placar.py`

Cliente da ESPN. `buscar(liga)` → lista de partidas com placar, estado e relógio.
`mudou(antes, agora)` → quais partidas ganharam gol.

Testes: JSON gravado em disco como amostra (**nunca** teste que dependa de rede).
Cubra: partida sem começar, 1º tempo, intervalo, gol, fim de jogo, e a API
devolvendo lixo/HTML (acontece).

### Tarefa 2 — `nucleo/alinhamento.py`

`medir_deslocamentos(picos: dict[str, Achado], limiar_db) -> dict[str, float]`,
puro, sem I/O. Recebe os picos já medidos, devolve os deslocamentos.

Testes obrigatórios:
- 3 canais concordando → deslocamentos pequenos e simétricos em torno de zero
- 1 canal só → dicionário vazio (**sem consenso não se inventa deslocamento**)
- 1 canal muito fora (o caso `arena-rubro-negra` real, 56 s) → a mediana ignora
- todos abaixo do limiar → vazio
- dois canais empatados → mediana funciona com número par

### Tarefa 3 — medir os picos de verdade

`alinhamento.picos_do_gol(pasta_bruto, momento, cfg)`: para cada canal, extrai
o áudio da janela larga e roda o detector. Reaproveite `cortador.comando_audio`
e `esteira.medir_reacao` — **não escreva outro extrator de áudio**.

Rode em paralelo (`cortes_em_paralelo` já existe na config).

### Tarefa 4 — gravar e usar o deslocamento

- `gravador.escrever_gravacao` ganha o campo (cuidado: **não apague o que já
  está lá** — o arquivo é lido por `esteira._sessoes_do_canal`)
- `esteira.etapa_cortar` soma o deslocamento do canal antes de calcular a janela
- Deslocamento manual vence o de consenso, sempre

### Tarefa 5 — painel

- Campo de deslocamento por canal, editável (é o "atrasador" que o operador pediu)
- Botão "medir alinhamento" que roda o consenso sobre um gol já marcado
- Mostrar o espalhamento: se for grande, o operador precisa saber que a medida
  é frágil

### Tarefa 6 — o laço da ESPN

Só depois de tudo acima funcionar na mão. Um processo que pergunta de 20 em 20 s
e marca o gol. **Nunca** deixe o laço da ESPN derrubar a gravação: erro de rede
ali é um aviso, não uma exceção que sobe.

## 7. Régua de aceite

Sem estas medidas, **não afirme que funciona**:

1. **O consenso acerta**: rodando sobre os gols já gravados de 02/09/2026
   (`C:\REACAO DA TORCIDA\2026-09-02 vitoria x vasco`, gols marcados às
   23:12:36 e 23:29:03), a mediana dos picos deve cair a menos de 10 s do
   instante em que o clipe já cortado mostra a reação.
2. **Não inventa**: com um canal só acusando, nenhum deslocamento é gravado.
3. **O material existente prova**: o gol 1 tem 3 canais com pico; o gol 2 tem 4.
   Use os dois — um caso com 3 e um com 4 é melhor teste que dois iguais.
4. **A ESPN não trava nada**: desligue a internet no meio e a gravação continua.

## 8. Armadilhas já pagas (não repita)

- **yt-dlp desatualizado derruba tudo em 30 s**, com o processo vivo e mudo.
  Se a gravação morrer em meio minuto, rode `yt-dlp -U` **antes** de investigar
  qualquer outra coisa. Já custou uma noite.
- **`--encoding UTF-8`** no yt-dlp ao ler nome de canal, senão o acento vira
  lixo e o nome de pasta nasce errado para sempre (`dirio-do-peixe`).
- **Nunca mate processo por nome** (`Get-Process ffmpeg | Stop-Process`) enquanto
  houver gravação em andamento — derruba as outras partidas junto. Use os pids
  que estão em `gravacao.json`.
- **A mediana, não a média.** Um canal 56 s fora é caso real, não hipótese.
- **Teste nenhum pode depender de rede** nem de vídeo grande. Áudio sintético
  para o detector, JSON gravado para a ESPN, arquivos falsos para o resto.

## 9. Como trabalhar

Homologação existe e deve ser usada: worktree em
`C:\Users\user\Desktop\cods\reacao-da-torcida-homolog`, branch `homologacao`,
biblioteca própria em `C:\REACAO DA TORCIDA - HOMOLOG`. Merge para `main` só
depois de passar num teste com gravação de verdade.

Troca a quente já funciona: matar **só** o Python do supervisor
(`Stop-Process`, **sem** `/T`) e subir de novo — ele adota a gravação em
andamento sem perder um segundo. Ensaiado e usado em produção no dia 02/09.
