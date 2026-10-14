"""Measured version boundary, typed actor handling and immutable palette data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT/'tools'))
from projection.cauldron_native_data import DATA, SOURCE_SHA256
from projection.cauldron_profile import CauldronProfile, candidate_profile
from generate_cauldron_native_data import generate


def actor(**fields):
    result = {'id': {'__type__': 8, '__value__': 'Cauldron'}}
    for name, value in fields.items():
        result[name] = {'__type__': 3 if name == 'CustomColor' else 2, '__value__': value}
    return result


class CauldronProfileTests(unittest.TestCase):
    def test_generated_data_matches_measured_source_and_every_evidence_hash(self):
        source = ROOT/'tools/data/cauldron_native_nemc310_v1.json'
        self.assertEqual(SOURCE_SHA256, hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(DATA, json.loads(source.read_bytes()))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'generated.py'
            generate(source, ROOT/'docs/evidence/cauldron-surface-r15', output)
            self.assertEqual(output.read_bytes(),
                             (ROOT/'behavior_pack/modern_projection/projection/cauldron_native_data.py').read_bytes())

    def test_six_lava_levels_use_measured_height_and_color(self):
        profile = candidate_profile()
        for level in range(1, 7):
            top = profile.top(('minecraft:cauldron', level+8), None, 'plains')
            self.assertEqual((DATA['heights'][level-1], 'lava', (255,255,255), None), top)
        self.assertIsNone(profile.top(('minecraft:cauldron', 8), None, 'plains'))

    def test_potion_forms_and_signed_rgb_preserve_unknown_actor_fields(self):
        profile = candidate_profile()
        for form in (0, 1, 2):
            payload = actor(PotionId=43, PotionType=form)
            payload['Future'] = {'__type__': 10, '__value__': {'x': 8}}
            before = deepcopy(payload)
            self.assertEqual(tuple(DATA['potion_colors']['43']),
                             profile.top(('minecraft:cauldron', 6), payload, 'plains').color)
            self.assertEqual(before, payload)
        for value in (-65536, 16711680):
            self.assertEqual((255,0,0), profile.top(('minecraft:cauldron', 6),
                                                   actor(CustomColor=value), 'plains').color)

    def test_plain_water_tracks_document_biome_and_snow_uses_verified_static_plane(self):
        from projection import biomes
        profile = candidate_profile()
        for biome in biomes.KEYS:
            for level in range(1, 7):
                for payload in (None, actor(PotionId=-1, PotionType=-1)):
                    with self.subTest(biome=biome, level=level, actor=payload):
                        top = profile.top(('minecraft:cauldron', level), payload, biome)
                        self.assertEqual('plain_water', top.texture)
                        self.assertEqual(biomes.water_appearance(biome)[0], top.color)
                        self.assertEqual(DATA['heights'][level-1], top.height)
        for level in range(1,7):
            top = profile.top(('minecraft:cauldron',16+level), None, 'plains')
            self.assertEqual((DATA['heights'][level-1], 'snow', (255,255,255), None), top)

    def test_biome_changes_preserve_potion_and_custom_rgb_appearances(self):
        from projection import biomes
        profile = candidate_profile()
        for payload in (actor(PotionId=43, PotionType=0), actor(CustomColor=0x345678)):
            before = deepcopy(payload)
            reference = profile.top(('minecraft:cauldron', 6), payload, biomes.DEFAULT)
            for biome in biomes.KEYS:
                with self.subTest(biome=biome, actor=payload):
                    self.assertEqual(reference, profile.top(('minecraft:cauldron', 6), payload, biome))
                    self.assertEqual(before, payload)

    def test_future_state_and_malformed_tags_stay_native(self):
        profile = candidate_profile()
        for material, payload in (
                (('minecraft:cauldron',99), None),
                (('minecraft:cauldron',6), actor(PotionId=999, PotionType=0)),
                (('minecraft:cauldron',6), actor(PotionId=5, PotionType=99)),
                (('minecraft:cauldron',6), actor(CustomColor=1 << 32))):
            with self.subTest(material=material, payload=payload):
                self.assertIsNone(profile.top(material, payload, 'plains'))
        malformed = actor(PotionId=5, PotionType=0)
        malformed['PotionId']['__type__'] = 3
        self.assertIsNone(profile.top(('minecraft:cauldron',6), malformed, 'plains'))

    def test_version_and_geometry_changes_require_a_new_adapter(self):
        for field, value in (('engine_version','3.11.0'),('geometry_measured',False),
                             ('heights',[.3]*6),('inset',.2)):
            changed = deepcopy(DATA)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                CauldronProfile(changed)


if __name__ == '__main__':
    unittest.main()
