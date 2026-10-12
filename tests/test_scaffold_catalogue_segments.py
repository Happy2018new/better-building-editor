"""Interrupted native runs must not become a full scaffold capability table."""
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from generate_scaffold_support import capabilities
from merge_scaffold_support_segments import (
    collect_segments, dump_states, merge_segments, missing_ranges, validate_segment)
from verify_scaffold_support_catalogue import SEGMENT_METHOD, MAX_SEGMENT_STATES, START, STATUS, RESTORE, MARKER
from verify_scaffolding_native import registry


class _BlockInfo:
    def __init__(self):
        self.cells = {}
        self.liquids = {}
        self.writes = []
        self.fail_palette = False

    def GetBlockNew(self, pos, dimension):
        return dict(self.cells.get(pos, {'name': 'minecraft:air', 'aux': 0}))

    def SetBlockNew(self, pos, value, *args):
        self.writes.append((pos, dict(value)))
        self.cells[pos] = dict(value)
        return True

    def GetLiquidBlock(self, pos, dimension):
        return dict(self.liquids.get(pos, {'name': 'minecraft:air', 'aux': 0}))

    def GetBlankBlockPalette(self):
        return types.SimpleNamespace(DeserializeBlockPalette=self.deserialize)

    def deserialize(self, data):
        if data['common'] != {('minecraft:air', 0): [0]} or data['extra'] != {('minecraft:air', 0): [0]}:
            raise AssertionError('Reset must explicitly clear both layers')
        return True

    def SetBlockByBlockPalette(self, palette, dimension, pos, *args):
        if self.fail_palette:
            raise RuntimeError('Injected palette reset failure')
        self.cells[pos] = {'name': 'minecraft:air', 'aux': 0}
        self.liquids.pop(pos, None)
        self.writes.append((pos, dict(self.cells[pos])))
        return True


class _Game:
    def __init__(self):
        self.tile_drops = True
        self.flow_forbidden = False
        self.timers = []

    def GetGameRulesInfoServer(self):
        return {'option_info': {'tile_drops': self.tile_drops}}

    def SetGameRulesInfoServer(self, value):
        self.tile_drops = value['option_info']['tile_drops']
        return True

    def AddTimer(self, delay, callback):
        self.timers.append(callback)

    def ForbidLiquidFlow(self, forbidden):
        self.flow_forbidden = forbidden
        return True


class ScaffoldCatalogueSegmentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        cls.expected = dump_states()

    def segment(self, start, count=8):
        stop = min(start + count, len(self.expected))
        return {'schema': 1, 'method': SEGMENT_METHOD, 'completed': True, 'restored': True,
                'game_version': self.manifest['game_version'],
                'palette_sha256': self.manifest['source_sha256'].lower(), 'source_sha256': 'a' * 64,
                'native': {'done': True, 'states': len(self.expected), 'range': [start, stop],
                           'index': stop, 'rows': [{'requested': list(value)}
                                                  for value in self.expected[start:stop]]}}

    def test_empty_plan_covers_every_dump_index_once_with_bounded_ranges(self):
        ranges = missing_ranges([None] * len(self.expected))
        indices = [index for row in ranges for index in range(row['start_index'], row['start_index'] + row['count'])]
        self.assertEqual(list(range(len(self.expected))), indices)
        self.assertTrue(all(0 < row['count'] <= MAX_SEGMENT_STATES for row in ranges))

    def test_noncontiguous_saved_ranges_only_plan_unmeasured_states(self):
        rows = collect_segments([self.segment(8), self.segment(32)], self.manifest, self.expected)
        ranges = missing_ranges(rows, 16)
        planned = {index for row in ranges for index in range(row['start_index'], row['start_index'] + row['count'])}
        self.assertFalse(planned & (set(range(8, 16)) | set(range(32, 40))))
        self.assertEqual(set(range(len(self.expected))) - set(range(8, 16)) - set(range(32, 40)), planned)

    def test_interrupted_or_unrestored_segment_is_rejected(self):
        for key, value in (('completed', False), ('restored', False),
                           ('game_version', 'NEMC next'), ('palette_sha256', '0' * 64),
                           ('source_sha256', ''), ('error', 'SDK timed out'), ('cleanup_error', 'IPC failed')):
            report = self.segment(0)
            report[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_segment(report, self.manifest, self.expected)

    def test_missing_changed_or_reordered_readback_is_rejected(self):
        for kind in ('missing', 'changed', 'reordered', 'progress'):
            report = self.segment(0)
            rows = report['native']['rows']
            if kind == 'missing':
                rows.pop()
            elif kind == 'changed':
                rows[0]['requested'] = ['custom:unknown', 0]
            elif kind == 'reordered':
                rows.reverse()
            else:
                report['native']['index'] -= 1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_segment(report, self.manifest, self.expected)

    def test_legacy_single_layer_resets_cannot_enter_dual_layer_catalogue(self):
        report = self.segment(0)
        report['method'] = ('8 isolated native legacy-state support/scaffold cells; '
                            'tile drops disabled; .35s delayed readback; bounded-range-v1')
        with self.assertRaisesRegex(ValueError, 'mismatching'):
            validate_segment(report, self.manifest, self.expected)

    def test_overlapping_or_mixed_source_segments_are_rejected(self):
        first, second = self.segment(0), self.segment(4)
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            collect_segments([first, second], self.manifest, self.expected)
        second = self.segment(8)
        second['source_sha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'different probe sources'):
            collect_segments([first, second], self.manifest, self.expected)

    def test_one_successful_segment_cannot_generate_a_full_capability_table(self):
        report = self.segment(0)
        with self.assertRaises(ValueError):
            capabilities(report, self.manifest)
        with self.assertRaisesRegex(ValueError, 'Incomplete scaffold catalogue'):
            merge_segments([report], self.manifest, self.expected)

    def test_complete_union_is_accepted_with_unmeasured_outcomes_remaining_unknown(self):
        reports = [self.segment(index, MAX_SEGMENT_STATES)
                   for index in range(0, len(self.expected), MAX_SEGMENT_STATES)]
        merged = merge_segments(list(reversed(reports)), self.manifest, self.expected)
        self.assertEqual(len(self.expected), len(merged['native']['rows']))
        result = capabilities(merged, self.manifest)
        self.assertEqual('full_catalogue', result['scope'])
        self.assertEqual(0, result['unobserved_states'])
        self.assertEqual(len(self.expected), sum(len(aux) for aux in result['unknown'].values()))
        self.assertEqual((), result['blocks'])


class ScaffoldSegmentLifecycleTests(unittest.TestCase):
    """Run the generated server script against a deterministic scheduler stub."""

    def setUp(self):
        self.info, self.game, self.scope = _BlockInfo(), _Game(), {}
        factory = types.SimpleNamespace(
            CreateBlockInfo=lambda level: self.info, CreateBlock=lambda level: self.info,
            CreateGame=lambda level: self.game,
            CreateDimension=lambda player: types.SimpleNamespace(GetEntityDimensionId=lambda: 0),
            CreatePos=lambda player: types.SimpleNamespace(GetFootPos=lambda: (0, 64, 0)))
        api = types.ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = lambda: factory
        api.GetLevelId, api.GetPlayerList = lambda: 'level', lambda: ['player']
        api.GetMinecraftVersion = lambda: 'scheduler-stub'
        mod, server = types.ModuleType('mod'), types.ModuleType('mod.server')
        mod.server, server.extraServerApi = server, api
        package = types.ModuleType('modern_projection')
        projection = types.ModuleType('modern_projection.projection')
        package.projection, projection.block_registry = projection, registry
        replacement = {'mod': mod, 'mod.server': server, 'mod.server.extraServerApi': api,
                       'modern_projection': package, 'modern_projection.projection': projection}
        self.modules = patch.dict(sys.modules, replacement)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.addCleanup(lambda: vars(sys).pop(MARKER, None))

    def run_script(self, code):
        exec(compile(code, '<scaffold-segment-server>', 'exec'), self.scope)
        return json.loads(self.scope['_result'])

    def test_short_range_never_places_extra_states_and_restores_rules(self):
        self.run_script(START % (MARKER, 5, 1, registry.SOURCE_VERSION, registry.SOURCE_SHA256))
        self.game.timers.pop(0)()
        progress = self.run_script(STATUS % MARKER)
        self.assertTrue(progress['done'])
        self.assertEqual([5, 6], progress['range'])
        self.assertEqual([list(dump_states()[5])], [row['requested'] for row in progress['rows']])
        cleanup = self.run_script(RESTORE % MARKER)
        self.assertTrue(cleanup['restored'])
        self.assertTrue(self.game.tile_drops)
        self.assertFalse(self.game.flow_forbidden)
        self.assertFalse(hasattr(sys, MARKER))

    def test_cancelled_pending_readback_cannot_place_another_batch(self):
        self.run_script(START % (MARKER, 0, 16, registry.SOURCE_VERSION, registry.SOURCE_SHA256))
        self.run_script(RESTORE % MARKER)
        writes_after_cleanup = len(self.info.writes)
        self.game.timers.pop(0)()
        self.assertEqual(writes_after_cleanup, len(self.info.writes))
        self.assertTrue(all(value['name'] == 'minecraft:air' for value in self.info.cells.values()))

    def test_reset_clears_retained_background_water_before_next_batch_and_cleanup(self):
        start = self.run_script(START % (MARKER, 0, 16, registry.SOURCE_VERSION, registry.SOURCE_SHA256))
        pos = tuple(start['origin'])
        self.info.liquids[pos] = {'name': 'minecraft:water', 'aux': 0}
        self.game.timers.pop(0)()
        self.assertFalse(self.info.liquids)
        self.info.liquids[pos] = {'name': 'minecraft:water', 'aux': 0}
        cleanup = self.run_script(RESTORE % MARKER)
        self.assertTrue(cleanup['restored'])
        self.assertEqual([], cleanup['remaining'])
        self.assertFalse(self.info.liquids)

    def test_cleanup_reset_exception_still_restores_rules_and_retains_recovery_state(self):
        self.run_script(START % (MARKER, 0, 16, registry.SOURCE_VERSION, registry.SOURCE_SHA256))
        self.info.fail_palette = True
        with self.assertRaisesRegex(RuntimeError, 'reset failure'):
            self.run_script(RESTORE % MARKER)
        self.assertTrue(self.game.tile_drops)
        self.assertFalse(self.game.flow_forbidden)
        self.assertTrue(hasattr(sys, MARKER))
        self.info.fail_palette = False
        self.assertTrue(self.run_script(RESTORE % MARKER)['restored'])

    def test_old_timer_cannot_advance_a_new_segment_in_the_same_execution_scope(self):
        self.run_script(START % (MARKER, 0, 16, registry.SOURCE_VERSION, registry.SOURCE_SHA256))
        old_callback = self.game.timers.pop(0)
        self.run_script(RESTORE % MARKER)
        self.run_script(START % (MARKER, 50, 16, registry.SOURCE_VERSION, registry.SOURCE_SHA256))
        writes_before_old_timer = len(self.info.writes)
        old_callback()
        self.assertEqual(writes_before_old_timer, len(self.info.writes))
        progress = self.run_script(STATUS % MARKER)
        self.assertEqual(50, progress['index'])
        self.assertEqual([], progress['rows'])
        self.run_script(RESTORE % MARKER)


if __name__ == '__main__':
    unittest.main()
