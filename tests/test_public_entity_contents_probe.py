"""Public source selection and native probe ownership remain independent gates."""
from copy import deepcopy
import json
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT / 'behavior_pack'))
import probe_public_entity_contents as probe
from modern_projection.projection.cell import actor_data, foreground
from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.visible_actor import entity_nbt
from test_entity_appearance_probe import NativeFixture, fake_api, tag


def request(**values):
    result = {'fixture': 'test.entities.recent', 'material': 'minecraft:oak_shelf',
              'source_cell': None, 'placement_item': None, 'placement_face': 1,
              'placement_aux': 0, 'yaw': 0., 'item': 'minecraft:diamond_sword',
              'item_aux': 0, 'interaction_face': 3, 'enchantment': None, 'nonce': 'owned-test'}
    result.update(values)
    return result


class ContentFixture(NativeFixture):
    def __init__(self, used=True):
        super().__init__()
        self.used = used
        self.content_calls = 0

    def SpawnItemToPlayerInv(self, item, player, slot):
        super().SpawnItemToPlayerInv(item, player, slot)
        return True

    def GetInvItemEnchantData(self, slot):
        return []

    def PlayerUseItemToPos(self, pos, item_type, slot, face):
        if tuple(pos) in self.entities:
            self.content_calls += 1
            self.entities[tuple(pos)]['FutureNativeField'] = {
                'nested': [{'UnknownTypedValue': tag(17, 2)}]}
            return self.used
        result = super().PlayerUseItemToPos(pos, item_type, slot, face)
        self.entities[next(reversed(self.entities))]['id'] = tag('Shelf', 8)
        return result


class PublicContentSelectionTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(sys, '_p0_entity_appearance_public_plans'):
            del sys._p0_entity_appearance_public_plans

    def plan(self, values):
        exec(compile(probe.PUBLIC_PLAN % values, '<public-content-selection>', 'exec'), {})
        return deepcopy(sys._p0_entity_appearance_public_plans[0])

    def test_shelf_plan_comes_from_the_actual_public_document_without_mutation(self):
        document = build('test.entities.recent')
        original = deepcopy(document.blocks)
        position, cell = next((pos, cell) for pos, cell in document.blocks.items()
                              if foreground(cell)[0] == 'minecraft:oak_shelf')
        plan = self.plan(request())
        self.assertEqual(position, plan['public_source'])
        self.assertEqual(foreground(cell), plan['public_material'])
        self.assertEqual(entity_nbt(actor_data(cell)), plan['public_entity_nbt'])
        self.assertTrue(plan['content_probe'])
        self.assertEqual(original, document.blocks)
        self.assertNotIn('userData', plan)

    def test_ambiguous_sources_require_an_explicit_public_cell(self):
        values = request(fixture='test.entities.item_contents', material='minecraft:frame')
        with self.assertRaisesRegex(AssertionError, 'explicitly'):
            self.plan(values)
        plan = self.plan(dict(values, source_cell=(17, 2, 3)))
        self.assertEqual((17, 2, 3), plan['public_source'])

    def test_nonpublic_absent_and_multiblock_sources_reject_before_setup(self):
        for values in (request(fixture='private.shelf'), request(material='minecraft:missing'),
                       request(fixture='test.entities.classic', material='minecraft:bed',
                               source_cell=(9, 1, 27))):
            with self.subTest(values=values), self.assertRaises(AssertionError):
                self.plan(values)
            self.assertFalse(hasattr(sys, '_p0_entity_appearance_public_plans'))

    def test_existing_native_state_is_rejected_without_replacing_it(self):
        foreign = {'rows': [{'probe_nonce': 'foreign'}]}
        with patch.object(sys, '_p0_entity_appearances', foreign, create=True):
            with self.assertRaisesRegex(AssertionError, 'previous entity'):
                self.plan(request())
            self.assertIs(foreign, sys._p0_entity_appearances)


