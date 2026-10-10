"""Native default generation verifies provenance and preserves typed payloads."""
import base64
import copy
import json
from pathlib import Path
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from generate_entity_blueprints import field_audit, generate_text
from projection import block_registry as registry
from projection.cell import thaw


class EntityBlueprintGeneratorTests(unittest.TestCase):
    def source(self):
        return {'schema': 1, 'game_version': registry.source_version(),
                'palette_sha256': registry.fingerprint(), 'method': 'native test capture',
                'block_entities': {'minecraft:chest': {
                    'aux': registry.DEFAULT_AUX['minecraft:chest'],
                    'nbt': {'__type__': 10, '__value__': {
                        'id': {'__type__': 8, '__value__': 'Chest'},
                        'x': {'__type__': 3, '__value__': 104},
                        'y': {'__type__': 3, '__value__': 64},
                        'z': {'__type__': 3, '__value__': -12},
                        'Items': {'__type__': 9, '__value__': []},
                        'unknown': {'__type__': 1, '__value__': 7}}}}}}

    def test_generation_is_deterministic_and_lossless(self):
        source = self.source()
        before = copy.deepcopy(source)
        generated = generate_text(source, 'evidence-hash')
        namespace = {}
        exec(compile(generated, '<native defaults>', 'exec'), namespace)
        packed = namespace['DEFAULTS']['minecraft:chest']
        aux, tree = json.loads(zlib.decompress(base64.b64decode(packed)))
        self.assertEqual(source['block_entities']['minecraft:chest']['aux'], aux)
        self.assertEqual(source['block_entities']['minecraft:chest']['nbt'], thaw(tree))
        self.assertEqual('evidence-hash', namespace['SOURCE_SHA256'])
        self.assertEqual(before, source)
        self.assertEqual(generated, generate_text(source, 'evidence-hash'))

    def test_field_audit_records_actual_types_without_claiming_numeric_ids(self):
        report = field_audit(self.source())
        fields = report['entities']['Chest']['root_fields']
        self.assertEqual([8], fields['id']['sdk_tag_types'])
        self.assertEqual([3], fields['x']['sdk_tag_types'])
        self.assertEqual(['list'], fields['Items']['python_types'])
        self.assertNotIn('enum_id', report['entities']['Chest'])

    def test_version_identity_state_and_coordinates_are_checked(self):
        for key, value in (('schema', 2), ('game_version', 'future'),
                           ('palette_sha256', '0' * 64), ('block_entities', [])):
            data = self.source()
            data[key] = value
            with self.assertRaises(ValueError):
                generate_text(data, 'hash')
        for mutate in ('aux', 'id', 'x', 'missing_name'):
            data = self.source()
            row = data['block_entities']['minecraft:chest']
            if mutate == 'aux':
                row['aux'] = 32767
            elif mutate == 'missing_name':
                data['block_entities']['minecraft:unknown_future_block'] = row
            else:
                row['nbt']['__value__'][mutate]['__value__'] = False
            with self.assertRaises(ValueError):
                generate_text(data, 'hash')


if __name__ == '__main__':
    unittest.main()
