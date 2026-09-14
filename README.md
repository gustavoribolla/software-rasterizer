# Renderizador

Renderizador por software desenvolvido para a disciplina de **Computação Gráfica**.

O projeto implementa a rasterização de arquivos X3D e reúne as funcionalidades desenvolvidas nas partes **1.1, 1.2 e 1.3** do Projeto 1. Até esta etapa, o renderizador suporta primitivas 2D, objetos 3D, transformações de modelo e câmera, projeção perspectiva, malhas de triângulos e composição de `Transform` em grafos de cena.

## Pré-requisitos

Instale as dependências com:

```sh
pip3 install -r requirements.txt
```

## Uso

Para executar o renderizador diretamente:

```sh
python3 renderizador/renderizador.py -i <arquivo.x3d>
```

Também é possível executar os exemplos disponíveis no projeto:

```sh
python3 exemplos.py <nome_do_exemplo>
```

### Opções do renderizador

* `-i`, `--input`: arquivo X3D de entrada
* `-o`, `--output`: arquivo de saída (imagem)
* `-w`, `--width`: resolução horizontal
* `-h`, `--height`: resolução vertical
* `-g`, `--graph`: imprime o grafo de cena
* `-p`, `--pause`: inicia a visualização em pausa
* `-q`, `--quiet`: executa sem exibir a janela

## Funcionalidades implementadas

| Função | Descrição |
| --- | --- |
| `GL.polypoint2D()` | Desenha pontos 2D no framebuffer. |
| `GL.polyline2D()` | Rasteriza segmentos de reta usando DDA e recorte aos limites da tela. |
| `GL.circle2D()` | Aproxima e rasteriza o contorno de círculos 2D. |
| `GL.triangleSet2D()` | Preenche triângulos 2D usando funções de aresta e regra top-left. |
| `GL.triangleSet()` | Processa triângulos 3D pelo pipeline de modelo, câmera, perspectiva e tela. |
| `GL.viewpoint()` | Monta a matriz de visualização a partir da posição, orientação e `fieldOfView` da câmera. |
| `GL.transform_in()` | Compõe a transformação local com a matriz de modelo acumulada e salva a matriz do nó pai. |
| `GL.transform_out()` | Restaura a matriz do nó pai ao sair de um `Transform`, permitindo grafos de cena aninhados. |
| `GL.triangleStripSet()` | Converte tiras de vértices em triângulos e as envia para o pipeline 3D. |
| `GL.indexedTriangleStripSet()` | Monta tiras de triângulos a partir de índices separados por `-1`. |
| `GL.indexedFaceSet()` | Triangula faces indexadas em leque e as envia para o pipeline 3D. |

## Projeto 1.1 — Rasterização 2D

A primeira etapa implementa a rasterização básica diretamente no framebuffer:

* pontos;
* segmentos de reta;
* círculos;
* triângulos preenchidos.

As linhas são rasterizadas pelo algoritmo DDA. Para triângulos, a implementação testa o centro dos pixels dentro da bounding box e utiliza a regra **top-left** para tratar pixels compartilhados entre triângulos vizinhos.

## Projeto 1.2 — Pipeline 3D

Os vértices de um objeto 3D passam pelas seguintes etapas:

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

### Transformação de modelo

Os nós `Transform` podem aplicar:

* escala;
* rotação eixo-ângulo;
* translação.

As operações são representadas por matrizes homogêneas 4×4. Para vetores-coluna, a matriz local utilizada é:

```text
Mlocal = T · R · S
```

### Transformação de câmera

O nó `Viewpoint` fornece a posição, a orientação e o campo de visão da câmera. A matriz de visualização utiliza a transformação inversa da câmera para levar os pontos do mundo ao espaço de visão.

### Projeção perspectiva

Depois da transformação de câmera, é aplicada uma matriz de projeção perspectiva usando o `fieldOfView`, a razão de aspecto e os planos `near` e `far`.

Após a divisão pela coordenada homogênea `w`, os vértices ficam em NDC e são convertidos para coordenadas de pixels do framebuffer.

## Projeto 1.3 — Malhas e grafo de cena

### Malhas de triângulos

O renderizador suporta três novas formas de representar malhas 3D.

#### `TriangleStripSet`

Cada valor de `stripCount` informa quantos vértices pertencem a uma tira. Uma tira com `n` vértices gera `n - 2` triângulos consecutivos.

A ordem dos vértices é alternada entre triângulos pares e ímpares para manter uma orientação consistente.

#### `IndexedTriangleStripSet`

Funciona de forma semelhante ao `TriangleStripSet`, mas os triângulos são construídos usando índices para a lista de coordenadas. O valor `-1` separa uma tira da seguinte.

#### `IndexedFaceSet`

Cada sequência de índices terminada em `-1` representa uma face. Faces com mais de três vértices são trianguladas em leque:

```text
(v0, v1, v2)
(v0, v2, v3)
(v0, v3, v4)
...
```

Os triângulos resultantes reutilizam `GL.triangleSet()`, mantendo um único pipeline de transformação e rasterização 3D.

### Grafo de cena e `Transform` aninhado

Para permitir `Transform` dentro de outros `Transform`, o renderizador mantém uma pilha de matrizes de modelo.

Ao entrar em um nó:

```text
salva matriz atual na pilha
        ↓
Mmodelo = Mmodelo · Mlocal
```

Ao terminar os filhos desse nó:

```text
Mmodelo = matriz removida da pilha
```

Dessa forma, um filho herda todas as transformações de seus ancestrais, enquanto objetos fora daquele ramo do grafo continuam usando a transformação correta.

## Exemplos

### Projeto 1.1 — 2D

```sh
python3 exemplos.py aleatorios
python3 exemplos.py linhas_cores
python3 exemplos.py octogono
python3 exemplos.py linhas_cruzes
python3 exemplos.py varias_linhas
python3 exemplos.py circulo
python3 exemplos.py triangulos
python3 exemplos.py helice
python3 exemplos.py pontas
```

### Projeto 1.2 — pipeline 3D

```sh
python3 exemplos.py um_triangulo
python3 exemplos.py varios_triangs
python3 exemplos.py zoom
```

### Projeto 1.3 — malhas

```sh
python3 exemplos.py tiras
python3 exemplos.py letras
python3 exemplos.py leques
python3 exemplos.py vertices10
```

### Projeto 1.3 — grafo de cena

```sh
python3 exemplos.py bound500
python3 exemplos.py avatar
python3 exemplos.py girando
```

Os exemplos `bound500`, `avatar` e `girando` verificam principalmente a composição e a restauração correta de transformações em diferentes níveis do grafo de cena.

## Estrutura

A implementação principal das operações gráficas está concentrada em `renderizador/gl.py`, na classe `GL`.

O projeto utiliza um framebuffer simulado em software para armazenar os pixels gerados antes da exibição ou do salvamento da imagem final.

Até o **Projeto 1.3**, a geometria 3D implementada utiliza principalmente a cor emissiva do `Material`. Recursos como iluminação, texturas, profundidade e outras primitivas 3D pertencem às próximas etapas do renderizador.
