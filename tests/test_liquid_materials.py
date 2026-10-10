"""Native material descendants retain flags and reject stale source coverage."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from generate_liquid_materials import (BASE, FRAGMENT, VERTEX, adapted_materials,
                                       checked_descendants, liquid_descendants, parse_native, snapshot)

RAW = b'''{"materials":{"version":"1.0.0",
  "netease_block_as_entity_mesh":{"+states":["DisableAlphaWrite"],
    "variants":[{"fog":{}},{"underwater":{}},{"fog.underwater":{}}]},
  "netease_block_as_mesh_blend:netease_block_as_entity_mesh":{"+defines":["BLEND"],
    "+states":["Blending"],"+variants":[{"underwater":{}},{"fog.underwater":{}}]},
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
        native = parse_native(RAW.decode('ascii'))
        native_original = copy.deepcopy(native)
        adapted = adapted_materials(current, [BASE, 'new_liquid'], native)
        self.assertEqual(original, current)
        self.assertEqual(native_original, native)
        self.assertEqual(current['non_liquid'], adapted['non_liquid'])
        blend = BASE + ':netease_block_as_entity_mesh'
        self.assertEqual(['BLEND'], adapted[blend]['+defines'])
        self.assertEqual('LessEqual', adapted[blend]['depthFunc'])
        for key in (blend, 'new_liquid:' + BASE):
            self.assertEqual(VERTEX, adapted[key]['vertexShader'])
            self.assertEqual(FRAGMENT, adapted[key]['fragmentShader'])
        self.assertNotIn(BASE, adapted)
        self.assertNotIn('new_liquid', adapted)
        self.assertEqual(native['netease_block_as_entity_mesh']['variants'],
                         adapted['netease_block_as_entity_mesh']['variants'])
        self.assertEqual(native[blend]['+variants'], adapted[blend]['+variants'])
        self.assertEqual(adapted, adapted_materials(adapted, [BASE, 'new_liquid'], native))

    def test_custom_additive_flags_extend_native_ancestors(self):
        native = parse_native(RAW.decode('ascii'))
        current = {'netease_block_as_entity_mesh': {'+states': ['Blending'],
                   'vertexShader': 'custom'}, BASE: {'+defines': ['CUSTOM', 'BLEND']}}
        result = adapted_materials(current, [BASE], native)
        ancestor = result['netease_block_as_entity_mesh']
        self.assertEqual(['DisableAlphaWrite', 'Blending'], ancestor['+states'])
        self.assertEqual('custom', ancestor['vertexShader'])
        self.assertEqual(['BLEND', 'CUSTOM'], result[BASE + ':netease_block_as_entity_mesh']['+defines'])

    def test_missing_ancestor_and_duplicate_override_are_rejected(self):
        native = {BASE + ':missing': {}}
        with self.assertRaises(ValueError):
            adapted_materials({}, [BASE], native)
        with self.assertRaises(ValueError):
            adapted_materials({BASE: {}, BASE + ':other': {}}, [BASE], parse_native(RAW.decode('ascii')))

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
