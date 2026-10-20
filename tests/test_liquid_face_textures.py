"""Resource drift and per-face payload contracts, not native UV acceptance."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
import generate_liquid_face_textures as generate
from projection.debug_blueprints import material
from projection.liquid_face_textures import LiquidFaceTextures
from projection.liquid_render_plan import LIQUID_NAMES, LiquidSurface, iter_groups, render_steps
from projection.model import Document


class Shapes(object):
    def __init__(self, texture='still_water_grey', uv=None):
        self.texture, self.uv = texture, uv

    def surface(self, document, pos, layer, value):
        return LiquidSurface(pos, layer, (.2, .4, .6, .8), 63, self.texture, self.uv)


class LiquidFaceTextureTests(unittest.TestCase):
    def test_provider_ownership_is_detached_immutable_and_preserves_empty_or_legacy_declarations(self):
        for declaration in (None, set(), {'minecraft:water'}, set(LIQUID_NAMES)):
            with self.subTest(declaration=declaration):
                shapes = Shapes()
                if declaration is not None:
                    shapes.supported_names = declaration
                provider = LiquidFaceTextures(shapes, {'flowing_water_grey': ('verified_side', 0)})
                expected = LIQUID_NAMES if declaration is None else frozenset(declaration)
                self.assertIsInstance(provider.supported_names, frozenset)
                self.assertEqual(expected, provider.supported_names)
                if declaration is not None:
                    declaration.clear()
                self.assertEqual(expected, provider.supported_names)

    def test_snapshot_reproduces_current_runtime_and_rejects_resource_drift(self):
        data = json.loads(generate.DEFAULT_SOURCE.read_text(encoding='utf8'))
        manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        generate.validate(data, manifest)
        self.assertEqual(generate.DEFAULT_OUTPUT.read_text(encoding='ascii'), generate.runtime_source(data))
        for field, value in (('schema_version', 2), ('game_version', 'future'), ('rows_sha256', '0' * 64)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                generate.validate(dict(data, **{field: value}), manifest)
        changed = copy.deepcopy(data)
        changed['rows']['minecraft:water']['side'] = 'still_lava'
        changed['rows_sha256'] = generate.digest(changed['rows'])
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            generate.validate(changed, manifest)

    def test_static_top_bottom_and_side_keep_disjoint_masks_and_identical_corners(self):
        document = Document((4, 3, 4), {(1, 1, 1): material('water')})
        provider = LiquidFaceTextures(Shapes(), {'flowing_water_grey': ('verified_side', 0)})
        groups = list(iter_groups(document, provider))
        parts = [part for group in groups for part in group.surfaces]
        self.assertEqual({33, 30}, {part.faces for part in parts})
        self.assertEqual({(.2, .4, .6, .8)}, {part.heights for part in parts})
        sides = next(part for part in parts if part.faces == 30)
        self.assertEqual(('flowing_water_grey', ('verified_side', 0)), (sides.texture_key, sides.flow_uv))

    def test_flowing_top_retains_rotation_separately_from_native_side_uvs(self):
        document = Document((4, 3, 4), {(1, 1, 1): material('water')})
        provider = LiquidFaceTextures(Shapes('flowing_water_grey', ('verified_flow', 64)),
                                     {'flowing_water_grey': ('verified_side', 0)})
        models = {('still_water_grey', None): 'still', ('flowing_water_grey', 'verified_flow'): 'flow',
                  ('flowing_water_grey', 'verified_side'): 'side'}
        draws = list(render_steps(iter_groups(document, provider), models, .5, 3))
        self.assertEqual({'still', 'flow', 'side'}, {draw.model_name for draw in draws})
        self.assertEqual(64, int(next(draw for draw in draws if draw.model_name == 'flow').uniforms[0][0]) >> 12)
        self.assertEqual(0, int(next(draw for draw in draws if draw.model_name == 'side').uniforms[0][0]) >> 12)

    def test_unverified_side_template_and_version_mismatch_are_explicit(self):
        document = Document((4, 3, 4), {(1, 1, 1): material('water')})
        with self.assertRaisesRegex(ValueError, 'UV template'):
            list(iter_groups(document, LiquidFaceTextures(Shapes(), {})))
        with patch('projection.liquid_face_textures.source.SOURCE_VERSION', 'future'):
            with self.assertRaisesRegex(ValueError, 'regeneration'):
                LiquidFaceTextures(Shapes(), {})
