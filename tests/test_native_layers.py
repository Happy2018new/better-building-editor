import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'behavior_pack/HelloScript'))
from projection.native_layers import apply_layers, PendingLayers


class LayerBatchTests(unittest.TestCase):
    def setUp(self):
        self.writes=[]

    def control(self, identity):
        writes=self.writes
        class Control:
            def SetLayer(self, layer, sync, force):
                writes.append((identity,layer,sync,force))
        return Control()

    def test_public_updates_refresh_once_without_duplicate_final_write(self):
        controls=[self.control(i) for i in range(6)]
        apply_layers([(control,50+i) for i,control in enumerate(controls)])
        self.assertEqual(6,len(self.writes))
        self.assertEqual(list(range(50,56)),[v[1] for v in self.writes])
        self.assertEqual(1,sum(v[3] for v in self.writes))
        self.assertTrue(self.writes[-1][3])

    def test_latest_request_wins_for_same_control(self):
        a,b=self.control(1),self.control(2)
        apply_layers([(a,30),(b,40),(a,50)])
        self.assertEqual([(1,50,False,False),(2,40,False,True)],self.writes)

    def test_large_order_change_is_bounded_and_eventually_complete(self):
        controls=[self.control(i) for i in range(104)]
        queue=PendingLayers()
        queue.add([(control,50+i) for i,control in enumerate(controls)])
        while queue.pending:
            before=len(self.writes)
            queue.flush(controls)
            self.assertLessEqual(len(self.writes)-before,4)
        self.assertEqual(104,len(self.writes))
        self.assertEqual(list(range(50,154)),[v[1] for v in self.writes])

    def test_removed_controls_are_discarded_and_new_camera_target_wins(self):
        controls=[self.control(i) for i in range(8)]
        queue=PendingLayers()
        queue.add([(control,50+i) for i,control in enumerate(controls)])
        queue.flush(controls,2)
        queue.add([(controls[7],90)])
        queue.flush(controls[4:],8)
        self.assertEqual([0,1,4,5,6,7],[v[0] for v in self.writes])
        self.assertEqual(90,self.writes[-1][1])
        self.assertFalse(queue.pending)

    def test_empty_batch_does_not_touch_engine(self):
        apply_layers([])
        self.assertEqual([],self.writes)


if __name__=='__main__':unittest.main()
