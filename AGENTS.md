# Regras deste projeto

Leia antes de escrever qualquer linha de código. Isto vale mais do que o hábito.

## Onde começar

1. `DESIGN.md` — como a tela se parece. Este arquivo diz como o codigo se escreve;
   aquele diz como a interface se veste. Leia antes de mexer em qualquer `.html`.
2. `docs/superpowers/specs/2026-09-01-reacao-da-torcida-design.md` — o desenho aprovado.
3. `docs/superpowers/plans/2026-09-01-reacao-da-torcida-plan.md` — as tarefas, em ordem.

O plano é para ser seguido na ordem. Cada tarefa entrega algo que roda e é testado.

## Onde tudo mora

Uma pasta só, na Área de Trabalho, fixada no Explorador:

```
Desktop\REACAO DA TORCIDA├── 0..4 - *.lnk        atalhos numerados, na ordem de uso
├── PROJETO\            este repositório (branch main)
├── MIDIA\              gravações, clipes e compilações
└── HOMOLOGACAO    ├── PROJETO\        worktree da branch homologacao
    └── MIDIA\          biblioteca de teste
```

A biblioteca tem que ficar em disco local. O `G:` é o Google Drive: gravar lá
dispara upload durante o jogo, e o upload disputa a mesma banda que baixa as
lives. Só a compilação pronta sobe para o Drive.

## A máquina onde isto roda

Windows 10, PowerShell. Ryzen 5 5600G (6 núcleos), 15,4 GB de RAM, **sem GPU dedicada**.

- **Placa de rede de 100 Mbps** (92 Mbps reais medidos). É o gargalo do projeto inteiro.
- **Grave sempre em disco local** (`C:`, com folga de centenas de GB). O `G:` é o
  Google Drive e está proibido: veja acima. Confira o espaço antes do jogo — onze
  canais comem dezenas de GB e o disco enche DEPOIS da largada.
- **Trave o formato em 720p.** A 1080p, 13 canais ocupam 85% da banda e a gravação cai
  no meio do jogo.
- Nada de modelo pesado de IA. Sem GPU, o detector tem que ser aritmética sobre o áudio.

## Ferramentas já instaladas

Conferido nesta máquina em 02/09/2026:

- `yt-dlp.exe` e `ffmpeg.exe` em `C:\yt-dlp`
- `ffprobe.exe` em **`C:\ffmpeg\bin`** — repare que **não** fica junto do ffmpeg do
  `C:\yt-dlp`. Está no PATH.
- `numpy` 2.5.2 já instalado
- Fonte da cartela: `C:\Windows\Fonts\arialbd.ttf` (o `drawtext` do ffmpeg no Windows
  exige `fontfile=` explícito, senão falha com "Cannot find a valid font")
- Python com faster-whisper e Ollama (do projeto LEGENDAR VIDEO) — **não são necessários
  aqui**, e usá-los seria contrariar o desenho.

## Como escrever

- **Teste antes do código.** pytest, e nenhum teste pode depender de internet ou de
  arquivo de vídeo grande. Áudio sintético para o detector, arquivos falsos para o resto.
- **A lógica mora no núcleo, não nos `.bat`.** Os `.bat` são cascas finas. É isso que
  permite pendurar um agendador por cima mais tarde sem reescrever nada.
- **Falha de um canal não derruba os outros.** Canal sem live é resultado normal, não erro.
- **Nada só na memória da página aberta.** Toda escolha do operador grava em disco na
  hora. Recarregar o painel não pode perder trabalho.
- **Nunca sumir calado.** Clipe que o detector não achou vai marcado em vermelho, não
  descartado.
- Português no código, nos commits e na interface. Nomes de módulo em português, como
  na spec.

## O que o placar e o áudio fazem, cada um

`docs/superpowers/specs/2026-09-02-alinhamento-e-gatilho-automatico.md` está **implementado**.
A divisão de trabalho é o coração dele:

- **`nucleo/placar.py` + `nucleo/vigia.py`** — a ESPN sabe **QUE** houve gol. Placar oficial,
  sem falso positivo. Mas tem atraso próprio e variável: nunca serve de relógio.
