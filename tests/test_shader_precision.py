"""Guard mobile defaults before engine uniforms, hash helpers and varyings."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKS = (ROOT / 'resource_pack', ROOT / 'extras/astral_survey_v1/resource_pack')


def code_only(source):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)


class MobileShaderPrecisionTests(unittest.TestCase):
    def test_shader_precision_is_explicit_before_headers_or_declarations(self):
        # GLES permits a mediump default. An override after an include cannot
        # repair TIME, matrices or function signatures already declared there.
        shaders = [p for pack in PACKS for p in (pack / 'shaders/glsl').iterdir()
                   if p.suffix in ('.vertex', '.fragment')]
        self.assertTrue(shaders)
        for path in shaders:
            with self.subTest(shader=path.relative_to(ROOT).as_posix()):
                code = code_only(path.read_text(encoding='utf8')).strip()
                self.assertRegex(code, r'^precision\s+highp\s+float\s*;')
                # A later engine-independent downgrade would affect locals
                # and function arguments even if varyings remain highp.
                defaults = re.findall(r'precision\s+(\w+)\s+float\s*;', code)
                self.assertEqual(['highp'], defaults)


if __name__ == '__main__':
    unittest.main()
