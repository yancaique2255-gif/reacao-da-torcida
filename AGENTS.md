# Regras deste projeto

Leia antes de escrever qualquer linha de código. Isto vale mais do que o hábito.

## Onde começar

1. `docs/superpowers/specs/2026-09-01-reacao-da-torcida-design.md` — o desenho aprovado.
2. `docs/superpowers/plans/2026-09-01-reacao-da-torcida-plan.md` — as tarefas, em ordem.

O plano é para ser seguido na ordem. Cada tarefa entrega algo que roda e é testado.

## A máquina onde isto roda

Windows 10, PowerShell. Ryzen 5 5600G (6 núcleos), 15,4 GB de RAM, **sem GPU dedicada**.

- **Placa de rede de 100 Mbps** (92 Mbps reais medidos). É o gargalo do projeto inteiro.
- **Grave sempre no `G:`** (323 GB livres). Nunca encher o `C:`.
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

## Duas coisas medidas em jogo, não deduzidas

**O download do HLS é do yt-dlp, nunca do ffmpeg.** Para live, o yt-dlp entrega o HLS ao
ffmpeg por padrão; o ffmpeg guarda a URL dos pedaços e não renova. Medido em quatro canais
nesta máquina: entre 31 e 35 segundos, o YouTube responde 403 em todo pedaço e a gravação
para — **com o processo vivo**. Não é o cano nem falta de cookie (testado sem cano e com os
cookies do Opera: mesmos 403). O que resolve é `--downloader m3u8:native`. E como a saída
padrão não junta duas faixas, o formato tem que ser um combinado único (`b[height<=720]`).

**O t0 não é a hora em que o processo subiu.** Entre subir e o primeiro frame cabem o
arranque do yt-dlp e o trecho velho que ele puxa acelerado até alcançar o ao vivo. Medido:
meio minuto num teste, cinco segundos em outro — variável por canal. O t0 vem do relógio do
disco (`esteira.ancorar_t0`), não do `datetime.now()` do lançamento.

## O que não fazer

- Recodificar durante a gravação. A gravação é `-c copy`.
- Deixar o ffmpeg baixar o HLS. Veja acima: morre calado em meio minuto.
- Gravar `.mp4` direto. Processo morto deixa `.mp4` ilegível — por isso é MPEG-TS.
- Cortar pelo auge do grito. O corte é pelo **começo da subida**; o susto é a graça.
- Implementar fonte automática de placar, publicação, corte vertical ou gravação de dois
  jogos ao mesmo tempo. Está tudo fora do escopo, de propósito.

## Como saber se funcionou

O modo teste é a régua: rodar sobre um VOD com gols de posição conhecida e medir o erro
em segundos. Critério de aceite do piloto: **no máximo 3 segundos de erro em pelo menos
80% dos gols**. Sem essa medida, não afirme que funciona.
