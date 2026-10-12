"""Native interaction success remains separate from preserved enchantment data."""
import copy
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack'))
from modern_projection.projection.cell import actor_data, foreground
from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_item_blueprints import ENCHANTMENT, IDENTITY, PAIRS
from modern_projection.projection.visible_actor import entity_nbt
from verify_enchanted_frame_nbt import WRITE_PHYSICAL
from generate_native_item_contents import canonical, runtime, validate, snapshot


class PhysicalFrameReadbackTests(unittest.TestCase):
    def run_sample(self, added=True, used=True, inventory_enchants=None):
        document = build(IDENTITY)
        rows, payloads = [], {}
        for pair in PAIRS:
            position = pair['enchanted']
            cell = document.get(position)
            material = foreground(cell)
            rows.append({'case': pair['source_case'], 'pos': position, 'face': 2,
                         'fill_item': 'minecraft:diamond_sword',
                         'block': {'name': material[0], 'aux': material[1]}})
            payloads[position] = entity_nbt(actor_data(cell))
        before = copy.deepcopy(payloads)
        items, info, factory = Mock(), Mock(), Mock()
        factory.CreateItem.return_value = items
        factory.CreateBlockInfo.return_value = info
        items.SetInvItemNum.return_value = True
        items.SpawnItemToPlayerInv.return_value = True
        items.GetPlayerItem.return_value = {'itemName': 'minecraft:diamond_sword', 'count': 1}
        items.AddEnchantToInvItem.return_value = added
        after_enchants = [ENCHANTMENT] if inventory_enchants is None else inventory_enchants
        items.GetInvItemEnchantData.side_effect = [[], after_enchants] * len(rows)
        info.PlayerUseItemToPos.return_value = used
        info.GetBlockEntityData.side_effect = lambda dimension, position: payloads[position]
        info.GetBlockNew.side_effect = lambda position, dimension: rows[
            [row['pos'] for row in rows].index(position)]['block']
        api = ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = lambda: factory
        api.GetMinecraftEnum = lambda: SimpleNamespace(
            ItemPosType=SimpleNamespace(INVENTORY=0),
            EnchantType=SimpleNamespace(WeaponDamage=ENCHANTMENT[0]))
        mod, server = ModuleType('mod'), ModuleType('mod.server')
        mod.server, server.extraServerApi = server, api
        saved = {'player': 'owned-player', 'slot': 8, 'dimension': 0, 'rows': rows,
                 'game_version': 'test', 'palette_sha256': '0' * 64}
        environment = {}
        with patch.dict(sys.modules, {'mod': mod, 'mod.server': server,
                                     'mod.server.extraServerApi': api}), \
                patch.object(sys, '_p0_entity_appearances', saved, create=True):
            exec(compile(WRITE_PHYSICAL, '<physical-frame-readback>', 'exec'), environment)
        self.assertEqual(before, payloads)
        return json.loads(environment['_result']), items, info

    def test_public_controls_are_enchanted_before_native_interaction(self):
        report, items, info = self.run_sample()
        self.assertTrue(all(row['passed'] for row in report['results']))
        self.assertEqual(2, info.PlayerUseItemToPos.call_count)
        self.assertEqual([ENCHANTMENT], [tuple(value) for value in
                         report['results'][0]['observed_enchantments']])
        items.AddEnchantToInvItem.assert_called_with(8, *ENCHANTMENT)
        self.assertEqual([list(pair['enchanted']) for pair in PAIRS],
                         [row['public_source'] for row in report['results']])

    def test_failed_native_interaction_cannot_pass_from_matching_tags(self):
        report, unused, info = self.run_sample(used=False)
        self.assertEqual(2, info.PlayerUseItemToPos.call_count)
        self.assertTrue(all(row['readback_is_enchanted'] for row in report['results']))
        self.assertFalse(any(row['passed'] for row in report['results']))

    def test_failed_or_unconfirmed_inventory_enchantment_is_not_used(self):
        for values in ({'added': False}, {'inventory_enchants': []}):
            with self.subTest(values=values):
                report, unused, info = self.run_sample(**values)
                info.PlayerUseItemToPos.assert_not_called()
                self.assertFalse(any(row['passed'] for row in report['results']))