class NativePublicContentTests(unittest.TestCase):
    def rejected_setup(self, fixture, message):
        original_inventory = deepcopy(fixture.inventory)
        original_rotation = deepcopy(fixture.rotation)
        exec(compile(probe.PUBLIC_PLAN % request(), '<public-content-selection>', 'exec'), {})
        try:
            with fake_api(fixture), \
                    patch.object(fixture, 'SetBlockNew', wraps=fixture.SetBlockNew) as world_write, \
                    patch.object(fixture, 'SetInvItemNum', wraps=fixture.SetInvItemNum) as inventory_write, \
                    patch.object(fixture, 'SetRot', wraps=fixture.SetRot) as rotation_write:
                with self.assertRaisesRegex(AssertionError, message):
                    runpy.run_path(str(ROOT / 'tools/p0_entity_appearance_setup.py'))
                world_write.assert_not_called()
                inventory_write.assert_not_called()
                rotation_write.assert_not_called()
        finally:
            if hasattr(sys, '_p0_entity_appearance_public_plans'):
                del sys._p0_entity_appearance_public_plans
        self.assertEqual({}, fixture.world)
        self.assertEqual(0, fixture.placements)
        self.assertEqual(original_inventory, fixture.inventory)
        self.assertEqual(original_rotation, fixture.rotation)

    def test_invalid_rotation_baseline_rejects_before_any_mutation(self):
        for rotation in (None, (), (0.,), ('0', 0.), (False, 0.),
                         (float('nan'), 0.), (0., float('inf'))):
            fixture = ContentFixture()
            with self.subTest(rotation=rotation), patch.object(fixture, 'GetRot', return_value=rotation):
                self.rejected_setup(fixture, 'Player rotation readback failed')

    def test_malformed_nonempty_inventory_is_not_selected_or_cleared(self):
        for count in (None, -1, False, '0'):
            fixture = ContentFixture()
            fixture.inventory = {'itemName': 'minecraft:diamond_sword',
                                 'userData': {'FutureNativeField': {'nested': [42]}}}
            if count is not None:
                fixture.inventory['count'] = count
            with self.subTest(count=count):
                self.rejected_setup(fixture, 'Malformed inventory count')

    def sample(self, used=True):
        fixture = ContentFixture(used=used)
        values = request()
        exec(compile(probe.PUBLIC_PLAN % values, '<public-content-selection>', 'exec'), {})
        with fake_api(fixture):
            setup = json.loads(runpy.run_path(str(ROOT / 'tools/p0_entity_appearance_setup.py'))['_result'])
            self.assertEqual(7, len(setup['reserved']))
            self.assertFalse(hasattr(sys, '_p0_entity_appearance_public_plans'))
            environment = {}
            exec(compile(probe.INTERACT % values, '<public-content-native-interaction>', 'exec'), environment)
            report = json.loads(environment['_result'])
            runpy.run_path(str(ROOT / 'tools/p0_entity_appearance_cleanup.py'))
        self.assertEqual(fixture.original_rotation, fixture.rotation)
        self.assertIsNone(fixture.inventory)
        self.assertTrue(all(block['name'] == 'minecraft:air' for block in fixture.world.values()))
        return report, fixture

    def test_one_native_interaction_preserves_unknown_complete_payload_and_cleanup(self):
        report, fixture = self.sample()
        self.assertEqual(1, fixture.content_calls)
        result = report['result']
        self.assertTrue(result['native_interaction_passed'])
        self.assertTrue(result['nbt_changed'])
        self.assertEqual({'nested': [{'UnknownTypedValue': tag(17, 2)}]},
                         result['after_nbt']['FutureNativeField'])
        self.assertEqual(result['after_nbt'], report['rows'][0]['cell_nbt'][0]['nbt'])
        self.assertEqual(7, len(report['reserved_after_interaction']))

    def test_changed_payload_cannot_pass_a_failed_native_interaction(self):
        report, unused = self.sample(used=False)
        self.assertTrue(report['result']['nbt_changed'])
        self.assertFalse(report['result']['native_interaction_passed'])

    def test_occupied_interaction_neighbor_rejects_before_any_world_write(self):
        fixture = ContentFixture()
        occupied = (21, 80, -20)
        fixture.world[occupied] = {'name': 'minecraft:stone', 'aux': 0}
        before = deepcopy(fixture.world)
        exec(compile(probe.PUBLIC_PLAN % request(), '<public-content-selection>', 'exec'), {})
        with fake_api(fixture):
            with self.assertRaises(AssertionError):
                runpy.run_path(str(ROOT / 'tools/p0_entity_appearance_setup.py'))
        self.assertEqual(before, fixture.world)
        self.assertEqual(0, fixture.placements)

    def test_changed_native_ownership_rejects_before_any_inventory_or_world_write(self):
        fixture = ContentFixture()
        foreign = {'rows': [{'probe_nonce': 'foreign'}]}
        with fake_api(fixture), patch.object(sys, '_p0_entity_appearances', foreign, create=True):
            with self.assertRaisesRegex(AssertionError, 'ownership changed'):
                exec(compile(probe.INTERACT % request(), '<public-content-native-interaction>', 'exec'), {})
        self.assertEqual({}, fixture.world)
        self.assertIsNone(fixture.inventory)
        self.assertEqual(0, fixture.content_calls)


