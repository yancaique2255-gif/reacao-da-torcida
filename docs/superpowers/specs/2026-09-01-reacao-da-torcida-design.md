# REAÇÃO DA TORCIDA — desenho do projeto

Data: 01/09/2026
Status: aprovado, aguardando implementação

## O que é

Ferramenta para produzir vídeos de compilação de reações de torcida. Durante um jogo,
o sistema grava as lives de vários canais de YouTube da torcida de um time. Quando sai
um gol contra esse time, ele acha o instante exato da reação em cada gravação, corta um
clipe curto de cada canal e organiza tudo numa pasta. Depois, um painel local deixa o
operador ouvir cada reação, escolher as boas e montar a compilação.

O trabalho braçal (ficar com 13 abas abertas, achar o momento, cortar um por um) vira
automático. A curadoria — decidir qual reação tem graça — continua sendo do operador,
de propósito.

## Por que assim

Três decisões definem o projeto:

**Grava ao vivo, não baixa VOD depois.** Canal de torcida costuma apagar ou deixar a
live privada quando o time perde feio — que é exatamente o material que interessa. Se
esperar o jogo acabar, o vídeo já era.

**Placar diz *que* houve gol; o áudio diz *onde* cortar.** Cada live tem atraso próprio,
de 30 segundos a 2 minutos, e o atraso varia dentro do mesmo jogo. Não existe um
"segundo 4.412" que sirva para todos os canais. Então a informação de placar só delimita
uma janela larga de busca, e a explosão do narrador dentro de cada gravação define o
corte daquele canal. Consequência prática importante: **fonte de placar imprecisa ou
atrasada não atrapalha**, o que faz plano grátis de API caber no projeto.

**Esteira de `.bat` numerados + núcleo Python + painel HTML.** É o mesmo desenho de
LEGENDAR VIDEO e VEIA BANGUELA, os outros projetos da casa. O operador já sabe operar
sem manual, e o núcleo fica testável com pytest.

## O ambiente

Medido em 01/09/2026 na máquina onde isto vai rodar:

| Recurso | Situação | O que isso impõe |
|---|---|---|
| Processador | Ryzen 5 5600G, 6 núcleos / 12 threads | Folgado. Gravação é cópia direta, sem recodificar. |
| Memória | 15,4 GB (≈5 GB livres em uso normal) | 13 gravações usam ~2–3 GB. Cabe, sem exagero de abas abertas. |
| Placa de rede | **100 Mbps**, com 92 Mbps reais medidos | **É o gargalo.** Teto seguro: ~20 canais a 720p. |
| Vídeo | Radeon integrada, sem GPU dedicada | Nada de modelo pesado de IA. O detector é aritmética simples. |
| Disco | C: 347 GB, **G: 323 GB**, H: 93 GB livres | Grava no `G:`. ~3,4 GB por canal num jogo de 2h30. |

Daí as duas travas obrigatórias: **formato limitado a 720p** (reação de torcedor não
precisa de mais) e **biblioteca no `G:`**, nunca no `C:`.

## Arquitetura

### A esteira

```
0 - CANAIS.bat     cadastrar canais por time e ver quem está ao vivo
1 - GRAVAR.bat     iniciar as gravações do jogo
2 - CORTAR.bat     informar os gols e gerar os clipes
3 - ESTUDIO.bat    ouvir, escolher e montar a compilação
```

Cada `.bat` é uma casca fina que chama o núcleo Python. Toda a lógica fica no núcleo,
testável sem interface.

### Os módulos

| Módulo | Responsabilidade | Depende de |
|---|---|---|
| `canais` | Cadastro time → canais. Descobrir a live ativa de um canal. | yt-dlp |
| `gravador` | Subir e supervisionar N gravações em paralelo. Religar o que cair. | yt-dlp, ffmpeg |
| `relogio` | Traduzir horário de relógio em (arquivo, segundo). É a peça central. | nada |
| `detector` | Achar o início da explosão de áudio dentro de uma janela. | ffmpeg, numpy |
| `cortador` | Extrair o clipe, mesmo quando ele atravessa dois pedaços. | ffmpeg |
| `catalogo` | Estado do jogo em disco: gols, clipes, confiança, escolhas. | nada |
| `montador` | Juntar os clipes escolhidos numa compilação com cartelas. | ffmpeg |
| `painel` | Servidor local + página de curadoria. | catalogo, montador |

