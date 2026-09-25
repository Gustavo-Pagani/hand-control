# Hand Control

Um platformer 2D controlado inteiramente pelas mãos, através da webcam. Sem teclado, sem controle: você anda, pula, navega nos menus e faz compras na loja com gestos.

![Python](https://img.shields.io/badge/python-3.13-blue) ![pygame](https://img.shields.io/badge/pygame-2.6-green) ![MediaPipe](https://img.shields.io/badge/mediapipe-1.0-orange) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

## O jogo

Cinco fases com temas e mecânicas próprias, inimigos que andam, pulam, atiram e voam, moedas que compram vidas e itens, estrelas por fase e uma loja entre fases.

| Fase | Tema | Novidade |
|---|---|---|
| 1. Primeiros Passos | grama | andar, pular, pisar em inimigos, blocos `?` |
| 2. Plataformas | deserto | escadas de plataformas, inimigos nas beiradas |
| 3. Espinhos | neve | espinhos, saltadores, canhão, checkpoint |
| 4. Corredores | fábrica | tetos baixos, abelha, moedas escondidas |
| 5. Final | fábrica em chamas | tudo junto, mais denso |

**Economia.** Cada 20 moedas dão uma vida extra (máximo 5). Entre as fases, a loja vende Coração, Escudo (absorve um toque) e Pulo alto. Ao terminar uma fase você ganha até três estrelas: completar, pegar todas as moedas e não morrer. O progresso fica salvo em `progress.json`.

**Inimigos.** Slime (anda e vira nas beiradas), bloco saltador, canhão (atira pedras lentas quando você se aproxima) e abelha (voa em zigue-zague e não pode ser pisada).

## Controles por gesto

O jogo usa as duas mãos. A mão que aparece à esquerda da tela controla o movimento; a da direita, o pulo e os menus.

| Onde | Gesto | Ação |
|---|---|---|
| jogo | esquerda: só o indicador | andar para frente |
| jogo | esquerda: só o polegar | andar para trás |
| jogo | direita: indicador, polegar ou os dois | pular (um pulo por levantada) |
| jogo | punho ou mão aberta | parado |
| menus | direita: 1, 2, 3 dedos, mão aberta (4), aberta com polegar (5) | escolhe o item |
| menus | sinal de OK com qualquer mão, segurando | confirma, compra, continua |
| menus e jogo | esquerda: três dedos, segurando | volta, sai da loja, abandona a fase |

Os comandos de confirmar e voltar precisam ser segurados por menos de um segundo; uma barra na parte de baixo da tela mostra o progresso. Isso evita comprar ou sair sem querer.

A tela **Calibrar câmera** pede os quatro gestos principais (frente, trás, pulo, OK), mede as proporções dos seus dedos e ajusta os limiares do reconhecedor. O resultado fica em `calibration.json`.

## Como rodar

Requisitos: Python 3.13, uma webcam.

```bash
pip install -r requirements.txt
python main.py
```

Para abrir direto numa fase, por exemplo a terceira:

```bash
python main.py 3
```

Teclas úteis durante o desenvolvimento: `V` esconde a câmera, `M` silencia o som, `ESC` volta ao menu.

## Como funciona

### Visão computacional

A webcam é lida por uma thread própria que guarda apenas o frame mais recente, para que nunca exista fila no driver. Uma segunda thread reduz o frame para 320×240, roda o **MediaPipe Hand Landmarker** (21 pontos por mão, até duas mãos) e classifica cada mão por regras geométricas:

- um dedo está estendido quando a distância da ponta ao pulso supera a distância da articulação do meio ao pulso, numa razão acima do limiar calibrado;
- o polegar usa a distância da sua ponta à base do dedo mínimo, normalizada pelo tamanho da palma;
- o sinal de OK é a ponta do polegar encostando na ponta do indicador com os outros dedos abertos.

As métricas são razões entre distâncias, então não dependem da distância da mão à câmera nem da rotação. Um debounce de 80 ms filtra os estados intermediários de uma transição entre gestos. Com duas mãos visíveis, a mais à esquerda da tela é a mão de movimento; com uma só, vale a lateralidade informada pelo modelo.

### Jogo

A física é um platformer clássico com passo fixo de 1/60 s, colisão resolvida por eixo, *coyote time* e *jump buffer*, que perdoam o atraso natural do reconhecimento por câmera. Toda a lógica consome apenas uma estrutura `Input` (mover, pular, confirmar, voltar, selecionar), então o jogo não sabe se o comando veio da câmera ou de outra fonte.

As fases são mapas ASCII em `handcontrol/levels.py`:

```
#  sólido      P  início        E  slime       H  saltador
C  canhão      B  abelha        ^  espinho     o  moeda
?  bloco       K  checkpoint    G  bandeira    .  vazio
```

Sons são sintetizados em código (ondas quadradas e senoidais com envelope), sem arquivos de áudio. A arte é do pacote **Pixel Platformer** do [Kenney](https://kenney.nl) (CC0), com tiles escolhidos por vizinhança e fundo em duas camadas de parallax.

## Estrutura

```
main.py                     ponto de entrada
handcontrol/
  config.py                 janela, física, regras
  inputs.py                 Input, gestos -> Input, segurar-para-confirmar
  physics.py                gravidade e colisão por eixo
  entities.py               Player, inimigos, pedra do canhão
  level.py                  mapa ASCII -> dados da fase
  levels.py                 as cinco fases
  game.py                   uma tentativa numa fase
  run.py                    campanha: vidas, moedas, itens, progresso salvo
  effects.py                partículas e tremor de tela
  sound.py                  sons sintetizados
  assets.py                 sprites e fontes
  ui.py                     texto, painéis, ícones
  camview.py                preview da câmera com landmarks
  menu.py  levelselect.py  shop.py  calibration.py  app.py
  vision/
    gestures.py             landmarks -> gesto, debounce, calibração
    tracker.py              threads de captura e detecção
tests/                      python -m tests
assets/                     sprites Kenney (CC0), fontes, modelo do MediaPipe
```

## Testes

```bash
python -m tests
```

Cobrem física (pisão, cabeçada, coyote time, jump buffer), inimigos, escudo, blocos, checkpoint, economia, loja, estrelas, classificação dos gestos com mãos sintéticas e o debounce. Nenhum teste precisa de câmera.

## Licença

Código sob licença MIT. Arte de [Kenney](https://kenney.nl) (CC0). Modelo `hand_landmarker.task` do MediaPipe (Apache 2.0).
