"""The normal-clock native candidate must remain separate from the old default."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from generate_portal_native_candidate_r21 import EVIDENCE, PREFIX, generate, install
from projection import portal_profile
from projection.model import Document
from projection.portal_render_plan import iter_render_steps


class PortalNativeCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.output = Path(cls.directory.name) / 'candidate'
        cls.contract = generate(ROOT, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_native_profile_never_inherits_the_old_qualification(self):
        legacy = portal_profile.production_profile(portal_profile.ENGINE_VERSION)
        self.assertIsNotNone(legacy)
        self.assertFalse(portal_profile.NATIVE_PRODUCT_QUALIFIED)
        for version in (None, portal_profile.ENGINE_VERSION, '3.10.0.420448'):
            self.assertIsNone(portal_profile.native_production_profile(version))
        candidate = portal_profile.native_candidate_profile()
        self.assertEqual(portal_profile.PortalProfile, type(candidate))
        self.assertNotEqual(legacy.identity, candidate.identity)
        with patch.object(portal_profile, 'NATIVE_PRODUCT_QUALIFIED', True):
            with self.assertRaises(ValueError):
                portal_profile.native_production_profile(portal_profile.ENGINE_VERSION)
        for budget in (True, 0, -1, 1.2):
            with self.assertRaises(ValueError):
                portal_profile.native_candidate_profile(budget)

    def test_existing_plan_publishes_distinct_ui_and_world_aliases_without_mutation(self):
        document = Document((4, 4, 4), {(1, 1, 1): ('minecraft:end_gateway', 0),
                                      (2, 1, 1): ('minecraft:end_portal', 0)})
        before = deepcopy(document.to_data())
        profile = portal_profile.native_candidate_profile()
        for world in (False, True):
            groups = [group for group in iter_render_steps(document, profile, world=world) if group]
            self.assertEqual(2, len(groups))
            suffix = '_world' if world else ''
            self.assertEqual({PREFIX + family + suffix for family in ('end_gateway', 'end_portal')},
                             {group.model_name for group in groups})
        self.assertEqual(before, document.to_data())

    def test_measured_world_source_and_native_artwork_retain_raw_bytes(self):
        frozen = EVIDENCE / 'frozen/resource_pack'
        actual = self.output / 'resource_pack'
        self.assertEqual((frozen / 'shaders/glsl/r19_native_portal_world.vertex').read_bytes(),
                         (actual / ('shaders/glsl/' + PREFIX + 'world.vertex')).read_bytes())
        self.assertEqual((frozen / 'shaders/glsl/r19_native_portal_original.h').read_bytes(),
                         (actual / ('shaders/glsl/' + PREFIX + 'original.h')).read_bytes())
        self.assertEqual((frozen / 'textures/models/modern_projection/portal/r19_native_starfield.png').read_bytes(),
                         (actual / 'textures/models/modern_projection/portal/native_starfield.png').read_bytes())
        world = (actual / ('shaders/glsl/' + PREFIX + 'world.vertex')).read_text(encoding='ascii')
        self.assertIn('parallaxUV.y+=TIME/256.0;', world)
        self.assertNotIn('64.0/256.0', world)
        self.assertFalse((actual / 'materials/portal.material').exists())
        self.assertFalse(self.contract['native_product_qualified'])
        for name, expected in self.contract['output_sha256'].items():
            self.assertEqual(expected, hashlib.sha256((self.output / name).read_bytes()).hexdigest())

    def test_ui_keeps_existing_geometry_clip_and_material_composition(self):
        ui = (self.output / ('resource_pack/shaders/glsl/' + PREFIX + 'ui.vertex')).read_text(encoding='ascii')
        self.assertIn('entityPoint=vec4(-localPoint.x,-localPoint.z+1.5,-localPoint.y,1.0);', ui)
        self.assertIn('portalUniformPreviewDepth(vec3(-localPoint.x,-localPoint.z,-localPoint.y)', ui)
        self.assertIn('vec3 planeNormal=vec3(-NORMAL.x,-NORMAL.z,-NORMAL.y);', ui)
        self.assertIn('vec3 viewPoint=(WORLDVIEW*entityPoint).xyz;', ui)
        self.assertNotIn('vec3 viewRay=(WORLD*entityPoint).xyz;', ui)
        self.assertIn('else portalVisible=0.0;', ui)
        self.assertIn('varying highp vec2 parallaxUV;', ui)
        self.assertIn('parallaxUV.y+=TIME/256.0;', ui)
        materials = json.loads((self.output / 'resource_pack/materials/entity.material').read_bytes())['materials']
        self.assertEqual(4, len(materials) - 1)
        for name, material in materials.items():
            if name == 'version':
                continue
            self.assertEqual(('One', 'SourceAlpha', 'LessEqual'),
                             (material['blendSrc'], material['blendDst'], material['depthFunc']))
            self.assertEqual(['Blending', 'DisableCulling'], material['+states'])
            self.assertEqual(['DisableDepthWrite'], material['-states'])

    def test_install_creates_missing_contract_directory(self):
        target = Path(self.directory.name) / 'minimal_project'
        for relative in ('resource_pack/models/netease_models.json', 'resource_pack/materials/entity.material'):
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        self.assertFalse((target / 'tools').exists())
        install(self.output, target)
        self.assertEqual((self.output / 'contract.json').read_bytes(),
                         (target / 'tools/data/portal_native_candidate_r21.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
