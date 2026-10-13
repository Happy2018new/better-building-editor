"""Opaque-body native route rejects wrong IDs and preserves frozen inputs."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_item_skeleton_candidate_r13 as candidate
import execute_item_skeleton_candidate_r13 as runtime


class CandidateContracts(unittest.TestCase):
    def test_same_actor_api_and_positive_gate_precede_sword(self):
        programs=candidate.snippets('0'*32)
        install=programs['install_client.py']
        self.assertLess(install.index("saved['actor']=candidate"),install.index('.SetModel('))
        self.assertIn('identity>=0',install)
        self.assertIn("saved['skeleton_setup']",install)
        self.assertNotIn('BindItem',install)
        source=programs['ui_plain_client.py']
        self.assertIn("BindItemToSkeletonModel(saved['actor'],item,'root',True",source)
        self.assertIn("assert params['entity_id']==saved['actor']",source)
        self.assertNotIn('BindItemToMinecraftModel',source)
        self.assertNotIn('SetModelMaterial',source)
        self.assertNotIn('GetModelId(),item',source)
        self.assertIn('identity>=0',programs['status_client.py'])
        self.assertEqual(candidate.STATES[0],candidate.POSITIVE_STATES[0])
        for name,code in programs.items():
            ast.parse(code,filename=name)

    def test_cube_is_finite_opaque_outward_root_weighted_and_unencoded(self):
        resources=candidate.resources()
        model=candidate.opaque_mesh()['mesh'][0]
        self.assertEqual(len(model['vertices']),24)
        self.assertEqual(len(model['indices']),12)
        positions=[v['pos'] for v in model['vertices']]
        self.assertEqual(min(p[1] for p in positions),0.)
        self.assertEqual(max(p[1] for p in positions),.5)
        self.assertTrue(all(v['weight']==[['root',1.]] for v in model['vertices']))
        for face in model['indices']:
            a,b,c=[model['vertices'][i]['pos'] for i in face]
            ab=[b[i]-a[i] for i in range(3)]
            ac=[c[i]-a[i] for i in range(3)]
            cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
            normal=model['vertices'][face[0]]['normal']
            self.assertGreater(sum(cross[i]*normal[i] for i in range(3)),0)
        registration=json.loads(resources['registration.json'])[candidate.MODEL]
        self.assertEqual(registration['material'],'entity_for_skeleton')
        self.assertNotIn('EXTRA',repr(resources))
        from io import BytesIO
        from PIL import Image
        image=Image.open(BytesIO(resources['textures/models/'+candidate.TEXTURE_PATH+'.png']))
        self.assertEqual(image.getextrema()[3],(255,255))

    def test_freeze_rejects_changed_snippet_or_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'candidate'
            plan=candidate.prepare(bundle)
            self.assertEqual(candidate.verify(bundle),plan)
            resource=bundle/'resources/models/modern_projection/item_diagnostic_r13/mesh.json'
            original=resource.read_bytes()
            resource.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError,'Frozen candidate bytes changed'):
                candidate.verify(bundle)
            resource.write_bytes(original)
            source=bundle/'ui_plain_client.py'
            source.write_bytes(source.read_bytes().replace(b"saved['actor'],item",b"saved['ref'],item"))
            with self.assertRaisesRegex(ValueError,'Frozen candidate bytes changed'):
                candidate.verify(bundle)

    def test_install_and_restore_preserve_exact_original_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            bundle=root/'candidate'
            candidate.prepare(bundle)
            (root/'.git').write_text('gitdir: elsewhere',encoding='ascii')
            registration=root/'resource_pack/models/netease_models.json'
            registration.parent.mkdir(parents=True)
            original=b'{\r\n "existing": {"opaque": true}\r\n}\r\n'
            registration.write_bytes(original)
            receipt=root/'receipt.json'
            with patch.object(candidate,'ROOT',root):
                candidate.install(bundle,receipt)
                self.assertIn(candidate.MODEL,json.loads(registration.read_bytes()))
                self.assertEqual(candidate.restore(receipt)['restored'],True)
                self.assertEqual(registration.read_bytes(),original)
                self.assertFalse((root/'resource_pack'/candidate.RESOURCE_DIR/'mesh.json').exists())

    def test_independent_registration_edit_blocks_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            bundle=root/'candidate'
            candidate.prepare(bundle)
            (root/'.git').write_text('gitdir: elsewhere',encoding='ascii')
            registration=root/'resource_pack/models/netease_models.json'
            registration.parent.mkdir(parents=True)
            registration.write_bytes(b'{}')
            with patch.object(candidate,'ROOT',root):
                candidate.install(bundle,root/'receipt.json')
                modified=registration.read_bytes()+b' '
                registration.write_bytes(modified)
                with self.assertRaisesRegex(ValueError,'Registration changed independently'):
                    candidate.restore(root/'receipt.json')
                self.assertEqual(registration.read_bytes(),modified)

    def test_partial_resource_install_is_recoverable_from_journal(self):
        for fail_at in (1,2,3,4):
            with self.subTest(fail_at=fail_at),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                bundle=root/'candidate'
                candidate.prepare(bundle)
                (root/'.git').write_text('gitdir: elsewhere',encoding='ascii')
                registration=root/'resource_pack/models/netease_models.json'
                registration.parent.mkdir(parents=True)
                original=b'{\r\n "existing": {}\r\n}\r\n'
                registration.write_bytes(original)
                receipt=root/'receipt.json'
                write=Path.write_bytes
                writes=[]
                def interrupted(path,raw):
                    if path.is_relative_to(root/'resource_pack'):
                        writes.append(path)
                        if len(writes)==fail_at:
                            raise OSError('injected native disk failure')
                    return write(path,raw)
                with patch.object(candidate,'ROOT',root):
                    with patch.object(Path,'write_bytes',interrupted):
                        with self.assertRaisesRegex(OSError,'injected native disk failure'):
                            candidate.install(bundle,receipt)
                    restored=candidate.restore(receipt)
                    self.assertTrue(restored['restored'])
                    self.assertEqual(registration.read_bytes(),original)
                    self.assertTrue(all(not (root/'resource_pack'/name).exists()
                                        for name in restored['paths']))


def state(label='ui_plain'):
    setup={'model':candidate.MODEL,'model_id':12,'state':'returned'}
    ui=dict(candidate.UI,entity_id='owned')
    attachment={'id':21,'item':{'isEnchanted':False,'newAuxValue':0,'newItemName':'minecraft:diamond_sword','userData':{}},
                'offset':[0.,0.,0.],'rotation':[0.,0.,0.],'scale':1.,'item_nonmutation':True,'state':'bound'}
    journal=[{'operation':'RenderEntity:'+label,'state':'returned','value':True}]
    initial={'ui_params':ui,'actor':'owned','skeleton_setup':setup}
    native={'control':label,'actor':'owned','journal':journal,'attachments':[attachment],
            'native_item':{'id':21,'offset':[0.,0.,0.],'rotation':[0.,0.,0.],'scale':1.}}
    status={'control':label,'last_submission':ui,'ui_params':ui,'journal':journal,'attachments':[attachment],
            'skeleton_setup':setup,'model_id':31}
    return initial,status,native


class NativeIdentityGates(unittest.TestCase):
    def test_separate_actor_and_ui_model_ids_have_distinct_roles(self):
        initial,status,native=state()
        self.assertEqual(runtime.validate_state('ui_plain',status,initial,native,None),21)
        for identity in (-1,None,True,'31'):
            changed=deepcopy(status)
            changed['model_id']=identity
            with self.assertRaisesRegex(ValueError,'identity changed'):
                runtime.validate_state('ui_plain',changed,initial,native,None)
        changed=deepcopy(status)
        changed['last_submission']['entity_id']='31'
        with self.assertRaisesRegex(ValueError,'identity changed'):
            runtime.validate_state('ui_plain',changed,initial,native,None)

    def test_wrong_item_or_changed_binding_cannot_pass(self):
        initial,status,native=state()
        with self.assertRaisesRegex(ValueError,'binding identity changed'):
            runtime.validate_state('ui_plain',status,initial,native,99)
        status['attachments'][0]['item']['isEnchanted']=True
        with self.assertRaisesRegex(ValueError,'ordinary sword payload'):
            runtime.validate_state('ui_plain',status,initial,native,None)

    def test_restored_body_requires_actual_removal(self):
        initial,status,native=state('ui_body_restored')
        with self.assertRaisesRegex(ValueError,'item removal'):
            runtime.validate_state('ui_body_restored',status,initial,native,21)
        status['attachments'][0].update(state='removed',remove_result=True,remove_attempted=True)
        native['native_item']=None
        self.assertEqual(runtime.validate_state('ui_body_restored',status,initial,native,21),21)


if __name__=='__main__':
    unittest.main()
