"""Version upgrade reports distinguish aux remapping from typed state changes."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from diff_block_palettes import compare, main, records


def row(name='minecraft:test', aux=0, states=()):
    return {'name': name, 'data': aux,
            'states': [{'name': key, 'type': kind, 'value': value} for key, kind, value in states]}


class PaletteDiffTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.old = Path(self.directory.name) / 'nemc_old.json'
        self.new = Path(self.directory.name) / 'nemc_new.json'

    def dump(self, path, rows):
        path.write_text(json.dumps({'blocks': rows}), encoding='utf8')

    def test_aux_swap_does_not_invent_semantic_additions_or_deletions(self):
        north, east = [('direction', 'int', 2)], [('direction', 'int', 3)]
        self.dump(self.old, [row(aux=0, states=north), row(aux=1, states=east)])
        self.dump(self.new, [row(aux=1, states=north), row(aux=0, states=east)])
        result = compare(self.old, self.new)
        self.assertEqual(2, result['changed_records'])
        self.assertFalse(result['added_semantic_states'])
        self.assertFalse(result['removed_semantic_states'])
        self.assertEqual([([0], [1]), ([1], [0])],
                         [(entry['old_data'], entry['new_data']) for entry in result['remapped_semantic_states']])

    def test_native_byte_and_int_are_different_semantics(self):
        self.dump(self.old, [row(states=[('lit', 'byte', 1)])])
        self.dump(self.new, [row(states=[('lit', 'int', 1)])])
        result = compare(self.old, self.new)
        self.assertEqual(1, len(result['added_semantic_states']))
        self.assertEqual(1, len(result['removed_semantic_states']))
        self.assertFalse(result['remapped_semantic_states'])
        self.assertFalse(result['added_state_keys'])

    def test_name_state_schema_and_alternative_aux_changes_are_visible(self):
        self.dump(self.old, [row('minecraft:removed'), row('minecraft:retained', 0)])
        self.dump(self.new, [row('minecraft:added', states=[('new_direction', 'string', 'east')]),
                             row('minecraft:retained', 0), row('minecraft:retained', 3)])
        result = compare(self.old, self.new)
        self.assertEqual(['minecraft:added'], result['added_names'])
        self.assertEqual(['minecraft:removed'], result['removed_names'])
        self.assertEqual(['new_direction'], result['added_state_keys'])
        self.assertEqual([0, 3], result['remapped_semantic_states'][0]['new_data'])

    def test_record_and_property_order_are_irrelevant_but_source_hash_is_exact(self):
        rows = [row(aux=1, states=[('a', 'byte', 1), ('b', 'string', 'north')]), row(aux=2)]
        self.dump(self.old, rows)
        changed = copy.deepcopy(rows[::-1])
        changed[1]['states'].reverse()
        changed[1]['states'][1]['value'] = True
        self.dump(self.new, changed)
        result = compare(self.old, self.new)
        self.assertEqual(0, result['changed_records'])
        self.assertFalse(result['remapped_semantic_states'])
        self.assertNotEqual(result['old_sha256'], result['new_sha256'])

    def test_duplicate_or_malformed_records_never_silently_overwrite_dump_entries(self):
        invalid = ([row(), row()], [row(states=[('a', 'int', 1), ('a', 'int', 2)])],
                   [row(states=[('a', 'int', True)])], [row(states=[('a', 'byte', 2)])],
                   [row(states=[('a', 'unknown', 0)])], [row(aux=True)])
        for rows in invalid:
            with self.subTest(rows=rows):
                self.dump(self.old, rows)
                with self.assertRaises(ValueError):
                    records(self.old)

    def test_source_dumps_cannot_be_overwritten_by_report(self):
        self.dump(self.old, [row()])
        self.dump(self.new, [row(aux=1)])
        before = self.old.read_bytes(), self.new.read_bytes()
        for output in (self.old, self.new):
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                main(self.old, self.new, output)
            self.assertEqual(before, (self.old.read_bytes(), self.new.read_bytes()))

    def test_current_dump_has_zero_semantic_changes_against_itself(self):
        path = ROOT / 'docs/reference/block_palettes/nemc_3.9.0.401155.json'
        result = compare(path, path)
        self.assertEqual(15858, result['old_records'])
        self.assertEqual(0, result['changed_records'])
        self.assertFalse(result['added_semantic_states'])
        self.assertFalse(result['removed_semantic_states'])
        self.assertFalse(result['remapped_semantic_states'])
