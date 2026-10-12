"""Frame item candidates preserve NBT and use target-only overlay transport."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry, static_frame_item_data
from projection.cell import make_cell
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.model import Document
from projection.render_context import prepare_context_palette, prepare_document_context, ContextBatchBuilder
from projection.render_layout import OVERLAY_BASE
from projection.static_frame_item import frame_item_proxy

spec = importlib.util.spec_from_file_location('flat_item_generator', ROOT / 'tools/generate_flat_item_proxies.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def tag(kind, value):
    return {'__type__': kind, '__value__': value}


def actor(rotation=0., item='minecraft:diamond_sword', user_data=None):
    value = {'Name': tag(8, item), 'Damage': tag(2, 0), 'Count': tag(1, 1)}
    if user_data is not None:
        value['tag'] = tag(10, user_data)
    return {'id': tag(8, 'ItemFrame'), 'Item': tag(10, value),
            'ItemRotation': tag(5, rotation), 'unknown': tag(3, 4711)}


def frame(facing=2):
    return block_registry.from_states('minecraft:frame', {'facing_direction': facing,
                                     'item_frame_map_bit': False, 'item_frame_photo_bit': False})


class StaticFrameItems(unittest.TestCase):
    def setUp(self):
        self.profiles = copy.deepcopy(static_frame_item_data.FRAME_ITEMS)
        self.profile = self.profiles[('minecraft:diamond_sword', 0)]
        self.profile['accepted'] = True

    def test_candidates_are_disabled_and_hidden_from_item_picker(self):
        self.assertFalse(static_frame_item_data.FRAME_ITEMS[('minecraft:diamond_sword', 0)]['accepted'])
        self.assertIsNone(frame_item_proxy(frame(), actor()))
        self.assertTrue(set(self.profile['proxies'].values()).issubset(INTERNAL_RENDER_BLOCKS))

    def test_all_facing_and_rotation_steps_have_separate_proxies(self):
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.profiles):
            for facing in range(6):
                for step in range(8):
                    source = actor(step * 45.)
                    saved = copy.deepcopy(source)
                    self.assertEqual((self.profile['proxies'][(facing, step)], 0), frame_item_proxy(frame(facing), source))
                    self.assertEqual(saved, source)

    def test_unknown_userdata_and_invalid_rotation_do_not_render_or_discard_content(self):
        cases = [actor(item='custom:unknown'), actor(user_data={'custom': tag(3, 1)}),
                 actor(user_data={'ench': tag(9, [tag(10, {})])}), actor(22.5), actor(float('inf'))]
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.profiles):
            for payload in cases:
                source = {'volume': (1, 1, 1), 'common': {frame(): [0]}, 'actor': {'minecraft:frame': {0: payload}}}
                saved = copy.deepcopy(source)
                self.assertIsNone(frame_item_proxy(frame(), payload))
                self.assertEqual((1, 1, 1), prepare_palette(source)['volume'])
                self.assertEqual(saved, source)

    def test_overlay_rebases_sparse_index_and_keeps_native_frame_body(self):
        doc = Document((5, 7, 3), {(4, 6, 2): make_cell(frame(), nbt=actor())})
        source, saved = doc.palette_data(), copy.deepcopy(doc.to_data())
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.profiles):
            result = prepare_palette(source)
            proxy = (self.profile['proxies'][(2, 0)], 0)
            self.assertEqual([104 + OVERLAY_BASE * 15], result['common'][proxy])
            self.assertEqual([104], result['common'][frame()])
            self.assertEqual((3, 5, OVERLAY_BASE + 7), result['volume'])
            self.assertEqual(saved, doc.to_data())
            for invalid in ({'volume': (1, 1, 1), 'common': {frame(): [2]},
                             'actor': {'minecraft:frame': {2: actor()}}},):
                with self.assertRaises(ValueError):
                    prepare_palette(invalid)

    def test_editor_overlay_band_uses_the_declared_offset(self):
        source = {'volume': (16, 16, 16), 'common': {frame(): [4095]}, 'actor': {'minecraft:frame': {4095: actor()}}}
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.profiles):
            result = prepare_palette(source, overlay_base=17)
            self.assertEqual((16, 16, 33), result['volume'])
            self.assertEqual([4095 + 17 * 256], result['common'][(self.profile['proxies'][(2, 0)], 0)])
            with self.assertRaises(ValueError):
                prepare_palette(source, overlay_base=16)

    def test_context_routes_only_target_item_and_keeps_neighbor_frame_body(self):
        doc = Document((2, 1, 1), {(0, 0, 0): make_cell(frame(), nbt=actor()),
                                  (1, 0, 0): make_cell(frame(), nbt=actor(45.))})
        targets = {'volume': (1, 2, 1), 'common': {frame(): [0]}}
        saved = copy.deepcopy(doc.to_data())
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.profiles):
            palettes = [prepare_context_palette(doc.palette_data(), targets), prepare_document_context(doc, targets)]
            batch = ContextBatchBuilder(doc, targets)
            for unused in batch.prepare():
                pass
            palettes.extend(row[2] for row in batch.data['_context_batches'])
            proxies = set(self.profile['proxies'].values())
            overlay_count = sum(len(indices) for data in palettes[2:] for value, indices in data['common'].items()
                                if value[0] in proxies)
            self.assertEqual(1, overlay_count)
            for data in palettes[:2]:
                items = {value[0]: indices for value, indices in data['common'].items() if value[0] in proxies}
                self.assertEqual({self.profile['proxies'][(2, 0)]}, set(items))
                self.assertEqual(2, len(data['common'][frame()]))
            self.assertEqual(saved, doc.to_data())


class BitmapResourceTests(unittest.TestCase):
    def test_new_registry_requires_new_versioned_item_and_pose_sources(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'tools/data/block_registry_manifest.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'game_version': 'NEMC next', 'source_sha256': 'a' * 64}), encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'Missing versioned flat item resources and frame pose'):
                generator.source_path(root)
        manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        current = json.loads(generator.source_path().read_text(encoding='utf8'))
        for field in ('schema', 'game_version', 'palette_sha256'):
            stale = copy.deepcopy(current)
            stale[field] = None
            with self.assertRaises(ValueError):
                generator.validate_source(stale, manifest)
        current['observation']['game_executable_version'] = 'old'
        with self.assertRaisesRegex(ValueError, 'different executable version'):
            generator.validate_source(current, manifest)

    def test_resolution_uses_definition_or_unique_observed_path(self):
        atlas = {'texture_data': {'tools': {'textures': ['textures/items/a', {'path': 'textures/items/b'}]}}}
        item = {'identifier': 'test:generic', 'texture_path': 'textures/items/b'}
        expected = {'texture_key': 'tools', 'texture_index': 1, 'texture_path': item['texture_path']}
        self.assertEqual(expected, generator.resolve_item(item, atlas))
        definition = {'minecraft:item': {'description': {'identifier': 'test:generic'},
                                         'components': {'minecraft:icon': {'texture': 'tools', 'index': 1}}}}
        self.assertEqual(expected, generator.resolve_item(item, atlas, definition))
        atlas['texture_data']['alias'] = {'textures': 'textures/items/b'}
        with self.assertRaises(ValueError):
            generator.resolve_item(item, atlas)

    def test_mesh_has_two_bitmap_faces_and_only_exposed_pixel_edges(self):
        image = Image.new('RGBA', (2, 2))
        image.putpixel((0, 0), (255, 0, 0, 255))
        image.putpixel((1, 0), (0, 255, 0, 255))
        cubes = generator.silhouette_cubes(image, {'size_pixels': 8., 'thickness_pixels': .5, 'front_z_pixels': 1.})
        self.assertEqual({'north', 'south'}, set(cubes[0]['uv']))
        self.assertEqual(6, sum(len(cube['uv']) for cube in cubes[1:]))
        self.assertEqual([8., 8., .5], cubes[0]['size'])
        image.putpixel((0, 1), (255, 0, 0, 127))
        with self.assertRaises(ValueError):
            generator.silhouette_cubes(image, {'size_pixels': 8., 'thickness_pixels': .5, 'front_z_pixels': 1.})


if __name__ == '__main__':
    unittest.main()
