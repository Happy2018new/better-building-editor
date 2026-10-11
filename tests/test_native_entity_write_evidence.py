"""Reject unrestored, stale, lossy and overgeneralized native tile rules."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
import generate_native_entity_writes as generate
from projection import native_entity_write as native


class NativeEntityWriteEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        cls.snapshot = json.loads((ROOT / 'tools/data/native_entity_writes_nemc_3.9.0.401155.json').read_bytes())

    def test_complete_before_after_evidence_generates_only_observed_pot_rules(self):
        self.assertEqual({'minecraft:decorated_pot': generate.STAGES}, generate.inspect(self.snapshot, self.manifest))
        self.assertEqual(48, sum(len(case['writes']) for case in self.snapshot['after']['cases']))
        self.assertEqual((), native.tile_rebuild_stages(('minecraft:chest',0), ('minecraft:air',0), {}))
        self.assertEqual((), native.tile_rebuild_stages(('minecraft:decorated_pot',0), ('minecraft:water',1), {}))
        self.assertEqual((), native.tile_rebuild_stages(('minecraft:decorated_pot',0), ('minecraft:air',0), None))

    def test_missing_client_water_inventory_or_restore_cannot_generate_rules(self):
        for failure in ('client_water', 'inventory', 'restore', 'negative', 'coverage', 'stage'):
            data = copy.deepcopy(self.snapshot)
            row = data['after']['cases'][1]['writes'][1]
            if failure == 'client_water':
                row['replication']['last']['extra'] = []
            elif failure == 'inventory':
                row['nbt']['item']['Count']['__value__'] = 0
            elif failure == 'restore':
                data['after']['cleanup']['remaining'] = [[0,0,0]]
            elif failure == 'negative':
                data['before']['passed'] = True
            elif failure == 'coverage':
                data['after']['cases'].pop()
            else:
                row['air_staging'][0]['block']['name'] = 'minecraft:stone'
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                generate.inspect(data, self.manifest)

    def test_stale_runtime_version_or_dump_is_rejected_before_world_writes(self):
        for version, fingerprint in (('NEMC next', native.source.PALETTE_SHA256),
                                     (native.source.SOURCE_VERSION, '0'*64)):
            with patch.object(native.registry, 'source_version', return_value=version), \
                    patch.object(native.registry, 'fingerprint', return_value=fingerprint), \
                    self.assertRaisesRegex(ValueError, 'need observations'):
                native.tile_rebuild_stages(('minecraft:decorated_pot',0), ('minecraft:water',0), {})


if __name__ == '__main__':
    unittest.main()