- **`nucleo/alinhamento.py`** — o áudio sabe **QUANDO** cada canal reagiu. Quando sai um gol,
  todo canal que o transmite explode, e a diferença entre os picos é o atraso entre eles.

Uma cobre exatamente o buraco da outra. Não tente usar só uma.

## Sobrar vídeo é barato; faltar não tem conserto

As duas falhas do corte não custam a mesma coisa, e o sistema é assimétrico de propósito:

- Canal **sem alinhamento confirmado** corta com `margem_sem_alinhamento` a mais de cada
  lado. O clipe sai longo, o operador apara no editor dele.
- Canal **com alinhamento confirmado** corta justo. A margem some sozinha conforme os gols
  vão confirmando o atraso daquele canal — os clipes apertam sem ninguém mexer.
- Cobertura **parcial** não é mais descartada: vem o que existe, marcado `parcial`. Metade
  do lance vale mais que nada.
- Só se desiste quando o material realmente não está no disco (`SEM MATERIAL`), e mesmo aí
  o canal aparece na saída com a cobertura que tem. **Nunca sumir calado.**

## Quatro coisas medidas em jogo, não deduzidas

**yt-dlp em dia é requisito, não higiene.** Com a versão de 04/08/2026, a gravação de
qualquer live morria entre 31 e 35 segundos: o YouTube passava a responder 403 em todo
pedaço e o processo continuava **vivo**, mudo, enganando o supervisor. Não era o cano, nem
falta de cookie, nem o downloader — tudo isso foi testado e deu o mesmo 403. Atualizando
para 30/08/2026, os mesmos canais gravaram 110 segundos seguidos sem um único erro. Se a
gravação voltar a morrer em meio minuto, rode `yt-dlp -U` antes de investigar qualquer
outra coisa. Passe sempre `--js-runtimes node`: o node já está na máquina e sem ele o
yt-dlp avisa que a extração está obsoleta.

**Medida de alinhamento só vale confirmada.** Rodando o consenso sobre os dois gols de
02/09/2026: dois canais deram +8,5/+10,0 e +12,5/+11,5 — estáveis. Um terceiro deu −54,5 e
+29,5, oitenta e quatro segundos de diferença; era o detector achando outra coisa no áudio
dele. Aplicado, aquele número jogou o corte para fora do lance (conferido quadro a quadro).
Por isso `alinhamento.estavel` exige duas medidas concordando antes de aplicar, e sem
confirmação o canal corta no horário cru.

**Canal pode baixar mais devagar do que o jogo acontece.** O ffmpeg entra na playlist
atrás da ponta e não alcança. O canal escreve bytes sem parar — passa por saudável em
qualquer teste de crescimento — e mesmo assim, quando sai o gol, o trecho ainda não
existe no disco. Medido em 02/09/2026: os saudáveis ficaram em 0,2 min de atraso e cinco
canais de onze em 60 min. `gravador.ficou_para_tras` compara conteúdo no disco contra
tempo decorrido e recomeça quem passou de cinco minutos.

**O t0 não é a hora em que o processo subiu.** Entre subir e o primeiro frame cabem o
arranque do yt-dlp e o trecho velho que ele puxa acelerado até alcançar o ao vivo. Medido:
meio minuto num teste, cinco segundos em outro — variável por canal. O t0 vem do relógio do
disco (`esteira.ancorar_t0`), não do `datetime.now()` do lançamento.

## O que não fazer

- Recodificar durante a gravação. A gravação é `-c copy`.
- Culpar o cano, o cookie ou o downloader quando a gravação morre em meio minuto.
  Veja acima: é o yt-dlp velho.
- Gravar `.mp4` direto. Processo morto deixa `.mp4` ilegível — por isso é MPEG-TS.
- Cortar pelo auge do grito. O corte é pelo **começo da subida**; o susto é a graça.
- Implementar fonte automática de placar, publicação, corte vertical ou gravação de dois
  jogos ao mesmo tempo. Está tudo fora do escopo, de propósito.

## Como saber se funcionou

O modo teste é a régua: rodar sobre um VOD com gols de posição conhecida e medir o erro
em segundos. Critério de aceite do piloto: **no máximo 3 segundos de erro em pelo menos
80% dos gols**. Sem essa medida, não afirme que funciona.
