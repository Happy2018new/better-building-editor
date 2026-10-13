"""Independent public-fixture checks through real product editor/world owners."""
import copy
from fractions import Fraction
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import liquid_product_deployment as deployment
from projection.cell import make_cell
from projection.debug_blueprints import material
from projection.debug_product_water_blueprints import CASES, FOCUS, source_document
from projection.liquid_preview import LiquidPreview
from projection.liquid_projection import LiquidProjection
from tests.test_liquid_render import Runtime


def session(document):
    return SimpleNamespace(editor=SimpleNamespace(document=document, revision=0, layer=FOCUS[1]),
        preview_hidden=lambda: (), solo_layer=False, emit=lambda unused: None, opacity=1.)


def finish(owner):
    for unused in range(1000):
        if owner.advance():
            return
        if owner.error is not None:
            raise owner.error
    raise AssertionError('Finite water owner did not complete')


def records(groups):
    """Decode the public payload bit contract independently of its encoder."""
    result = []
    for group in groups:
        packed = group.uniforms[1] + group.uniforms[2]
        for slot, raw in enumerate(group.uniforms[0]):
            code = int(raw)
            faces = code >> 6 & 63
            if not faces:
                continue
            address = code & 63
            relative = address & 3, address >> 4 & 3, address >> 2 & 3
            pos = tuple(group.origin[axis] + relative[axis] for axis in range(3))
            first, second = int(packed[slot * 2]), int(packed[slot * 2 + 1])
            heights = first & 255, first >> 8, second & 255, second >> 8
            result.append((pos, faces, heights, code >> 12 & 255))
    return sorted(result)


def focus_records(groups):
    return [row[1:] for row in records(groups) if row[0] == FOCUS]


def world_groups(owner):
    return [record['group'] for record in owner.renderer.active.values()]


def only_layer_targets(document, layer):
    selected = document.palette_data(lambda pos: pos == FOCUS)
    selected['extra' if layer == 0 else 'common'] = {}
    return selected


