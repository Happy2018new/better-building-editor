"""Native source/flow distinctions and complete-cell editing regressions."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, actor_data, background, edit_cell, foreground, make_cell
from projection.model import Document, Editor
from projection.sharing_codec import decode_steps, encode_steps
from projection.water_interactions import accepts_source, is_source, source_state
from projection.water_interaction_data import SOURCE_STATE_CHANGES, WATER_SENSITIVE_BLOCKS
from projection import water_interaction_data

spec = importlib.util.spec_from_file_location('water_generator', ROOT / 'tools/generate_water_interactions.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def material(name, **properties):
    name = 'minecraft:' + name
    original = (name, registry.DEFAULT_AUX[name])
    wanted = registry.states(original)
    wanted.update(properties)
    result = registry.from_states(name, wanted)
    if result is None:
        raise AssertionError((name, wanted))
    return result


class WaterInteractionTests(unittest.TestCase):
    def test_stale_interaction_tables_refuse_auto_edit_and_preserve_strict_snapshots(self):
        lit = material('campfire', extinguished=False)
        water = material('water')
        for field, value in (('SCHEMA_VERSION', 99), ('SOURCE_VERSION', 'NEMC future'),
                             ('PALETTE_SHA256', '0' * 64)):
            with self.subTest(field=field), patch.object(water_interaction_data, field, value):
                with self.assertRaisesRegex(ValueError, 'regeneration'):
                    accepts_source(lit)
                with self.assertRaisesRegex(ValueError, 'regeneration'):
                    source_state(lit)
                with self.assertRaisesRegex(ValueError, 'regeneration'):
                    edit_cell(lit, water, 2)
                self.assertEqual(make_cell(lit, water), edit_cell(lit, water, 1))

    def test_depth_identifies_source_for_both_native_water_names(self):
        fence = material('oak_fence')
        for name in ('water', 'flowing_water'):
            for depth in range(16):
                water = material(name, liquid_depth=depth)
                self.assertEqual(depth == 0, is_source(water))
                for first, second in ((water, fence), (fence, water)):
                    expected = make_cell(fence, water) if depth == 0 else fence
                    self.assertEqual(expected, edit_cell(first, second, 2))
        self.assertFalse(is_source(fence))

    def test_every_observed_lit_state_extinguishes_without_losing_other_states(self):
        self.assertEqual(36, len(WATER_SENSITIVE_BLOCKS))
        self.assertEqual(93, len(SOURCE_STATE_CHANGES))
        water = material('water', liquid_depth=0)
        for name in WATER_SENSITIVE_BLOCKS:
            for aux in registry.aux_values(name):
                before = (name, aux)
                expected = registry.states(before)
                if 'lit' in expected:
                    expected['lit'] = False
                if 'extinguished' in expected:
                    expected['extinguished'] = True
                for first, second in ((before, water), (water, before)):
                    result = edit_cell(first, second, 2)
                    self.assertEqual(expected, registry.states(foreground(result)), (before, result))
                    self.assertEqual(water, background(result))

    def test_source_changes_preserve_actor_and_removing_water_does_not_relight(self):
        lit = material('campfire', extinguished=False)
        wet = material('campfire', extinguished=True)
        actor = {'nbt': {'Items': [{'Name': 'minecraft:cod'}]}, 'render': {'custom': 2}}
        cell = edit_cell(make_cell(lit, AIR, actor), material('water'), 2)
        self.assertEqual(actor, actor_data(cell))
        self.assertEqual(wet, foreground(cell))
        self.assertEqual(make_cell(wet, AIR, actor), edit_cell(cell, AIR, 1))
        # Repainting inside an existing wet cell also updates the visible state.
        self.assertEqual(wet, foreground(edit_cell(cell, lit, 2)))

    def test_strict_layers_and_loaded_snapshots_keep_lit_or_flowing_combinations(self):
        lit = material('white_candle', lit=True, candles=3)
        for depth in (0, 3, 8):
            water = material('water', liquid_depth=depth)
            expected = make_cell(lit, water)
            self.assertEqual(expected, edit_cell(lit, water, 1))
            self.assertEqual(expected, edit_cell(make_cell(AIR, water), lit, 0))
            document = Document((2, 2, 2), {(1, 1, 1): expected})
            self.assertEqual(document.blocks, Document.from_data(document.to_data()).blocks)
            text = list(encode_steps(document))[-1]['text']
            self.assertEqual(expected, list(decode_steps(text))[-1]['document'].get((1, 1, 1)))

    def test_source_destroyed_plants_do_not_become_automatic_wet_snapshots(self):
        water = material('water')
        for name in ('cocoa', 'leaf_litter', 'pink_petals', 'snow_layer', 'wildflowers', 'hanging_roots'):
            plant = material(name)
            self.assertFalse(accepts_source(plant), name)
            self.assertEqual(water, edit_cell(plant, water, 2))
            self.assertEqual(plant, edit_cell(water, plant, 2))
            self.assertEqual(make_cell(plant, water), edit_cell(plant, water, 1))

    def test_extinguish_is_one_undoable_edit_and_share_preserves_it(self):
        pos = (1, 1, 1)
        lit = material('blue_candle', lit=True, candles=2)
        editor = Editor(Document((4, 4, 4), {pos: lit}))
        editor.edit_layer = 2
        editor.material = material('water')
        editor.paint_at(pos, respect_selection=False)
        expected = editor.document.get(pos)
        self.assertFalse(registry.states(foreground(expected))['lit'])
        editor.undo()
        self.assertEqual(lit, editor.document.get(pos))
        editor.redo()
        self.assertEqual(expected, editor.document.get(pos))
        text = list(encode_steps(editor.document))[-1]['text']
        self.assertEqual(expected, list(decode_steps(text))[-1]['document'].get(pos))

    def test_generated_data_matches_sources_and_rejects_missing_state(self):
        generator.generate(check=True)
        manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        palette = json.loads((ROOT / manifest['source_file']).read_text(encoding='utf8'))
        suffix = '_nemc_' + manifest['game_version'].split()[-1] + '.json'
        def data(name):
            return json.loads((ROOT / 'tools/data' / ('native_water_' + name + suffix)).read_text(encoding='utf8'))
        extinguish, stability, water = data('extinguish'), data('source_stability'), data('overlays')
        incomplete = copy.deepcopy(extinguish)
        incomplete['rows'].pop()
        with self.assertRaisesRegex(ValueError, 'coverage'):
            generator.rules(palette, water, incomplete, stability)
        invalid = copy.deepcopy(extinguish)
        invalid['rows'][0]['dry_valid'] = False
        with self.assertRaisesRegex(ValueError, 'dry seed'):
            generator.rules(palette, water, invalid, stability)

    def test_public_blueprint_metadata_resolves_dry_source_and_flow_cells(self):
        from projection.debug_blueprints import build, entries, VISUAL_CASES
        from projection.debug_water_blueprints import dry_state
        case = VISUAL_CASES['water_behaviors']
        document = build(case['fixture'])
        self.assertIn(case['fixture'], {row[0] for row in entries('layers')})
        self.assertEqual(47, len(case['cells']))
        for row in case['cells']:
            dry = dry_state(row['name'])
            self.assertEqual(dry, foreground(document.get(row['dry'])))
            source = document.get(row['source'])
            self.assertEqual(edit_cell(dry, material('water'), 2),
                             make_cell(foreground(source), background(source)))
            self.assertEqual(dry, foreground(document.get(row['flow'])))
            self.assertEqual(AIR, background(document.get(row['flow'])))


if __name__ == '__main__':
    unittest.main()