Cada módulo tem uma fronteira estreita: `detector` recebe um caminho de wav e devolve
um instante, não sabe o que é futebol. `relogio` faz aritmética de tempo e não abre
arquivo de vídeo. `cortador` não sabe de gols, recebe início e fim.

### Fluxo

```
canais.json
    │
    v
gravador ──> G:\...\<jogo>\bruto\<canal>\parte-001.ts, parte-002.ts...
             + segmentos.csv (início e fim de cada pedaço)
             + gravacao.json (horário real do primeiro frame)
                    │
horário dos gols ───┤
(operador informa)  │
                    v
             relogio ──> janela de busca por canal (−30s a +180s)
                    │
                    v
             detector ──> instante do início do grito + confiança
                    │
                    v
             cortador ──> clipes\gol-01\<canal>.mp4
                    │
                    v
             catalogo.json ──> painel (curadoria) ──> montador ──> saida\compilacao.mp4
```

## As peças em detalhe

### canais

`dados/canais.json` guarda times e seus canais:

```json
{
  "cruzeiro": [
    {"nome": "Canal Exemplo", "url": "https://www.youtube.com/@exemplo", "ativo": true}
  ]
}
```

Para descobrir se um canal está ao vivo, consulta `<url do canal>/live` com
`yt-dlp --print`. Canal sem live devolve erro — isso é resultado normal, não falha:
registra e segue para o próximo.

### gravador

Uma gravação por canal, em processo próprio. O comando é um cano de yt-dlp para ffmpeg:

```
yt-dlp -f "bv*[height<=720]+ba/b[height<=720]" -o - <url>
  | ffmpeg -i pipe: -c copy -f segment -segment_time 600
      -segment_format mpegts -reset_timestamps 1
      -segment_list segmentos.csv -segment_list_type csv
      parte-%03d.ts
```

Três decisões dentro desse comando:

- **`-c copy`**: não recodifica. É por isso que 13 gravações custam ~10% do processador.
- **MPEG-TS em pedaços de 10 minutos**: `.ts` sobrevive a processo morto (`.mp4` sem
  finalizar fica ilegível), e pedaços de 10 min tornam a busca por tempo precisa e barata.
- **`-segment_list segmentos.csv`**: o próprio ffmpeg escreve `arquivo,início,fim` de cada
  pedaço. Esse arquivo é metade do manifesto — a outra metade é o horário de relógio.

Um detalhe que morde: **o ffmpeg só escreve a linha do CSV quando o pedaço fecha.**
Encerrar a gravação mata o processo no meio de um pedaço de 10 minutos — o `.ts` fica no
disco, mas fora do manifesto. Como gol no fim de jogo é o material mais valioso, na hora
de cortar o sistema varre a pasta e mede com `ffprobe` qualquer pedaço órfão, em vez de
declarar "não coberto".

`gravacao.json` guarda, por canal: url, horário local do início (`t0`), formato obtido,
e a lista de sessões. Se a gravação cair e religar, abre uma nova sessão com seu próprio
`t0` e o buraco fica registrado e visível.

O gravador recusa começar se o disco livre estiver abaixo do mínimo configurado, e avisa
(sem bloquear) se o número de canais passar do teto de banda calculado.

### relogio

Traduz um horário de relógio (ex.: 21:37:00) para um par (arquivo, segundo), somando o
`t0` da sessão com os intervalos do `segmentos.csv`. Trata: pedaços de duração desigual,
buracos entre sessões, e horário que cai fora de qualquer gravação (devolve "não coberto",
não estoura).

**Entrada dos gols.** O operador informa apenas os gols **contra** o time cujos canais
foram gravados — é a reação de quem sofreu que vira vídeo. O dado é o **horário de
relógio** do gol: não precisa de conversão nenhuma e é o que uma API de placar entrega.
Informar por minuto
de jogo ("38 do 2º tempo") é opcional e só funciona se os horários de início de cada tempo
tiverem sido registrados, porque acréscimo e intervalo tornam a conversão impossível sem
eles.

**A virada da meia-noite.** Jogo de Copa do Brasil começa 21:30 e termina depois da
meia-noite. O horário informado (`00:05`) é resolvido contra o intervalo realmente gravado,
escolhendo entre o dia do início e o seguinte — colar na data de hoje jogaria o gol doze
horas antes do começo da gravação.

