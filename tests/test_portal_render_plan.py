"""Portal surface ownership and targets preserve the complete logical source."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import make_cell, actor_data
from projection.debug_blueprints import material, Fixture
from projection.debug_portal_blueprints import METADATA, populate
from projection.model import Document
from projection.portal_profile import candidate_profile, production_profile, suppress
from projection import portal_profile
from projection.portal_render_plan import iter_render_steps


class PortalPlanTests(unittest.TestCase):
    def test_product_gate_is_bound_to_reviewed_surfaces_and_resources(self):
        path=ROOT/'docs/evidence/portal-product-r16/qualification.json'
        report=json.loads(path.read_bytes())
        self.assertTrue(portal_profile.PRODUCT_QUALIFIED)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),portal_profile.QUALIFICATION_SHA256)
        self.assertTrue(all(report['gates'].values()))
        resource=ROOT/'tools/data/portal_resource_contract_nemc310_v1.json'
        self.assertEqual(hashlib.sha256(resource.read_bytes()).hexdigest(),report['resource_contract_sha256'])
        for name,expected in json.loads(resource.read_bytes())['output_sha256'].items():
            if name not in ('resource_pack/materials/entity.material','resource_pack/models/netease_models.json'):
                self.assertEqual(expected,hashlib.sha256((ROOT/name).read_bytes()).hexdigest())

    def test_profile_does_not_enable_unqualified_or_future_resources(self):
        with patch.object(portal_profile,'PRODUCT_QUALIFIED',False):
            for version in ('3.10.0.420447', '3.9.0.401155', '3.11.0.0', None):
                self.assertIsNone(production_profile(version))
        with patch.multiple(portal_profile,PRODUCT_QUALIFIED=True,QUALIFICATION_SHA256='a'*64):
            self.assertIsNotNone(production_profile('3.10.0.420447'))
            for version in ('3.10.0.420448','3.9.0.401155','3.11.0.0',None):
                self.assertIsNone(production_profile(version))
        with patch.multiple(portal_profile,PRODUCT_QUALIFIED=True,QUALIFICATION_SHA256='invalid'):
            with self.assertRaises(ValueError):
                production_profile('3.10.0.420447')
        for budget in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                candidate_profile(budget)

    def test_supported_surfaces_strip_only_the_detached_native_draw_map(self):
        portal, gateway, stone = material('end_portal'), material('end_gateway'), material('stone')
        entries = {portal: [1], gateway: [2], stone: [3]}
        records = {portal: {}, gateway: {}, stone: {}}
        before = copy.deepcopy((entries, records))
        result, states = suppress(entries, records, candidate_profile())
        self.assertEqual({stone: [3]}, result)
        self.assertEqual({stone: {}}, states)
        self.assertEqual(before, (entries, records))

    def test_render_targets_keep_neighbor_context_and_actor_data(self):
        gateway = material('end_gateway')
        actor = {'id': {'__type__': 8, '__value__': 'EndGateway'}, 'opaque': ['kept']}
        doc = Document((8, 8, 8), {(3, 3, 3): make_cell(gateway, nbt=actor),
                                   (4, 3, 3): make_cell(gateway, nbt=actor)})
        before = copy.deepcopy(doc.to_data())
        index = (3 * 8 + 3) * 8 + 3
        targets = {'volume': (8, 8, 8), 'common': {gateway: [index]}, 'extra': {}}
        groups = [group for group in iter_render_steps(doc, candidate_profile(), targets) if group]
        self.assertEqual(1, len(groups))
        code = int(groups[0].uniforms[0][0])
        self.assertEqual(63 & ~(1 << 4), (code >> 6) & 63)
        self.assertEqual(before, doc.to_data())
        self.assertEqual(actor, actor_data(doc.get((3, 3, 3))))
        with self.assertRaises(ValueError):
            list(iter_render_steps(doc, candidate_profile(), dict(targets, volume=(4, 4, 4))))

    def test_public_gallery_covers_all_three_portal_names_and_complete_groups(self):
        doc = populate(Fixture(METADATA))
        names = set(value[0] for value in doc.palette_data()['common'])
        self.assertTrue({'minecraft:portal', 'minecraft:end_portal', 'minecraft:end_gateway'} <= names)
        groups = [group for group in iter_render_steps(doc, candidate_profile()) if group]
        self.assertEqual(2, len(groups))
        self.assertTrue(any('end_portal' in group.model_name for group in groups))
        self.assertTrue(any('end_gateway' in group.model_name for group in groups))

    def test_rectangular_targets_and_background_layer_preserve_logical_actor(self):
        gateway,stone=material('end_gateway'),material('stone')
        actor={'id':{'__type__':8,'__value__':'EndGateway'},'retained':[1,2,3]}
        doc=Document((6,5,7),{(3,2,5):make_cell(stone,gateway,actor)})
        before=copy.deepcopy(doc.to_data())
        index=(2*6+3)*7+5
        targets={'volume':(7,6,5),'common':{},'extra':{gateway:[index]}}
        groups=[group for group in iter_render_steps(doc,candidate_profile(),targets) if group]
        self.assertEqual(1,len(groups))
        self.assertEqual(before,doc.to_data())
        self.assertEqual(actor,actor_data(doc.get((3,2,5))))
        for indices in ([index,index],[True],[-1],[6*5*7]):
            with self.assertRaises(ValueError):
                list(iter_render_steps(doc,candidate_profile(),dict(targets,extra={gateway:indices})))

    def test_visibility_uses_full_neighbors_and_budget_is_bounded(self):
        gateway=material('end_gateway')
        doc=Document((8,8,8),{(0,0,0):gateway,(1,0,0):gateway,(4,0,0):gateway})
        groups=[group for group in iter_render_steps(doc,candidate_profile(),visible=lambda pos:pos==(0,0,0)) if group]
        faces=(int(groups[0].uniforms[0][0])>>6)&63
        self.assertEqual(63&~(1<<4),faces)
        with self.assertRaises(ValueError):
            list(iter_render_steps(doc,candidate_profile(max_groups=1)))


if __name__ == '__main__':
    unittest.main()
