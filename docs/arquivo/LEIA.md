# Código que saiu do caminho

Estes dois módulos foram escritos antes de a esteira existir e não são mais
chamados por ninguém. Ficam aqui porque a ideia deles pode voltar a servir,
mas fora de `nucleo/` para não dar a impressão de que participam do fluxo.

- **`corte_manual.py`** — cortava um VOD já baixado nos instantes informados.
  Hoje `esteira cortar` faz isso e mais, trabalhando sobre a gravação ao vivo.
- **`teste_vod.py`** — media o erro do detector contra um VOD com gols de
  posição conhecida. Era a régua do detector quando ele decidia sozinho onde
  estava o gol; hoje quem decide é o placar, e o detector só mede intensidade
  e alinhamento.
