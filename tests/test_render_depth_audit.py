"""Depth audit must apply native inheritance, removals and project overlays."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_render_depth_states import overlay,resolve


class RenderDepthAuditTests(unittest.TestCase):
    def test_opaque_companion_removes_native_alpha_depth_disable(self):
        definitions={}
        overlay(definitions,{'entity':{},'alpha:entity':{
            '+states':['Blending','DisableDepthWrite']}},'native')
        overlay(definitions,{'book:alpha':{'-states':['DisableDepthWrite'],
                                          '+states':['DisableCulling']}},'project')
        self.assertFalse(resolve(definitions,'alpha')['depth_write'])
        result=resolve(definitions,'book')
        self.assertTrue(result['depth_write'])
        self.assertTrue(result['depth_test'])
        self.assertEqual(['Blending','DisableCulling'],result['states'])
        self.assertEqual(['entity','alpha','book'],result['ancestors'])

    def test_project_patch_keeps_parent_and_reports_variant_caveat(self):
        definitions={}
        overlay(definitions,{'base':{'states':['Blending']},'child:base':{
            'variants':[{'late':{'+states':['DisableDepthWrite']}}]}},'native')
        overlay(definitions,{'child':{'+states':['DisableDepthTest']}},'project')
        result=resolve(definitions,'child')
        self.assertTrue(result['depth_write'])
        self.assertFalse(result['depth_test'])
        self.assertEqual('late',result['variant_state_overrides'][0]['variant'])
        self.assertEqual(['native','project'],definitions['child']['sources'])

    def test_missing_parent_and_cycle_fail_instead_of_assuming_depth_writes(self):
        definitions={}
        overlay(definitions,{'a:b':{}},'project')
        with self.assertRaisesRegex(ValueError,'Missing'):resolve(definitions,'a')
        overlay(definitions,{'b:a':{}},'project')
        with self.assertRaisesRegex(ValueError,'cycle'):resolve(definitions,'a')


if __name__=='__main__':unittest.main()
