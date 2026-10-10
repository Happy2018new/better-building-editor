"""Native material descendants retain flags and reject stale source coverage."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from generate_liquid_materials import (BASE, FRAGMENT, VERTEX, adapted_materials,
                                       checked_descendants, liquid_descendants, snapshot)

RAW = b'''{"materials":{"version":"1.0.0",
  "netease_block_as_entity_mesh":{},
  "netease_block_as_mesh_blend:netease_block_as_entity_mesh":{"+defines":["BLEND"]},
  // A new engine descendant must be adapted without adding a name to Python.
  "new_liquid:netease_block_as_mesh_blend":{"+defines":["FOG"]},
  "new_nested:new_liquid":{},"non_liquid:netease_block_as_entity_mesh":{}}}'''
MANIFEST = {'game_version': 'NEMC test', 'source_sha256': 'registry'}


class LiquidMaterialTests(unittest.TestCase):
    def test_new_nested_descendants_are_selected_without_ordinary_meshes(self):
        source = snapshot(RAW, MANIFEST)
        self.assertEqual([BASE, 'new_liquid', 'new_nested'], checked_descendants(source, MANIFEST))

    def test_native_flags_and_unrelated_bindings_are_preserved(self):
        current = {'version': '1.0.0', BASE: {'+defines': ['BLEND'], 'depthFunc': 'LessEqual'},
                   'non_liquid': {'fragmentShader': 'native'}}
        original = copy.deepcopy(current)
        adapted = adapted_materials(current, [BASE, 'new_liquid'])
        self.assertEqual(original, current)
        self.assertEqual(current['non_liquid'], adapted['non_liquid'])
        self.assertEqual(['BLEND'], adapted[BASE]['+defines'])
        self.assertEqual('LessEqual', adapted[BASE]['depthFunc'])
        for name in (BASE, 'new_liquid'):
            self.assertEqual(VERTEX, adapted[name]['vertexShader'])
            self.assertEqual(FRAGMENT, adapted[name]['fragmentShader'])
        self.assertEqual(adapted, adapted_materials(adapted, [BASE, 'new_liquid']))

    def test_source_content_version_and_descendant_tampering_are_rejected(self):
        source = snapshot(RAW, MANIFEST)
        for key, changed in (('native_text', '{}'), ('game_version', 'NEMC old'),
                             ('palette_sha256', 'old'), ('liquid_materials', [BASE])):
            altered = copy.deepcopy(source)
            altered[key] = changed
            with self.subTest(key=key), self.assertRaises(ValueError):
                checked_descendants(altered, MANIFEST)

    def test_missing_root_duplicate_identity_and_cycles_are_rejected(self):
        for values in ({}, {BASE: {}, BASE+':other': {}},
                       {BASE: {}, 'first:second': {}, 'second:first': {}}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                liquid_descendants(values)

    def test_duplicate_json5_keys_cannot_be_silently_replaced(self):
        with self.assertRaises(ValueError):
            snapshot(b'{"materials":{"version":"1","version":"2"}}', MANIFEST)


if __name__ == '__main__':
    unittest.main()
