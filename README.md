# REAÇÃO DA TORCIDA

Ferramenta para montar vídeos de compilação de reações de torcida a gols.

Durante o jogo, grava as lives dos canais de YouTube da torcida de um time. Quando sai um
gol contra esse time, acha o instante exato da reação **dentro de cada gravação** — cada
live tem seu próprio atraso — corta um clipe curto de cada canal e organiza numa pasta.
Depois, um painel local deixa ouvir cada reação, escolher as boas e montar a compilação.

O trabalho braçal é automático. A escolha de qual reação tem graça continua sendo de
quem edita.

## A esteira

```
0 - CANAIS.bat     cadastrar canais por time e ver quem está ao vivo
1 - GRAVAR.bat     iniciar as gravações do jogo
2 - CORTAR.bat     informar os gols e gerar os clipes
3 - ESTUDIO.bat    ouvir, escolher e montar a compilação
```

## Como acha o momento certo

O placar diz **que** houve gol. O áudio diz **onde** cortar.

Cada live atrasa de 30 segundos a 2 minutos, e o atraso muda durante o jogo — não existe
um instante único que sirva para todos os canais. Então o horário do gol só delimita uma
janela larga de busca, e a explosão do narrador dentro de cada gravação define o corte
daquele canal.

Por causa disso, **fonte de placar atrasada ou imprecisa não atrapalha** — o que mais
tarde vai permitir usar plano grátis de API de futebol.

## Situação

Desenho aprovado, implementação não começou.

- Desenho: [`docs/superpowers/specs/2026-09-01-reacao-da-torcida-design.md`](docs/superpowers/specs/2026-09-01-reacao-da-torcida-design.md)
- Plano: [`docs/superpowers/plans/2026-09-01-reacao-da-torcida-plan.md`](docs/superpowers/plans/2026-09-01-reacao-da-torcida-plan.md)
- Regras da casa: [`AGENTS.md`](AGENTS.md)

O piloto é **um canal**, calibrado sobre um VOD de live já encerrada com gols de posição
conhecida. Só depois de o erro ficar aceitável é que se liga a gravação ao vivo.
