"""Fixed-coordinate public sign fixtures use NBT rather than render test hints."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
from projection.debug_blueprints import Fixture
from projection.debug_sign_blueprints import METADATA, CASES, VISUAL_CASE, populate
from projection.cell import foreground, actor_data
from projection.native_sign import native_sign_actor
from projection.nbt_spatial import root_payload,scalar
from projection.visible_actor import render_actor,entity_nbt


class SignBlueprintTests(unittest.TestCase):
    def test_each_stable_case_has_native_two_sided_tags_and_no_renderer_shortcut(self):
        doc=populate(Fixture(METADATA))
        for case in CASES:
            value=doc.get(case['position'])
            self.assertEqual(case['name'],foreground(value)[0])
            actor=actor_data(value)
            self.assertEqual({},render_actor(actor))
            root=root_payload(entity_nbt(actor))
            self.assertEqual(case['position'],tuple(scalar(root,axis) for axis in ('x','y','z')))
            renderer=native_sign_actor(foreground(value),actor,{})
            self.assertEqual('Front\nNative',renderer['signRealText'])
            self.assertEqual('Back\nNative',renderer['signRealTextBack'])
            self.assertTrue(renderer['signGlowing'])
            self.assertFalse(renderer['signGlowingBack'])
            self.assertEqual('minecraft:stone',foreground(doc.get(case['support']))[0])

    def test_visual_parameters_associate_both_views_with_the_same_builtin_cases(self):
        self.assertEqual(METADATA[0],VISUAL_CASE['fixture'])
        self.assertEqual(CASES,VISUAL_CASE['cases'])
        self.assertEqual({'front','back'},{view['id'] for view in VISUAL_CASE['views']})


if __name__=='__main__':
    unittest.main()
