"""Candidate book companions retain immutable source NBT and target bounds."""
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
from projection.book_profile import candidate_profile,production_profile
from projection.book_render_plan import appearance,iter_render_steps
from projection.debug_compatibility_blueprints import source_document
from projection.debug_item_blueprints import slot_document
from projection.cell import actor_data,foreground


class BookRenderPlanTests(unittest.TestCase):
    def test_unqualified_companion_does_not_admit_any_production_engine(self):
        for version in (None,'3.9.0.401155','3.10.0.420447','3.11.0.0'):
            self.assertIsNone(production_profile(version))
        for value in (0,-1,True,1.5):
            with self.assertRaises(ValueError):candidate_profile(value)

    def test_public_empty_lectern_has_no_book_and_real_item_payload_has_one(self):
        for case,count in (('lectern.empty',0),('lectern.book',1)):
            document=slot_document(case);before=copy.deepcopy(document.to_data())
            groups=[group for group in iter_render_steps(document,candidate_profile()) if group]
            self.assertEqual(count,len(groups));self.assertEqual(before,document.to_data())

    def test_table_uses_real_actor_and_targeting_keeps_native_body(self):
        document=source_document('test.dynamic.special','enchanting_table.default')
        before=copy.deepcopy(document.to_data());cell=document.get((3,3,3));material=foreground(cell)
        self.assertEqual(('enchanting_table',0),appearance(material,actor_data(cell),'3.10.0.420447'))
        self.assertIsNone(appearance(material,None,'3.10.0.420447'))
        self.assertIsNone(appearance(material,actor_data(cell),'3.11.0.0'))
        targets={'volume':(8,8,8),'common':{material:[(3*8+3)*8+3]},'extra':{}}
        groups=[group for group in iter_render_steps(document,candidate_profile(),targets) if group]
        self.assertEqual(1,len(groups));self.assertEqual(before,document.to_data())
        self.assertEqual((),candidate_profile().supported_names)
        self.assertEqual([],list(group for group in iter_render_steps(document,candidate_profile(),targets,visible=lambda pos:False) if group))
        for indices in ([True],[-1],[512],[(3*8+3)*8+3]*2):
            with self.assertRaises(ValueError):list(iter_render_steps(document,candidate_profile(),dict(targets,common={material:indices})))


if __name__=='__main__':unittest.main()
