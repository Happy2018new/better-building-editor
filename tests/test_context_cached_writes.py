"""Repeated material writes keep output batches and rebased actors independent."""
import copy
import unittest
from unittest.mock import patch

import test_render_context
from projection.cell import make_cell
from projection.debug_blueprints import material
from projection.model import Document
from projection import render_context
from projection.render_context import ContextPaletteBuilder, prepare_context_batches
from projection.storage import integer_types
from projection.render_layout import local_context_position
from projection.visible_actor import compose_actor


def index(position):
    return (position[1] * 64 + position[0]) * 64 + position[2]


class CachedContextWritesTests(unittest.TestCase):
    def test_cached_barrel_actor_is_rebased_and_copied_for_each_target(self):
        barrel = material('barrel')
        first, second = (5, 2, 3), (6, 2, 3)
        actor = {'x': 6, 'y': 2, 'z': 3, 'opaque': {'x': 99, 'payload': [1, 2]}}
        document = Document((8, 4, 5), {first: barrel, second: make_cell(
            barrel, nbt=compose_actor(actor, {'id': {'__type__': 8, '__value__': 'Barrel'}}))})
        saved = copy.deepcopy(document.to_data())
        data = prepare_context_batches(document, document.palette_data())
        palette = data['_context_batches'][0][2]
        actors = []
        for target in (first, second):
            delta = tuple(second[axis] - target[axis] for axis in range(3))
            encoded = local_context_position(target, delta)
            payload = palette['actor'][barrel[0]][index(encoded)]
            self.assertEqual(encoded, tuple(payload[axis] for axis in ('x', 'y', 'z')))
            actors.append(payload)
        actors[0]['opaque']['payload'][0] = 0
        self.assertEqual([1, 2], actors[1]['opaque']['payload'])
        self.assertEqual(saved, document.to_data())

    def test_reused_material_buckets_do_not_alias_other_chunks_or_later_jobs(self):
        stone = material('stone')
        document = Document((32, 4, 4), {(15, 1, 1): stone, (16, 1, 1): stone})
        data = prepare_context_batches(document, document.palette_data())
        first, second = [row[2]['common'][stone] for row in data['_context_batches']]
        other = list(second)
        first.append(12345)
        self.assertEqual(other, second)
        fresh = prepare_context_batches(document, document.palette_data())
        self.assertNotIn(12345, fresh['_context_batches'][0][2]['common'][stone])

    def test_uniform_chest_chunk_still_resolves_each_logical_position(self):
        chest = material('chest', {'minecraft:cardinal_direction': 'north'})
        document = Document((16, 16, 16))
        document.blocks.fill_chunk((0, 0, 0), chest)
        self.assertIsInstance(document.blocks.chunks[(0, 0, 0)], integer_types)
        builder = ContextPaletteBuilder(document, document.palette_data())
        with patch.object(render_context, 'document_chest_part',
                          wraps=render_context.document_chest_part) as pairing:
            for unused in range(10):
                builder.material(1, 1, 1)
                builder.material(2, 1, 1)
            self.assertEqual([(1, 1, 1), (2, 1, 1)],
                             [call.args[1] for call in pairing.call_args_list])

    def test_sparse_air_slot_is_cached_without_becoming_a_render_cell(self):
        document = Document((16, 16, 16), {(1, 1, 1): material('stone')})
        builder = ContextPaletteBuilder(document, document.palette_data())
        for unused in range(10):
            self.assertIsNone(builder.material(2, 1, 1))
        self.assertEqual(1, len(builder.chunk_cache))
        result = prepare_context_batches(document, document.palette_data())
        self.assertEqual(1, sum(len(rows) for rows in result['_context_batches'][0][2]['common'].values()))


if __name__ == '__main__':
    unittest.main()
