# Laudo: o estúdio de edição rodado num jogo de verdade

Data: 2026-09-04
Jogo: `MIDIA\2026-09-03 gremio x internacional`
Código: commit `a8134b2` (os sete passos da seção 14 da spec do estúdio)

O `5 - EDICAO.bat` foi aberto no jogo real, o alvo foi posto em `inter`, o
RENDER FINAL rodou e o vídeo longo foi conferido de ponta a ponta: quadros
amostrados nos 12 minutos, áudio medido em 13 janelas, capa e `publicar.md`
abertos. Isto é o que quebrou, do pior para o menor. Cada item tem a prova que
o achou — quem for consertar não precisa refazer a medição.

O que **funcionou** está no fim, e não é pouco.

---

## 1. O corte pega o minuto ANTES do gol. O vídeo inteiro não tem reação

**O defeito.** `nucleo/esteira.py:422` grava em `instante` o `deslocamento`
devolvido por `cortador.preparar_fonte` — que é o offset de onde o corte começou
DENTRO do `.ts` de origem, e não o instante do pico dentro do clipe. Pior:
`medir_reacao` (`nucleo/esteira.py:367`) chama `detector.analisar`, que devolve
exatamente o número certo em `achado.instante`, e **joga ele fora**, devolvendo
só `(confianca_db, tem_pico)`.

**A prova.** Rodei o detector de novo em cima dos clipes:

| Clipe | Pico real | `instante` no catálogo | Janela que o estúdio cortou |
| --- | --- | --- | --- |
| gol 1 `farid-germano-filho` | **80,0 s** | 0,0 | 0–60 s |
| gol 3 `farid-germano-filho` | **34,5 s** | 21,8 | 3,6–63,6 s |
| gol 1 `baldasso-tv` | 158,0 s (sem pico) | 0,0 | 0–60 s |

Os clipes são cortados com `segundos_antes: 60`, ou seja o gol está no segundo
60. Com o pico em 80,0 s e a janela indo até 60 s, **o grito não entra no
clipe**. No vídeo montado, os três canais do bloco GOL 1 mostram o placar da
própria transmissão ainda em **0x0** — o gol não acontece na tela nenhuma vez.

**Quem mais depende disso:** `melhor.janela_do_clipe`, `estudio.instante_de_espiar`
(o botão ESPIAR e o quadro da capa) e `capa.rostos` — a capa pega os rostos no
momento calmo, que é o oposto do que ela existe para mostrar.

**Conserto.** `medir_reacao` devolve também o instante; `ClipeCortado` ganha o
campo; `cortar_um_canal` passa o instante do detector e não o deslocamento. Mais
um comando que recalcula o `instante` dos jogos já cortados — ele só extrai o
wav e roda o detector, não recorta vídeo (~25 s por clipe, ~10 min nos 24).

---

## 2. Um clipe sumiu do vídeo e o painel disse "pronto"

**O defeito.** `estudio.montar:357` decide reaproveitar o cache com
`if destino.is_file()`. Quando um render morre no meio de um item, o ffmpeg
deixa no disco um `.mp4` **de 48 bytes** (só o `ftyp`, sem `moov`). O render
seguinte reaproveita esse arquivo como se fosse bom, o `concat` engole, e a
compilação sai sem aquele clipe — sem uma linha de aviso.

**A prova.** O painel prometia 12:08 (728,0 s). O arquivo saiu com **668,3 s =
11:08**, exatamente os 60 s do `baldasso-tv` no gol 4. Mandei RENDER de novo
duas vezes: das duas o log disse `reaproveitado: baldasso-tv no gol 4` e o vídeo
continuou com 11:08. **Repetir o render não conserta** — o lixo é permanente até
alguém apagar o arquivo na mão.

**Conserto.** Renderizar para `<nome>.parcial` e renomear só quando o ffmpeg
sair com zero; e conferir o candidato do cache (tamanho mínimo / `ffprobe`)
antes de reaproveitar.

---

## 3. O render trava e não tem tempo-limite

**O defeito.** `cortador.executar:37` é
`subprocess.run(comando, check=True, capture_output=True)` — sem `timeout=`.
Quando o ffmpeg trava, o render espera para sempre e o painel fica "rodando"
para sempre. E como o `capture_output=True` engole o stderr, o operador nunca vê
o motivo: quando enfim quebra, o console mostra um traceback de Python.

**A prova.** O ffmpeg travou com **0% de CPU e ~1,4 GB de RAM presos**, saída
congelada nos 48 bytes do cabeçalho, por 11 minutos, até eu matar. Aconteceu nos
dois renders lançados pelo painel e também rodando o `nucleo.esteira render`
direto do terminal.

**O que ainda não sei.** A causa. O mesmo comando rodado na mão termina em 23 s.
Repetindo o mesmo item 10 vezes, ele travou em ~2 de cada 3 — é intermitente, e
piora com a RAM apertada (a máquina tem 15,4 GB, sobravam 3,4 GB, e o pagefile
está capado em 10 GB). Não é o stdin (`-nostdin` não muda), não é o
`capture_output` (o mesmo `subprocess.run` às vezes passa), não é a fonte do
`drawtext`. Limitar as entradas de imagem com `-t` melhorou (3 de 4 passaram) e
trocar `-shortest` por `-t` na saída **piorou** (0 de 3).

