"""Verificações do Projeto 1.5: python3 -m unittest discover -s tests -v."""
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

os.environ.setdefault('MPLBACKEND', 'Agg')
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'renderizador'))
from gl import GL
from gpu import GPU
from renderizador import Renderizador
from x3d import X3D, X3DNode, DirectionalLight


def carregar(nome, width=60, height=40):
    path = next((ROOT / 'docs/exemplos').rglob(nome + '.x3d'))
    r = Renderizador()
    r.width, r.height = width, height
    GPU('teste.png', str(path.parent))
    X3D.preview = None
    X3D.current_texture = []
    X3DNode.named_nodes = {}
    r.scene = X3D(str(path))
    GL.setup(width, height)
    r.mapping()
    r.scene.parse()
    r.setup()
    return r


class IluminacaoTest(unittest.TestCase):
    def setUp(self):
        GL.setup(60, 40)
        self.posicao = np.array([0., 0., -5.])
        self.normal = np.array([0., 0., 1.])

    def cor(self, material, difusa=(0.4, 0.2, 0.1), posicao=None):
        return GL._iluminar(self.posicao if posicao is None else posicao,
                            self.normal, material, np.array(difusa))

    def test_emissao_independe_de_luz(self):
        np.testing.assert_allclose(self.cor({'emissiveColor': [0.2, 0.3, 0.4]}),
                                   [0.2, 0.3, 0.4])

    def test_difusa_e_ambiente_com_luz_colorida(self):
        GL.directionalLight(0.5, [1, 0.5, 0.25], 0.6, [0, 0, -2])
        np.testing.assert_allclose(self.cor({'ambientIntensity': 0.4}),
                                   [0.32, 0.08, 0.02])

    def test_luz_por_tras_so_contribui_ambiente(self):
        GL.directionalLight(0.5, [1, 1, 1], 1, [0, 0, 1])
        np.testing.assert_allclose(self.cor({'ambientIntensity': 0.4,
                                            'specularColor': [1, 1, 1]}),
                                   [0.08, 0.04, 0.02])

    def test_shininess_concentra_reflexo(self):
        GL.navigationInfo(True)
        material = {'specularColor': [0.8, 0.6, 0.4], 'shininess': 0.2}
        centro = self.cor(material, [0, 0, 0])
        posicao = np.array([4., 0., -5.])
        largo = self.cor(material, [0, 0, 0], posicao)
        material['shininess'] = 0.8
        estreito = self.cor(material, [0, 0, 0], posicao)
        np.testing.assert_allclose(centro, [0.8, 0.6, 0.4])
        self.assertTrue(np.all(centro > largo))
        self.assertTrue(np.all(largo > estreito))

    def test_luzes_somam_e_on_false_desliga(self):
        GL.navigationInfo(False)
        self.assertEqual(len(GL._lights), 0)
        node = DirectionalLight(ET.fromstring('<DirectionalLight on="false"/>'))
        node.render()
        self.assertEqual(len(GL._lights), 0)
        GL.directionalLight(0, [1, 0, 0], 0.5, [0, 0, -1])
        GL.directionalLight(0, [0, 1, 0], 0.5, [0, 0, -1])
        np.testing.assert_allclose(self.cor({}), [0.2, 0.1, 0])

    def test_headlight_segue_camera_mas_luz_mundial_nao(self):
        GL.view_matrix = GL._matriz_rotacao([0, 1, 0, math.pi / 2]).T
        GL.navigationInfo(True)
        GL.directionalLight(0, [1, 1, 1], 1, [0, 0, -1])
        np.testing.assert_allclose(GL._lights[0]['to_light'], [0, 0, 1])
        np.testing.assert_allclose(GL._lights[1]['to_light'], [-1, 0, 0], atol=1e-12)

    def test_normal_com_escala_nao_uniforme(self):
        carregar('mineiro')
        GL.transform_in([0, 0, 0], [2, 1, 0.5], [0, 1, 0, 0.3])
        vertices = np.array([[0., 0., -2.], [1., 0., -2.], [0., 1., -1.]])
        modelview = GL.view_matrix @ GL.model_matrix
        normal_local = np.cross(vertices[1]-vertices[0], vertices[2]-vertices[0])
        esperada = GL._normalizar(np.linalg.inv(modelview[:3, :3]).T @ normal_local)
        with patch.object(GL, '_triangulo') as rasterizar:
            GL.triangleSet(vertices.flatten().tolist(), {'diffuseColor': [1, 1, 1]})
        np.testing.assert_allclose(rasterizar.call_args.kwargs['normal'], esperada)


