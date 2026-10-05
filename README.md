# Renderizador

Renderizador por software desenvolvido para a disciplina de **Computação Gráfica**.

O projeto reúne as partes **1.1 a 1.5** do Projeto 1 e implementa rasterização de
arquivos X3D em software. O pipeline inclui rasterização 2D e 3D, transformações,
grafos de cena, supersampling, interpolação de atributos, Z-buffer, transparência,
texturas, iluminação e animação.

A parte 1.5 contempla as tarefas obrigatórias. As primitivas geométricas extras
(`Box`, `Sphere`, `Cone` e `Cylinder`) permanecem como esboços do código base.

---

## Pré-requisitos

Instale as dependências a partir da raiz do repositório.

### Windows

```powershell
python -m pip install -r requirements.txt
```

### Linux/macOS

```sh
python3 -m pip install -r requirements.txt
```

---

## Uso

### Windows

Para executar diretamente um arquivo X3D:

```powershell
python renderizador/renderizador.py -i <arquivo.x3d>
```

Para abrir a lista de exemplos e escolher um deles:

```powershell
python exemplos.py
```

Também é possível executar um exemplo pelo **nome**:

```powershell
python exemplos.py zoom
```

ou pelo **número** mostrado na lista:

```powershell
python exemplos.py 11
```

O carregador também aceita uma faixa de exemplos:

```powershell
python exemplos.py 9..11
```

e vários números de uma vez:

```powershell
python exemplos.py 9 10 11
```

### Linux/macOS

Os mesmos comandos podem ser executados com `python3`:

```sh
python3 renderizador/renderizador.py -i <arquivo.x3d>
python3 exemplos.py
python3 exemplos.py zoom
python3 exemplos.py 11
python3 exemplos.py 9..11
```

> Os números dos exemplos começam em **0**. Assim, `zoom` corresponde ao exemplo
> **11**, enquanto `aleatorios` corresponde ao exemplo **0**.

---

## Opções do renderizador

- `-i`, `--input`: arquivo X3D de entrada
- `-o`, `--output`: arquivo de saída (imagem)
- `-w`, `--width`: resolução horizontal
- `-h`, `--height`: resolução vertical
- `-g`, `--graph`: imprime o grafo de cena
- `-p`, `--pause`: inicia a visualização em pausa
- `-q`, `--quiet`: executa sem exibir a janela

---

# Mapa dos exemplos para o código

Esta é a referência rápida para relacionar o número apresentado por
`exemplos.py` com as funções da classe `GL`.

A coluna **Onde começar** indica a melhor função para procurar primeiro em
`renderizador/gl.py`. A coluna **Funções relacionadas** mostra o caminho
principal usado pela implementação.

## Projeto 1.1 - Rasterização 2D

| Nº | Exemplo | Onde começar | Funções relacionadas | Principal funcionalidade |
| ---: | --- | --- | --- | --- |
| **0** | `aleatorios` | `GL.polypoint2D()` | `polypoint2D()` → `_rgb8()` → `_pixel()` | Pontos 2D coloridos |
| **1** | `linhas_cores` | `GL.polyline2D()` | `polyline2D()` → `_linha()` → `_faixa_visivel()` → `_pixel()` | Linhas, DDA e clipping |
| **2** | `octogono` | `GL.polyline2D()` | `polyline2D()` → `_linha()` → `_faixa_visivel()` → `_pixel()` | Poligonal formada por segmentos |
| **3** | `linhas_cruzes` | `GL.polyline2D()` | `polyline2D()` → `_linha()` → `_faixa_visivel()` → `_pixel()` | Linhas em diferentes direções |
| **4** | `varias_linhas` | `GL.polyline2D()` | `polyline2D()` → `_linha()` → `_faixa_visivel()` → `_pixel()` | Vários segmentos e recorte |
| **5** | `circulo` | `GL.circle2D()` | `circle2D()` → `_linha()` → `_faixa_visivel()` → `_pixel()` | Círculo aproximado por segmentos |
| **6** | `triangulos` | `GL.triangleSet2D()` | `triangleSet2D()` → `_triangulo()` | Triângulos 2D preenchidos |
| **7** | `helice` | `GL.triangleSet2D()` | `triangleSet2D()` → `_triangulo()` | Conjunto de triângulos 2D |
| **8** | `pontas` | `GL.triangleSet2D()` | `triangleSet2D()` → `_triangulo()` | Triângulos 2D em diferentes orientações |