class ProductWaterOwnerContracts(unittest.TestCase):
    def owners(self, document):
        adapter = deployment.candidate_profile()
        selected_session = session(document)
        preview = LiquidPreview(selected_session, adapter.provider_factory, adapter.models, adapter.max_groups)
        runtime = Runtime()
        runtime.session = selected_session
        world = LiquidProjection(runtime, document, (10, 64, 20), adapter, 0)
        world.renderer.SETTLE_SECONDS = 0.
        world.request()
        finish(preview)
        finish(world)
        world.publish()
        self.addCleanup(preview.close)
        self.addCleanup(world.close)
        return selected_session, preview, world, runtime

    def occupancy(self, owner, positions):
        mask = bytearray(owner.document.volume)
        sx, unused_sy, sz = owner.document.size
        for x, y, z in positions:
            mask[(y * sx + x) * sz + z] = 2
        return mask

    def test_missing_neighbors_change_draws_only_in_all_public_water_cases(self):
        for row in CASES:
            with self.subTest(case=row['id']):
                document = source_document(row['id'])
                before = copy.deepcopy(document.to_data())
                unused_session, preview, world, runtime = self.owners(document)
                expected = focus_records(world_groups(world))
                self.assertTrue(expected)
                omitted = [tuple(FOCUS[axis] + offset[axis] for axis in range(3))
                           for offset, unused_depth in row['shape'] if offset != (0, 0, 0)]
                world.request(occupied=self.occupancy(world, omitted))
                finish(world)
                self.assertEqual(expected, focus_records(world_groups(world)))
                self.assertTrue(all(record[0] not in omitted for record in records(world_groups(world))))
                self.assertEqual(before, document.to_data())
                self.assertEqual(document.blocks, world.document.blocks)
                self.assertEqual(document.size, world.document.size)
                self.assertEqual(document.biome, world.document.biome)
                self.assertEqual(expected, focus_records(preview.groups.values()))
                self.assertTrue(all(not runtime.hidden(model) for model in runtime.models))
                self.assertTrue(world.close())
                preview.close()

    def test_filtered_flowing_neighbor_keeps_independent_fraction_height_and_direction(self):
        document = source_document('flow_east')
        unused_session, unused_preview, world, unused_runtime = self.owners(document)
        world.request(only_layer_targets(world.document, 0))
        finish(world)
        actual = focus_records(world_groups(world))
        encoded = tuple(int(float(height) * 255 + .5) for height in
                        (Fraction(85, 117), Fraction(1, 6), Fraction(1, 6), Fraction(85, 117)))
        self.assertTrue(actual)
        self.assertTrue(all(record[1] == encoded for record in actual))
        tops = [record for record in actual if record[0] & 1]
        self.assertEqual(1, len(tops))
        self.assertEqual(192, tops[0][2])
        world.request(occupied=self.occupancy(world, ((FOCUS[0] + 1, FOCUS[1], FOCUS[2]),)))
        finish(world)
        self.assertEqual(actual, focus_records(world_groups(world)))

    def test_occupied_lower_drop_neighbor_keeps_flow_with_unchanged_corner_height(self):
        document = source_document('drop_north')
        unused_session, unused_preview, world, unused_runtime = self.owners(document)
        world.request(occupied=self.occupancy(world, ((FOCUS[0], FOCUS[1] - 1, FOCUS[2] - 1),)))
        finish(world)
        actual = focus_records(world_groups(world))
        encoded = int(float(Fraction(20, 27)) * 255 + .5)
        self.assertTrue(all(record[1] == (encoded,) * 4 for record in actual))
        self.assertEqual([128], [record[2] for record in actual if record[0] & 1])

    def test_editor_cutaway_keeps_hidden_above_water_as_full_height_context(self):
        document = source_document('falling')
        selected_session, preview, world, unused_runtime = self.owners(document)
        before = focus_records(preview.groups.values())
        self.assertTrue(all(record[1] == (255,) * 4 for record in before))
        self.assertFalse(any(record[0] & 1 for record in before))
        selected_session.preview_hidden = lambda: (FOCUS[1] + 1,)
        finish(preview)
        self.assertEqual(before, focus_records(preview.groups.values()))
        self.assertTrue(all(record[0][1] != FOCUS[1] + 1 for record in records(preview.groups.values())))
        world.request(occupied=self.occupancy(world, ((FOCUS[0], FOCUS[1] + 1, FOCUS[2]),)))
        finish(world)
        self.assertEqual(before, focus_records(world_groups(world)))

    def test_coincident_identical_layers_render_once_without_discarding_typed_actor(self):
        for back_name in ('water', 'flowing_water'):
            with self.subTest(back=back_name):
                single = source_document('source')
                unused_session, single_preview, unused_world, unused_runtime = self.owners(single)
                expected = focus_records(single_preview.groups.values())
                source = source_document('source')
                nbt = {'typed': {'byte': True, 'int': 1, 'bytes': b'\x00\xff', 'list': [False, 2]}}
                source.set_cell(FOCUS, make_cell(material('water'), material(back_name), nbt))
                before = copy.deepcopy(source.to_data())
                unused_session, preview, world, unused_runtime = self.owners(source)
                self.assertEqual(expected, focus_records(preview.groups.values()))
                self.assertEqual(expected, focus_records(world_groups(world)))
                for layer in (0, 1):
                    world.request(only_layer_targets(world.document, layer))
                    finish(world)
                    self.assertEqual(expected, focus_records(world_groups(world)))
                    self.assertEqual(source.blocks, world.document.blocks)
                world.request()
                finish(world)
                self.assertEqual(expected, focus_records(world_groups(world)))
                self.assertEqual(nbt, source.get(FOCUS).nbt)
                self.assertEqual(before, source.to_data())

    def test_different_depth_layers_fail_without_replacing_published_editor_water(self):
        document = source_document('source')
        selected_session, preview, unused_world, unused_runtime = self.owners(document)
        previous = copy.deepcopy(preview.groups)
        document.set_cell(FOCUS, make_cell(material('water'), material('water', {'liquid_depth': 3})))
        selected_session.editor.revision += 1
        before = copy.deepcopy(document.to_data())
        self.assertFalse(preview.advance())
        self.assertRegex(str(preview.error), 'Conflicting liquid depths')
        self.assertEqual(previous, preview.groups)
        self.assertEqual(before, document.to_data())

    def test_failed_product_uniform_upload_preserves_visible_generation_then_recovers(self):
        document = source_document('flow_east')
        unused_session, unused_preview, world, runtime = self.owners(document)
        old_ids = set(runtime.models)
        old_records = records(world_groups(world))
        occupied = self.occupancy(world, ((FOCUS[0] + 1, FOCUS[1], FOCUS[2]),))
        runtime.fail_uniform_index = 1
        world.request(occupied=occupied)
        world.set_biome('swampland')  # Changed tint requires a new native payload, not only retiring a neighbor.
        with patch('projection.liquid_projection.traceback.print_exc'):
            for unused in range(1000):
                world.advance()
                if world.error is not None:
                    break
        self.assertIsNotNone(world.error)
        self.assertEqual(old_ids, set(runtime.models))
        self.assertEqual(old_records, records(world_groups(world)))
        self.assertTrue(all(not runtime.hidden(model) for model in old_ids))
        calls = len(runtime.uniform_calls)
        for unused in range(10):
            self.assertFalse(world.advance())
        self.assertEqual(calls, len(runtime.uniform_calls))
        runtime.fail_uniform_index = None
        world.request(occupied=occupied)
        finish(world)
        self.assertIsNone(world.error)
        self.assertEqual(focus_records(world_groups(world)), [row[1:] for row in old_records if row[0] == FOCUS])
        self.assertTrue(all(not runtime.hidden(model) for model in runtime.models))

    def test_failed_native_release_retains_hidden_ownership_until_retry(self):
        document = source_document('wet_oak_fence')
        unused_session, unused_preview, world, runtime = self.owners(document)
        live = set(runtime.models)
        runtime.remove_ok = False
        self.assertFalse(world.close())
        self.assertEqual(live, set(runtime.models))
        self.assertTrue(all(runtime.hidden(model) for model in live))
        self.assertFalse(world.advance())
        runtime.remove_ok = True
        self.assertTrue(world.close())
        self.assertEqual({}, runtime.models)


if __name__ == '__main__':
    unittest.main()
