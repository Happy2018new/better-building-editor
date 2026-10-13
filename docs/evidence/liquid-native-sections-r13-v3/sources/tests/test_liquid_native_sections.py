"""Publication controls must require a spatial stone body and blue wet change."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_liquid_native_sections as probe


class NativePositiveTests(unittest.TestCase):
    def masks(self):
        support = np.zeros((100, 100), bool); support[50:90, 20:80] = True
        water = np.zeros((100, 100), bool); water[5:45, 20:80] = True
        return {'support': support, 'water_envelope': water}

    def test_sparse_white_chicken_cannot_qualify_native_stone(self):
        empty = np.full((100, 100, 3), 80, np.int16)
        dry = empty.copy(); dry[65:75, 30:50] = 240
        wet = dry.copy(); wet[5:45, 20:80] = [40, 100, 200]
        actual = probe.native_positive(dry, wet, empty, self.masks())
        self.assertFalse(actual['support_observed'])
        self.assertTrue(actual['water_observed'])
        self.assertFalse(actual['production_qualified'])

    def test_broad_gray_stone_and_separate_blue_contribution_observed(self):
        empty = np.full((100, 100, 3), 80, np.int16)
        dry = empty.copy(); dry[50:90, 20:80] = 150
        wet = dry.copy(); wet[5:45, 20:80] = [40, 100, 200]
        actual = probe.native_positive(dry, wet, empty, self.masks())
        self.assertTrue(actual['support_observed'])
        self.assertTrue(actual['water_observed'])
        self.assertEqual(1., actual['support_coverage'])

    def test_grass_and_changing_gray_backdrop_do_not_qualify_water(self):
        empty = np.full((100, 100, 3), 80, np.int16)
        dry = empty.copy(); dry[50:90, 20:80] = [20, 180, 40]
        wet = dry.copy(); wet[5:45, 20:80] = 170
        actual = probe.native_positive(dry, wet, empty, self.masks())
        self.assertFalse(actual['support_observed'])
        self.assertFalse(actual['water_observed'])

    def test_stone_only_is_not_water(self):
        empty = np.full((100, 100, 3), 80, np.int16)
        dry = empty.copy(); dry[50:90, 20:80] = 150
        actual = probe.native_positive(dry, dry, empty, self.masks())
        self.assertTrue(actual['support_observed'])
        self.assertFalse(actual['water_observed'])


class ReservationTests(unittest.TestCase):
    def run_prepare(self, occupied=None):
        class Info:
            def GetBlockNew(self, position, dimension):
                return {'name': 'minecraft:stone' if position == occupied else 'minecraft:air', 'aux': 0}
            def GetLiquidBlock(self, position, dimension):
                return None
        factory = SimpleNamespace(CreateDimension=lambda player: SimpleNamespace(GetEntityDimensionId=lambda: 0),
            CreatePos=lambda player: SimpleNamespace(GetFootPos=lambda: (0., -60., 0.)),
            CreateBlockInfo=lambda player: Info())
        api = SimpleNamespace(GetEngineCompFactory=lambda: factory, GetPlayerList=lambda: ['player'])
        marker = SimpleNamespace()
        server = SimpleNamespace(extraServerApi=api)
        with patch.dict(sys.modules, {'mod': SimpleNamespace(server=server), 'mod.server': server,
                                     'mod.server.extraServerApi': api, 'sys': marker}):
            scope = {}
            exec(probe.PREPARE, scope)
        return json.loads(scope['_result']), marker

    def test_two_sections_are_air_reserved_without_world_or_player_writes(self):
        result, marker = self.run_prepare()
        self.assertEqual([[6, -58, 6], [6, -36, 6]], result['origins'])
        self.assertEqual(432, result['reserved_air_cells'])
        self.assertEqual(432, len(marker._liquid_pose_world['region']))
        self.assertEqual([], marker._liquid_pose_world['workspace_cells'])
        self.assertFalse(result['position_write_attempted'])

    def test_existing_near_section_block_rejects_before_saving_mutation_journal(self):
        with self.assertRaises(AssertionError):
            self.run_prepare((6, -58, 6))

if __name__ == '__main__':
    unittest.main()
