# Artes de fundo do palco

`fundo-estadio-monterrey.png` — 1920×1080, o cenário que fica atrás da janela da
reação no arranjo `palco-lateral`.

- **Origem:** foto do Estádio BBVA (Monterrey), do Pexels:
  https://www.pexels.com/photo/people-inside-a-football-stadium-12327672/
- **Licença:** Pexels License — uso comercial liberado, sem exigência de crédito.
  A licença cobre a fotografia; as marcas que aparecem dentro dela não são
  licenciadas, e por isso o corte deixa a publicidade de campo atrás da janela
  do vídeo.
- **Tratamento:** cortada cobrindo 16:9, escurecida 45%, saturação a 85% e
  vinheta nas pontas. Sem esse tratamento a foto disputa atenção com o clipe, e
  a logo na coluna da esquerda some em cima da arquibancada.

Trocar a arte é trocar o caminho em `arte_de_fundo`, no `dados/identidade.json`
(esse arquivo é pessoal e não entra no Git). O estúdio percebe a troca sozinho:
o relógio e o tamanho do arquivo entram na assinatura do palco.

## A logo

`logo-reacao-da-torcida.png` — 1222×1171, PNG com transparência. É o medalhão
recortado da arte do canal (os dois torcedores no círculo laranja): o papel de
fundo saiu por preenchimento a partir das bordas, e as sombras de bolinha que
sobraram foram apagadas mantendo só a ilha do meio.

O estúdio encaixa a logo INTEIRA na caixa do arranjo, sem deformar e sem cortar
— então a moldura circular pode passar perto da borda sem risco.
