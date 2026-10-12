"""Destination plant coordinates survive snow bands, chunking and native context packing."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import make_cell
from projection.geometry_palette import prepare_palette
from projection.model import Document
from projection.plant_position import POSITION_PLANT_PROXIES, render_origin
from projection.render_context import ContextBatchBuilder, ContextPaletteBuilder, prepare_context_palette

POPPY = ('minecraft:poppy', 0)


class PlantPositionTests(unittest.TestCase):
    def setUp(self):
        self.observed = []

        def profile(position):
            self.observed.append(position)
            return ('modern_projection:r11_position_%d_%d_%d' % position, .6875)

        self.profile = profile
        self.scope = patch.dict(POSITION_PLANT_PROXIES, {POPPY: profile}, clear=True)
        self.scope.start()
        self.addCleanup(self.scope.stop)

    def document(self):
        snow = registry.from_states('minecraft:snow_layer', {'height': 0, 'covered_bit': True})
        return Document((33, 2, 3), {(x, 1, 1): make_cell(snow, POPPY) if x % 2 else POPPY
                                    for x in (0, 1, 15, 16, 17, 32)})

    def test_flat_source_and_snow_overlay_use_original_destination_cell(self):
        document = self.document()
        original = deepcopy(document.to_data())
        source = document.palette_data()
        result = prepare_palette(source, render_origin=(-47, 117, -70))
        expected = {(-47 + x, 118, -69) for x in (0, 1, 15, 16, 17, 32)}
        proxies = {value[0] for value in result['common'] if value[0].startswith('modern_projection:r11_position_')}
        self.assertEqual({'modern_projection:r11_position_%d_%d_%d' % pos for pos in expected}, proxies)
        self.assertEqual(expected, set(self.observed))
        self.assertEqual(original, document.to_data())
        self.assertEqual(source['extra'], result['extra'])

    def test_context_builders_select_before_chunk_rebasing_and_neighbor_packing(self):
        document = self.document()
        origin = (257, 117, -513)
        expected = {(origin[0] + x, origin[1] + 1, origin[2] + 1) for x in (0, 1, 15, 16, 17, 32)}
        for builder_type in (ContextPaletteBuilder, ContextBatchBuilder):
            self.observed[:] = []
            builder = builder_type(document, document.palette_data(), render_origin=origin)
            for unused in builder.prepare():
                pass
            self.assertEqual(expected, set(self.observed))
            self.assertEqual(6, len(builder.cache))
        self.observed[:] = []
        prepare_context_palette(document.palette_data(), document.palette_data(), render_origin=origin)
        self.assertEqual(expected, set(self.observed))

    def test_uniform_chunk_caches_each_position_and_relocation_selects_new_destination(self):
        document = Document((16, 16, 16))
        document.blocks.fill_chunk((0, 0, 0), POPPY)
        for origin in ((0, 0, 0), (-16, 117, 65536)):
            self.observed[:] = []
            builder = ContextBatchBuilder(document, document.palette_data(), render_origin=origin)
            first = builder.material(0, 0, 0)
            neighbor = builder.material(1, 0, 0)
            self.assertIs(first, builder.material(0, 0, 0))
            self.assertNotEqual(first[0]['common'], neighbor[0]['common'])
            self.assertEqual([origin, (origin[0] + 1, origin[1], origin[2])], self.observed)

    def test_burial_uses_position_profile_alpha_top_and_origin_requires_integers(self):
        snow = registry.from_states('minecraft:snow_layer', {'height': 5, 'covered_bit': True})
        document = Document((1, 1, 1), {(0, 0, 0): make_cell(snow, POPPY)})
        rendered = prepare_palette(document.palette_data(), render_origin=(6, 149, 6))
        self.assertEqual({snow}, set(rendered['common']))
        self.assertEqual([(6, 149, 6)], self.observed)
        for value in (None, (0, 0), (True, 0, 0), (0., 0, 0), ('0', 0, 0)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_origin(value)

    def test_archived_foreground_and_snow_background_do_not_share_position_cache(self):
        legacy = ('minecraft:red_flower', 0)
        snow = registry.from_states('minecraft:snow_layer', {'height': 0, 'covered_bit': True})
        origin = (257, 117, -513)
        for value in (legacy, make_cell(snow, legacy)):
            document = Document((2, 1, 1), {(0, 0, 0): value, (1, 0, 0): value})
            before = deepcopy(document.to_data())
            for builder_type in (ContextPaletteBuilder, ContextBatchBuilder):
                self.observed[:] = []
                builder = builder_type(document, document.palette_data(), render_origin=origin)
                first, second = builder.material(0, 0, 0), builder.material(1, 0, 0)
                self.assertIsNot(first, second)
                self.assertIs(first, builder.material(0, 0, 0))
                self.assertEqual({origin, (258, 117, -513)}, set(self.observed))
            self.assertEqual(before, document.to_data())

    def test_archived_uniform_chunks_keep_per_cell_position(self):
        legacy = ('minecraft:red_flower', 0)
        snow = registry.from_states('minecraft:snow_layer', {'height': 0, 'covered_bit': True})
        for value in (legacy, make_cell(snow, legacy)):
            document = Document((16, 16, 16))
            document.blocks.fill_chunk((0, 0, 0), value)
            self.observed[:] = []
            builder = ContextBatchBuilder(document, document.palette_data(), render_origin=(-17, 149, 16))
            self.assertIsNot(builder.material(0, 0, 0), builder.material(1, 0, 0))
            self.assertEqual({(-17, 149, 16), (-16, 149, 16)}, set(self.observed))


if __name__ == '__main__':
    unittest.main()