### Funções principais da etapa

- `GL.polypoint2D()`: recebe pares `(x, y)` e escreve os pixels correspondentes.
- `GL.polyline2D()`: liga cada ponto ao próximo.
- `GL._linha()`: rasteriza cada segmento pelo algoritmo DDA.
- `GL._faixa_visivel()`: aplica clipping de Liang-Barsky antes de percorrer a linha.
- `GL.circle2D()`: aproxima o círculo por segmentos de reta.
- `GL.triangleSet2D()`: agrupa três vértices por triângulo e chama `_triangulo()`.
- `GL._triangulo()`: realiza o preenchimento do triângulo.

---

## Projeto 1.2 - Pipeline 3D

| Nº | Exemplo | Onde começar | Funções relacionadas | Principal funcionalidade |
| ---: | --- | --- | --- | --- |
| **9** | `um_triangulo` | `GL.triangleSet()` | `transform_in()` → `viewpoint()` → `triangleSet()` → `_triangulo()` | Pipeline 3D básico |
| **10** | `varios_triangs` | `GL.triangleSet()` | `transform_in()` → `viewpoint()` → `triangleSet()` → `_triangulo()` | Pipeline aplicado a vários triângulos |
| **11** | `zoom` | `GL.viewpoint()` | `viewpoint()` → `triangleSet()` → `_triangulo()` | Câmera, `fieldOfView` e projeção perspectiva |

### Fluxo de um vértice 3D

```text
vértice local
    ↓
GL.transform_in()
    ↓
matriz de modelo
    ↓
GL.viewpoint()
    ↓
matriz de câmera
    ↓
GL.triangleSet()
    ↓
projeção perspectiva
    ↓
divisão por w
    ↓
NDC
    ↓
viewport
    ↓
GL._triangulo()
    ↓
framebuffer
```

### Onde observar o `zoom`

O exemplo **11 - `zoom`** é especialmente relacionado a:

- `GL.viewpoint()`: recebe `position`, `orientation` e `fieldOfView`;
- `GL.triangleSet()`: usa `GL.field_of_view` para construir a matriz de projeção;
- transformação para NDC: `clip[:3] / clip[3]`;
- viewport: converte `x` e `y` de NDC para coordenadas da tela;
- `GL._triangulo()`: rasteriza o resultado final.

A matriz de projeção em `triangleSet()` usa:

```text
f = 1 / tan(fieldOfView / 2)
```

Assim, alterar o campo de visão modifica o tamanho aparente dos objetos na tela.

---

## Projeto 1.3 - Malhas e grafo de cena

| Nº | Exemplo | Onde começar | Funções relacionadas | Principal funcionalidade |
| ---: | --- | --- | --- | --- |
| **12** | `tiras` | `GL.triangleStripSet()` | `triangleStripSet()` → `triangleSet()` → `_triangulo()` | Triangle strips |
| **13** | `letras` | `GL.indexedTriangleStripSet()` | `indexedTriangleStripSet()` → `triangleSet()` → `_triangulo()` | Triangle strips indexadas |
| **14** | `leques` | `GL.indexedFaceSet()` | `indexedFaceSet()` → triangulação → `triangleSet()` → `_triangulo()` | Faces indexadas e triangulação |
| **15** | `vertices10` | `GL.indexedFaceSet()` | `indexedFaceSet()` → triangulação → `triangleSet()` → `_triangulo()` | Face com vários vértices |
| **16** | `estrela` | `GL.indexedFaceSet()` / `GL.indexedTriangleStripSet()` | malha indexada → `triangleSet()` → `_triangulo()` | Malha construída por índices |
| **17** | `bound500` | `GL.transform_in()` | `transform_in()` ↔ `transform_out()` → geometria | Transformações no grafo de cena |
| **18** | `avatar` | `GL.transform_in()` | `transform_in()` ↔ `transform_out()` → `indexedFaceSet()` → `triangleSet()` | `Transform` aninhado |
| **19** | `girando` | `GL.transform_in()` | `_matriz_rotacao()` → `transform_in()` ↔ `transform_out()` | Rotação e hierarquia |

