#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# pylint: disable=invalid-name

"""
Biblioteca Gráfica / Graphics Library.

Desenvolvido por: Gustavo Colombi Ribolla e Luigi Orlandi Quinze
Disciplina: Computação Gráfica
Data: 21/09/2026
"""

import time         # Para operações com tempo
import gpu          # Simula os recursos de uma GPU
import math         # Funções matemáticas
import numpy as np  # Biblioteca do NumPy


class GL:
    """Classe que representa a biblioteca gráfica (Graphics Library)."""

    width = 800   # largura da tela
    height = 600  # altura da tela
    near = 0.01   # plano de corte próximo
    far = 1000    # plano de corte distante

    # Estado usado pelo pipeline 3D.
    # A matriz de modelo começa como identidade e é empilhada ao entrar em Transforms.
    model_matrix = np.identity(4)
    model_stack = []

    # Matriz que leva pontos do mundo para o sistema de coordenadas da câmera.
    view_matrix = np.identity(4)

    # Campo de visão vertical usado na projeção perspectiva.
    field_of_view = math.pi / 4

    # Projeto 1.4: supersampling 2x2. Cada pixel final mantém quatro amostras
    # internas; a cor exibida é a média delas. O buffer é reiniciado a cada
    # passagem pelo Viewpoint, que ocorre no início de cada frame.
    supersampling = 2
    _ssaa_buffer = None

    @staticmethod
    def setup(width, height, near=0.01, far=1000):
        """Define o tamanho da tela e os planos de corte próximo e distante."""
        GL.width = width
        GL.height = height
        GL.near = near
        GL.far = far

        # Reinicia o estado do pipeline 3D a cada nova renderização.
        GL.model_matrix = np.identity(4)
        GL.model_stack = []
        GL.view_matrix = np.identity(4)
        GL.field_of_view = math.pi / 4
        GL._ssaa_buffer = None

    @staticmethod
    def _matriz_rotacao(rotation):
        """Cria uma matriz 4x4 a partir da rotação eixo-ângulo do X3D."""
        if not rotation or len(rotation) < 4:
            return np.identity(4)

        x, y, z, angulo = rotation[:4]

        # O X3D informa uma rotação no formato eixo (x, y, z) + ângulo em radianos.
        # Normalizamos o eixo antes de aplicar a fórmula de Rodrigues.
        norma = math.sqrt(x * x + y * y + z * z)
        if norma == 0 or angulo == 0:
            return np.identity(4)

        x /= norma
        y /= norma
        z /= norma

        c = math.cos(angulo)
        s = math.sin(angulo)
        t = 1 - c

        return np.array([
            [t*x*x + c,     t*x*y - s*z,   t*x*z + s*y,   0.0],
            [t*x*y + s*z,   t*y*y + c,     t*y*z - s*x,   0.0],
            [t*x*z - s*y,   t*y*z + s*x,   t*z*z + c,     0.0],
            [0.0,           0.0,           0.0,           1.0]
        ], dtype=float)

    # ------------------------------------------------------------------
    # Rotinas auxiliares de rasterização (uso interno da biblioteca)
    # ------------------------------------------------------------------

    @staticmethod
    def _rgb8(colors, campo="emissiveColor"):
        """Converte uma cor do X3D (0.0 a 1.0) para o formato do framebuffer (0 a 255)."""
        cor = [0.0, 0.0, 0.0]
        if colors and colors.get(campo) is not None:
            cor = colors[campo]
        # Arredonda para o inteiro mais próximo e limita a faixa, evitando erro caso o
        # arquivo traga valores fora de [0, 1]
        return [min(255, max(0, round(c * 255))) for c in cor[:3]]

    @staticmethod
    def _pixel(x, y, rgb):
        """Pinta o pixel (x, y), ignorando o que estiver fora da tela (clipping)."""
        if 0 <= x < GL.width and 0 <= y < GL.height:
            gpu.GPU.draw_pixel([x, y], gpu.GPU.RGB8, rgb)

            # Primitivas que não passam por _triangulo() continuam compatíveis
            # com o buffer de supersampling: tratamos o pixel como totalmente
            # coberto pelas quatro amostras.
            if (GL._ssaa_buffer is not None and
                    GL._ssaa_buffer.shape[:2] == (GL.height, GL.width)):
                GL._ssaa_buffer[y, x, :, :] = np.array(rgb[:3], dtype=np.uint8)

    @staticmethod
    def _faixa_visivel(x0, y0, dx, dy):
        """Recorta o segmento à tela (Liang-Barsky).

        Devolve o intervalo (t_min, t_max), com t variando de 0 (início do segmento)
        a 1 (fim do segmento), no qual a reta está dentro da tela. Devolve None se o
        segmento estiver totalmente fora. Serve para não percorrer trechos inúteis de
        retas muito maiores que a tela.
        """
        t_min, t_max = 0.0, 1.0
        eps = 1e-9  # a borda direita/inferior é aberta: x < width e y < height

        # Cada borda da tela vira uma restrição do tipo: p * t <= q
        restricoes = (
            (-dx, x0),                          # x >= 0
            (dx, GL.width - eps - x0),          # x <  width
            (-dy, y0),                          # y >= 0
            (dy, GL.height - eps - y0),         # y <  height
        )

        for p, q in restricoes:
            if p == 0:                  # segmento paralelo a essa borda
                if q < 0:
                    return None         # e completamente fora dela
            else:
                t = q / p
                if p < 0:               # a reta entra na tela por essa borda
                    if t > t_max:
                        return None
                    t_min = max(t_min, t)
                else:                   # a reta sai da tela por essa borda
                    if t < t_min:
                        return None
                    t_max = min(t_max, t)

        return t_min, t_max

    @staticmethod
    def _linha(x0, y0, x1, y1, rgb):
        """Rasteriza um segmento de reta usando o algoritmo DDA."""
        dx = x1 - x0
        dy = y1 - y0

        # Número de passos = tamanho do segmento no eixo em que ele mais anda.
        # Com o arredondamento para cima, cada passo anda no máximo 1 pixel,
        # garantindo uma linha contínua (sem "buracos").
        passos = math.ceil(max(abs(dx), abs(dy)))
        if passos == 0:  # segmento degenerado: os dois extremos no mesmo pixel
            GL._pixel(math.floor(x0), math.floor(y0), rgb)
            return

        faixa = GL._faixa_visivel(x0, y0, dx, dy)
        if faixa is None:  # segmento inteiro fora da tela
            return

        # Converte o intervalo visível (t) para o índice dos passos do DDA,
        # com uma folga de um passo para cada lado por conta do arredondamento.
        inicio = max(0, math.floor(faixa[0] * passos) - 1)
        fim = min(passos, math.ceil(faixa[1] * passos) + 1)

        inc_x = dx / passos
        inc_y = dy / passos
        for i in range(inicio, fim + 1):
            GL._pixel(math.floor(x0 + i * inc_x), math.floor(y0 + i * inc_y), rgb)

    @staticmethod
    def _reiniciar_supersampling():
        """Recria as quatro amostras internas de cada pixel para um novo frame."""
        # O Renderizador limpa o framebuffer antes de percorrer a cena. Usamos a
        # mesma cor de limpeza como valor inicial de cada uma das quatro amostras.
        fundo = getattr(gpu.GPU, "clear_color_val", [0, 0, 0])
        fundo = np.array(fundo[:3], dtype=np.uint8)

        GL._ssaa_buffer = np.empty(
            (GL.height, GL.width, GL.supersampling, GL.supersampling, 3),
            dtype=np.uint8
        )
        GL._ssaa_buffer[:] = fundo

    @staticmethod
    def _triangulo(x0, y0, x1, y1, x2, y2, rgb,
                   cores_vertices=None, inv_w=None):
        """Rasteriza um triângulo com supersampling 2x2 e cores interpoladas."""
        # Dobro da área com sinal. Também será o denominador das coordenadas
        # baricêntricas usadas para interpolar atributos dentro do triângulo.
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if area == 0:
            return

        # Mantém a orientação anti-horária para a regra top-left. Se os vértices
        # forem trocados, os atributos associados a eles também precisam ser.
        if area < 0:
            x1, y1, x2, y2 = x2, y2, x1, y1
            area = -area
            if cores_vertices is not None:
                cores_vertices = [cores_vertices[0], cores_vertices[2],
                                   cores_vertices[1]]
            if inv_w is not None:
                inv_w = [inv_w[0], inv_w[2], inv_w[1]]

        # O buffer de supersampling é criado de forma preguiçosa. O Viewpoint o
        # reinicia no começo de cada frame, então triângulos vizinhos compartilham
        # corretamente suas quatro amostras sem criar costuras nas bordas.
        if GL._ssaa_buffer is None or GL._ssaa_buffer.shape[:2] != (GL.height, GL.width):
            GL._reiniciar_supersampling()

        min_x = max(0, math.floor(min(x0, x1, x2)))
        max_x = min(GL.width - 1, math.ceil(max(x0, x1, x2)))
        min_y = max(0, math.floor(min(y0, y1, y2)))
        max_y = min(GL.height - 1, math.ceil(max(y0, y1, y2)))

        # Arestas percorridas sempre no mesmo sentido.
        ax0, ay0 = x1 - x0, y1 - y0
        ax1, ay1 = x2 - x1, y2 - y1
        ax2, ay2 = x0 - x2, y0 - y2

        # Regra top-left: amostras exatamente sobre uma aresta pertencem a apenas
        # um dos triângulos que compartilham essa aresta.
        b0 = ay0 < 0 or (ay0 == 0 and ax0 > 0)
        b1 = ay1 < 0 or (ay1 == 0 and ax1 > 0)
        b2 = ay2 < 0 or (ay2 == 0 and ax2 > 0)

        # Posições regulares das quatro amostras de um supersampling 2x2.
        offsets = (0.25, 0.75)
        cor_constante = np.array(rgb, dtype=float)
        cores = None
        if cores_vertices is not None and len(cores_vertices) == 3:
            cores = [np.array(c, dtype=float) for c in cores_vertices]

        for py in range(min_y, max_y + 1):
            for px in range(min_x, max_x + 1):
                alterou_pixel = False

                for sy, oy in enumerate(offsets):
                    cy = py + oy
                    for sx, ox in enumerate(offsets):
                        cx = px + ox

                        e0 = ax0 * (cy - y0) - ay0 * (cx - x0)
                        if e0 < -1e-12 or (abs(e0) < 1e-12 and not b0):
                            continue
                        e1 = ax1 * (cy - y1) - ay1 * (cx - x1)
                        if e1 < -1e-12 or (abs(e1) < 1e-12 and not b1):
                            continue
                        e2 = ax2 * (cy - y2) - ay2 * (cx - x2)
                        if e2 < -1e-12 or (abs(e2) < 1e-12 and not b2):
                            continue

                        # e1, e2 e e0 correspondem, respectivamente, aos pesos
                        # baricêntricos dos vértices 0, 1 e 2.
                        l0 = e1 / area
                        l1 = e2 / area
                        l2 = e0 / area

                        cor_amostra = cor_constante
                        if cores is not None:
                            # Interpolação afim seria simplesmente
                            # l0*c0 + l1*c1 + l2*c2. Quando inv_w está disponível
                            # fazemos a correção de perspectiva, interpolando c/w e
                            # 1/w e dividindo os resultados no final.
                            if inv_w is not None and len(inv_w) == 3:
                                denominador = (l0 * inv_w[0] + l1 * inv_w[1] +
                                               l2 * inv_w[2])
                                if abs(denominador) > 1e-12:
                                    cor_amostra = (
                                        l0 * cores[0] * inv_w[0] +
                                        l1 * cores[1] * inv_w[1] +
                                        l2 * cores[2] * inv_w[2]
                                    ) / denominador
                                else:
                                    cor_amostra = (l0 * cores[0] + l1 * cores[1] +
                                                   l2 * cores[2])
                            else:
                                cor_amostra = (l0 * cores[0] + l1 * cores[1] +
                                               l2 * cores[2])

                        GL._ssaa_buffer[py, px, sy, sx] = np.clip(
                            np.rint(cor_amostra), 0, 255
                        ).astype(np.uint8)
                        alterou_pixel = True

                if alterou_pixel:
                    # Resolve as quatro amostras para o pixel final. Isso equivale
                    # ao downsampling do framebuffer 2x maior, mas sem exigir
                    # alterações no Renderizador ou na GPU simulada.
                    resolvida = np.rint(
                        GL._ssaa_buffer[py, px].astype(float).mean(axis=(0, 1))
                    ).astype(int).tolist()
                    gpu.GPU.draw_pixel([px, py], gpu.GPU.RGB8, resolvida)

    # ------------------------------------------------------------------
    # Nós de geometria 2D do X3D
    # ------------------------------------------------------------------

    @staticmethod
    def polypoint2D(point, colors):
        """Função usada para renderizar Polypoint2D."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/geometry2D.html#Polypoint2D
        # Nessa função você receberá pontos no parâmetro point, esses pontos são uma lista
        # de pontos x, y sempre na ordem. Assim point[0] é o valor da coordenada x do
        # primeiro ponto, point[1] o valor y do primeiro ponto. Já point[2] é a
        # coordenada x do segundo ponto e assim por diante.

        rgb = GL._rgb8(colors)  # cor emissiva convertida para a faixa do framebuffer

        # Percorre a lista de dois em dois valores (x, y) e acende o pixel
        # correspondente. O piso (floor) leva a coordenada contínua para o pixel
        # que a contém: o pixel n cobre o intervalo [n, n+1).
        for i in range(0, len(point) - 1, 2):
            GL._pixel(math.floor(point[i]), math.floor(point[i + 1]), rgb)

    @staticmethod
    def polyline2D(lineSegments, colors):
        """Função usada para renderizar Polyline2D."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/geometry2D.html#Polyline2D
        # Nessa função você receberá os pontos de uma linha no parâmetro lineSegments,
        # esses pontos são uma lista de pontos x, y sempre na ordem. A quantidade mínima
        # de pontos são 2 (4 valores), porém a função pode receber mais pontos para
        # desenhar vários segmentos contíguos.

        rgb = GL._rgb8(colors)

        # Liga cada ponto ao seguinte formando a poligonal
        for i in range(0, len(lineSegments) - 3, 2):
            GL._linha(lineSegments[i], lineSegments[i + 1],
                      lineSegments[i + 2], lineSegments[i + 3], rgb)

    @staticmethod
    def circle2D(radius, colors):
        """Função usada para renderizar Circle2D."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/geometry2D.html#Circle2D
        # Nessa função você receberá um valor de raio e deverá desenhar o contorno de
        # um círculo. Pelo X3D o círculo é sempre centrado na origem (0, 0).

        rgb = GL._rgb8(colors)
        raio = abs(radius)

        # O círculo é aproximado por uma poligonal. O número de lados acompanha o
        # perímetro (2*pi*r) para que cada lado tenha cerca de 1 pixel de comprimento.
        por_quadrante = max(6, math.ceil(math.pi * raio / 2))

        # Calcula só o primeiro quadrante, de (r, 0) até (0, r)
        arco = [(raio * math.cos((math.pi / 2) * i / por_quadrante),
                 raio * math.sin((math.pi / 2) * i / por_quadrante))
                for i in range(por_quadrante)]
        arco.append((0.0, raio))  # extremo exato, sem o erro de arredondamento do cosseno

        # Os outros três quadrantes são o mesmo arco girado de 90 em 90 graus, o que
        # equivale a trocar as coordenadas de lugar e o sinal. Assim o traço fica
        # perfeitamente simétrico, sem depender da precisão do seno e do cosseno.
        contorno = list(arco)
        contorno += [(-y, x) for x, y in arco[1:]]
        contorno += [(-x, -y) for x, y in arco[1:]]
        contorno += [(y, -x) for x, y in arco[1:]]

        # Liga os pontos do contorno, fechando o círculo no final
        for i in range(len(contorno)):
            x_ini, y_ini = contorno[i]
            x_fim, y_fim = contorno[(i + 1) % len(contorno)]
            GL._linha(x_ini, y_ini, x_fim, y_fim, rgb)

    @staticmethod
    def triangleSet2D(vertices, colors):
        """Função usada para renderizar TriangleSet2D."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/geometry2D.html#TriangleSet2D
        # Nessa função você receberá os vertices de um triângulo no parâmetro vertices,
        # esses pontos são uma lista de pontos x, y sempre na ordem. A quantidade de
        # pontos é sempre múltiplo de 3, ou seja, 6 valores, 12 valores, etc.

        rgb = GL._rgb8(colors)

        # A cada 6 valores temos um triângulo (3 vértices de 2 coordenadas)
        for i in range(0, len(vertices) - 5, 6):
            GL._triangulo(vertices[i], vertices[i + 1],
                          vertices[i + 2], vertices[i + 3],
                          vertices[i + 4], vertices[i + 5], rgb)

    @staticmethod
    def triangleSet(point, colors, vertex_colors=None):
        """Renderiza TriangleSet e permite interpolação de cores por vértice."""
        # O parâmetro vertex_colors é opcional e foi acrescentado no Projeto 1.4.
        # Quando ausente, o comportamento continua igual ao das etapas anteriores:
        # o triângulo usa a cor emissiva do Material.
        rgb = GL._rgb8(colors)

        aspecto = GL.width / GL.height
        f = 1.0 / math.tan(GL.field_of_view / 2.0)

        projecao = np.array([
            [f / aspecto, 0.0, 0.0, 0.0],
            [0.0, f, 0.0, 0.0],
            [0.0, 0.0, -(GL.far + GL.near) / (GL.far - GL.near),
             -(2.0 * GL.far * GL.near) / (GL.far - GL.near)],
            [0.0, 0.0, -1.0, 0.0]
        ], dtype=float)

        for i in range(0, len(point) - 8, 9):
            vertices_tela = []
            inversos_w = []
            triangulo_valido = True

            for j in range(3):
                k = i + j * 3
                vertice = np.array([point[k], point[k + 1], point[k + 2], 1.0],
                                    dtype=float)

                mundo = GL.model_matrix @ vertice
                camera = GL.view_matrix @ mundo
                clip = projecao @ camera

                # Nesta etapa ainda não há clipping 3D contra o plano near.
                if clip[3] <= 0:
                    triangulo_valido = False
                    break

                inversos_w.append(1.0 / clip[3])
                ndc = clip[:3] / clip[3]

                x_tela = (ndc[0] + 1.0) * GL.width / 2.0
                y_tela = (1.0 - ndc[1]) * GL.height / 2.0
                vertices_tela.append((x_tela, y_tela))

            if not triangulo_valido:
                continue

            cores_triangulo = None
            primeiro_vertice = i // 3
            if (vertex_colors is not None and
                    len(vertex_colors) >= (primeiro_vertice + 3) * 3):
                cores_triangulo = []
                for j in range(3):
                    c = (primeiro_vertice + j) * 3
                    cores_triangulo.append([
                        min(255, max(0, round(vertex_colors[c] * 255))),
                        min(255, max(0, round(vertex_colors[c + 1] * 255))),
                        min(255, max(0, round(vertex_colors[c + 2] * 255)))
                    ])

            GL._triangulo(vertices_tela[0][0], vertices_tela[0][1],
                          vertices_tela[1][0], vertices_tela[1][1],
                          vertices_tela[2][0], vertices_tela[2][1], rgb,
                          cores_vertices=cores_triangulo, inv_w=inversos_w)

    @staticmethod
    def viewpoint(position, orientation, fieldOfView):
        """Monta a matriz de visualização a partir do Viewpoint do X3D."""
        # A câmera possui uma transformação no mundo, mas para transformar o mundo
        # para o espaço da câmera precisamos usar a transformação inversa.
        #
        # Se C = T * R representa a câmera no mundo, então:
        # View = C^-1 = R^-1 * T^-1.
        #
        # Como R é uma matriz de rotação, R^-1 = R.T.

        if not position or len(position) < 3:
            position = [0.0, 0.0, 10.0]

        if not orientation or len(orientation) < 4:
            orientation = [0.0, 0.0, 1.0, 0.0]

        px, py, pz = position[:3]

        # Inversa da translação da câmera.
        translacao_inversa = np.identity(4)
        translacao_inversa[0, 3] = -px
        translacao_inversa[1, 3] = -py
        translacao_inversa[2, 3] = -pz

        # Inversa da rotação da câmera.
        rotacao = GL._matriz_rotacao(orientation)
        rotacao_inversa = rotacao.T

        GL.view_matrix = rotacao_inversa @ translacao_inversa

        # O Viewpoint é processado no início de cada frame. Aproveitamos esse
        # ponto para limpar as quatro amostras internas do supersampling.
        GL._reiniciar_supersampling()

        # Guarda o FOV para a matriz de projeção usada em triangleSet().
        GL.field_of_view = fieldOfView if fieldOfView is not None else math.pi / 4

    @staticmethod
    def transform_in(translation, scale, rotation):
        """Entra em um Transform e atualiza a matriz de modelo atual."""
        # Valores padrão do nó Transform do X3D.
        if not translation or len(translation) < 3:
            translation = [0.0, 0.0, 0.0]

        if not scale or len(scale) < 3:
            scale = [1.0, 1.0, 1.0]

        if not rotation or len(rotation) < 4:
            rotation = [0.0, 0.0, 1.0, 0.0]

        tx, ty, tz = translation[:3]
        sx, sy, sz = scale[:3]

        # Matriz de translação.
        matriz_translacao = np.identity(4)
        matriz_translacao[0, 3] = tx
        matriz_translacao[1, 3] = ty
        matriz_translacao[2, 3] = tz

        # Matriz de escala.
        matriz_escala = np.identity(4)
        matriz_escala[0, 0] = sx
        matriz_escala[1, 1] = sy
        matriz_escala[2, 2] = sz

        # Matriz de rotação eixo-ângulo.
        matriz_rotacao = GL._matriz_rotacao(rotation)

        # No X3D, para este projeto, aplicamos escala, depois rotação e por último
        # translação ao ponto. Com vetores-coluna isso resulta em T @ R @ S.
        matriz_local = matriz_translacao @ matriz_rotacao @ matriz_escala

        # Projeto 1.3: o grafo de cena pode ter Transform dentro de Transform.
        # Guardamos a matriz do pai antes de entrar no filho.
        GL.model_stack.append(GL.model_matrix.copy())

        # A transformação local é composta com a transformação acumulada do pai.
        # Assim, todos os descendentes usam corretamente o sistema de coordenadas
        # definido pelos Transforms acima deles no grafo de cena.
        GL.model_matrix = GL.model_matrix @ matriz_local

    @staticmethod
    def transform_out():
        """Sai de um Transform e recupera a matriz do nó pai no grafo de cena."""
        if GL.model_stack:
            # Ao terminar os filhos do Transform atual, voltamos exatamente ao
            # sistema de coordenadas que estava ativo antes de entrar nesse nó.
            GL.model_matrix = GL.model_stack.pop()
        else:
            # Segurança para não deixar uma transformação antiga ativa caso a
            # função seja chamada sem um Transform correspondente na pilha.
            GL.model_matrix = np.identity(4)

    @staticmethod
    def triangleStripSet(point, stripCount, colors):
        """Renderiza uma ou mais tiras de triângulos."""
        # Cada valor de stripCount informa quantos vértices consecutivos pertencem
        # àquela tira. Uma tira com n vértices gera n - 2 triângulos.
        triangulos = []
        primeiro_vertice = 0
        total_vertices = len(point) // 3

        for quantidade in stripCount:
            # Ignora tiras inválidas sem comprometer as próximas.
            if quantidade < 3:
                primeiro_vertice += max(quantidade, 0)
                continue

            fim = min(primeiro_vertice + quantidade, total_vertices)

            for i in range(primeiro_vertice, fim - 2):
                # Em uma triangle strip a orientação alterna a cada triângulo.
                # Trocamos os dois primeiros vértices nos triângulos ímpares para
                # manter todos com o mesmo sentido de orientação.
                local = i - primeiro_vertice
                if local % 2 == 0:
                    indices = (i, i + 1, i + 2)
                else:
                    indices = (i + 1, i, i + 2)

                for indice in indices:
                    base = indice * 3
                    triangulos.extend(point[base:base + 3])

            primeiro_vertice += quantidade

        # Reaproveita o pipeline 3D já implementado no Projeto 1.2.
        if triangulos:
            GL.triangleSet(triangulos, colors)

    @staticmethod
    def indexedTriangleStripSet(point, index, colors):
        """Renderiza tiras de triângulos definidas por índices."""
        triangulos = []
        tira = []
        total_vertices = len(point) // 3

        def adicionar_tira(indices_tira):
            """Converte uma tira indexada em triângulos independentes."""
            for i in range(len(indices_tira) - 2):
                if i % 2 == 0:
                    indices_triangulo = (indices_tira[i], indices_tira[i + 1],
                                         indices_tira[i + 2])
                else:
                    indices_triangulo = (indices_tira[i + 1], indices_tira[i],
                                         indices_tira[i + 2])

                # Um índice inválido é simplesmente ignorado para evitar acesso
                # fora da lista de coordenadas.
                if not all(0 <= indice < total_vertices
                           for indice in indices_triangulo):
                    continue

                for indice in indices_triangulo:
                    base = indice * 3
                    triangulos.extend(point[base:base + 3])

        # O -1 separa uma tira da próxima.
        for indice in index:
            if indice == -1:
                if len(tira) >= 3:
                    adicionar_tira(tira)
                tira = []
            else:
                tira.append(indice)

        # Também aceita uma última tira sem -1 no final.
        if len(tira) >= 3:
            adicionar_tira(tira)

        if triangulos:
            GL.triangleSet(triangulos, colors)

    @staticmethod
    def indexedFaceSet(coord, coordIndex, colorPerVertex, color, colorIndex,
                       texCoord, texCoordIndex, colors, current_texture):
        """Renderiza faces indexadas e interpola cores definidas nos vértices."""
        if not coord or not coordIndex:
            return

        total_vertices = len(coord) // 3
        total_cores = len(color) // 3 if color else 0

        # Separa uma lista indexada por -1 em faces. Essa mesma rotina serve
        # tanto para coordIndex quanto para colorIndex.
        def separar_faces(indices):
            faces = []
            atual = []
            for indice in indices or []:
                if indice == -1:
                    if atual:
                        faces.append(atual)
                    atual = []
                else:
                    atual.append(indice)
            if atual:
                faces.append(atual)
            return faces

        faces_coord = separar_faces(coordIndex)
        faces_cor = separar_faces(colorIndex) if colorIndex else []

        triangulos = []
        cores_triangulos = []
        tem_cores_vertices = bool(color)

        for numero_face, face in enumerate(faces_coord):
            if len(face) < 3:
                continue

            # Define como cada posição da face encontra sua cor.
            indices_cor_face = None
            cor_face = None

            if tem_cores_vertices and colorPerVertex:
                if numero_face < len(faces_cor):
                    indices_cor_face = faces_cor[numero_face]
                else:
                    # Pelo X3D, colorIndex vazio significa usar os próprios
                    # índices das coordenadas para buscar as cores.
                    indices_cor_face = face
            elif tem_cores_vertices:
                # colorPerVertex=false: uma única cor vale para a face inteira.
                # Quando colorIndex está vazio, a ordem das faces escolhe a cor.
                if colorIndex:
                    indices_planos = [i for i in colorIndex if i != -1]
                    indice_cor = (indices_planos[numero_face]
                                  if numero_face < len(indices_planos)
                                  else numero_face)
                else:
                    indice_cor = numero_face

                if 0 <= indice_cor < total_cores:
                    base_cor = indice_cor * 3
                    cor_face = color[base_cor:base_cor + 3]

            # Triangulação em leque: (v0,v1,v2), (v0,v2,v3), ...
            for i in range(1, len(face) - 1):
                posicoes = (0, i, i + 1)
                indices_triangulo = tuple(face[p] for p in posicoes)

                if not all(0 <= indice < total_vertices
                           for indice in indices_triangulo):
                    continue

                for indice in indices_triangulo:
                    base = indice * 3
                    triangulos.extend(coord[base:base + 3])

                if tem_cores_vertices:
                    if colorPerVertex:
                        cores_validas = True
                        cores_temp = []
                        for posicao in posicoes:
                            if (indices_cor_face is None or
                                    posicao >= len(indices_cor_face)):
                                cores_validas = False
                                break
                            indice_cor = indices_cor_face[posicao]
                            if not 0 <= indice_cor < total_cores:
                                cores_validas = False
                                break
                            base_cor = indice_cor * 3
                            cores_temp.extend(color[base_cor:base_cor + 3])

                        if cores_validas:
                            cores_triangulos.extend(cores_temp)
                        else:
                            # Mantém o alinhamento com os vértices já adicionados.
                            cores_triangulos.extend([0.0] * 9)
                    else:
                        if cor_face is not None:
                            cores_triangulos.extend(cor_face * 3)
                        else:
                            cores_triangulos.extend([0.0] * 9)

        if triangulos:
            vertex_colors = cores_triangulos if tem_cores_vertices else None
            GL.triangleSet(triangulos, colors, vertex_colors=vertex_colors)

    @staticmethod
    def box(size, colors):
        """Função usada para renderizar Boxes."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/geometry3D.html#Box
        # A função box é usada para desenhar paralelepípedos na cena. O Box é centrada no
        # (0, 0, 0) no sistema de coordenadas local e alinhado com os eixos de coordenadas
        # locais. O argumento size especifica as extensões da caixa ao longo dos eixos X, Y
        # e Z, respectivamente, e cada valor do tamanho deve ser maior que zero. Para desenha
        # essa caixa você vai provavelmente querer tesselar ela em triângulos, para isso
        # encontre os vértices e defina os triângulos.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("Box : size = {0}".format(size)) # imprime no terminal pontos
        print("Box : colors = {0}".format(colors)) # imprime no terminal as cores

        # Exemplo de desenho de um pixel branco na coordenada 10, 10
        gpu.GPU.draw_pixel([10, 10], gpu.GPU.RGB8, [255, 255, 255])  # altera pixel

    @staticmethod
    def sphere(radius, colors):
        """Função usada para renderizar Esferas."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/geometry3D.html#Sphere
        # A função sphere é usada para desenhar esferas na cena. O esfera é centrada no
        # (0, 0, 0) no sistema de coordenadas local. O argumento radius especifica o
        # raio da esfera que está sendo criada. Para desenha essa esfera você vai
        # precisar tesselar ela em triângulos, para isso encontre os vértices e defina
        # os triângulos.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("Sphere : radius = {0}".format(radius)) # imprime no terminal o raio da esfera
        print("Sphere : colors = {0}".format(colors)) # imprime no terminal as cores

    @staticmethod
    def cone(bottomRadius, height, colors):
        """Função usada para renderizar Cones."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/geometry3D.html#Cone
        # A função cone é usada para desenhar cones na cena. O cone é centrado no
        # (0, 0, 0) no sistema de coordenadas local. O argumento bottomRadius especifica o
        # raio da base do cone e o argumento height especifica a altura do cone.
        # O cone é alinhado com o eixo Y local. O cone é fechado por padrão na base.
        # Para desenha esse cone você vai precisar tesselar ele em triângulos, para isso
        # encontre os vértices e defina os triângulos.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("Cone : bottomRadius = {0}".format(bottomRadius)) # imprime no terminal o raio da base do cone
        print("Cone : height = {0}".format(height)) # imprime no terminal a altura do cone
        print("Cone : colors = {0}".format(colors)) # imprime no terminal as cores

    @staticmethod
    def cylinder(radius, height, colors):
        """Função usada para renderizar Cilindros."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/geometry3D.html#Cylinder
        # A função cylinder é usada para desenhar cilindros na cena. O cilindro é centrado no
        # (0, 0, 0) no sistema de coordenadas local. O argumento radius especifica o
        # raio da base do cilindro e o argumento height especifica a altura do cilindro.
        # O cilindro é alinhado com o eixo Y local. O cilindro é fechado por padrão em ambas as extremidades.
        # Para desenha esse cilindro você vai precisar tesselar ele em triângulos, para isso
        # encontre os vértices e defina os triângulos.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("Cylinder : radius = {0}".format(radius)) # imprime no terminal o raio do cilindro
        print("Cylinder : height = {0}".format(height)) # imprime no terminal a altura do cilindro
        print("Cylinder : colors = {0}".format(colors)) # imprime no terminal as cores

    @staticmethod
    def navigationInfo(headlight):
        """Características físicas do avatar do visualizador e do modelo de visualização."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/navigation.html#NavigationInfo
        # O campo do headlight especifica se um navegador deve acender um luz direcional que
        # sempre aponta na direção que o usuário está olhando. Definir este campo como TRUE
        # faz com que o visualizador forneça sempre uma luz do ponto de vista do usuário.
        # A luz headlight deve ser direcional, ter intensidade = 1, cor = (1 1 1),
        # ambientIntensity = 0,0 e direção = (0 0 −1).

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("NavigationInfo : headlight = {0}".format(headlight)) # imprime no terminal

    @staticmethod
    def directionalLight(ambientIntensity, color, intensity, direction):
        """Luz direcional ou paralela."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/lighting.html#DirectionalLight
        # Define uma fonte de luz direcional que ilumina ao longo de raios paralelos
        # em um determinado vetor tridimensional. Possui os campos básicos ambientIntensity,
        # cor, intensidade. O campo de direção especifica o vetor de direção da iluminação
        # que emana da fonte de luz no sistema de coordenadas local. A luz é emitida ao
        # longo de raios paralelos de uma distância infinita.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("DirectionalLight : ambientIntensity = {0}".format(ambientIntensity))
        print("DirectionalLight : color = {0}".format(color)) # imprime no terminal
        print("DirectionalLight : intensity = {0}".format(intensity)) # imprime no terminal
        print("DirectionalLight : direction = {0}".format(direction)) # imprime no terminal

    @staticmethod
    def pointLight(ambientIntensity, color, intensity, location):
        """Luz pontual."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/lighting.html#PointLight
        # Fonte de luz pontual em um local 3D no sistema de coordenadas local. Uma fonte
        # de luz pontual emite luz igualmente em todas as direções; ou seja, é omnidirecional.
        # Possui os campos básicos ambientIntensity, cor, intensidade. Um nó PointLight ilumina
        # a geometria em um raio de sua localização. O campo do raio deve ser maior ou igual a
        # zero. A iluminação do nó PointLight diminui com a distância especificada.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("PointLight : ambientIntensity = {0}".format(ambientIntensity))
        print("PointLight : color = {0}".format(color)) # imprime no terminal
        print("PointLight : intensity = {0}".format(intensity)) # imprime no terminal
        print("PointLight : location = {0}".format(location)) # imprime no terminal

    @staticmethod
    def fog(visibilityRange, color):
        """Névoa."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/environmentalEffects.html#Fog
        # O nó Fog fornece uma maneira de simular efeitos atmosféricos combinando objetos
        # com a cor especificada pelo campo de cores com base nas distâncias dos
        # vários objetos ao visualizador. A visibilidadeRange especifica a distância no
        # sistema de coordenadas local na qual os objetos são totalmente obscurecidos
        # pela névoa. Os objetos localizados fora de visibilityRange do visualizador são
        # desenhados com uma cor de cor constante. Objetos muito próximos do visualizador
        # são muito pouco misturados com a cor do nevoeiro.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("Fog : color = {0}".format(color)) # imprime no terminal
        print("Fog : visibilityRange = {0}".format(visibilityRange))

    @staticmethod
    def timeSensor(cycleInterval, loop):
        """Gera eventos conforme o tempo passa."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/time.html#TimeSensor
        # Os nós TimeSensor podem ser usados para muitas finalidades, incluindo:
        # Condução de simulações e animações contínuas; Controlar atividades periódicas;
        # iniciar eventos de ocorrência única, como um despertador;
        # Se, no final de um ciclo, o valor do loop for FALSE, a execução é encerrada.
        # Por outro lado, se o loop for TRUE no final de um ciclo, um nó dependente do
        # tempo continua a execução no próximo ciclo. O ciclo de um nó TimeSensor dura
        # cycleInterval segundos. O valor de cycleInterval deve ser maior que zero.

        # Deve retornar a fração de tempo passada em fraction_changed

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("TimeSensor : cycleInterval = {0}".format(cycleInterval)) # imprime no terminal
        print("TimeSensor : loop = {0}".format(loop))

        # Esse método já está implementado para os alunos como exemplo
        epoch = time.time()  # time in seconds since the epoch as a floating point number.
        fraction_changed = (epoch % cycleInterval) / cycleInterval

        return fraction_changed

    @staticmethod
    def splinePositionInterpolator(set_fraction, key, keyValue, closed):
        """Interpola não linearmente entre uma lista de vetores 3D."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/interpolators.html#SplinePositionInterpolator
        # Interpola não linearmente entre uma lista de vetores 3D. O campo keyValue possui
        # uma lista com os valores a serem interpolados, key possui uma lista respectiva de chaves
        # dos valores em keyValue, a fração a ser interpolada vem de set_fraction que varia de
        # zero a um. O campo keyValue deve conter exatamente tantos vetores 3D quanto os
        # quadros-chave no key. O campo closed especifica se o interpolador deve tratar a malha
        # como fechada, com uma transições da última chave para a primeira chave. Se os keyValues
        # na primeira e na última chave não forem idênticos, o campo closed será ignorado.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("SplinePositionInterpolator : set_fraction = {0}".format(set_fraction))
        print("SplinePositionInterpolator : key = {0}".format(key)) # imprime no terminal
        print("SplinePositionInterpolator : keyValue = {0}".format(keyValue))
        print("SplinePositionInterpolator : closed = {0}".format(closed))

        # Abaixo está só um exemplo de como os dados podem ser calculados e transferidos
        value_changed = [0.0, 0.0, 0.0]
        
        return value_changed

    @staticmethod
    def orientationInterpolator(set_fraction, key, keyValue):
        """Interpola entre uma lista de valores de rotação específicos."""
        # https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/interpolators.html#OrientationInterpolator
        # As rotações interpoladas são absolutas no espaço do objeto e, portanto, não são cumulativas.
        # Uma orientação representa a posição final de um objeto após a aplicação de uma rotação.
        # Um OrientationInterpolator interpola entre duas orientações calculando o caminho mais
        # curto na esfera unitária entre as duas orientações. A interpolação é linear em
        # comprimento de arco ao longo deste caminho. Os resultados são indefinidos se as duas
        # orientações forem diagonalmente opostas. O campo keyValue possui uma lista com os
        # valores a serem interpolados, key possui uma lista respectiva de chaves
        # dos valores em keyValue, a fração a ser interpolada vem de set_fraction que varia de
        # zero a um. O campo keyValue deve conter exatamente tantas rotações 3D quanto os
        # quadros-chave no key.

        # O print abaixo é só para vocês verificarem o funcionamento, DEVE SER REMOVIDO.
        print("OrientationInterpolator : set_fraction = {0}".format(set_fraction))
        print("OrientationInterpolator : key = {0}".format(key)) # imprime no terminal
        print("OrientationInterpolator : keyValue = {0}".format(keyValue))

        # Abaixo está só um exemplo de como os dados podem ser calculados e transferidos
        value_changed = [0, 0, 1, 0]

        return value_changed

    # Para o futuro (Não para versão atual do projeto.)
    def vertex_shader(self, shader):
        """Para no futuro implementar um vertex shader."""

    def fragment_shader(self, shader):
        """Para no futuro implementar um fragment shader."""