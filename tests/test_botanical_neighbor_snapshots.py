"""Saved chain snapshots remain local edits and keep occupancy-hidden neighbors."""
import copy
import json
import subprocess
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, background, foreground
from projection.debug_blueprints import build, entries, material
from projection.debug_botanical_blueprints import VISUAL_CASE, source_document
from projection.model import Editor, close_group_selection
from projection.render_context import prepare_document_context
from projection.render_layout import context_position


class BotanicalNeighborSnapshotTests(unittest.TestCase):
    def test_public_cases_are_disjoint_legal_snapshots_and_keep_declared_water(self):
        document = build(VISUAL_CASE['fixture'])
        self.assertIn(VISUAL_CASE['fixture'], {row[0] for row in entries('connections')})
        self.assertEqual(13, len(VISUAL_CASE['cases']))
        positions = set()
        names = set()
        for row in VISUAL_CASE['cases']:
            declared = row['supports'] + row['blocks']
            current = {pos for pos, name, states in declared}
            self.assertFalse(positions & current)
            positions.update(current)
            self.assertEqual(len(declared), len(current))
            for pos, name, states in declared:
                names.add(name)
                cell = document.get(pos)
                self.assertTrue(document.contains(pos))
                self.assertEqual(material(name, states), foreground(cell))
                self.assertEqual(material('water') if pos in row['water'] else AIR, background(cell))
                self.assertEqual(foreground(cell), registry.canonical(foreground(cell)))
            self.assertIn(row['keep'], row['cells'])
            self.assertIn(row['occupied'], row['cells'])
        self.assertTrue({'bamboo', 'cactus', 'cactus_flower', 'kelp', 'reeds', 'chorus_flower',
                         'trip_wire', 'tripwire_hook', 'cave_vines_head_with_berries',
                         'cave_vines_body_with_berries'} <= names)
        self.assertEqual({'pending'}, set(VISUAL_CASE['acceptance'].values()))

    def test_erasing_one_chain_cell_keeps_unselected_snapshot_parts_and_one_undo(self):
        for row in VISUAL_CASE['cases']:
            with self.subTest(case=row['id']):
                source = source_document(row['id'])
                editor = Editor(source)
                selected = row['keep']
                self.assertEqual({selected}, set(close_group_selection(source, [selected])))
                before = source.blocks.copy()
                editor.paint_at(selected, erase=True, respect_selection=False)
                for pos, cell in before.items():
                    if pos != selected:
                        self.assertEqual(cell, editor.document.get(pos))
                self.assertEqual(1, len(editor.undo_stack))
                editor.undo()
                self.assertEqual(before, editor.document.blocks)

    def test_partial_projection_retains_original_hidden_neighbor_and_both_layers(self):
        for row in VISUAL_CASE['cases']:
            with self.subTest(case=row['id']):
                source = source_document(row['id'])
                saved = copy.deepcopy(source.to_data())
                keep, occupied = row['keep'], row['occupied']
                self.assertTrue(all(abs(occupied[i] - keep[i]) <= 1 for i in range(3)))
                result = prepare_document_context(source, source.palette_data(lambda pos: pos == keep))
                neighbor = tuple(occupied[i] - keep[i] for i in range(3))
                encoded = context_position(keep, neighbor)
                z_size, x_size, y_size = result['volume']
                index = (encoded[1] * x_size + encoded[0]) * z_size + encoded[2]
                original = source.get(occupied)
                self.assertIn(index, result['common'][foreground(original)])
                if background(original) != AIR:
                    self.assertIn(index, result['extra'][background(original)])
                self.assertEqual(saved, source.to_data())

    def test_dry_native_wrapper_rejects_wet_cases_and_changed_public_source(self):
        script = '''import sys
sys.path.insert(0,'tools')
import verify_botanical_neighbor_world_visuals as botanical
from projection.debug_blueprints import material
from projection.debug_botanical_blueprints import VISUAL_CASE
assert botanical.world.world_case is botanical.source_suite.suite.static_world_case
assert len(botanical.DRY_CASES)==11
assert not {'kelp_wet_chain','reeds_water_support'}.intersection(botanical.world.CASES)
for row in VISUAL_CASE['cases']:
 delta=(7,85,-27)
 translate=lambda pos:tuple(pos[i]+delta[i] for i in range(3))
 cells=[(translate(pos),material(name,properties)) for pos,name,properties in row['blocks']]
 if row not in botanical.DRY_CASES:
  try:botanical.supports(cells)
  except ValueError:pass
  else:raise AssertionError('Wet source accepted as dry')
  continue
 expected=[(translate(pos),material(name,properties)) for pos,name,properties in row['supports']]
 assert botanical.supports(cells)==expected,row
 changed=list(cells)
 changed[0]=(changed[0][0],('minecraft:air',0))
 try:botanical.supports(changed)
 except ValueError:pass
 else:raise AssertionError('Changed public source accepted')
'''
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', script], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_public_botanical_blueprint_compiles_under_game_python2(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Local game-compatible Python 2 interpreter is unavailable')
        source = (ROOT / 'behavior_pack/modern_projection/projection/debug_botanical_blueprints.py').read_bytes()
        result = subprocess.run([str(pypy), '-c', 'compile(%r,"blueprint","exec")' % source],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_frozen_native_dry_report_keeps_failures_and_original_source(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        from verify_botanical_snapshots_native import compare, plans
        report = json.loads((ROOT / 'tools/data/native_botanical_snapshots_r11_nemc_3.9.0.401155.json').read_bytes())
        before = copy.deepcopy(report)
        replay = compare(report, plans())
        self.assertEqual(report['comparison'], json.loads(json.dumps(replay)))
        self.assertEqual(before, report)
        self.assertFalse(replay['all_matched'])
        self.assertEqual({'vine_sides', 'chorus_branch', 'tripwire_short', 'tripwire_cross_chunk_long'},
                         {row['case'] for row in replay['cases'] if row['source_matches_native'] and row['stable']})
        self.assertEqual({'pending'}, set(report['acceptance'].values()))
        self.assertEqual(266, report['cleanup']['reserved_air'])
        for changed in ('restore', 'runtime', 'write'):
            value = copy.deepcopy(report)
            if changed == 'restore':
                value['restored'] = False
            elif changed == 'runtime':
                value['start']['runtime'] = 'other'
            else:
                value['native']['rows'][0]['writes'][0]['value'] = ['minecraft:stone', 0]
            with self.subTest(change=changed), self.assertRaises(ValueError):
                compare(value, plans())


if __name__ == '__main__':
    unittest.main()