### Malhas

#### `GL.triangleStripSet()`

Uma tira com `n` vértices gera `n - 2` triângulos. A orientação alterna entre
triângulos pares e ímpares, portanto a ordem dos dois primeiros vértices é
invertida quando necessário.

#### `GL.indexedTriangleStripSet()`

Funciona como `TriangleStripSet`, mas busca os vértices por índices. O valor
`-1` encerra uma tira e inicia a próxima.

#### `GL.indexedFaceSet()`

O valor `-1` também separa as faces. Uma face com mais de três vértices é
triangulada em leque:

```text
(v0, v1, v2)
(v0, v2, v3)
(v0, v3, v4)
...
```

### Grafo de cena

`GL.transform_in()` salva a matriz atual em `model_stack` e compõe a matriz
local:

```text
Mlocal = T · R · S
Mmodelo = Mmodelo · Mlocal
```

`GL.transform_out()` restaura a matriz do nó pai ao finalizar aquele ramo do
grafo.

---

## Projeto 1.4 - Amostragem, interpolação, visibilidade e texturas

| Nº | Exemplo | Onde começar | Funções relacionadas | Principal funcionalidade |
| ---: | --- | --- | --- | --- |
| **20** | `quadrado` | `GL._triangulo()` | `indexedFaceSet()` → `triangleSet()` → `_triangulo()` → `_perspective_interp()` | Interpolação de cores |
| **21** | `flechas` | `GL._perspective_interp()` | `indexedFaceSet()` → `triangleSet()` → `_triangulo()` → `_perspective_interp()` | Interpolação com correção de perspectiva |
| **22** | `textura` | `GL.indexedFaceSet()` | `_carregar_mipmaps()` → `_perspective_interp()` → `_amostrar_textura()` → `_triangulo()` | Mapeamento de textura |
| **23** | `texturas` | `GL._gerar_mipmaps()` | `_carregar_mipmaps()` → `_gerar_mipmaps()` → `_lod_triangulo()` → `_amostrar_textura()` | Texturas e mipmapping |
| **24** | `retangulos` | `GL._triangulo()` | `triangleSet()` → `_triangulo()` → `_sincronizar_depth_pixel()` | Z-buffer |
| **25** | `transparente` | `GL._triangulo()` | `triangleSet()` → `_triangulo()` | Composição alpha |
| **26** | `tri_color` | `GL._perspective_interp()` | `indexedFaceSet()` → `_perspective_interp()` → `_triangulo()` | Teste reduzido de cor por vértice |
| **27** | `tri_textur` | `GL._amostrar_textura()` | `indexedFaceSet()` → `_perspective_interp()` → `_amostrar_textura()` | Teste reduzido de textura |
| **28** | `dois_tri` | `GL._triangulo()` | `_triangulo()` → `_sincronizar_depth_pixel()` | Teste reduzido de profundidade |
| **29** | `tri_trans` | `GL._triangulo()` | `_triangulo()` | Teste reduzido de transparência |

### Supersampling

O rasterizador utiliza supersampling **2×2**. Cada pixel contém quatro
subamostras, avaliadas nas posições internas:

```text
(0.25, 0.25)    (0.75, 0.25)
(0.25, 0.75)    (0.75, 0.75)
```

A função principal para acompanhar essa etapa é `GL._triangulo()`. O resultado
final de um pixel é a média das quatro subamostras.

### Coordenadas baricêntricas

Também em `GL._triangulo()`, as funções de aresta geram os pesos:

```text
l0 = e1 / area
l1 = e2 / area
l2 = e0 / area
```

Esses pesos são usados para interpolar profundidade, cor, UV e posição.

### Correção de perspectiva

`GL._perspective_interp()` interpola os atributos usando `atributo / w` e
`1 / w`, evitando a deformação produzida por uma interpolação puramente afim
depois da projeção perspectiva.

### Z-buffer

A profundidade é armazenada por subamostra. Antes de escrever uma nova cor,
`GL._triangulo()` compara o novo valor de Z com o valor já armazenado.

### Transparência

O X3D fornece `transparency`, enquanto a composição utiliza alpha:

```text
alpha = 1 - transparency
```

Para superfícies transparentes é utilizada composição **source-over**:

```text
saida = alpha * origem + (1 - alpha) * destino
```

