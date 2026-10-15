"""Guard native inventory restoration and keep incomplete source rules honest."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tests'))
import audit_intrinsic_glint_r21 as audit
import probe_intrinsic_glint_r21 as probe
from probe_intrinsic_glint_aux_r21 import requests as auxiliary_requests
from analyze_intrinsic_glint_ui_r21 import GLINT_COLOR, classify, glint_signature
from census_intrinsic_glint_ui_r21 import requests, resource_stop
from projection.item_sprite_plan import _contents, sprite_content, sprite_item
from projection.intrinsic_item_glint import CONFIRMED_PAIRS, item_glint
from projection.visible_item_contents import ContentSlot
from tests.test_static_frame_items import actor, frame


class NativeItems:
    def __init__(self, fail_name=None):
        self.inventory = [None] * 36
        self.inventory[0] = {'newItemName': 'minecraft:apple', 'count': 5, 'userData': {}}
        self.fail_name = fail_name

    def GetPlayerItem(self, kind, index, data):
        return copy.deepcopy(self.inventory[index])

    def SetInvItemNum(self, index, count):
        if count != 0:
            raise AssertionError('Probe may only clear its owned slot')
        self.inventory[index] = None
        return True

    def SpawnItemToPlayerInv(self, item, player, index):
        if item['itemName'] == self.fail_name:
            raise RuntimeError('injected native failure')
        self.inventory[index] = copy.deepcopy(item)
        return True

    def AddEnchantToInvItem(self, index, kind, level):
        self.inventory[index]['enchantData'] = [(kind, level)]
        return True

    def GetInvItemEnchantData(self, index):
        return self.inventory[index].get('enchantData', []) if self.inventory[index] else []


def native_modules(items):
    api = ModuleType('mod.server.extraServerApi')
    api.GetMinecraftVersion = lambda: '1.21.130.0'
    api.GetPlayerList = lambda: ['diagnostic-player']
    api.GetEngineCompFactory = lambda: SimpleNamespace(CreateItem=lambda player: items)
    api.GetMinecraftEnum = lambda: SimpleNamespace(ItemPosType=SimpleNamespace(INVENTORY=0))
    mod, server = ModuleType('mod'), ModuleType('mod.server')
    mod.server, server.extraServerApi = server, api
    return {'mod': mod, 'mod.server': server, 'mod.server.extraServerApi': api}


class NativeProbeTests(unittest.TestCase):
    def test_native_positive_control_and_all_inventory_slots_restore(self):
        items = NativeItems()
        before = copy.deepcopy(items.inventory)
        namespace = {'CASES': probe.CASES[:2]}
        with patch.dict(sys.modules, native_modules(items)):
            exec(probe.PROBE, namespace)
        report = json.loads(namespace['_result'])
        self.assertEqual(before, items.inventory)
        self.assertTrue(report['restored'])
        self.assertEqual([], report['rows'][0]['readback']['enchantData'])
        self.assertEqual([[9, 1]], report['rows'][1]['readback']['enchantData'])
        self.assertNotIn('isEnchanted', report['rows'][1]['readback'])
        self.assertEqual(35, report['slot'])

    def test_native_failure_still_clears_only_owned_slot(self):
        items = NativeItems(fail_name='minecraft:nether_star')
        before = copy.deepcopy(items.inventory)
        namespace = {'CASES': (('minecraft:apple', 0, False), ('minecraft:nether_star', 0, False))}
        with patch.dict(sys.modules, native_modules(items)):
            with self.assertRaisesRegex(RuntimeError, 'injected native failure'):
                exec(probe.PROBE, namespace)
        self.assertEqual(before, items.inventory)
        self.assertTrue(namespace['intrinsic_report']['restored'])

    def test_private_project_and_exact_engine_are_required(self):
        valid = {'project': str(ROOT / '.runtime/projects/test-glint'),
                 'game_executable': str(probe.ROOT / probe.VERSION / 'Minecraft.Windows.exe')}
        probe.validate_private_session(valid)
        for project in (ROOT, ROOT / '.runtime/projects', ROOT / '.runtime/projects-foreign/project'):
            with self.assertRaises(ValueError):
                probe.validate_private_session(dict(valid, project=str(project)))
        with self.assertRaises(ValueError):
            probe.validate_private_session(dict(valid, game_executable=str(ROOT / 'old/Minecraft.Windows.exe')))


class PublicCensusTests(unittest.TestCase):
    def test_new_positive_family_auxiliary_gaps_are_filled_without_repeating_observed_pairs(self):
        summary = {'pages': [{'rows': [
            {'name': 'minecraft:debug_stick', 'aux': 0,
             'classification': 'intrinsic_glint_native_confirmed'},
            {'name': 'minecraft:stick', 'aux': 0,
             'classification': 'no_intrinsic_glint_in_this_probe'}]}]}
        textures = {'rows': [{'name': name, 'aux': aux} for name in
                             ('minecraft:debug_stick', 'minecraft:stick') for aux in (0, 1, 15)]}
        self.assertEqual([('minecraft:debug_stick', 1, False),
                          ('minecraft:debug_stick', 15, False)], auxiliary_requests(summary, textures))

    def test_restored_page_resource_budget_stops_before_low_commit_or_high_handles(self):
        live = {'status': 'live', 'handle_count': 199999}
        enough = {'commit_available_bytes': 3 * 1024 ** 3}
        self.assertIsNone(resource_stop(live, enough, 200000, 3.))
        self.assertEqual('system_commit_budget', resource_stop(
            live, {'commit_available_bytes': enough['commit_available_bytes'] - 1}, 200000, 3.))
        self.assertEqual('owned_game_handle_budget', resource_stop(
            dict(live, handle_count=200000), enough, 200000, 3.))
        self.assertEqual('owned_game_handle_budget', resource_stop(
            {'status': 'exited'}, enough, 200000, 3.))

    def test_all_ids_remain_unknown_without_public_item_rule(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / 'data'
            definitions = data / 'behavior_packs/vanilla/items'
            definitions.mkdir(parents=True)
            (data / 'resource_packs/vanilla/entity').mkdir(parents=True)
            (definitions / 'golden_apple.json').write_text(json.dumps({'minecraft:item': {
                'description': {'identifier': 'minecraft:golden_apple'},
                'components': {'minecraft:foil': False}}}), encoding='utf8')
            (data / 'resource_packs/vanilla/entity/experience_bottle.entity.json').write_text(
                json.dumps({'minecraft:client_entity': {'description': {
                    'identifier': 'minecraft:xp_bottle', 'materials': {'default': 'xp_bottle_glint'}}}}),
                encoding='utf8')
            basic = {'engine_version': audit.VERSION, 'completed': True,
                     'rows': [{'name': name, 'aux': 0, 'value': {}} for name in
                              ('minecraft:golden_apple', 'minecraft:nether_star', 'minecraft:experience_bottle')]}
            catalog = {'engine_version': audit.VERSION, 'items': [],
                       'source_basic_catalog_sha256': hashlib.sha256(
                           (json.dumps(basic, indent=2, ensure_ascii=True) + '\n').encode('ascii')).hexdigest()}
            basic_path, catalog_path = root / 'basic.json', root / 'catalog.json'
            basic_path.write_text(json.dumps(basic), encoding='utf8')
            catalog_path.write_text(json.dumps(catalog), encoding='utf8')
            report = audit.build(root, basic_path, catalog_path)
        self.assertEqual(3, report['coverage']['loaded_ids'])
        self.assertFalse(report['full_intrinsic_glint_census_complete'])
        statuses = {row['name']: row['classification'] for row in report['rows']}
        self.assertEqual('public_definition_false', statuses['minecraft:golden_apple'])
        self.assertEqual('native_item_rule_unresolved', statuses['minecraft:nether_star'])
        self.assertEqual('native_item_rule_unresolved', statuses['minecraft:experience_bottle'])
        self.assertEqual('entity', report['render_glint_branches'][0]['asset_scope'])

    def test_auxiliary_zero_is_exhaustive_and_variant_limits_are_explicit(self):
        basic = {'engine_version': audit.VERSION, 'completed': True,
                 'rows': [{'name': name} for name in ('minecraft:apple', 'minecraft:potion')]}
        textures = {'engine_version': audit.VERSION, 'completed': True,
                    'rows': [{'name': 'minecraft:potion', 'aux': aux, 'texture': texture}
                             for aux, texture in ((0, 'water'), (1, 'water'), (5, 'healing'), (6, ''))]}
        self.assertEqual([('minecraft:apple', 0, False), ('minecraft:potion', 0, False)],
                         requests(basic, textures, False))
        self.assertEqual([('minecraft:apple', 0, False), ('minecraft:potion', 0, False),
                          ('minecraft:potion', 5, False)], requests(basic, textures, True))

    def test_known_rule_candidates_cover_equal_texture_auxiliary_values(self):
        basic = {'engine_version': audit.VERSION, 'completed': True,
                 'rows': [{'name': 'minecraft:nether_star'}]}
        textures = {'engine_version': audit.VERSION, 'completed': True,
                    'rows': [{'name': 'minecraft:nether_star', 'aux': aux, 'texture': 'same'}
                             for aux in (0, 1, 15)]}
        self.assertEqual([('minecraft:nether_star', aux, False) for aux in (0, 1, 15)],
                         requests(basic, textures, True))


class NativeGlintSignatureTests(unittest.TestCase):
    def test_indicator_motion_needs_all_three_same_phase_glint_pairs_for_a_negative(self):
        row = {'name': 'minecraft:recovery_compass', 'native_set_succeeded': True,
               'unforced_glint_signature': {'detected': False, 'matching_samples': 0},
               'forced_glint_signature': {'detected': True},
               'unforced_temporal_deltas': {'changed_over_3': 2000},
               'paired_glint_signatures': [{'detected': True} for unused in range(3)]}
        self.assertEqual('no_intrinsic_glint_in_this_probe', classify(row)[0])
        row['paired_glint_signatures'][1]['detected'] = False
        self.assertEqual('unresolved', classify(row)[0])
        row['paired_glint_signatures'][1]['detected'] = True
        row['unforced_glint_signature']['matching_samples'] = 1
        self.assertEqual('unresolved', classify(row)[0])
        row['unforced_glint_signature']['detected'] = True
        self.assertEqual('intrinsic_glint_native_confirmed', classify(row)[0])
        row['unforced_glint_signature'] = {'detected': False, 'matching_samples': 0}
        row['paired_glint_signatures'] = []
        self.assertEqual('unresolved', classify(row)[0])

    def test_purple_glint_passes_while_dynamic_needle_motion_does_not(self):
        base = np.full((16, 16, 3), 90, dtype=np.int16)
        glint = np.round(base + GLINT_COLOR * 50).astype(np.int16)
        signature = glint_signature([base, glint, base])
        self.assertTrue(signature['detected'])
        self.assertEqual(512, signature['matching_samples'])
        needle = base.copy()
        needle[:, :8] += (40, 100, 45)
        self.assertFalse(glint_signature([base, needle, base])['detected'])
        self.assertFalse(glint_signature([base, base, base])['detected'])


class PerItemQualificationTests(unittest.TestCase):
    def test_indicators_never_iterate_or_read_tracking_metadata_and_unknown_aux_stays_rejected(self):
        class UnreadMetadata:
            def __iter__(self):
                raise AssertionError('Indicator metadata must stay opaque')

            def __getitem__(self, key):
                raise AssertionError('Indicator targets must never be read')

            def get(self, key, default=None):
                raise AssertionError('Indicator targets must never be read')

        for name in ('minecraft:clock', 'minecraft:compass',
                     'minecraft:lodestone_compass', 'minecraft:recovery_compass'):
            item = {'newItemName': name, 'newAuxValue': 0, 'isEnchanted': False,
                    'userData': UnreadMetadata()}
            profiles = {(name, 0): {}}
            self.assertEqual((name, 0), sprite_item(item, profiles))
            self.assertEqual(name == 'minecraft:lodestone_compass', item_glint(item))
            item['isEnchanted'] = True
            self.assertTrue(item_glint(item))
            item['newAuxValue'] = 65535
            self.assertIsNone(sprite_item(item, profiles))

    def test_frame_only_geometry_cannot_leak_into_shelf_or_campfire(self):
        item = {'newItemName': 'minecraft:stone', 'newAuxValue': 0,
                'isEnchanted': False, 'userData': {}}
        profiles = {('minecraft:stone', 0): {'content_families': ('frame',)}}
        self.assertEqual(('minecraft:stone', 0), sprite_item(item, profiles))
        self.assertIsNone(sprite_item(item, profiles, 'shelf'))
        self.assertIsNone(sprite_item(item, profiles, 'campfire'))

    def test_artificial_enchantment_on_quartz_is_allowed_without_changing_item_data(self):
        item = {'newItemName': 'minecraft:quartz_block', 'newAuxValue': 0,
                'isEnchanted': True, 'userData': {'ench': []}}
        saved = copy.deepcopy(item)
        profiles = {('minecraft:quartz_block', 0): {'supports_enchantment': False}}
        self.assertEqual(('minecraft:quartz_block', 0), sprite_item(item, profiles))
        self.assertTrue(item_glint(item))
        self.assertEqual(saved, item)

    def test_intrinsic_glint_never_rewrites_actual_enchantment_or_reads_indicator_nbt(self):
        for name, aux in CONFIRMED_PAIRS:
            item = {'newItemName': name, 'newAuxValue': aux, 'isEnchanted': False,
                    'userData': {'not_inspected': object()}}
            before = dict(item)
            self.assertTrue(item_glint(item))
            self.assertEqual(before, item)
            self.assertFalse(item['isEnchanted'])
        self.assertFalse(item_glint({'newItemName': 'minecraft:nether_star', 'newAuxValue': 1,
                                    'isEnchanted': False}))

    def test_intrinsic_glint_reaches_frame_shelf_and_campfire_uniform_inputs(self):
        key = ('minecraft:nether_star', 0)
        profile = SimpleNamespace(items={key: {}}, engine_version=audit.VERSION,
                                  content_families=('frame', 'shelf', 'campfire'))
        nbt = actor(item=key[0])
        before = copy.deepcopy(nbt)
        self.assertTrue(sprite_content(frame(), nbt, profile.items)[3])
        item = {'newItemName': key[0], 'newAuxValue': 0, 'isEnchanted': False, 'userData': {}}
        for family in ('shelf', 'campfire'):
            with patch('projection.visible_item_contents.content_slots',
                       return_value=(ContentSlot(family, 0, item, 'south'),)):
                result = _contents(('minecraft:oak_shelf', 0), None, profile)
            self.assertTrue(result[0][3])
        self.assertEqual(before, nbt)
        self.assertFalse(item['isEnchanted'])


if __name__ == '__main__':
    unittest.main()
