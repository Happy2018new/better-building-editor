"""The attachment family and entity origin remain explicit through failures."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'behavior_pack/modern_projection'))
from projection.entity_overlays import BoundItems


class Items(object):
    def __init__(self):self.calls=[];self.fail=set();self.identity=0
    def BindItemToMinecraftModel(self,*args):self.calls.append(('minecraft',args));return self.identity
    def BindItemToSkeletonModel(self,*args):self.calls.append(('skeleton',args));return self.identity
    def SetBindBoneForBindItem(self,*args):self.calls.append(('remove',args));return 'remove' not in self.fail
    def SetBindItemOffset(self,*args):self.calls.append(('offset',args));return 'offset' not in self.fail
    def SetBindItemRotation(self,*args):self.calls.append(('rotation',args));return 'rotation' not in self.fail
    def SetBindItemScale(self,*args):self.calls.append(('scale',args));return 'scale' not in self.fail


class Routes(unittest.TestCase):
    def setUp(self):
        self.component=Items()
        self.item={'newItemName':'minecraft:diamond_sword','newAuxValue':0,'isEnchanted':True,'userData':{}}
        self.row=('frame',self.item,(0.,0.,0.),(90.,0.,0.),1./16.)

    def test_skeleton_server_actor_false_flag_survives_update_and_failed_remove(self):
        owner=BoundItems(self.component,'exact_actor','skeleton',False)
        self.assertTrue(owner.sync([self.row]))
        self.assertEqual('skeleton',self.component.calls[0][0])
        self.assertIs(self.component.calls[0][1][3],False)
        self.component.fail.add('offset')
        changed=('frame',self.item,(1.,0.,0.),(90.,45.,0.),.5)
        self.assertFalse(owner.sync([changed]))
        self.assertEqual((0.,0.,0.),owner.rows['frame'][2])
        self.component.fail.clear()
        self.assertTrue(owner.sync([changed]))
        self.component.fail.add('remove')
        self.assertFalse(owner.clear())
        self.assertIn('frame',owner.rows)
        self.component.fail.clear()
        self.assertTrue(owner.clear())
        self.assertTrue(all(args[-1] is False for name,args in self.component.calls if name in ('offset','rotation','scale','remove')))

    def test_failed_remove_cannot_rebind_changed_payload_and_old_owner_is_retained(self):
        owner=BoundItems(self.component,'exact_actor','skeleton',False)
        owner.sync([self.row])
        self.component.fail.add('remove')
        item=dict(self.item,isEnchanted=False)
        self.assertFalse(owner.sync([('frame',item,*self.row[2:])]))
        self.assertEqual(1,len([call for call in self.component.calls if call[0]=='skeleton']))
        self.assertIn('frame',owner.rows)
        self.component.fail.clear()
        self.assertTrue(owner.sync([('frame',item,*self.row[2:])]))
        self.assertEqual(['skeleton','remove','remove','skeleton'],[call[0] for call in self.component.calls])

    def test_invalid_native_identity_never_enters_cleanup_ledger(self):
        for identity in (-1,None,False,'0'):
            self.component.identity=identity
            owner=BoundItems(self.component,'exact_actor','skeleton',False)
            self.assertFalse(owner.sync([self.row]))
            self.assertEqual({},owner.rows)

    def test_default_native_route_and_input_payload_are_preserved(self):
        before=copy.deepcopy(self.item)
        owner=BoundItems(self.component,'client_actor')
        self.assertTrue(owner.sync([self.row]))
        self.assertEqual('minecraft',self.component.calls[0][0])
        self.assertIs(self.component.calls[0][1][3],True)
        self.assertEqual(before,self.item)
        for family,flag in (('ui_model',False),('skeleton',0),('minecraft',None)):
            with self.assertRaises(ValueError):BoundItems(self.component,'actor',family,flag)


if __name__=='__main__':unittest.main()
