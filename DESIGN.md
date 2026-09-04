# DESIGN.md — REAÇÃO DA TORCIDA

O par visual do `AGENTS.md`. Aquele diz **como o código se escreve**; este diz **como a
tela se parece**. Leia antes de mexer em qualquer `.html` do projeto.

O projeto tem três telas, e elas não competem:

| Tela | Arquivo | Porta | Quando é usada |
| --- | --- | --- | --- |
| Painel da gravação | `painel/gravacao.html` | 8771 | **Durante** o jogo, de canto de olho |
| Estúdio | `painel/pagina.html` | 8770 | **Depois** do jogo, escolhendo clipe |
| Estúdio de edição | `painel/edicao.html` | 8772 | **Depois** da escolha, montando o vídeo |

O estúdio de edição nasceu ao lado do da 8770, e não no lugar dele: reforma
grande não se faz na ferramenta em uso. Os três `:root` têm os mesmos tokens, e
a bateria reprova se um divergir.

---

## 1. Tema visual e atmosfera

Sala escura, jogo na TV, painel num monitor lateral. Quem olha não está lendo: está
**conferindo**. A tela tem que responder de relance, a dois metros de distância, com o
rabo do olho.

Daí três compromissos que valem mais que estética:

- **Escuro sempre.** Não existe modo claro, e não é preguiça: tela clara num quarto
  escuro ofusca e apaga a diferença entre verde e vermelho, que é a informação mais
  importante da tela.
- **Cor é estado, nunca enfeite.** Se uma cor aparece, ela quer dizer alguma coisa. Um
  botão azul e um botão verde são coisas diferentes, e não duas opções de gosto.
- **Nada pisca à toa.** Movimento é caro: só o que mudou tem direito a se mexer.

O estúdio é mais espaçoso e pode respirar — ninguém escolhe clipe com pressa. O painel
da gravação é apertado de propósito: cabe tudo sem rolar a página.

---

## 2. Paleta e o papel de cada cor

Os tokens vivem no `:root` de cada tela e têm **o mesmo nome e o mesmo valor nas duas**.
Se você precisar de uma cor que não está aqui, o problema é o estado que você está
inventando, não a paleta.

| Token | Valor | Papel |
| --- | --- | --- |
| `--fundo` | `#0f1115` | Fundo da página. Nada mais usa. |
| `--caixa` | `#171a21` | Superfície de cartão, tabela, quadro. |
| `--caixa-2` | `#1e222c` | Segunda camada: botão dentro de cartão, cabeçalho de tabela. |
| `--linha` | `#242833` | Toda borda e todo divisor. |
| `--texto` | `#e7e9ee` | Texto normal. |
| `--fraco` | `#8b93a7` | Rótulo, unidade, legenda, texto secundário. |
| `--viva` | `#35d07f` | **Está funcionando**: canal gravando, corte pronto. |
| `--morta` | `#ff5c5c` | **Parou**: canal caído, corte que morreu no meio. |
| `--alerta` | `#ffb020` | **Anda, mas confira**: cortando agora, cobertura parcial, medida que discordou. |
| `--info` | `#63a9ff` | Ação neutra que abre outra coisa (abrir pasta, ver quadro). |
| `--gol` | `#e5342b` | Só o botão MARCAR GOL. Mais nada no projeto tem direito a este vermelho. |

**Fundo colorido é a cor a 16% sobre a caixa**, nunca a cor cheia:
`background: rgba(53,208,127,.16)` com `color: var(--viva)`. Cor cheia com texto por cima
não passa em contraste e grita mais alto que o gol.

### O que cada cor NÃO pode fazer

- Verde não quer dizer "bom", quer dizer **vivo**. Um clipe ruim de um canal que gravou
  direito continua verde.
- Vermelho não quer dizer "erro do usuário", quer dizer **parou**. Erro de digitação é
  âmbar.
- `--gol` não é o vermelho de erro. São dois vermelhos diferentes de propósito: um chama
  para clicar, o outro avisa que algo caiu.

---

## 3. Tipografia

Uma família só, do sistema, sem baixar nada — a máquina é offline durante o jogo e uma
fonte que não carrega deixa a tela em Times New Roman no meio da partida.

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
```

| Papel | Tamanho | Peso | Observação |
| --- | --- | --- | --- |
| Título da página | `clamp(30px, 5vw, 54px)` | 700 | `letter-spacing: -.04em` |
| Nome do jogo (`h2`) | 22px | 700 | |
| Texto normal | 14px | 400 | |
| Rótulo, legenda, unidade | 12px | 600 | `--fraco`, `text-transform: uppercase`, `letter-spacing: .5px` |
| Número grande de resumo | 26px | 700 | `font-variant-numeric: tabular-nums` |

**Todo número que muda sozinho leva `tabular-nums`.** Sem isso o "12,4 MB" vira "9,8 MB" e
a coluna inteira dança a cada 3 segundos — o olho persegue o movimento e não lê o valor.

---

## 4. Componentes

### Botão

| Variante | Fundo | Texto | Onde |
| --- | --- | --- | --- |
| normal | `--caixa-2` | `--texto` | ações comuns |
| perigo | `#3a1f22` | `#ff8b8b` | apagar, parar |
| abrir | `#23303a` | `#9fd8ff` | abrir pasta, ver quadro |
| gol | `--gol` | branco | só MARCAR GOL |

