"""Guard mobile defaults before engine uniforms, hash helpers and varyings."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKS = (ROOT / 'resource_pack', ROOT / 'extras/astral_survey_v1/resource_pack')
FLOAT_TYPES = r'(?:float|vec[234]|mat[234](?:x[234])?)'
# This native normalized normal/layer packet deliberately retains the same
# lowp interface at both ends. Its raw fragment/world bytes and generated UI
# source are checked by test_portal_native_candidate; changing their precision
# here would invalidate the captured native rendering comparison.
NATIVE_PLANE_INTERFACE = frozenset(
    'resource_pack/shaders/glsl/modern_projection_portal_native_' + name
    for name in ('original.h', 'ui.vertex', 'world.vertex'))
NATIVE_PLANE_DECLARATION = r'\bvarying\s+lowp\s+vec4\s+encodedPlane\s*;'


def code_only(source):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)


def shader_sources(suffixes):
    return sorted(p for pack in PACKS for p in (pack / 'shaders/glsl').rglob('*')
                  if p.is_file() and p.suffix in suffixes)


class MobileShaderPrecisionTests(unittest.TestCase):
    def test_shader_precision_is_explicit_before_headers_or_declarations(self):
        # GLES permits a mediump default. An override after an include cannot
        # repair TIME, matrices or function signatures already declared there.
        shaders = shader_sources(('.vertex', '.fragment'))
        self.assertTrue(shaders)
        for path in shaders:
            with self.subTest(shader=path.relative_to(ROOT).as_posix()):
                code = code_only(path.read_text(encoding='utf8')).strip()
                self.assertRegex(code, r'^precision\s+highp\s+float\s*;')
                # A later engine-independent downgrade would affect locals
                # and function arguments even if varyings remain highp.
                defaults = re.findall(r'precision\s+(\w+)\s+float\s*;', code)
                self.assertEqual(['highp'], defaults)

    def test_shared_headers_do_not_downgrade_the_callers_float_precision(self):
        headers = shader_sources(('.h', '.glsl'))
        self.assertTrue(headers)
        for path in headers:
            with self.subTest(shader=path.relative_to(ROOT).as_posix()):
                code = code_only(path.read_text(encoding='utf8'))
                defaults = re.findall(r'precision\s+(\w+)\s+float\s*;', code)
                self.assertTrue(all(value == 'highp' for value in defaults))

    def test_float_uniforms_and_varyings_do_not_override_highp_with_lower_precision(self):
        # Positions, time and product payloads must retain highp. Only the
        # exact native normalized packet above has a lower-precision contract.
        pattern = (r'\b(?:uniform|UNIFORM|varying)\s+(?:lowp|mediump)\s+'
                   + FLOAT_TYPES + r'\b')
        native_interfaces = set()
        for path in shader_sources(('.vertex', '.fragment', '.h', '.glsl')):
            relative = path.relative_to(ROOT).as_posix()
            with self.subTest(shader=relative):
                code = code_only(path.read_text(encoding='utf8'))
                if relative in NATIVE_PLANE_INTERFACE:
                    self.assertEqual(1, len(re.findall(NATIVE_PLANE_DECLARATION, code)))
                    code = re.sub(NATIVE_PLANE_DECLARATION, '', code, count=1)
                    native_interfaces.add(relative)
                self.assertNotRegex(code, pattern)
        self.assertEqual(NATIVE_PLANE_INTERFACE, native_interfaces)


if __name__ == '__main__':
    unittest.main()
