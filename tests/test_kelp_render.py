# -*- coding: utf-8 -*-
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SOURCE, 'behavior_pack', 'modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, make_cell, foreground, background
from projection.geometry_palette import prepare_palette, INTERNAL_RENDER_BLOCKS
from projection.kelp_render import PROXIES, document_part, palette_parts, complete_source_parts
from projection.large_preview import SurfacePalette, build_preview
from projection.model import Document
from projection.render_context import ContextPaletteBuilder, ContextBatchBuilder
from projection.session import Session


class PreviewBridge(object):
    def __init__(self):
        self.queue, self.builds, self.rendered = [], [], {}

    def later(self, delay, callback):
        self.queue.append(callback)

    def geometry(self, palette, name=None, render_origin=(0, 0, 0)):
        source = palette.palette_data()
        parts = palette_parts(source, palette.source_document, palette.source_origin)
        self.builds.append((name, parts))
        self.rendered[name] = prepare_palette(source, kelp_parts=parts)
        return name

    def settle(self, session):
        for unused in range(10000):
            for part in session.tiles.parts.values():
                part['pending'] = False
            if not self.queue:
                return
            self.queue.pop(0)()
        raise AssertionError('preview did not settle')


def kelp(age=0):
    return registry.from_states('minecraft:kelp', {'kelp_age': age})


def builder(document, targets=None, visible_layer=None, kind=ContextPaletteBuilder):
    return kind(document, document.palette_data() if targets is None else targets,
                visible_layer=visible_layer)


