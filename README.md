# Renderizador

Renderizador por software desenvolvido para a disciplina de **Computação Gráfica**.

O projeto implementa a rasterização de primitivas gráficas a partir de arquivos X3D, incluindo desenho de elementos 2D e processamento de objetos 3D por meio de transformações de modelo, câmera e projeção perspectiva.

## Pré-requisitos

Instale as dependências do projeto com:

```sh
pip3 install -r requirements.txt
```

## Uso

Para executar o renderizador:

```sh
python3 renderizador.py
```

Também é possível executar os exemplos disponíveis no projeto:

```sh
python3 exemplos.py
```

### Opções

* `-i`, `--input`: arquivo X3D de entrada
* `-o`, `--output`: arquivo de saída (imagem)
* `-w`, `--width`: resolução horizontal
* `-h`, `--height`: resolução vertical
* `-q`, `--quiet`: executa sem exibir a janela

## Funcionalidades

O renderizador possui suporte para rasterização de primitivas 2D e processamento de objetos em cenas 3D.

| Função               | Descrição                                                                                                                  |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `GL.polypoint2D()`   | Desenha pontos no framebuffer utilizando suas posições e cores.                                                            |
| `GL.polyline2D()`    | Rasteriza segmentos de reta entre os vértices recebidos, interpolando as cores ao longo da linha.                          |
| `GL.circle2D()`      | Rasteriza círculos 2D no framebuffer.                                                                                      |
| `GL.triangleSet2D()` | Rasteriza e preenche triângulos 2D, realizando a interpolação das cores dos vértices.                                      |
| `GL.triangleSet()`   | Processa e rasteriza triângulos em uma cena 3D, aplicando as transformações necessárias até chegar às coordenadas da tela. |
| `GL.viewpoint()`     | Configura a câmera da cena utilizando sua posição, orientação e campo de visão (`fieldOfView`).                            |
| `GL.transform_in()`  | Aplica as transformações de escala, rotação e translação aos objetos da cena através de matrizes homogêneas.               |
| `GL.transform_out()` | Finaliza o escopo de uma transformação e recupera a transformação anterior.                                                |

## Pipeline 3D

Para renderizar objetos 3D, os vértices passam por uma sequência de transformações até chegarem aos pixels da imagem.

### Transformação de modelo

Posiciona cada objeto no espaço do mundo.

São consideradas as transformações definidas pelo nó `Transform`:

* escala;
* rotação;
* translação.

Essas operações são combinadas utilizando matrizes homogêneas 4×4.

### Transformação de câmera

Os vértices do mundo são convertidos para o sistema de coordenadas da câmera.

O nó `Viewpoint` fornece:

* posição da câmera;
* orientação da câmera;
* campo de visão.

A matriz de visualização corresponde à transformação inversa da câmera.

### Projeção perspectiva

Depois da transformação para o espaço da câmera, é aplicada a projeção perspectiva.

Essa etapa utiliza o `fieldOfView` da câmera e faz com que objetos mais distantes apareçam menores na imagem.

Após a projeção, é realizada a divisão pelas coordenadas homogêneas para obter as coordenadas normalizadas do dispositivo (NDC).

### Coordenadas da tela

As coordenadas normalizadas são convertidas para posições de pixels de acordo com a resolução do framebuffer.

Depois dessa conversão, os triângulos são enviados para a rotina de rasterização 2D e desenhados na imagem final.

O pipeline utilizado pode ser resumido como:

```text
Vértices do objeto
        ↓
Transformação de modelo
        ↓
Transformação de câmera
        ↓
Projeção perspectiva
        ↓
Coordenadas normalizadas (NDC)
        ↓
Coordenadas da tela
        ↓
Rasterização
        ↓
Framebuffer
```

## Exemplos

Os exemplos podem ser executados através de:

```sh
python3 exemplos.py <nome_do_exemplo>
```

Alguns exemplos para testar as funcionalidades 2D:

```sh
python3 exemplos.py aleatorios
python3 exemplos.py linhas_cores
python3 exemplos.py octogono
python3 exemplos.py circulo
python3 exemplos.py triangulos
```

Para testar as funcionalidades 3D:

```sh
python3 exemplos.py um_triangulo
python3 exemplos.py varios_triangs
python3 exemplos.py zoom
```

Os exemplos `um_triangulo`, `varios_triangs` e `zoom` permitem verificar principalmente o funcionamento das transformações de modelo, câmera, projeção perspectiva e conversão para coordenadas da tela.

## Estrutura

A implementação principal das operações gráficas está concentrada na classe `GL`, responsável pelas rotinas de rasterização e pelas transformações utilizadas durante a renderização.

O projeto utiliza um framebuffer para armazenar os pixels gerados pelo rasterizador antes da apresentação ou salvamento da imagem final.