**Janela de busca:** de `gol − 30s` a `gol + 180s`, configurável. Larga de propósito: o
atraso da live é desconhecido e variável, e o áudio é quem resolve.

### detector

Recebe um arquivo e uma janela. Extrai o áudio com
`ffmpeg -ss <início> -i <arquivo> -t <duração> -vn -ac 1 -ar 16000 -f wav -`,
calcula a energia RMS em quadros de 0,5 s e suaviza com média móvel de 3 s.

Sobre a curva suavizada:

- **pico** = ponto de maior energia da janela;
- **linha de base** = mediana da janela;
- **instante do corte** = o ponto da subida, antes do pico, em que a curva cruza
  `base + 50% da altura do pico`. Esse é o começo do grito, não o auge dele — cortar pelo
  auge perde o susto, que é a parte engraçada;
- **confiança** = quantos dB o pico está acima da linha de base.

Abaixo do limiar de confiança (padrão 6 dB) devolve `sem_pico`. Nesse caso o `cortador`
corta pelo tempo estimado mesmo assim, e o clipe é marcado em vermelho no painel para
conferência manual — nunca sumindo silenciosamente.

Isso é aritmética sobre alguns minutos de áudio: roda em segundos, sem IA, sem GPU.

### cortador

`início = instante − 8s`, `fim = instante + 12s` (configurável). Como o corte precisa ser
preciso, recodifica só esses 20 segundos:

```
ffmpeg -ss <início> -i <fonte> -t <duração>
  -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 128k <saida>.mp4
```

Quando a janela atravessa a fronteira entre dois pedaços, junta os pedaços envolvidos
num arquivo temporário antes de cortar. Esse caso **precisa de teste** — é o defeito mais
provável do módulo.

### catalogo

`catalogo.json` na pasta do jogo é o estado inteiro: gols (horário, descrição), clipes
(canal, arquivo, instante achado, confiança, `sem_pico`), e as escolhas do operador.
Tudo em disco, nada só na memória da página aberta — recarregar o painel não pode perder
trabalho.

### montador

Recebe a lista de clipes escolhidos, normaliza todos para 1280x720 a 30 fps (canais
diferentes entregam formatos diferentes), sobrepõe o nome do canal nos primeiros
3 segundos de cada trecho e concatena. Saída em `saida/compilacao.mp4`.

### painel

Servidor `http.server` local servindo a página e os clipes como arquivos estáticos, para
o `<video>` do navegador tocar direto. A página mostra um bloco por gol com os canais
lado a lado, marcação ✓/✗ por clipe, destaque vermelho nos `sem_pico`, e um botão MONTAR.
Toda marcação grava no `catalogo.json` na hora.

## Modo teste — a régua do projeto

`testar` recebe um VOD (arquivo local ou link) e a lista de instantes onde os gols
realmente estão, roda detector e cortador, e informa **de quantos segundos errou em cada
gol**. Sem essa medida não existe base para afirmar que o sistema funciona.

É por aqui que o piloto começa: um canal, um VOD de live já encerrada, gols de posição
conhecida. Só depois de o erro ser aceitável é que se liga gravação ao vivo.

Critério de aceite do piloto: erro de no máximo 3 segundos em pelo menos 80% dos gols de
um VOD de referência.

## Quando dá errado

| Situação | Comportamento |
|---|---|
| Canal sem live no ar | Registra e segue. Não derruba os outros canais. |
| Gravação cai no meio | Religa em nova sessão. O buraco fica registrado no manifesto e visível no painel. |
| Sem pico na janela | Corta pelo tempo estimado, marca `sem_pico`, sinaliza em vermelho. Nunca some calado. |
| Disco abaixo do mínimo | Recusa iniciar, antes de gravar — não no meio do jogo. |
| Canais acima do teto de banda | Avisa e pede confirmação. Não bloqueia. |
| Horário do gol fora da gravação | Devolve "não coberto" e diz o intervalo que foi realmente gravado. |

## Testes

pytest, no espírito do LEGENDAR VIDEO. **Nenhum teste pode depender de internet.**

- `relogio`: horário → (arquivo, segundo), com pedaços de duração desigual, com buraco
  entre sessões, e com horário fora de cobertura.
