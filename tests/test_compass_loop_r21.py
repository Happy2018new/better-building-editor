"""Opaque compass aliases keep intrinsic glint and reject unmeasured variants."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))

import generate_item_icon_catalog as generator
from projection.intrinsic_item_glint import item_glint
from projection.item_sprite_plan import sprite_item, _contents
from projection.item_sprite_profile import candidate_profile, production_profile
from projection.visible_item_contents import ContentSlot

ENGINE = '3.10.0.420447'


class OpaqueMetadata:
    def __iter__(self):
        raise AssertionError('Indicator metadata must remain opaque')

    def __getitem__(self, key):
        raise AssertionError('Indicator targets must not be read')

    def get(self, key, default=None):
        raise AssertionError('Indicator targets must not be read')


class CompassLoopTests(unittest.TestCase):
    def test_real_candidate_alias_keeps_item_glint_and_never_reads_tracking_data(self):
        profile = candidate_profile(ENGINE)
        canonical = ('minecraft:compass', 0)
        for name in sorted(generator.COMPASS_NAMES):
            for aux in range(16):
                item = {'newItemName': name, 'newAuxValue': aux, 'isEnchanted': False,
                        'userData': OpaqueMetadata()}
                original = dict(item)
                self.assertEqual(canonical, sprite_item(item, profile.items))
                self.assertEqual(name == 'minecraft:lodestone_compass', item_glint(item))
                self.assertEqual(original, item)
            for aux in (16, 65535):
                item['newAuxValue'] = aux
                self.assertIsNone(sprite_item(item, profile.items))
        self.assertIsNone(profile.items.get(('minecraft:clock', 0)))
        self.assertIsNone(profile.items.get(('minecraft:recovery_compass', 0)))
        self.assertIsNone(production_profile(ENGINE))

    def test_alias_in_visible_slots_uses_original_intrinsic_glint_after_resource_resolution(self):
        profile = candidate_profile(ENGINE)
        for family in ('shelf', 'campfire'):
            for name in sorted(generator.COMPASS_NAMES):
                item = {'newItemName': name, 'newAuxValue': 0, 'isEnchanted': False,
                        'userData': OpaqueMetadata()}
                slot = ContentSlot(family, 0, item, 'south')
                with patch('projection.visible_item_contents.content_slots', return_value=(slot,)):
                    contents = _contents(('minecraft:oak_shelf', 0), None, profile)
                self.assertEqual(('minecraft:compass', 0), contents[0][0])
                self.assertEqual(name == 'minecraft:lodestone_compass', contents[0][3])

    def test_one_thickness_mesh_rejects_changing_alpha_or_nonbinary_native_frames(self):
        image = Image.new('RGBA', (2, 64), (50, 70, 90, 255))
        self.assertEqual((2, 2), generator.compass_reference(image).size)
        for alpha in (0, 127):
            changed = image.copy()
            changed.putpixel((0, 63), (50, 70, 90, alpha))
            with self.assertRaisesRegex(ValueError, 'binary alpha'):
                generator.compass_reference(changed)
        with self.assertRaisesRegex(ValueError, '32-frame'):
            generator.compass_reference(Image.new('RGBA', (2, 62)))
        with self.assertRaisesRegex(ValueError, 'visible silhouette'):
            generator.compass_reference(Image.new('RGBA', (2, 64)))

    def test_generated_loop_owns_atlas_material_and_rejects_stale_animation_or_dangling_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            install = Path(directory)
            pack = install / 'data/resource_packs/vanilla'
            atlas = pack / 'textures/items/compass_atlas.png'
            atlas.parent.mkdir(parents=True)
            Image.new('RGBA', (2, 64), (50, 70, 90, 255)).save(atlas)
            glint = pack / (generator.GLINT_TEXTURE + '.png')
            glint.parent.mkdir(parents=True)
            glint.write_bytes(b'explicit synthetic glint fixture')
            catalog = {'schema': 1, 'engine_version': ENGINE, 'pose': generator.POSE,
                       'lighting': generator.LIGHTING,
                       'glint': dict(generator.GLINT, source_pack='vanilla',
                                     texture_path=generator.GLINT_TEXTURE,
                                     texture_sha256=generator.sha(glint.read_bytes())),
                       'resources': {'loop_fixture': {'source_pack': 'vanilla',
                           'texture_path': 'textures/items/compass_atlas',
                           'sha256': generator.sha(atlas.read_bytes()),
                           'animation': dict(generator.COMPASS_LOOP)}},
                       'items': [{'name': name, 'aux': 0, 'resource': 'loop_fixture',
                                  'max_durability': 0, 'resource_alias': ['minecraft:compass', 0]}
                                 for name in sorted(generator.COMPASS_NAMES)], 'unsupported': {}}
            output = generator.outputs(catalog, install)
            registration = json.loads(output['tools/data/item_icon_registrations_nemc_' + ENGINE + '.json'])
            for suffix in ('', '_world'):
                row = registration['models']['modern_projection_item_icon_loop_fixture' + suffix]
                self.assertEqual('modern_projection_item_compass_loop' + suffix, row['material'])
                material = registration['materials'][row['material'] + ':entity_for_skeleton_alpha']
                self.assertEqual('shaders/glsl/modern_projection_item_icon' + suffix + '.vertex',
                                 material['vertexShader'])
            self.assertEqual(atlas.read_bytes(), output[
                'resource_pack/textures/models/modern_projection/item_icons/loop_fixture.png'])
            stale = copy.deepcopy(catalog)
            stale['resources']['loop_fixture']['animation']['metadata_policy'] = 'tracking'
            with self.assertRaisesRegex(ValueError, 'opaque loop contract'):
                generator.outputs(stale, install)
            stale = copy.deepcopy(catalog)
            stale['items'] = [row for row in stale['items'] if row['name'] == 'minecraft:lodestone_compass']
            with self.assertRaisesRegex(ValueError, 'canonical profile'):
                generator.outputs(stale, install)


if __name__ == '__main__':
    unittest.main()