### Texturas e mipmaps

O fluxo principal é:

```text
GL.indexedFaceSet()
    ↓
GL._carregar_mipmaps()
    ↓
GL._gerar_mipmaps()
    ↓
GL.triangleSet()
    ↓
GL._perspective_interp()
    ↓
GL._lod_triangulo()
    ↓
GL._amostrar_textura()
    ↓
GL._triangulo()
```

---

## Projeto 1.5 - Iluminação e animação

| Nº | Exemplo | Onde começar | Funções relacionadas | Principal funcionalidade |
| ---: | --- | --- | --- | --- |
| **30** | `difusos` | `GL._iluminar()` | `directionalLight()` / `navigationInfo()` → `triangleSet()` → `_iluminar()` | Iluminação difusa |
| **31** | `mineiro` | `GL.navigationInfo()` | `navigationInfo()` → `triangleSet()` → `_iluminar()` | Headlight da câmera |
| **32** | `senoide_difusa` | `GL._iluminar()` | `directionalLight()` → `triangleSet()` → `_iluminar()` | Variação do termo difuso |
| **33** | `senoide_especular` | `GL._iluminar()` | `directionalLight()` → `triangleSet()` → `_iluminar()` | Termo especular / `shininess` |
| **34** | `teapot` | `GL._iluminar()` | `indexedFaceSet()` → `triangleSet()` → `_iluminar()` | Iluminação de malha complexa |
| **35** | `coelho` | `GL._iluminar()` | `indexedFaceSet()` → `triangleSet()` → `_iluminar()` | Iluminação de malha complexa |
| **36** | `onda` | `GL.timeSensor()` | `timeSensor()` → `splinePositionInterpolator()` → `Transform` | Animação de posição |
| **37** | `piramide` | `GL.timeSensor()` | `timeSensor()` → `orientationInterpolator()` → `transform_in()` | Animação de rotação |
| **38** | `voltas` | `GL.orientationInterpolator()` | `timeSensor()` → `orientationInterpolator()` → `transform_in()` | Interpolação de orientação |
| **39** | `danca` | `GL.timeSensor()` | `timeSensor()` → `splinePositionInterpolator()` / `orientationInterpolator()` | Posição + orientação |
| **40** | `avatar_animado` | `GL.timeSensor()` | `timeSensor()` → interpoladores → `transform_in()` → `indexedFaceSet()` | Animação em grafo hierárquico |

### Iluminação

`GL.triangleSet()` calcula a normal da face pelo produto vetorial entre duas
arestas no espaço da câmera.

`GL._iluminar()` aplica o modelo de **Blinn-Phong**, usando:

- `emissiveColor`;
- `ambientIntensity`;
- `diffuseColor`;
- `specularColor`;
- `shininess`.

O termo difuso usa:

```text
max(N · L, 0)
```

O termo especular usa o vetor intermediário:

```text
H = normalize(L + V)
```

e:

```text
max(N · H, 0) ** (128 * shininess)
```

`GL.directionalLight()` registra e transforma a direção de uma luz direcional.

`GL.navigationInfo()` implementa o **headlight**, uma luz branca que acompanha
a câmera.

### Animação

O fluxo é:

```text
GL.begin_frame()
    ↓
GL.timeSensor()
    ↓
GL._intervalo_chaves()
    ↓
GL.splinePositionInterpolator()
ou
GL.orientationInterpolator()
    ↓
GL.transform_in()
    ↓
geometria atualizada
```

`GL.splinePositionInterpolator()` utiliza spline cúbica de Hermite para posições.

`GL.orientationInterpolator()` converte rotações eixo-ângulo para quaternions,
interpola por **SLERP** e converte o resultado novamente para eixo-ângulo.

---

## Exemplos extras - primitivas geométricas

As primitivas abaixo são opcionais e **não estão implementadas na versão atual**.
As funções ainda permanecem como placeholders do código base.

| Nº | Exemplo | Função correspondente | Estado |
| ---: | --- | --- | --- |
| **41** | `duas` | `GL.box()` / `GL.sphere()` | Extra / placeholder |
| **42** | `outras_duas` | `GL.cone()` / `GL.cylinder()` | Extra / placeholder |
| **43** | `caixas` | `GL.box()` | Extra / placeholder |
| **44** | `esferas` | `GL.sphere()` | Extra / placeholder |
| **45** | `cubo` | `GL.box()` | Extra / placeholder |

