import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'behavior_pack/HelloScript'))
from projection.native_layers import apply_layers


class LayerBatchTests(unittest.TestCase):
    def setUp(self):
        self.gui=types.ModuleType('gui')
        self.routes=[];self.writes=[]
        self.original=lambda *a,**k:self.routes.append((a,k))
        self.gui.handle_input_mode_change=self.original
        self.modules=patch.dict(sys.modules,{'gui':self.gui})
        self.modules.start();self.addCleanup(self.modules.stop)

    def control(self, identity, fail=False):
        case=self
        class Control:
            def SetLayer(self, layer, sync, force):
                case.writes.append((identity,layer,sync,force))
                case.gui.handle_input_mode_change()
                if fail:raise ValueError('native control removed')
        return Control()

    def test_large_orbit_keeps_every_layer_but_rebuilds_input_once(self):
        apply_layers([(self.control(i),50+i) for i in range(104)])
        self.assertEqual(105,len(self.writes))
        self.assertEqual(list(range(50,154)),[v[1] for v in self.writes[:-1]])
        self.assertEqual(1,sum(v[3] for v in self.writes))
        self.assertEqual(1,len(self.routes))
        self.assertIs(self.original,self.gui.handle_input_mode_change)
        self.gui.handle_input_mode_change()
        self.assertEqual(2,len(self.routes))

    def test_exception_restores_and_flushes_native_routing(self):
        with self.assertRaises(ValueError):
            apply_layers([(self.control(1),50),(self.control(2,True),51)])
        self.assertIs(self.original,self.gui.handle_input_mode_change)
        self.assertEqual(1,len(self.routes))

    def test_other_engine_versions_use_public_api(self):
        del self.gui.handle_input_mode_change
        writes=[]
        class Control:
            def SetLayer(self,*args):writes.append(args)
        apply_layers([(Control(),55)])
        self.assertEqual([(55,False,False),(55,False,True)],writes)

    def test_empty_batch_does_not_touch_engine(self):
        apply_layers([])
        self.assertEqual([],self.routes)


if __name__=='__main__':unittest.main()