class KelpCandidateTests(unittest.TestCase):
    def test_all_ages_same_and_different_ignore_age(self):
        for age in range(26):
            for upper in (age, (age + 13) % 26):
                document = Document((1, 3, 1), {(0, 0, 0): kelp(age), (0, 1, 0): kelp(upper)})
                self.assertEqual('stem', document_part(document, (0, 0, 0)))
                self.assertEqual('top', document_part(document, (0, 1, 0)))
                self.assertIsNone(document_part(document, (0, 2, 0)))

    def test_nonkelp_and_document_boundary_end_the_stem(self):
        for upper in (AIR, ('minecraft:stone', 0)):
            document = Document((1, 2, 1), {(0, 0, 0): kelp(), (0, 1, 0): upper})
            self.assertEqual('top', document_part(document, (0, 0, 0)))
        document = Document((1, 1, 1), {(0, 0, 0): kelp()})
        self.assertEqual('top', document_part(document, (0, 0, 0)))

    def test_asymmetric_native_indices_local_origin_and_cross_16(self):
        document = Document((8, 18, 7), {(4, 15, 3): kelp(25), (4, 16, 3): kelp(25),
                                              (5, 15, 4): kelp(3)})
        output = None
        for step in build_preview(document, region=((3, 15, 2), (7, 16, 6)), local=True):
            if step is not None:
                output, origin, unused = step
        self.assertEqual((3, 15, 2), origin)
        self.assertIs(document, output.source_document)
        self.assertEqual(origin, output.source_origin)
        self.assertEqual({5: 'stem', 10: 'top'}, palette_parts(output.palette_data(), document, origin))
        self.assertNotIn('source_document', output.palette_data())
        prepared = builder(document)
        self.assertEqual((PROXIES['stem'], 0), prepared.material(4, 15, 3)[0]['common'])
        self.assertEqual((PROXIES['top'], 0), prepared.material(4, 16, 3)[0]['common'])

    def test_missing_targets_and_hidden_upper_keep_complete_source_part(self):
        document = Document((1, 2, 1), {(0, 0, 0): kelp(), (0, 1, 0): kelp()})
        targets = document.palette_data(lambda pos: pos[1] == 0)
        for kind in (ContextPaletteBuilder, ContextBatchBuilder):
            for visible in (None, lambda y: y == 0):
                prepared = builder(document, targets, visible, kind)
                self.assertEqual((PROXIES['stem'], 0), prepared.material(0, 0, 0)[0]['common'])
                for unused in prepared.prepare():
                    pass
                self.assertTrue(prepared.data)
        self.assertEqual({0: 'stem'}, palette_parts(targets, document))

    def test_uniform_chunk_roles_have_separate_cache_and_per_cell_slots(self):
        document = Document((16, 16, 16))
        document.blocks.fill_chunk((0, 0, 0), kelp())
        prepared = builder(document)
        stem = prepared.material(3, 14, 7)
        tip = prepared.material(3, 15, 7)
        self.assertEqual((PROXIES['stem'], 0), stem[0]['common'])
        self.assertEqual((PROXIES['top'], 0), tip[0]['common'])
        self.assertIs(stem, prepared.material(4, 14, 8))
        self.assertIs(tip, prepared.material(4, 15, 8))
        self.assertEqual(4096, len(prepared.chunk_cache[(0, 0, 0)][1]))
        self.assertEqual(2, len(prepared.cache))

    def test_stone_keeps_uniform_cache(self):
        document = Document((16, 16, 16))
        document.blocks.fill_chunk((0, 0, 0), ('minecraft:stone', 0))
        prepared = builder(document)
        first = prepared.material(0, 0, 0)
        self.assertIs(first, prepared.material(15, 15, 15))
        self.assertEqual(1, len(prepared.chunk_cache[(0, 0, 0)][1]))
        self.assertEqual(1, len(prepared.cache))

    def test_front_back_water_and_standalone_extra(self):
        water, plant = ('minecraft:water', 0), kelp(8)
        for lower in (plant, make_cell(plant, water), make_cell(water, plant), make_cell(AIR, plant)):
            document = Document((1, 2, 1), {(0, 0, 0): lower, (0, 1, 0): make_cell(water, plant)})
            source = document.palette_data()
            rendered = prepare_palette(source, kelp_parts=palette_parts(source, document))
            values = set(rendered['common']) | set(rendered['extra'])
            self.assertNotIn(plant, values)
            self.assertIn((PROXIES['stem'], 0), values)
            self.assertIn((PROXIES['top'], 0), values)

    def test_source_snapshot_and_typed_nbt_remain_native(self):
        actor = {b'id': b'Kelp', 'typed': {'__type__': 1, '__value__': 7},
                 'tuple': (1, True, b'abc'), 'list': [False, 1.25, None]}
        document = Document((1, 2, 1), {(0, 0, 0): make_cell(kelp(17), ('minecraft:water', 0), actor),
                                              (0, 1, 0): kelp(24)})
        before = copy.deepcopy(document.to_data())
        source = copy.deepcopy(document.palette_data())
        frozen = Document(document.size)
        frozen.blocks = document.blocks.copy()
        old = builder(frozen)
        document.set_cell((0, 1, 0), AIR)
        self.assertEqual((PROXIES['stem'], 0), old.material(0, 0, 0)[0]['common'])
        self.assertEqual((PROXIES['top'], 0), builder(document).material(0, 0, 0)[0]['common'])
        prepare_palette(source, kelp_parts=palette_parts(source, frozen))
        self.assertEqual(before, frozen.to_data())
        self.assertEqual(source, frozen.palette_data())
        self.assertEqual(foreground(document.get((0, 0, 0))), kelp(17))
        self.assertEqual(background(document.get((0, 0, 0))), ('minecraft:water', 0))

    def test_complete_source_reference_and_document_agree(self):
        document = Document((3, 18, 5), {(2, 15, 4): kelp(25), (2, 16, 4): kelp(25),
                                               (1, 2, 3): make_cell(('minecraft:water', 0), kelp(7))})
        source = document.palette_data()
        self.assertEqual(palette_parts(source, document), complete_source_parts(source))

    def test_mesh_identity_changes_when_only_source_upper_neighbor_changes(self):
        bridge = PreviewBridge()
        session = Session(bridge)
        session._loaded(Document((1, 2, 1), {(0, 0, 0): kelp()}))
        bridge.settle(session)
        palette = SurfacePalette((1, 1, 1))
        palette.add((0, 0, 0), kelp())
        palette.source_document = session.editor.document
        for upper, expected in ((AIR, 'top'), (kelp(), 'stem'), (AIR, 'top')):
            session.editor.document.set_cell((0, 1, 0), upper)
            session.tiles.submit((0, 0, 0), palette, (0, 0, 0))
            part = session.tiles.parts[(0, 0, 0)]
            self.assertEqual(((0, expected),), part['data'][-1])
            self.assertEqual({(PROXIES[expected], 0): [0]}, bridge.rendered[part['name']]['common'])
        self.assertEqual(3, len(bridge.builds))

    def test_point_edit_cross_chunk_refresh_and_undo_redo_keep_source_roles(self):
        bridge = PreviewBridge()
        session = Session(bridge)
        session._loaded(Document((3, 18, 3), {(1, 15, 1): kelp()}))
        bridge.settle(session)

        def roles():
            self.assertFalse(session.preview_error)
            return set(value for key in session.tiles.region_owners
                       for value in bridge.rendered.get(session.tiles.parts[key]['name'], {}).get('common', {})
                       if value[0] in PROXIES.values())

        self.assertEqual({(PROXIES['top'], 0)}, roles())
        session.editor._commit('add upper kelp', {(1, 16, 1): kelp()}, whole=True)
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual({(PROXIES['stem'], 0), (PROXIES['top'], 0)}, roles())
        session.action(session.editor.undo)
        bridge.settle(session)
        self.assertEqual({(PROXIES['top'], 0)}, roles())
        session.action(session.editor.redo)
        bridge.settle(session)
        self.assertEqual({(PROXIES['stem'], 0), (PROXIES['top'], 0)}, roles())

    def test_missing_complete_source_is_explicit_and_generic_nonkelp_is_compatible(self):
        self.assertEqual({}, palette_parts({'volume': (1, 1, 1), 'common': {('minecraft:stone', 0): [0]}}, None))
        source = {'volume': (1, 1, 1), 'common': {kelp(): [0]}}
        self.assertRaises(ValueError, palette_parts, source, None)
        self.assertEqual(source['common'], prepare_palette(source)['common'])
        self.assertRaises(ValueError, prepare_palette, source, kelp_parts={})

    def test_resources_native_atlas_double_sided_and_hidden(self):
        for part, tile in (('stem', 'kelp_a'), ('top', 'kelp_top')):
            name = 'ordinary_kelp_' + part
            self.assertIn(PROXIES[part], INTERNAL_RENDER_BLOCKS)
            with open(os.path.join(SOURCE, 'behavior_pack', 'netease_blocks', name + '.json')) as stream:
                behavior = json.load(stream)['minecraft:block']
            self.assertFalse(behavior['description']['register_to_creative_menu'])
            with open(os.path.join(SOURCE, 'resource_pack', 'models', 'netease_block', name + '.json')) as stream:
                model = json.load(stream)['netease:block_geometry']
            self.assertEqual([tile], model['description']['textures'])
            self.assertFalse(model['description']['use_ao'])
            self.assertEqual(2, len(model['bones']))
            for bone in model['bones']:
                for cube in bone['cubes']:
                    self.assertEqual(set(('north', 'south')), set(cube['uv']))
                    self.assertEqual([16, 16], cube['uv']['north']['uv_size'])
                    self.assertEqual([-16, 16], cube['uv']['south']['uv_size'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