---

# Lista completa dos exemplos

Esta lista segue a numeração apresentada por `exemplos.py`.

```text
 0: aleatorios          12: tiras              24: retangulos        36: onda
 1: linhas_cores        13: letras             25: transparente      37: piramide
 2: octogono            14: leques             26: tri_color         38: voltas
 3: linhas_cruzes       15: vertices10         27: tri_textur        39: danca
 4: varias_linhas       16: estrela            28: dois_tri          40: avatar_animado
 5: circulo             17: bound500           29: tri_trans         41: duas
 6: triangulos          18: avatar             30: difusos           42: outras_duas
 7: helice              19: girando            31: mineiro           43: caixas
 8: pontas              20: quadrado           32: senoide_difusa    44: esferas
 9: um_triangulo        21: flechas            33: senoide_especular 45: cubo
10: varios_triangs      22: textura            34: teapot
11: zoom                23: texturas           35: coelho
```

Por exemplo, no Windows:

```powershell
# zoom
python exemplos.py 11

# mesmo exemplo pelo nome
python exemplos.py zoom

# exemplos do pipeline 3D
python exemplos.py 9..11

# exemplo de Z-buffer
python exemplos.py 24

# exemplo de transparência
python exemplos.py 25

# exemplo de mipmaps/texturas
python exemplos.py 23

# iluminação difusa
python exemplos.py 30

# animação do avatar
python exemplos.py 40
```

---

## Testes

### Windows

```powershell
python -m unittest discover -s tests -v
```

### Linux / macOS

```sh
python3 -m unittest discover -s tests -v
```

---

## Estrutura principal

A implementação das operações gráficas está concentrada em:

```text
renderizador/gl.py
```

na classe `GL`.

O framebuffer é simulado em software. Os vértices e atributos são processados
pela CPU até que a cor final de cada pixel seja escrita no framebuffer.

As rotinas mais centrais do projeto são:

| Função | Papel |
| --- | --- |
| `GL.polypoint2D()` | Rasterização de pontos 2D |
| `GL.polyline2D()` | Entrada para polilinhas 2D |
| `GL._linha()` | Rasterização DDA de segmentos |
| `GL.circle2D()` | Construção do contorno de círculos |
| `GL.triangleSet2D()` | Entrada para triângulos 2D |
| `GL._triangulo()` | Cobertura, baricêntricas, SSAA, Z-buffer, textura, iluminação e alpha |
| `GL.transform_in()` | Entrada em um `Transform` e composição da matriz de modelo |
| `GL.transform_out()` | Restauração da matriz do nó pai |
| `GL.viewpoint()` | Matriz de câmera e `fieldOfView` |
| `GL.triangleSet()` | Pipeline de vértices 3D e projeção |
| `GL.triangleStripSet()` | Conversão de strips em triângulos |
| `GL.indexedTriangleStripSet()` | Conversão de strips indexadas em triângulos |
| `GL.indexedFaceSet()` | Triangulação de faces e associação de cor/UV |
| `GL._perspective_interp()` | Interpolação de atributos com correção perspectiva |
| `GL._gerar_mipmaps()` | Construção da pirâmide de mipmaps |
| `GL._lod_triangulo()` | Escolha do nível de mipmap |
| `GL._amostrar_textura()` | Amostragem da textura |
| `GL._iluminar()` | Iluminação Blinn-Phong |
| `GL.navigationInfo()` | Headlight da câmera |
| `GL.directionalLight()` | Luz direcional |
| `GL.timeSensor()` | Fração temporal da animação |
| `GL.splinePositionInterpolator()` | Interpolação suave de posição |
| `GL.orientationInterpolator()` | SLERP de orientação |

---

## Limitações

A implementação cobre o subconjunto de X3D utilizado nos projetos.

Entre as limitações atuais:

- `Box`, `Sphere`, `Cone` e `Cylinder` permanecem como placeholders;
- `PointLight` e `Fog` não estão implementados;
- as normais são calculadas por face;
- não há suavização de normais entre faces;
- não há implementação do sistema completo de eventos do X3D;
- não há double buffering completo para as animações.