Altura mínima 28px, `padding: 3px 8px` no compacto e `6px 12px` no normal.
**Ação irreversível no meio do jogo pede `confirm()`** — parar a gravação por clique sem
querer custa o resto da partida.

### Selo de estado (pílula)

`border-radius: 999px`, 12px, peso 600, fundo a 16%, texto na cor cheia. É a forma padrão
de dizer em que pé está alguma coisa: corte, alinhamento, cobertura.

### Cartão

`background: var(--caixa)`, `border: 1px solid var(--linha)`, `border-radius: 16px`.
Sombra só no estúdio (`box-shadow: 0 18px 50px #0005`); no painel da gravação, não —
sombra em vinte cartões lado a lado vira sujeira.

### Tabela

Cabeçalho em `--fraco` 12px maiúsculo. Linha divisória `1px solid var(--linha)`.
Coluna numérica alinhada à direita com `tabular-nums`.

---

## 5. Layout

- **Escala de espaço: 4 / 8 / 16 / 24 / 32.** Nada de 5, 7, 13, 18.
- **Escala de raio: 6 (compacto) / 10 (controle) / 16 (cartão) / 999 (pílula).**
  Quatro valores, não dez.
- Largura máxima `min(1400px, calc(100% - 32px))`, centralizada.
- O painel da gravação **não rola horizontalmente**. Nunca. Se não coube, encolhe.
- Grade de quadros: `repeat(auto-fill, minmax(220px, 1fr))`.

---

## 6. Profundidade

Quase nenhuma. Três camadas e acabou:

1. `--fundo` — a página
2. `--caixa` — o cartão
3. `--caixa-2` — o controle dentro do cartão

Separação por **borda**, não por sombra. Sombra só no estúdio, e só nos cartões de gol.
Nada de gradiente decorativo — o único do projeto é o brilho do cabeçalho do estúdio, e
ele existe porque aquela tela é a de apresentar o trabalho pronto.

---

## 7. Pode e não pode

**Pode**

- Deixar o estado óbvio pela cor e **repetido em texto**. Cor sozinha exclui quem não
  distingue verde de vermelho, e são exatamente as duas cores mais usadas aqui.
- Mostrar o que falhou, marcado. Clipe que o detector não achou vai em vermelho na tela.
- Guardar em disco na hora do clique.

**Não pode**

- **Sumir com o que deu errado.** É a regra mais forte do projeto. Canal sem material
  aparece marcado, não some da lista.
- **Fingir que ainda está trabalhando.** Estado travado que nunca resolve é pior que erro:
  o operador espera por um arquivo que nunca vem.
- Guardar escolha do operador só na página aberta. Recarregar não pode perder trabalho.
- Inventar cor nova para um estado novo. Se não cabe em vivo / parou / confira / neutro,
  o estado está mal pensado.
- Animação de entrada, transição acima de 120ms, spinner girando sem fim.

---

## 8. Responsivo

Alvo é monitor de desktop, 1366px para cima. Não há versão de celular e não vai haver —
esta ferramenta roda na máquina que está gravando.

O que precisa aguentar: janela dividida ao meio (≈960px) e monitor grande (2560px).
Grade fluida com `auto-fill` resolve os dois sem media query. Abaixo de 900px a tabela
de canais pode rolar dentro do próprio contêiner (`overflow-x: auto`) — a página, não.

---

## 9. Guia rápido para agentes

Ao gerar ou mexer em interface deste projeto:

1. **Leia o `:root` da tela antes de escrever CSS.** Os tokens já existem; usar valor cru
   em vez de token é o erro mais comum e o mais chato de desfazer.
2. **Pergunte que estado a cor representa.** Não existe "um verde mais bonito": existe
   `--viva`, e ele quer dizer que está funcionando.
3. **Repita o estado em texto.** `✓ 6/6 cortado` ao lado do verde, não só o verde.
4. **Português na interface**, como no resto do projeto.
5. **Toda escolha do operador grava em disco na hora**, antes de a tela mudar.
6. **Não mude a tela do jogo com jogo rolando.** O painel da gravação pode ser reiniciado
   sem risco, mas a gravação em si, não — e as duas coisas moram em processos diferentes.

### Prompts prontos

> "Acrescente um selo de estado no painel da gravação seguindo o DESIGN.md: pílula, fundo
> a 16%, texto na cor cheia, com o estado repetido por escrito."

> "Unifique os tokens desta tela com o DESIGN.md, sem mudar o layout."