class NativeItemSourceTests(unittest.TestCase):
    def source(self):
        return json.loads((ROOT / 'tools/data/native_item_contents_nemc_3.9.0.401155.json').read_bytes())

    def test_generated_runtime_keeps_complete_source_without_mutation(self):
        import base64
        import hashlib
        import zlib
        source = self.source()
        before = copy.deepcopy(source)
        output = runtime(source)
        namespace = {}
        exec(compile(output, '<native-item-source>', 'exec'), namespace)
        self.assertEqual(source['rows'], json.loads(zlib.decompress(base64.b64decode(namespace['ROWS']))))
        self.assertEqual(hashlib.sha256(canonical(source)).hexdigest(), namespace['SOURCE_SHA256'])
        self.assertEqual(source['source_sha256'], namespace['PROBE_SHA256'])
        self.assertEqual(before, source)
        self.assertEqual(output, runtime(source))

    def test_stale_version_synthetic_source_failed_operation_and_changed_types_reject(self):
        for field, value in (('schema', 1), ('game_version', 'future'),
                             ('palette_sha256', '0' * 64), ('source_kind', 'synthetic')):
            source = self.source()
            source[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(source)
        for change in ('failed_use', 'wrong_slot_enchant', 'wrong_tag_type', 'extra_case'):
            source = self.source()
            row = source['rows'][0]
            if change == 'failed_use':
                row['native_interaction_return'] = False
            elif change == 'wrong_slot_enchant':
                row['inventory_enchantments'] = []
            elif change == 'wrong_tag_type':
                row['cell_nbt'][0]['nbt']['Item']['tag']['ench'][0]['id']['__type__'] = 3
            else:
                source['rows'].append(copy.deepcopy(row))
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(source)

    def test_arbitrary_report_hash_and_forged_session_runtime_are_rejected(self):
        for value in ('0' * 64, 'f' * 64, 'q' * 64):
            source = self.source()
            source['source_sha256'] = value
            with self.subTest(hash=value), self.assertRaises(ValueError):
                validate(source)
        for field, value in (('native_runtime_version', '999.0.0'),
                             ('native_runtime_verified', True),
                             ('build_directory_version', 'future')):
            source = self.source()
            source['runtime_identity'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(source)

    def test_payload_object_binding_and_unrecorded_native_version_are_explicit(self):
        source = self.source()
        payload = (ROOT / source['source_report_file']).read_bytes()
        report = json.loads(payload)
        session = json.loads((ROOT / source['source_session_manifest_file']).read_bytes())
        self.assertEqual(source, snapshot(report, payload, session))
        self.assertIsNone(source['runtime_identity']['native_runtime_version'])
        self.assertFalse(source['runtime_identity']['native_runtime_verified'])
        self.assertFalse(source['runtime_identity']['executable_at_capture_verified'])
        changed = copy.deepcopy(report)
        changed['runtime_version'] = '999.0.0'
        with self.assertRaisesRegex(ValueError, 'original raw bytes'):
            snapshot(changed, payload, session)
        with self.assertRaisesRegex(ValueError, 'Unbound native runtime'):
            snapshot(changed, canonical(changed), session)
        session['native_runtime_version'] = '1.21.120.0'
        session['native_runtime_verified'] = True
        with self.assertRaisesRegex(ValueError, 'did not record'):
            snapshot(report, payload, session)

    def test_new_runtime_reads_require_the_frozen_same_run_manifest(self):
        source = self.source()
        report = json.loads((ROOT / source['source_report_file']).read_bytes())
        session = json.loads((ROOT / source['source_session_manifest_file']).read_bytes())
        version = '1.21.120.0'
        session['native_runtime_version'] = version
        session['native_runtime_verified'] = True
        report['native_runtime_versions'] = {'server': version, 'client': version}
        with self.assertRaisesRegex(ValueError, 'frozen run'):
            snapshot(report, canonical(report), session)
        fields = ('id', 'owner', 'session_file', 'game_executable', 'game_pid',
                  'game_identity', 'mcdk_pid', 'mcdk_identity')
        report['native_runtime_evidence'] = {
            'session': {key: session['session'][key] for key in fields},
            'manifest_sha256': 'd' * 64, 'manifest_hash_format': 'raw_file_bytes',
            'native_runtime_versions': report['native_runtime_versions']}
        session['in_run_manifest_sha256'] = 'e' * 64
        with self.assertRaisesRegex(ValueError, 'frozen run'):
            snapshot(report, canonical(report), session)
        session['in_run_manifest_sha256'] = 'd' * 64
        projected = snapshot(report, canonical(report), session)
        self.assertEqual(version, projected['runtime_identity']['native_runtime_version'])
        report['native_runtime_evidence']['session']['game_identity'] = 'foreign'
        with self.assertRaisesRegex(ValueError, 'frozen run'):
            snapshot(report, canonical(report), session)

    def test_frozen_report_session_and_startup_bytes_are_verified_on_every_check(self):
        from tempfile import TemporaryDirectory
        source = self.source()
        session = json.loads((ROOT / source['source_session_manifest_file']).read_bytes())
        paths = (source['source_report_file'], source['source_session_manifest_file'],
                 session['startup_log']['file'])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / name).read_bytes())
            validate(source, root=root)
            for name in paths:
                path = root / name
                original = path.read_bytes()
                with self.subTest(path=name):
                    if name.endswith('_session.json'):
                        changed = json.loads(original)
                        changed['session']['owner'] = 'foreign'
                        path.write_bytes(canonical(changed))
                    else:
                        path.write_bytes(original + b'\n')
                    with self.assertRaises(ValueError):
                        validate(source, root=root)
                    path.write_bytes(original)

    def test_changed_source_rows_and_escaping_source_paths_are_rejected(self):
        source = self.source()
        source['rows'][0]['cell_nbt'][0]['nbt']['FutureNativeField'] = {'unknown': 7}
        with self.assertRaisesRegex(ValueError, 'independent original evidence'):
            validate(source)
        source = self.source()
        source['source_report_file'] = '../outside.json'
        with self.assertRaisesRegex(ValueError, 'inside the repository'):
            validate(source)


if __name__ == '__main__':
    unittest.main()