class PublicContentCleanupTests(unittest.TestCase):
    def test_inventory_validation_preserves_raw_fields_and_valid_empty_forms(self):
        item = {'itemName': 'minecraft:book', 'count': 1,
                'userData': {'FutureNativeField': {'nested': [42]}}}
        empty = {'itemName': 'minecraft:air', 'count': 0, 'FutureNativeField': 7}
        before = {'inventory': [item, empty, {}] + [None] * 33,
                  'selected_slot': 0, 'rotation': [5., 12.]}
        original = deepcopy(before)
        after = deepcopy(before)
        after['inventory'][1:3] = [None, None]
        self.assertEqual([], probe.player_restore_errors(before, after))
        self.assertEqual(original, before)
        after['inventory'][0]['userData']['FutureNativeField']['nested'] = [43]
        self.assertEqual(1, len(probe.player_restore_errors(before, after)))

    def test_malformed_inventory_readback_cannot_pass_as_empty(self):
        before = {'inventory': [None] * 36, 'selected_slot': 0, 'rotation': [5., 12.]}
        after = deepcopy(before)
        after['inventory'][13] = {'itemName': 'minecraft:book', 'userData': {'unknown': 42}}
        with self.assertRaisesRegex(ValueError, 'Malformed inventory readback at slot 13'):
            probe.player_restore_errors(before, after)
        report = {'request': request(), 'player_before': before}
        with patch.object(probe, 'execute', side_effect=[None, True, True, True, after]):
            probe.clean(object(), report)
        self.assertFalse(report['restored'])
        self.assertEqual(after, report['player_after_cleanup'])
        self.assertIn('slot 13', report['cleanup_errors'][0])

    def test_invalid_preflight_stays_raw_and_never_enters_setup(self):
        malformed = {'itemName': 'minecraft:book', 'userData': {'unknown': [42]}}
        for inventory, rotation, error in (([None] * 36, None, 'rotation'),
                                           ([malformed] + [None] * 35, [5., 12.], 'inventory')):
            state = {'inventory': inventory, 'selected_slot': 0, 'rotation': rotation,
                     'foot': [0., 64., 0.]}
            report = {'request': request(), 'completed': False}
            with self.subTest(error=error), \
                    patch.object(probe, 'native_runtime_evidence', return_value={'native_runtime_versions': {}}), \
                    patch.object(probe, 'execute', return_value=state) as execute, \
                    patch.object(probe, 'clean') as clean:
                with self.assertRaisesRegex(ValueError, error):
                    probe.collect(object(), report['request'], report)
                execute.assert_called_once()
                self.assertEqual(probe.PLAYER_STATE, execute.call_args[0][1])
                clean.assert_called_once()
                self.assertEqual(state, report['player_before'])
                self.assertFalse(report['completed'])

    def test_nonfinite_rotation_readback_cannot_pass_restore_comparison(self):
        state = {'inventory': [None] * 36, 'selected_slot': 0, 'rotation': [float('nan'), 0.]}
        self.assertEqual(['Player rotation differs from preflight'],
                         probe.player_restore_errors(state, deepcopy(state)))

    def test_complete_inventory_selected_slot_and_rotation_are_independent_restore_gates(self):
        before = {'inventory': [None] * 36, 'selected_slot': 0, 'rotation': [0., 0.]}
        after = deepcopy(before)
        self.assertEqual([], probe.player_restore_errors(before, after))
        for field in ('inventory', 'selected_slot', 'rotation'):
            after = deepcopy(before)
            if field == 'inventory':
                after[field][13] = {'itemName': 'minecraft:book', 'count': 1, 'userData': {'unknown': 7}}
            elif field == 'selected_slot':
                after[field] = 8
            else:
                after[field] = [0., 45.]
            with self.subTest(field=field):
                self.assertEqual(1, len(probe.player_restore_errors(before, after)))

    def test_player_readback_failure_prevents_restore_acceptance_after_other_cleanup(self):
        report = {'request': request(), 'player_before': {'inventory': [None] * 36}}
        with patch.object(probe, 'execute', side_effect=[None, True, True, True,
                                                        RuntimeError('Player snapshot unavailable')]):
            probe.clean(object(), report)
        self.assertFalse(report['restored'])
        self.assertIn('Player snapshot unavailable', report['cleanup_errors'][0])

    def execute_locally(self, unused_client, code, unused_client_side=False):
        environment = {}
        exec(compile(code, '<public-content-cleanup>', 'exec'), environment)
        result = environment['_result']
        return json.loads(result) if isinstance(result, str) else result

    def test_cleanup_cannot_clear_a_different_native_or_client_probe(self):
        foreign = {'rows': [{'probe_nonce': 'foreign'}]}
        plans = [{'probe_nonce': 'foreign'}]
        report = {'request': request()}
        with patch.object(sys, '_p0_entity_appearances', foreign, create=True), \
                patch.object(sys, '_p0_entity_appearance_public_plans', plans, create=True), \
                patch.object(sys, '_p0_entity_content_probe_nonce', 'foreign', create=True), \
                patch.object(sys, '_p0_entity_appearance_rows', [foreign], create=True), \
                patch.object(probe, 'execute', side_effect=self.execute_locally):
            probe.clean(object(), report)
            self.assertIs(foreign, sys._p0_entity_appearances)
            self.assertIs(plans, sys._p0_entity_appearance_public_plans)
            self.assertEqual('foreign', sys._p0_entity_content_probe_nonce)
            self.assertEqual([foreign], sys._p0_entity_appearance_rows)
        self.assertTrue(report['restored'])

    def test_snapshot_failure_still_attempts_native_pending_and_client_cleanup(self):
        report = {'request': request()}
        with patch.object(probe, 'execute', side_effect=[RuntimeError('Snapshot unavailable'),
                                                        True, True, True]) as execute:
            probe.clean(object(), report)
        self.assertEqual(4, execute.call_count)
        self.assertFalse(report['restored'])
        self.assertIn('Snapshot unavailable', report['cleanup_errors'][0])
        self.assertTrue(report['client_cleaned'])

    def test_primary_setup_failure_does_not_skip_cleanup(self):
        report = {'request': request(), 'completed': False}
        with patch.object(probe, 'execute', side_effect=RuntimeError('Primary setup failure')), \
                patch.object(probe, 'native_runtime_evidence', return_value={'native_runtime_versions': {}}), \
                patch.object(probe, 'clean') as clean:
            with self.assertRaisesRegex(RuntimeError, 'Primary setup failure'):
                probe.collect(object(), report['request'], report)
        clean.assert_called_once()
        self.assertFalse(report['completed'])


if __name__ == '__main__':
    unittest.main()