**Conserto (a dor, não a causa).** `timeout=` no `executar`, tentar o item de
novo N vezes, e mostrar as últimas linhas do stderr do ffmpeg quando falhar.
Assim um travamento vira "item X falhou, refazendo" em vez de painel morto.

---

## 4. Não existe onde digitar o placar

A seção 14.2 da spec do estúdio mandou isso para o painel do passo 5, e ele não
veio: `painel/edicao.py` não tem rota de placar e `painel/edicao.html` não tem
campo. Só a `nucleo/vigia.py:93` escreve placar, e só enquanto o jogo está no
ar — o jogo de 03/09 ficou sem.

**O que isso custa:** o estúdio abre com `alvo: "sem placar"` e **nada marcado**;
as cartelas saem escritas só `GOL 3`; o quadro fica sem placar; e o título do
`publicar.md` sai `REAÇÕES dos COLORADOS - GRÊMIO  INTERNACIONAL - VAMOS RIR DO
INTER!`, sem o 3x1.

**Conserto.** Um campo no painel e uma rota `POST /api/placar` chamando
`catalogo.registrar_placar`, que já existe e já é testado.

---

## 5. Clipes do mesmo gol vêm de momentos diferentes do jogo

**A prova**, lida nos relógios da própria transmissão dentro do vídeo montado:

| Gol | `baldasso-tv` | `paulo-brito` | `farid-germano-filho` |
| --- | --- | --- | --- |
| 3 (marcado 21:30:01) | 2T 23:04, 3×0 | 22:36, 2-0 | **1º TEMPO 22:55**, 2×0 |
| 4 (marcado 21:39:45) | 2T 32:16, 3×0 | 32:19, 3-0 | **1º TEMPO 32:45**, 3×0 |

Com o pontapé por volta das 20:01 (o gol 1, às 20:13:32, cai em 1T 12:15), a
marca das 21:30 é segundo tempo — o `baldasso-tv` bate. O `farid-germano-filho`
está no primeiro tempo nos dois gols, cerca de 45 minutos de jogo fora do lugar,
e o `paulo-brito` também erra o gol 3.

`baldasso-tv` não religou uma vez. `farid-germano-filho` religou 55x e
`paulo-brito` 61x. O suspeito é o mapa hora-do-relógio → posição no arquivo
quando o canal tem buracos de gravação (`relogio`/`cronometro`/`_gols_a_cortar`).

Isto é da esteira de corte, não do estúdio — mas é o segundo pior estrago no
vídeo, e o estúdio não tem como perceber.

**Mitigação barata, enquanto não conserta:** o estúdio marcar em vermelho todo
clipe cujo pico de áudio não caia perto do segundo 60.

---

## 6. A capa fica com dois buracos

`capa.py:CAIXAS` é um layout fixo de 1 rosto grande + 4 pequenos, cinco canais.
Entraram três. Sobra um quadrante vermelho vazio embaixo à direita, e a
composição fica torta. Some com isso um layout que se adapte a 1, 2, 3, 4 ou 5.

E, por causa do item 1, os "rostos" são o quadro inteiro da live no momento
calmo — nada de rosto, nada de frustração.

---

## 7. Miudezas

| O que | Onde |
| --- | --- |
| A prévia levou **48 s** (a spec promete "segundos") e usou `libx264`: `codec_previa` não existe no `dados/config.json`, e o padrão do código é o libx264, não o `h264_amf` da spec | `estudio.previa:439` |
| Ao clicar RENDER, a resposta imediata já diz "o render parou sozinho antes de terminar" — o `tasklist` ainda não enxerga o PID recém-criado. Some no refresh seguinte, mas é a primeira coisa que o operador lê | `estudio.estado:512` |
| O painel escreve `total: 12` (os clipes) e o render troca para `16` (com as cartelas): a barra anda para trás | `painel/edicao.py` × `estudio.montar` |
| `#copa-do-brasil` no `publicar.md`: hashtag com hífen não funciona no YouTube nem no Instagram | `nucleo/publicacao.py` |
| O gol 5 aparece no painel com 0 reações; os três `.mp4` em `clipes/gol-05/` estão corrompidos (sem `moov`), de um corte interrompido | pasta do jogo |
| O `render.json` em disco continua com `rodando: true` depois de o processo morrer — quem corrige é só a leitura | `estudio.estado` |

---

## O que funcionou

Molde e quadro (cantos arredondados, borda, tarja, e o nome do canal não vaza),
fundo na cor do time perdedor, áudio normalizado e uniforme (-17 a -22 dB de
média nas 13 janelas medidas ao longo dos 12 minutos), cache por item (o segundo
render reaproveitou 15 de 16 peças em segundos), emenda sem costura visível,
créditos certos no `publicar.md` com o nome de verdade de cada canal, o painel
detectando pelo PID um render que morreu, e o ESPIAR instantâneo (0,4 s).

O render inteiro, 16 peças, levou **cerca de 5 minutos** nesta máquina.

---

## Onde estão as peças desta rodada

`MIDIA\2026-09-03 gremio x internacional\saida\` — `compilacao-deitado.mp4`
(12:13; o operador esticou a alça do Farid no gol 1 para 65,5 s), `capa.jpg` e
`publicar.md`. O `rindo_de: inter` ficou gravado no catálogo.