class AnimacaoTest(unittest.TestCase):
    def setUp(self):
        GL.setup(60, 40)

    def test_relogio_loop_e_parada(self):
        for segundos, repetindo, unico in [(0, 0, 0), (1, 0.25, 0.25),
                                          (4, 1, 1), (5, 0.25, 1)]:
            with self.subTest(segundos=segundos):
                GL._frame_elapsed = segundos
                self.assertEqual(GL.timeSensor(4, True), repetindo)
                self.assertEqual(GL.timeSensor(4, False), unico)
        with self.assertRaises(ValueError):
            GL.timeSensor(0, True)

    def test_spline_aberta_hermite_e_limites(self):
        key, valores = [0, 1], [0, 0, 0, 4, 0, 0]
        for t, x in [(-1, 0), (0, 0), (0.25, 0.625), (0.5, 2), (1, 4), (2, 4)]:
            np.testing.assert_allclose(GL.splinePositionInterpolator(t, key, valores, False),
                                       [x, 0, 0])

    def test_spline_chaves_nao_uniformes_e_fechamento(self):
        key = [0, 0.2, 0.65, 1]
        valores = [0, 0, 0, 1, 2, 0, 3, 1, 0, 0, 0, 0]
        for i, t in enumerate(key):
            np.testing.assert_allclose(GL.splinePositionInterpolator(t, key, valores, True),
                                       valores[3*i:3*i+3])
        key = [0, 0.25, 0.5, 0.75, 1]
        valores = [0, 0, 0, 1, 2, 0, 2, 0, 0, 1, -2, 0, 0, 0, 0]
        h = 1e-5
        pos = lambda t: np.array(GL.splinePositionInterpolator(t, key, valores, True))
        np.testing.assert_allclose((pos(h)-pos(0))/h, (pos(1)-pos(1-h))/h, atol=0.002)
        # closed deve ser ignorado se as posições extremas forem diferentes.
        valores[-3] = 3
        np.testing.assert_allclose(GL.splinePositionInterpolator(0.1, key, valores, True),
                                   GL.splinePositionInterpolator(0.1, key, valores, False))

    def test_slerp_meia_volta_e_eixos_distintos(self):
        rot = GL.orientationInterpolator(0.5, [0, 1], [0, 1, 0, 0, 0, 1, 0, math.pi])
        np.testing.assert_allclose(GL._matriz_rotacao(rot),
                                   GL._matriz_rotacao([0, 1, 0, math.pi/2]), atol=1e-12)
        rot = GL.orientationInterpolator(0.5, [0, 1],
                                          [1, 0, 0, math.pi/2, 0, 1, 0, math.pi/2])
        np.testing.assert_allclose(GL._matriz_rotacao(rot)[:3, :3],
                                   [[2/3, 1/3, 2/3], [1/3, 2/3, -2/3], [-2/3, 2/3, 1/3]],
                                   atol=1e-12)

    def test_slerp_arco_curto_identidade_e_limites(self):
        valores = [0, 0, 1, math.radians(350), 0, 0, 1, math.radians(10)]
        rot = GL.orientationInterpolator(0.5, [0, 1], valores)
        np.testing.assert_allclose(GL._matriz_rotacao(rot), np.eye(4), atol=1e-12)
        for t, esperado in [(-1, valores[:4]), (2, valores[4:])]:
            self.assertEqual(GL.orientationInterpolator(t, [0, 1], valores), esperado)
        rot = GL.orientationInterpolator(0.5, [0, 1], [0, 0, 1, 0]*2)
        np.testing.assert_allclose(GL._matriz_rotacao(rot), np.eye(4))

    def test_routes_atualizam_geometria_no_mesmo_quadro(self):
        r = carregar('avatar_animado')
        with patch('gl.time.monotonic', return_value=100):
            r.render()
        with patch('gl.time.monotonic', return_value=100.75), patch.object(GL, 'transform_in', wraps=GL.transform_in) as entrar:
            r.mapping()
            r.render()
        np.testing.assert_allclose(entrar.call_args_list[0].kwargs['translation'], [0, 0.25, 0])
        self.assertAlmostEqual(X3DNode.named_nodes['Clock'].fraction_changed, 0.25)
        np.testing.assert_allclose(X3DNode.named_nodes['BracoE_Ombro'].rotation,
                                   [-1, 0, 0, 2.4], atol=1e-12)
        self.assertEqual(GL.model_stack, [])


class IntegracaoTest(unittest.TestCase):
    def test_sete_exemplos_e_limpeza_entre_quadros(self):
        estaticos = ['difusos', 'mineiro', 'senoide_difusa', 'senoide_especular']
        animados = ['onda', 'piramide', 'avatar_animado']
        for nome in estaticos + animados:
            with self.subTest(nome=nome):
                r = carregar(nome)
                with patch('gl.time.monotonic', return_value=100):
                    a = r.render().copy()
                with patch('gl.time.monotonic', return_value=100.75):
                    b = r.render().copy()
                with patch('gl.time.monotonic', return_value=100):
                    repetida = r.render().copy()
                self.assertTrue(np.any(a))
                np.testing.assert_array_equal(a, repetida)
                self.assertEqual(np.array_equal(a, b), nome in estaticos)
                self.assertEqual(len(GL._lights), 1)

    def test_pixel_preto_e_profundidade_zero(self):
        carregar('mineiro')
        GPU.draw_pixel([0, 0], GPU.RGB8, [255, 255, 255])
        GPU.draw_pixel([0, 0], GPU.RGB8, [0, 0, 0])
        np.testing.assert_array_equal(GPU.read_pixel([0, 0], GPU.RGB8), [0, 0, 0])
        GPU.framebuffer_storage(0, GPU.DEPTH_ATTACHMENT, GPU.DEPTH_COMPONENT32F, 60, 40)
        GPU.draw_pixel([0, 0], GPU.DEPTH_COMPONENT32F, [0.0])
        self.assertEqual(GPU.read_pixel([0, 0], GPU.DEPTH_COMPONENT32F)[0], 0.0)

    def test_cli_quiet_renderiza_antes_de_salvar(self):
        path = next((ROOT / 'docs/exemplos').rglob('difusos.x3d'))
        with tempfile.TemporaryDirectory(prefix='rasterizer-') as pasta:
            subprocess.run([sys.executable, '-B', str(ROOT/'renderizador/renderizador.py'),
                            '-i', str(path), '-w', '60', '-h', '40', '-q',
                            '-o', str(Path(pasta)/'frame.png')], check=True,
                           capture_output=True, env={**os.environ, 'MPLBACKEND': 'Agg'})
            with Image.open(Path(pasta)/'frame000.png') as image:
                self.assertTrue(np.any(np.array(image)))


if __name__ == '__main__':
    unittest.main()
