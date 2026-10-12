"""Experimental hypotheses restore exact bytes and retain source boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import prepare_plant_cross_candidates as candidate


class PlantCrossCandidateTests(unittest.TestCase):
    def originals(self):
        names = ('resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json',
                 'behavior_pack/modern_projection/projection/plant_proxy_data.py')
        return {name: ((ROOT/name).read_text(encoding='utf8') if name.endswith('.py')
                       else json.loads((ROOT/name).read_bytes())) for name in names}

    def test_hypotheses_preserve_accepted_fungus_assets_and_native_texture_identity(self):
        source = json.loads(candidate.SOURCE.read_bytes())
        originals = self.originals()
        before = deepcopy(originals)
        files = candidate.candidates(source, originals)
        self.assertEqual(before, originals)
        self.assertFalse(any('mushroom' in name or 'fungus' in name for name in files))
        atlas = json.loads(files['resource_pack/textures/terrain_texture.json'])['texture_data']
        for name in ('poppy', 'crimson_roots', 'warped_roots', 'nether_sprouts'):
            self.assertEqual(source['plants'][name]['texture_path'].rsplit('.', 1)[0],
                             atlas['modern_projection_static_'+name]['textures'])
        for name in ('short_grass', 'fern'):
            model = json.loads(files['resource_pack/models/netease_block/preview_'+name+'.json'])
            for bone in model['netease:block_geometry']['bones']:
                self.assertEqual(16., bone['cubes'][0]['size'][1])
                self.assertAlmostEqual(candidate.GRASS_Y_CLIP_HYPOTHESIS * 16.,
                                       bone['cubes'][0]['origin'][1])

    def test_restoration_rejects_changed_candidate_before_touching_other_files(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            for name in self.originals():
                path = temporary/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT/name).read_bytes())
            for name in candidate.NAMES:
                for part in ('behavior_pack/netease_blocks', 'resource_pack/models/netease_block'):
                    (temporary/part).mkdir(parents=True, exist_ok=True)
            snapshot = temporary/'snapshot.json'
            with patch.object(candidate, 'ROOT', temporary):
                record = candidate.apply(snapshot, False)
                first, second = tuple(record['candidate_sha256'])[:2]
                (temporary/second).write_bytes(b'changed externally')
                first_before = (temporary/first).read_bytes()
                with self.assertRaisesRegex(ValueError, 'Candidate bytes changed'):
                    candidate.restore(snapshot)
                self.assertEqual(first_before, (temporary/first).read_bytes())

    def test_exact_restoration_removes_new_files_and_recovers_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            before = {}
            for name in self.originals():
                path = temporary/name
                path.parent.mkdir(parents=True, exist_ok=True)
                before[name] = (ROOT/name).read_bytes()
                path.write_bytes(before[name])
            for name in candidate.NAMES:
                for part in ('behavior_pack/netease_blocks', 'resource_pack/models/netease_block'):
                    (temporary/part).mkdir(parents=True, exist_ok=True)
            snapshot = temporary/'snapshot.json'
            with patch.object(candidate, 'ROOT', temporary):
                record = candidate.apply(snapshot, False)
                self.assertFalse(record['production_acceptance'])
                self.assertFalse(record['native_mesh_or_offset_contract_recovered'])
                self.assertTrue(candidate.restore(snapshot)['restored'])
                for name in record['candidate_sha256']:
                    if name in before:
                        self.assertEqual(before[name], (temporary/name).read_bytes())
                    else:
                        self.assertFalse((temporary/name).exists())


if __name__ == '__main__':
    unittest.main()
