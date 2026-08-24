# Renderizador

Renderizador base utilizado na disciplina de **Computação Gráfica**.

Neste projeto foram implementadas rotinas de rasterização 2D para pontos, linhas, círculos e triângulos.

## Pré-requisitos

É necessário ter o **Python 3** instalado.

Na raiz do projeto, instale as dependências com:

```sh
python -m pip install -r requirements.txt
```

No Linux ou macOS, caso o comando `python` não esteja disponível, use:

```sh
python3 -m pip install -r requirements.txt
```

## Como executar

> Os comandos abaixo devem ser executados na **raiz do projeto**, onde estão `exemplos.py`, `requirements.txt` e a pasta `renderizador`.

A forma mais simples de testar o projeto é executar um dos exemplos disponíveis:

```sh
python exemplos.py 0
```

No Linux ou macOS:

```sh
python3 exemplos.py 0
```

O número `0` corresponde ao primeiro exemplo. Também é possível informar o nome do exemplo:

```sh
python exemplos.py aleatorios
```

Ao executar apenas:

```sh
python exemplos.py
```

o programa mostra a lista de exemplos e solicita qual deles deve ser aberto.

## Executar o renderizador diretamente

O arquivo principal do renderizador está dentro da pasta `renderizador`. Por isso, a partir da raiz do projeto, utilize:

```sh
python renderizador/renderizador.py -i <arquivo.x3d>
```

Por exemplo:

```sh
python renderizador/renderizador.py -i docs/exemplos/2D/pontos/aleatorios/aleatorios.x3d -w 30 -h 20
```

### Opções

* `-i`, `--input`: arquivo X3D de entrada
* `-o`, `--output`: arquivo de imagem de saída
* `-w`, `--width`: resolução horizontal
* `-h`, `--height`: resolução vertical
* `-g`, `--graph`: imprime o grafo de cena
* `-p`, `--pause`: inicia a simulação em pausa
* `-q`, `--quiet`: não exibe a janela de visualização

## Exemplos 2D

Os exemplos relacionados a esta etapa do projeto são:

0. `aleatorios` — pontos
1. `linhas_cores` — linhas coloridas
2. `octogono` — polilinha formando um octógono
3. `linhas_cruzes` — linhas que testam os limites da tela
4. `varias_linhas` — vários segmentos de linha
5. `circulo` — círculo 2D
6. `triangulos` — triângulos 2D
7. `helice` — composição de triângulos
8. `pontas` — triângulos grandes e clipping

Para executar outro exemplo, basta trocar o índice. Por exemplo:

```sh
python exemplos.py 6
```

## Visualização dos exemplos

Os exemplos também podem ser consultados na web:

[Exemplos do Renderizador](https://lpsoares.github.io/Renderizador/)

Para visualizar os arquivos da pasta `docs` localmente em um navegador, execute na raiz do projeto:

```sh
python -m http.server
```

Depois, acesse o endereço mostrado no terminal.

## Problemas comuns

### `python` não é reconhecido

No Windows, tente utilizar `py` no lugar de `python`:

```sh
py -m pip install -r requirements.txt
py exemplos.py 0
```

### `No such file or directory` / arquivo não encontrado

Confirme que o terminal está aberto na raiz do repositório. Nessa pasta devem aparecer, entre outros:

```text
README.md
requirements.txt
exemplos.py
renderizador/
docs/
```

### Erro de módulo não encontrado

Instale novamente as dependências:

```sh
python -m pip install -r requirements.txt
```

### A janela não abre

Primeiro teste um exemplo simples:

```sh
python exemplos.py 0
```