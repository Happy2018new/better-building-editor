"""Offline cache lifetime checks, optionally against another review worktree."""
import gc
import os
import sys
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get('CONTEXT_REVIEW_ROOT', str(ROOT)))
sys.path.insert(0, str(SOURCE_ROOT / 'behavior_pack/modern_projection'))

from projection import render_context as context
from projection.cell import AIR
from projection.debug_blueprints import material
from projection.entity_render import CHEST_PROXIES
from projection.model import Document


def builder(document):
    sx, sy, sz = document.size
    return context.ContextPaletteBuilder(document, {'volume': (sz, sx, sy)})


HAS_RENDER_CACHE = hasattr(context, '_NOT_RENDERED')


class ContextCacheLifetimeTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(context, '_ContextWriter'), 'Legacy context writer')
    def test_writer_keeps_identity_owner_alive_until_its_cache_is_released(self):
        class Rendered(object):
            def __init__(self, value):
                self.cell = {'common': value}

            def __getitem__(self, index):
                return (self.cell,)[index]

        stone, glass = material('stone'), material('glass')
        palette = {'common': {}, 'extra': {}, 'actor': {}}
        writer = context._ContextWriter(palette)
        rendered = Rendered(stone)
        reference = weakref.ref(rendered)
        writer.put(rendered, 10, (0, 0, 0))
        del rendered
        gc.collect()
        self.assertIsNotNone(reference())
        for index in range(20, 40):
            writer.put(Rendered(glass), index, (0, 0, 0))
        self.assertEqual([10], palette['common'][stone])
        self.assertEqual(list(range(20, 40)), palette['common'][glass])
        del writer
        gc.collect()
        self.assertIsNone(reference())

    @unittest.skipUnless(HAS_RENDER_CACHE, 'Legacy chunk decode cache')
    def test_uniform_chest_resolves_each_positions_pair_role_once(self):
        chest = material('chest', {'minecraft:cardinal_direction': 'north'})
        document = Document((16, 16, 16))
        document.blocks.fill_chunk((0, 0, 0), chest)
        prepared = builder(document)
        roles = {(0, 0, 0): 'main', (1, 0, 0): 'sub', (2, 0, 0): None}
        calls = []

        def pair_role(source, position, value):
            self.assertIs(document, source)
            self.assertEqual(chest, value)
            calls.append(position)
            return roles[position]

        with patch.object(context, 'document_chest_part', side_effect=pair_role):
            for position, part in roles.items():
                first = prepared.material(*position)
                self.assertIs(first, prepared.material(*position))
                expected = (CHEST_PROXIES[chest[0]][('north', part or 'single')], 0)
                self.assertEqual(expected, first[0]['common'])
        self.assertEqual(list(roles), calls)

    @unittest.skipUnless(HAS_RENDER_CACHE, 'Legacy chunk decode cache')
    def test_uniform_mixed_and_empty_chunks_use_bounded_render_slots(self):
        document = Document((48, 16, 16))
        document.blocks.fill_chunk((0, 0, 0), material('stone'))
        document.set_cell((16, 0, 0), material('glass'))
        prepared = builder(document)
        prepared.material(0, 0, 0)
        prepared.material(16, 0, 0)
        self.assertIsNone(prepared.material(32, 0, 0))
        self.assertEqual(1, len(prepared.chunk_cache[(0, 0, 0)][1]))
        self.assertEqual(4096, len(prepared.chunk_cache[(1, 0, 0)][1]))
        self.assertIsNone(prepared.chunk_cache[(2, 0, 0)][1])

    @unittest.skipUnless(HAS_RENDER_CACHE, 'Legacy chunk decode cache')
    def test_eviction_caps_render_slots_and_reloading_preserves_material(self):
        document = Document((64, 128, 64))
        stone = material('stone')
        positions = [(x * 16, y * 16, z * 16)
                     for y in range(8) for x in range(4) for z in range(4)][:33]
        for position in positions:
            document.set_cell(position, stone)
        prepared = builder(document)
        first = prepared.material(*positions[0])
        for position in positions[1:]:
            self.assertIs(first, prepared.material(*position))
            self.assertLessEqual(len(prepared.chunk_cache), context.MAX_CONTEXT_CHUNK_CACHE)
        self.assertNotIn((0, 0, 0), prepared.chunk_cache)
        self.assertIs(first, prepared.material(*positions[0]))
        slot_count = sum(len(entry[1]) for entry in prepared.chunk_cache.values()
                         if entry[1] is not None)
        self.assertEqual(context.MAX_CONTEXT_CHUNK_CACHE * 4096, slot_count)

    def test_source_branch_edits_do_not_change_cached_or_unread_snapshot_chests(self):
        chest = material('chest', {'minecraft:cardinal_direction': 'north'})
        first, second = (15, 1, 1), (16, 1, 1)
        source = Document((32, 16, 16), {first: chest, second: chest})
        snapshot = Document(source.size)
        snapshot.blocks = source.blocks.copy()
        prepared = builder(snapshot)
        main = prepared.material(*first)
        source.set_cell(second, AIR)
        sub = prepared.material(*second)
        expected_main = (CHEST_PROXIES[chest[0]][('north', 'main')], 0)
        expected_sub = (CHEST_PROXIES[chest[0]][('north', 'sub')], 0)
        self.assertEqual(expected_main, main[0]['common'])
        self.assertEqual(expected_sub, sub[0]['common'])
        self.assertIs(main, prepared.material(*first))
        fresh = builder(source).material(*first)
        self.assertEqual((CHEST_PROXIES[chest[0]][('north', 'single')], 0), fresh[0]['common'])
        self.assertEqual(chest, snapshot.get(second))

    def test_air_neighbors_never_enter_material_preparation_or_output(self):
        document = Document((32, 16, 16), {(0, 0, 0): material('stone')})
        prepared = builder(document)
        saved = document.to_data()
        with patch.object(context, 'prepare_palette', wraps=context.prepare_palette) as prepare:
            for position in ((1, 0, 0), (1, 0, 0), (16, 0, 0), (16, 0, 0)):
                self.assertIsNone(prepared.material(*position))
            self.assertEqual(0, prepare.call_count)
        self.assertEqual({}, prepared.cache)
        self.assertEqual(saved, document.to_data())


if __name__ == '__main__':
    unittest.main()
