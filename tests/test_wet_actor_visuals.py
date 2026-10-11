"""Public wet actor scenes and pixel controls reject absent water or actors."""
import copy
import ast
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_wet_actor_visuals import CASES, component_checks, reserve_code, replication_code, replication, PALETTE_PROBE, wire_json, camera_side_platform, player_camera_side, NEAR_PLAYER, WetActorCheck, SignCheck
from projection.cell import AIR, actor_data, background, foreground, encode, decode
from projection.debug_blueprints import build, material
from projection.nbt_spatial import root_payload, scalar
from projection.visible_actor import entity_nbt, render_actor


class WetActorFixtureTests(unittest.TestCase):
    def test_repeated_public_fixture_captures_keep_distinct_case_names(self):
        check=object.__new__(WetActorCheck)
        with patch.object(SignCheck,'capture',return_value={'path':'frame.png'}) as capture:
            for label in ('pot_isolated','pot_adjacent_water','pot_fence_context'):
                check.capture_case=label
                check.capture('test_entities_pottery',{'tree':'fixture'})
            check.capture('pot_fence_context_side_world')
        labels=[call.args[1] for call in capture.call_args_list]
        self.assertEqual(['pot_isolated_test_entities_pottery',
                          'pot_adjacent_water_test_entities_pottery',
                          'pot_fence_context_test_entities_pottery',
                          'pot_fence_context_side_world'],labels)
        self.assertEqual({'tree':'fixture'},capture.call_args_list[0].args[2])

    def test_native_player_reference_rejects_the_opposite_camera_side(self):
        cells=[((4,136,6),None),((6,136,6),None)]
        camera={'position':(5.5,136.9,10.5),'target':(5.5,136.5,6.5)}
        self.assertFalse(player_camera_side((.5,136.,2.5),camera)['passed'])
        platform=camera_side_platform(cells,(0.,.4,4.))
        self.assertEqual((5,135,10),platform)
        player=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
        self.assertTrue(player_camera_side(player,camera)['passed'])
        compile(NEAR_PLAYER % (platform,),'<same-camera-side-player>','exec')
        camera['position']=(1.5,136.9,2.5)
        platform=camera_side_platform(cells,(-4.,.4,-4.))
        self.assertEqual((0,135,2),platform)
        self.assertTrue(player_camera_side((.5,136.,2.5),camera)['passed'])
        self.assertFalse(player_camera_side((.5,136.,2.5),
                                           {'position':(5.5,140.,6.5),'target':camera['target']})['passed'])
        planned={'position':(5.5,136.9,10.5),'target':(5.5,136.5,6.5),
                 'stable':{'position':(5.5,136.9,2.5)}}
        self.assertFalse(player_camera_side((5.5,136.,10.5),planned)['passed'])

    def test_native_code_decodes_complete_cells_from_json(self):
        metadata, scene = CASES['sign_isolated']
        doc = build(metadata['fixture'])
        cells = [(scene['actor'], encode(doc.get(scene['actor'])))]
        supports = [(scene['supports'][0], encode(doc.get(scene['supports'][0])))]
        for source, names in ((reserve_code(cells, supports, (0, 0, 0)), ('source', 'supports')),
                              (replication_code(cells), ('cells',)),
                              (PALETTE_PROBE % (wire_json(cells), False), ('cells',))):
            tree = ast.parse(source)
            assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                              and isinstance(node.targets[0], ast.Tuple)
                              and node.targets[0].elts[0].id == names[0])
            for index, name in enumerate(names):
                expression = assignment.value.elts[index]
                self.assertIsInstance(expression, ast.Call)
                self.assertEqual('loads', expression.func.attr)
                payload = ast.literal_eval(expression.args[0])
                self.assertTrue(payload.isascii())
                restored = json.loads(payload)
                expected = cells if name in ('source', 'cells') else supports
                for (pos, encoded), (wanted_pos, wanted) in zip(restored, expected):
                    self.assertEqual(tuple(pos), wanted_pos)
                    self.assertEqual(decode(encoded), decode(wanted))

    def test_unreplicated_palette_is_preserved_without_merging(self):
        probe = {'matches': False, 'layers_match': False, 'actors_match': False,
                 'cells': [], 'actor_mismatches': [{'actor_name': 'minecraft:water'}],
                 'raw_palette': ['dict', []]}
        calls = []

        class Check(object):
            def run(self, source):
                calls.append(source)
                return probe

            def wait(self, label, predicate, read):
                self.result = read()
                self.accepted = predicate(self.result)
                raise TimeoutError('native layer mismatch')

        check, diagnostics = Check(), {}
        with self.assertRaisesRegex(TimeoutError, 'native layer mismatch'):
            replication(check, [((0, 0, 0), ['minecraft:water', 0])], diagnostics=diagnostics)
        self.assertFalse(check.accepted)
        self.assertEqual(probe, diagnostics)
        self.assertEqual(1, len(calls))
        self.assertIn('SerializeBlockPalette', calls[0])
        self.assertNotIn('merge_palette(', calls[0])

    def test_public_scenes_have_complete_nbt_water_and_containment(self):
        self.assertEqual(6, len(CASES))
        for label, (metadata, scene) in CASES.items():
            with self.subTest(label=label):
                doc = build(metadata['fixture'])
                before = copy.deepcopy(doc.to_data())
                value = doc.get(scene['actor'])
                self.assertEqual(material('water'), background(value))
                self.assertEqual({}, render_actor(actor_data(value)))
                root = root_payload(entity_nbt(actor_data(value)))
                self.assertEqual(scene['actor'], tuple(scalar(root, axis) for axis in ('x', 'y', 'z')))
                keep = doc.get(scene['keep'])
                if scene['id'] == 'isolated':
                    self.assertEqual(AIR, background(keep))
                    self.assertIsNotNone(actor_data(keep))
                elif scene['id'] == 'adjacent_water':
                    self.assertEqual(material('water'), foreground(keep))
                else:
                    self.assertEqual(material('oak_fence'), foreground(keep))
                    self.assertEqual(material('water'), background(keep))
                self.assertFalse(set(scene['cells']) & set(scene['supports']))
                for pos in scene['cells'] + scene['supports']:
                    self.assertTrue(doc.contains(pos))
                    self.assertNotEqual(AIR, doc.get(pos))
                    self.assertEqual(doc.get(pos), decode(encode(doc.get(pos))))
                for pos in scene['supports']:
                    self.assertEqual(material('stone' if pos[1] == 0 else 'glass'), doc.get(pos))
                self.assertEqual(before, doc.to_data())

    def test_component_oracle_rejects_missing_water_and_missing_actor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native.png'
            baseline = Image.new('RGB', (100, 80))
            draw = ImageDraw.Draw(baseline)
            draw.rectangle((10, 10, 40, 65), fill=(20, 60, 170))
            draw.rectangle((55, 15, 85, 65), fill=(150, 100, 50))
            baseline.save(path)
            masks = (Image.new('L', baseline.size), Image.new('L', baseline.size))
            ImageDraw.Draw(masks[0]).rectangle((10, 10, 40, 65), fill=255)
            ImageDraw.Draw(masks[1]).rectangle((55, 15, 85, 65), fill=255)
            same = component_checks(baseline, baseline, masks, path, 16, 80)
            self.assertTrue(all(row['passed'] for row in same.values()))
            for name, box in (('water', (10, 10, 40, 65)), ('actor', (55, 15, 85, 65))):
                actual = baseline.copy()
                ImageDraw.Draw(actual).rectangle(box, fill=0)
                checks = component_checks(baseline, actual, masks, path, 16, 80)
                self.assertFalse(checks[name]['passed'])
                self.assertTrue(checks['actor' if name == 'water' else 'water']['passed'])

    def test_keep_fence_cannot_supply_native_actor_positive_control(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fence.png'
            baseline = Image.new('RGB', (100, 80))
            draw = ImageDraw.Draw(baseline)
            draw.rectangle((10, 10, 25, 65), fill=(20, 60, 170))
            draw.rectangle((30, 15, 40, 65), fill=(150, 100, 50))
            baseline.save(path)
            masks = (Image.new('L', baseline.size), Image.new('L', baseline.size))
            ImageDraw.Draw(masks[0]).rectangle((5, 5, 45, 70), fill=255)
            ImageDraw.Draw(masks[1]).rectangle((55, 5, 95, 70), fill=255)

            result = component_checks(baseline, baseline, masks, path, 16, 80)

            self.assertTrue(result['water']['valid_baseline'])
            self.assertTrue(result['water']['passed'])
            self.assertFalse(result['actor']['valid_baseline'])
            self.assertFalse(result['actor']['passed'])

    def test_no_native_component_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'empty.png'
            empty = Image.new('RGB', (100, 80))
            empty.save(path)
            masks = (Image.new('L', empty.size, 255), Image.new('L', empty.size))
            result = component_checks(empty, empty, masks, path, 16, 80)
            self.assertFalse(any(row['passed'] for row in result.values()))


if __name__ == '__main__':
    unittest.main()
