import ast
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import prepare_item_glint_r13 as candidate
import execute_item_glint_r13 as runtime


class ItemGlintContracts(unittest.TestCase):
    def setUp(self):
        self.original=(candidate.PHASE,candidate.POSE)
        candidate.configure('glint','x90')

    def tearDown(self):candidate.configure(*self.original)

    def state(self,label,ids):
        initial={'actor':'owned_actor','skeleton_setup':{'model':candidate.MODEL,'model_id':7},'ui_params':{'entity_id':'owned_actor','scale':1.4}}
        controls=[s for s in candidate.STATES[:candidate.STATES.index(label)+1] if candidate.state_parameters(s)[0] is not None and s!='ui_enchanted_later']
        rows=[]
        active=candidate.state_parameters(label)[0] is not None
        for i,(control,identity) in enumerate(zip(controls,ids)):
            enchanted,rotation=candidate.state_parameters(control)
            live=active and i==len(controls)-1
            row={'id':identity,'control':control,'item':{'isEnchanted':enchanted,'newAuxValue':0,'newItemName':'minecraft:diamond_sword','userData':{}},
                 'offset':[0.,0.,0.],'rotation':list(rotation),'scale':candidate.ITEM_SCALE,'item_nonmutation':True,'state':'bound' if live else 'removed'}
            if not live:row.update(remove_attempted=True,remove_result=True)
            rows.append(row)
        journal=[{'operation':'RenderEntity:'+label,'state':'returned','value':True}]
        status={'control':label,'model_id':9,'skeleton_setup':initial['skeleton_setup'],'last_submission':initial['ui_params'],'ui_params':initial['ui_params'],
                'attachments':rows,'journal':journal}
        native={'control':label,'actor':'owned_actor','attachments':rows,'journal':journal,'native_item':None}
        if active:
            row=rows[-1]
            native['native_item']={k:row[k] for k in ('id','offset','rotation','scale')}
        return status,initial,native

    def test_prior_native_binding_id_cannot_change_in_later_temporal_sample(self):
        status,initial,native=self.state('ui_enchanted_later',(13,17))
        self.assertEqual(runtime.validate_state('ui_enchanted_later',status,initial,native,(13,17)),(13,17))
        for ids in ((14,17),(13,18)):
            status,initial,native=self.state('ui_enchanted_later',ids)
            with self.assertRaisesRegex(ValueError,'previously observed'):
                runtime.validate_state('ui_enchanted_later',status,initial,native,(13,17))

    def test_enchanted_payload_and_earlier_item_removal_are_mandatory(self):
        status,initial,native=self.state('ui_enchanted',(13,17))
        status['attachments'][0]['remove_result']=False
        with self.assertRaisesRegex(ValueError,'Earlier owned'):
            runtime.validate_state('ui_enchanted',status,initial,native,(13,))
        status,initial,native=self.state('ui_enchanted',(13,17))
        status['attachments'][1]['item']['isEnchanted']=False
        with self.assertRaisesRegex(ValueError,'payload'):
            runtime.validate_state('ui_enchanted',status,initial,native,(13,))

    def test_later_glint_state_never_rebinds_and_server_absence_is_observed(self):
        programs=candidate.snippets('0'*32)
        self.assertNotIn('BindItemToSkeletonModel(',programs['ui_enchanted_later_client.py'])
        self.assertIn("server_absence_kind",programs['destroy_server.py'])
        self.assertIn('kind is None',programs['destroy_server.py'])
        self.assertIn('rotation,0.0625)',programs['ui_plain_x90_client.py'])
        self.assertIn("'scale':0.0625",programs['ui_plain_x90_client.py'])
        for name,source in programs.items():ast.parse(source,filename=name)

    def test_frozen_pose_scale_or_payload_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'candidate'
            plan=candidate.prepare(bundle)
            self.assertEqual(plan['item_scale'],1./16.)
            self.assertFalse(plan['production_rendering_accepted'])
            target=bundle/'ui_enchanted_client.py'
            target.write_bytes(target.read_bytes().replace(b'rotation,0.0625)',b'rotation,1.)'))
            with self.assertRaisesRegex(ValueError,'Frozen candidate bytes changed'):
                candidate.verify(bundle)


if __name__=='__main__':unittest.main()
