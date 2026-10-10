"""Typed actor render items stay opaque to storage and own native attachments."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.entity_overlays import BoundItems, actor_item, banner_item, frame_item
from projection.visible_actor import compose_actor


def tag(kind, value):
    return {'__type__': kind, '__value__': value}


def frame(user_data=None):
    item = {'Name':tag(8,'minecraft:diamond_sword'), 'Count':tag(1,1), 'Damage':tag(2,0)}
    if user_data is not None:
        item['tag'] = user_data
    return {'id':tag(8,'ItemFrame'),'Item':item,'ItemRotation':tag(5,45.),'unknown':tag(3,42)}


class Items(object):
    def __init__(self):
        self.calls=[]
        self.next=0
        self.fail=set()

    def BindItemToMinecraftModel(self, *args):
        self.calls.append(('bind',args))
        if 'bind' in self.fail:return -1
        identity=self.next
        self.next+=1
        return identity

    def SetBindBoneForBindItem(self, *args):
        self.calls.append(('remove',args))
        return 'remove' not in self.fail

    def SetBindItemOffset(self, *args):
        self.calls.append(('offset',args))
        return 'offset' not in self.fail

    def SetBindItemRotation(self, *args):
        self.calls.append(('rotation',args))
        return 'rotation' not in self.fail

    def SetBindItemScale(self, *args):
        self.calls.append(('scale',args))
        return 'scale' not in self.fail


class ItemDataTests(unittest.TestCase):
    def test_frame_keeps_typed_item_userdata_without_mutating_payload(self):
        user_data={'ench':tag(9,[{'id':tag(2,9),'lvl':tag(2,2)}]),'foreign':tag(10,{'x':tag(3,17)})}
        source=compose_actor({},frame(user_data))
        before=copy.deepcopy(source)
        item=frame_item(('minecraft:frame',2),source)
        self.assertEqual('minecraft:diamond_sword',item['newItemName'])
        self.assertTrue(item['isEnchanted'])
        self.assertEqual(user_data,item['userData'])
        item['userData']['foreign']['__value__']['x']['__value__']=18
        self.assertEqual(before,source)

    def test_render_only_and_unrecognized_payloads_do_not_make_items(self):
        self.assertIsNone(frame_item(('minecraft:frame',0),{}))
        self.assertIsNone(frame_item(('minecraft:stone',0),frame()))
        for field,wrong in (('Count',tag(1,0)),('Damage',tag(3,0)),('Name',tag(8,17))):
            data=frame()
            data['Item'][field]=wrong
            self.assertIsNone(frame_item(('minecraft:frame',0),data))

    def test_banner_preserves_int_type_and_typed_patterns(self):
        nbt={'id':tag(8,'Banner'),'Base':tag(3,15),'Type':tag(3,1),
             'Patterns':tag(9,[{'Pattern':tag(8,'bs'),'Color':tag(3,1)}])}
        before=copy.deepcopy(nbt)
        item=actor_item(('minecraft:standing_banner',0),nbt)
        self.assertEqual('minecraft:banner',item['newItemName'])
        self.assertEqual(15,item['newAuxValue'])
        self.assertEqual({'Type':nbt['Type'],'Patterns':nbt['Patterns']},item['userData'])
        self.assertEqual(before,nbt)
        nbt['Base']=tag(3,16)
        self.assertIsNone(banner_item(('minecraft:wall_banner',2),nbt))

    def test_byte_keys_and_root_compounds_are_preserved(self):
        data={key.encode('ascii'):value for key,value in frame().items()}
        item=data[b'Item']
        data[b'Item']={key.encode('ascii'):value for key,value in item.items()}
        self.assertEqual('minecraft:diamond_sword',frame_item(('minecraft:glow_frame',0),tag(10,data))['newItemName'])


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.items=Items()
        self.bound=BoundItems(self.items,'actor')
        self.item={'newItemName':b'minecraft:apple','newAuxValue':0,'isEnchanted':False,'userData':{}}
        self.row=('cell',self.item,(0.,1.,0.),(0.,0.,0.),1.)

    def test_stable_repeated_sync_does_not_cross_native_boundary(self):
        self.assertTrue(self.bound.sync([self.row]))
        self.assertTrue(self.bound.sync([self.row]))
        self.assertEqual(['bind'],[name for name,args in self.items.calls])
        self.assertEqual(b'root',self.items.calls[0][1][2])
        self.assertIs(True,self.items.calls[0][1][3])

    def test_pose_updates_existing_binding_and_clear_removes_once(self):
        self.bound.sync([self.row])
        self.assertTrue(self.bound.sync([('cell',self.item,(2.,1.,0.),(0.,90.,45.),.5)]))
        self.assertEqual(['bind','offset','rotation','scale'],[name for name,args in self.items.calls])
        self.assertTrue(self.bound.clear())
        self.assertTrue(self.bound.clear())
        self.assertEqual(('remove',('actor',0,b'',True)),self.items.calls[-1])

    def test_content_changes_rebind_and_missing_cells_remove(self):
        self.bound.sync([self.row])
        item=dict(self.item,newAuxValue=1)
        self.assertTrue(self.bound.sync([('cell',item,*self.row[2:])]))
        self.assertEqual(['bind','remove','bind'],[name for name,args in self.items.calls])
        self.assertTrue(self.bound.sync([]))
        self.assertEqual({},self.bound.rows)

    def test_failed_updates_remain_retryable_and_failed_remove_retains_owner(self):
        self.bound.sync([self.row])
        self.items.fail.add('offset')
        changed=('cell',self.item,(2.,1.,0.),(0.,0.,0.),1.)
        self.assertFalse(self.bound.sync([changed]))
        self.assertEqual((0.,1.,0.),self.bound.rows['cell'][2])
        self.items.fail.clear()
        self.assertTrue(self.bound.sync([changed]))
        self.items.fail.add('remove')
        self.assertFalse(self.bound.clear())
        self.assertIn('cell',self.bound.rows)
        self.items.fail.clear()
        self.assertTrue(self.bound.clear())

    def test_bind_failure_does_not_track_invalid_model(self):
        self.items.fail.add('bind')
        self.assertFalse(self.bound.sync([self.row]))
        self.assertEqual({},self.bound.rows)
        self.items.fail.clear()
        self.assertTrue(self.bound.sync([self.row]))


if __name__=='__main__':
    unittest.main()