- `detector`: wav sintético com pico em posição conhecida → acha o começo da subida, não
  o auge. Wav de ruído constante → devolve `sem_pico`.
- `cortador`: janela dentro de um pedaço e janela atravessando dois pedaços.
- `catalogo`: escrita e releitura sem perder escolhas.
- `montador`: lista de clipes falsos → comando ffmpeg correto (sem executar codificação
  pesada no teste).

## Fora do escopo

De propósito, e não por esquecimento:

- Escolher sozinho a melhor reação. A curadoria é humana.
- Publicar nas redes. Isso é assunto do VEIA BANGUELA.
- Corte vertical para Shorts/Reels.
- Gravar mais de um jogo ao mesmo tempo.
- Fonte automática de placar (ver abaixo).
- **Limpeza automática do bruto.** Cada jogo deixa ~44 GB e o `G:` comporta ~7 antes de
  encher. Por ora o operador apaga a pasta `bruto/` na mão depois de montar a compilação;
  o sistema só avisa quando o disco está baixo, e recusa começar. Automatizar isso é a
  terceira evolução prevista.

## Depois do piloto

Duas evoluções já previstas, com o encaixe deixado pronto no desenho:

**Fonte automática de placar.** Hoje o operador informa o horário do gol. O `relogio`
recebe esse dado por uma interface estreita, então trocar "operador digita" por "API
avisa" não mexe em nenhum outro módulo. Levantamento inicial das opções gratuitas:

| Fonte | Grátis | Ressalva |
|---|---|---|
| football-data.org | 10 req/min, 12 competições incluindo Brasileirão Série A | Placar com atraso e **sem Copa do Brasil** |
| API-Football | ~100 requisições/dia | Cobre Copa do Brasil e estaduais; teto dá ~2 jogos/dia |
| Endpoint público da ESPN | sem cadastro | Não é API oficial, pode mudar sem aviso |

**Os limites e coberturas acima precisam ser reconferidos na hora de implementar** — mudam
com frequência. Como o áudio resolve o segundo exato, consulta de 2 em 2 minutos basta, e
é isso que faz o plano grátis caber.

**Serviço que roda sozinho.** Um agendador que lê o calendário de jogos, acorda na hora,
dispara o `gravador`, roda o `cortador` no fim e avisa que os clipes estão prontos.
Pendurado por cima da esteira atual, sem reescrever nada — foi por isso que a lógica ficou
toda no núcleo e não nos `.bat`.

## Estrutura em disco

Repositório (na Área de Trabalho, `REACAO DA TORCIDA`):

```
0 - CANAIS.bat
1 - GRAVAR.bat
2 - CORTAR.bat
3 - ESTUDIO.bat
nucleo/        canais, gravador, relogio, detector, cortador, catalogo, montador
painel/        html, css, js e o servidor local
testes/        pytest
dados/         config.json, canais.json
docs/          esta spec e o plano de implementação
```

Biblioteca de mídia (fora do repositório, no `G:`):

```
G:\REACAO DA TORCIDA\
  2026-09-01 atletico-mg x cruzeiro\
    bruto\<canal>\parte-001.ts, segmentos.csv, gravacao.json
    clipes\gol-01\<canal>.mp4
    catalogo.json
    saida\compilacao.mp4
```

## Configuração

`dados/config.json`, com estes padrões:

| Chave | Padrão | Para quê |
|---|---|---|
| `biblioteca` | `G:\REACAO DA TORCIDA` | Onde a mídia mora. Nunca no `C:`. |
| `altura_maxima` | `720` | Trava de banda. |
| `segundos_antes` / `segundos_depois` | `8` / `12` | Tamanho do clipe em volta do grito. |
| `janela_antes` / `janela_depois` | `30` / `180` | Busca em volta do horário informado. |
| `limiar_confianca_db` | `6` | Abaixo disso, `sem_pico`. |
| `duracao_pedaco` | `600` | Segundos por pedaço de gravação. |
| `teto_canais` | `20` | Limite de banda dos 100 Mbps. |
| `disco_minimo_gb` | `60` | Recusa gravar abaixo disso. |
| `segundos_entre_conferencias` | `20` | De quanto em quanto o supervisor confere as gravações. |
| `fonte_cartela` | `arialbd.ttf` | O `drawtext` do ffmpeg no Windows exige fonte explícita. |
