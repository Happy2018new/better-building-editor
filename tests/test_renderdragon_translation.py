"""Regression checks for the offline translator; not runtime parity tests."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools/renderdragon'
sys.path.insert(0, str(TOOLS))
from material_inventory import MaterialLibrary, merge_material, read_jsonc
from spirv_interface import Module, normalize_interfaces
from translate_all import check_pair, plan_jobs


def fixture_spirv(names, storage):
    words = [0x07230203, 0x00010000, 0, 100, 0]
    for variable, (name, location) in enumerate(names, 1):
        value = name.encode() + b'\0'
        value += b'\0' * (-len(value) % 4)
        encoded = list(struct.unpack('<%dI' % (len(value) // 4), value))
        words += [((2 + len(encoded)) << 16) | 5, variable] + encoded
        words += [(4 << 16) | 59, 90, variable, storage]
        words += [(4 << 16) | 71, variable, 30, location]
    return struct.pack('<%dI' % len(words), *words)


class RenderDragonTranslationTests(unittest.TestCase):
    def test_json_comments_do_not_corrupt_literal_strings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'material.json'
            path.write_text('{/* comment */"url":"https://example.com/a",'
                            '"literal":",} // not a comment", // comment\n'
                            '"values":[1,2,],}', encoding='utf8')
            self.assertEqual({'url': 'https://example.com/a',
                              'literal': ',} // not a comment', 'values': [1, 2]},
                             read_jsonc(path))

    def test_overlay_retains_parent_and_updates_inheriting_children(self):
        with tempfile.TemporaryDirectory() as temp:
            base, project = Path(temp) / 'base', Path(temp) / 'project'
            base.write_text(json.dumps({'materials': {
                'root': {'vertexShader': 'native', '+defines': ['LOW_PRECISION'],
                         '+states': ['DisableAlphaWrite']},
                'alpha:root': {'+defines': ['ALPHA_TEST']},
                'blend:alpha': {'+defines': ['BLEND'], '+states': ['Blending']},
            }}))
            project.write_text(json.dumps({'materials': {
                'root': {'vertexShader': 'custom'},
                'alpha': {'+defines': ['SEASONS']},
            }}))
            library = MaterialLibrary()
            library.add(base)
            library.add(project)
            material = library.resolve('blend')
            self.assertEqual('custom', material['vertexShader'])
            self.assertEqual(['LOW_PRECISION', 'ALPHA_TEST', 'SEASONS', 'BLEND'], material['defines'])
            self.assertEqual(['DisableAlphaWrite', 'Blending'], material['states'])

    def test_sampler_overrides_and_additive_glow_preserve_state(self):
        source = {'states': ['Blending', 'DisableCulling'],
                  'blendDst': 'OneMinusSrcAlpha',
                  'samplerStates': [{'samplerIndex': 0, 'textureFilter': 'Point'}]}
        material = merge_material(source, {'+states': ['DisableDepthWrite'],
                    'blendDst': 'One', '+samplerStates': [{'samplerIndex': 0, 'textureWrap': 'Repeat'}]})
        self.assertEqual('One', material['blendDst'])
        self.assertEqual(['Blending', 'DisableCulling', 'DisableDepthWrite'], material['states'])
        self.assertEqual([{'samplerIndex': 0, 'textureFilter': 'Point', 'textureWrap': 'Repeat'}],
                         material['samplerStates'])
        self.assertNotIn('DisableDepthWrite', source['states'])

    def test_cycle_fails_instead_of_silently_dropping_materials(self):
        library = MaterialLibrary()
        library.nodes = {'a': {'parent': 'b', 'patches': []},
                         'b': {'parent': 'a', 'patches': []}}
        with self.assertRaisesRegex(ValueError, 'cycle'):
            library.resolve('a')

    def test_varying_locations_match_despite_unused_engine_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            vertex, fragment = Path(temp) / 'v.spv', Path(temp) / 'f.spv'
            vertex.write_bytes(fixture_spirv([('uv', 0), ('skyRay', 1), ('gemNormal', 2)], 3))
            fragment.write_bytes(fixture_spirv([('skyRay', 0), ('gemNormal', 1)], 1))
            normalize_interfaces(vertex, fragment)
            left, right = Module(vertex.read_bytes()), Module(fragment.read_bytes())
            for name in ('skyRay', 'gemNormal'):
                a, b = left.located_variables(3)[name], right.located_variables(1)[name]
                self.assertEqual(left.words[left.decorations[a, 30]], right.words[right.decorations[b, 30]])

    def test_missing_varying_is_rejected_without_mutating_files(self):
        with tempfile.TemporaryDirectory() as temp:
            vertex, fragment = Path(temp) / 'v.spv', Path(temp) / 'f.spv'
            original = fixture_spirv([('skyRay', 0)], 3)
            vertex.write_bytes(original)
            fragment.write_bytes(fixture_spirv([('gemNormal', 0)], 1))
            with self.assertRaisesRegex(ValueError, 'missing'):
                normalize_interfaces(vertex, fragment)
            self.assertEqual(original, vertex.read_bytes())

    def test_type_mismatch_is_not_a_valid_pair(self):
        with self.assertRaisesRegex(ValueError, 'Mismatched varying'):
            check_pair({'outputs': [{'name': 'normal', 'type': 'vec3', 'location': 0}]},
                       {'inputs': [{'name': 'normal', 'type': 'vec4', 'location': 0}]})

    def test_skinning_and_quality_are_compiled_without_dropping_original_defines(self):
        record = {'pack': 'resource_pack', 'material': 'gem', 'variant': 'skinning',
                  'vertex': 'staff.vertex', 'fragment': 'staff.fragment',
                  'defines': ['USE_SKINNING', 'STAFF_VIOLET']}
        jobs = plan_jobs([record, dict(record, material='another_material')])
        self.assertEqual(9, len(jobs))
        for job in jobs:
            self.assertIn('USE_SKINNING', job['defines'])
            self.assertIn('STAFF_VIOLET', job['defines'])
            self.assertEqual(2, len(job['uses']))
        self.assertTrue(any('NETEASE_SKINNING' in j['defines'] for j in jobs))
        self.assertTrue(any('LARGE_VERTEX_SHADER_UNIFORMS' in j['defines'] for j in jobs))
        self.assertTrue(any('TEXEL_AA_FEATURE' in j['defines'] for j in jobs))


if __name__ == '__main__':
    unittest.main()
