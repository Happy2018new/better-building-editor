"""Native ownership must not change saved layers, targets, or neighbor bodies."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import AIR, make_cell
from projection.geometry_palette import prepare_palette
from projection.liquid_render_ownership import identity, owned_names
from projection.model import Document
from projection.render_context import (ContextBatchBuilder, TARGETS_PER_UNIT,
                                       prepare_context_batches)
from projection.render_layout import local_context_position
from projection.session import Session
from test_tiles import Bridge

WATER = ('minecraft:water', 0)
FLOWING = ('minecraft:flowing_water', 3)
LAVA = ('minecraft:lava', 0)
FENCE = ('minecraft:oak_fence', 0)
STONE = ('minecraft:stone', 0)


def water_profile():
    return SimpleNamespace(supported_names=frozenset((WATER[0], FLOWING[0])))


class LiquidOwnershipTests(unittest.TestCase):
    def test_both_layers_are_filtered_without_changing_source_targets_or_actors(self):
        document = Document((5, 1, 1), {
            (0, 0, 0): WATER,
            (1, 0, 0): make_cell(FENCE, FLOWING, nbt={'future': 7}),
            (2, 0, 0): make_cell(WATER, STONE),
            (3, 0, 0): make_cell(AIR, WATER),
            (4, 0, 0): LAVA,
        })
        source = document.palette_data()
        before = deepcopy((document.to_data(), source))
        rendered = prepare_palette(source, liquid_profile=water_profile())
        for layer, state_key in (('common', 'states'), ('extra', 'extraStates')):
            self.assertFalse(any(m[0] in owned_names(water_profile()) for m in rendered[layer]))
            self.assertFalse(any(m[0] in owned_names(water_profile()) for m in rendered[state_key]))
        self.assertEqual([1], rendered['common'][FENCE])
        self.assertEqual([2], rendered['common'][STONE])
        self.assertEqual([4], rendered['common'][LAVA])
        self.assertEqual(source['actor'], rendered['actor'])
        self.assertEqual(before, (document.to_data(), source))
        self.assertEqual(identity(water_profile()), rendered['_liquid_render_profile'])

    def test_native_fallback_and_unowned_lava_remain_available(self):
        source = Document((2, 1, 1), {(0, 0, 0): WATER, (1, 0, 0): LAVA}).palette_data()
        for profile in (None, SimpleNamespace(supported_names={'custom:water'})):
            rendered = prepare_palette(source, liquid_profile=profile)
            self.assertEqual(source['common'], rendered['common'])
            self.assertNotIn('_liquid_render_profile', rendered)
        rendered = prepare_palette(source, liquid_profile=water_profile())
        self.assertEqual({LAVA: [1]}, rendered['common'])

    def test_missing_context_keeps_hidden_cross_chunk_fence_without_native_water(self):
        first, second = (15, 1, 1), (16, 1, 1)
        document = Document((32, 3, 3), {
            first: make_cell(FENCE, WATER), second: make_cell(FENCE, FLOWING),
        })
        targets = document.palette_data(lambda pos: pos == first)
        before = deepcopy((document.to_data(), targets))
        result = prepare_context_batches(document, targets, liquid_profile=water_profile())
        origin, context, palette = result['_context_batches'][0]
        self.assertEqual((0, 0, 0), origin)
        self.assertTrue(context)
        expected = set()
        for neighbor in ((0, 0, 0), (1, 0, 0)):
            x, y, z = local_context_position(first, neighbor)
            expected.add((y * 64 + x) * 64 + z)
        self.assertEqual(expected, set(palette['common'][FENCE]))
        self.assertEqual({}, palette['extra'])
        self.assertEqual(identity(water_profile()), palette['_liquid_render_profile'])
        self.assertEqual(before, (document.to_data(), targets))

    def test_custom_only_context_yields_and_does_not_emit_neighbor_geometry(self):
        count = 64
        document = Document((count, 2, 1), {
            **{(x, 0, 0): WATER for x in range(count)}, (0, 1, 0): STONE,
        })
        targets = document.palette_data(lambda pos: pos[1] == 0)
        builder = ContextBatchBuilder(document, targets, liquid_profile=water_profile())
        steps = list(builder.prepare())
        self.assertGreaterEqual(len(steps), count // TARGETS_PER_UNIT + 2)
        self.assertEqual([], builder.data['_context_batches'])
        self.assertEqual(count, sum(len(p) for p in targets['common'].values()))

    def test_profile_changes_invalidate_meshes_and_reuse_matching_ownership(self):
        bridge = Bridge()
        session = Session(bridge)
        session.liquid_profile = None
        session._loaded(Document((2, 1, 1), {(0, 0, 0): WATER}))
        bridge.settle(session)
        before = len(bridge.builds)
        session.liquid_profile = water_profile()
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(before + 1, len(bridge.builds))
        session.liquid_profile = water_profile()
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(before + 1, len(bridge.builds))
        session.liquid_profile = None
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(before + 1, len(bridge.builds))
        self.assertEqual((), session.tiles.parts[(0, 0, 0)]['data'][-1])

    def test_custom_only_editor_does_not_report_empty_when_native_mesh_is_absent(self):
        bridge = Bridge()
        bridge.geometry = lambda *args, **kwargs: None
        session = Session(bridge)
        session.liquid_profile = water_profile()
        session._loaded(Document((2, 1, 1), {(0, 0, 0): WATER}))
        bridge.settle(session)
        self.assertIsNone(session.model_name)
        self.assertFalse(session.preview_pending)
        self.assertTrue(session.preview_has_content())
        session.editor.hidden_layers = {0}
        session.refresh_preview()
        bridge.settle(session)
        self.assertFalse(session.preview_has_content())


if __name__ == '__main__':
    unittest.main()
