"""Probe snapshots must tolerate asynchronous publication without claiming readiness."""
import importlib.util
import json
from collections import namedtuple
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack'))
import probe_liquid_original_sides as probe
from modern_projection.projection.cell import AIR, encode, make_cell


class ProjectionStateTests(unittest.TestCase):
    def test_native_compare_observes_complete_neighborhood_in_reserved_region(self):
        origin=(10,20,30)
        cells=[[[3,2,3],['minecraft:stone',0]],[[3,3,3],['minecraft:water',0]]]
        reserved=[(x,y,z) for x in range(10,17) for y in range(20,27) for z in range(30,37)]
        actual=probe.native_comparison_positions(cells,origin,reserved)
        expected=[(x,y,z) for x in range(12,15) for y in range(21,25) for z in range(32,35)]
        self.assertEqual(expected,actual)
        self.assertEqual(36,len(actual))
        with self.assertRaisesRegex(ValueError,'exceeds'):
            probe.native_comparison_positions(cells,origin,[pos for pos in reserved if pos!=(12,21,32)])

    def test_inactive_pending_and_published_snapshots_follow_publication(self):
        document=SimpleNamespace(blocks={(3,3,3):('minecraft:water',0)},biome=1)
        s=SimpleNamespace(projection_active=False,origin=(0,0,0),opacity=1.,
            editor=SimpleNamespace(document=document),projection_missing=False)
        b=SimpleNamespace(projection_work=None,projection_liquid=None,projection_occupancy=None,
            projection_serial=1,entity=99)
        def snapshot():
            scope={'b':b,'s':s,'json':json}
            exec(probe.WORLD_STATE,scope)
            return json.loads(scope['_result'])
        inactive=snapshot()
        self.assertEqual([],inactive['groups'])
        self.assertFalse(probe.workspace.world_ready(inactive))
        group_type=namedtuple('Group','origin key uniforms')
        group=group_type((0,0,0),('water',('texture','template')),((0,0,0,0),)*4)
        renderer=SimpleNamespace(active={'water':{'model_id':2,'group':group,'visible':True}},
            staging=[],retired=[],cleanup_errors=[])
        liquid=SimpleNamespace(renderer=renderer,ready=True,error=None,document=document)
        work=SimpleNamespace(ready=False,serial=1,document=document,error=None,liquid=liquid,
            shader=SimpleNamespace(uniforms=[],parts=[]))
        b.projection_work=work;s.projection_active=True
        pending=snapshot()
        self.assertEqual([],pending['groups'])
        self.assertFalse(pending['liquid_ready'])
        self.assertFalse(probe.workspace.world_ready(pending))
        b.projection_liquid=liquid;work.ready=True
        published=snapshot()
        self.assertEqual(1,len(published['groups']))
        self.assertTrue(probe.workspace.world_ready(published))
        work.error='publication failed'
        with self.assertRaisesRegex(RuntimeError,'publication failed'):
            probe.workspace.world_ready(snapshot())


class DirectWriteTests(unittest.TestCase):
    def run_write(self,cells,stored=None):
        stored=dict(stored or {})
        changes=[]
        class Info:
            def SetBlockNew(self,pos,value,handling,dimension,legacy,neighbors):
                pair=(value['name'],value['aux']);old=stored.get(pos,AIR)
                changes.append((pos,pair,handling,dimension,legacy,neighbors))
                stored[pos]=pair
                return pair!=old
        adapter=SimpleNamespace(info=Info(),read=lambda pos:stored.get(pos,AIR))
        saved={'player':'player','dimension':0,'region':[(1,2,3),(1,3,3)],
            'workspace_cells':list(stored)}
        scope={'sys':SimpleNamespace(_liquid_pose_world=saved),'json':json}
        fake=SimpleNamespace(WorldAdapter=lambda player:adapter)
        with patch.dict(sys.modules,{'modern_projection.server_system':fake}):
            exec(probe.DIRECT_WRITE % probe.native.wire(cells),scope)
        return json.loads(scope['_result']),stored,saved,changes

    def test_direct_write_clears_old_cells_and_keeps_only_changed_simple_cells(self):
        cells=[((1,2,3),encode(('minecraft:stone',0))),((1,3,3),encode(('minecraft:water',3)))]
        receipt,stored,saved,changes=self.run_write(cells,{(1,3,3):('minecraft:water',0)})
        self.assertEqual(('minecraft:stone',0),stored[(1,2,3)])
        self.assertEqual(('minecraft:water',3),stored[(1,3,3)])
        self.assertEqual([(1,2,3),(1,3,3)],saved['workspace_cells'])
        self.assertEqual(3,len(changes))
        self.assertTrue(all(change[2:]==(0,0,True,False) for change in changes))
        self.assertEqual('SetBlockNew',receipt['route'])
        self.assertTrue(all(row['changed'] for row in receipt['rows']))

    def test_layered_or_unreserved_values_are_rejected_before_clearing(self):
        layered=encode(make_cell(('minecraft:stone',0),('minecraft:water',0)))
        for cells in ([((1,2,3),layered)],[((99,2,3),encode(('minecraft:water',0)))]):
            with self.assertRaises(AssertionError):
                self.run_write(cells,{(1,3,3):('minecraft:water',0)})


class NearReservationTests(unittest.TestCase):
    def test_explicit_near_control_retains_every_air_gate_and_default_far_template(self):
        near = probe.native_comparison_prepare(2)
        self.assertIn('int(math.floor(foot[1]))+2,', near)
        self.assertIn("assert front and front.get('name')=='minecraft:air'", near)
        self.assertIn("assert back is None or back.get('name')=='minecraft:air'", near)
        self.assertEqual(probe.workspace.QUALIFICATION_PREPARE, probe.native_comparison_prepare(24))
        with self.assertRaisesRegex(ValueError, 'reviewed'):
            probe.native_comparison_prepare(-64)

    def test_changed_reservation_template_is_rejected(self):
        with patch.object(probe.workspace, 'QUALIFICATION_PREPARE', 'unknown origin'):
            with self.assertRaisesRegex(ValueError, 'template changed'):
                probe.native_comparison_prepare(2)


if __name__=='__main__':unittest.main()
