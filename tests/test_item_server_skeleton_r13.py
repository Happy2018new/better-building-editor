"""Server diagnostic actor IDs never become player or client-only ownership."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_item_server_skeleton_r13 as candidate
import execute_item_server_skeleton_r13 as runtime


class ServerContracts(unittest.TestCase):
    def test_ownership_and_false_client_flag_are_exact(self):
        programs=candidate.snippets('0'*32)
        self.assertNotIn('CreateClientEntityByTypeStr',programs['install_client.py'])
        self.assertNotIn('.SetModel(',programs['install_client.py'])
        create=programs['create_server.py']
        self.assertIn('dimension,True,False)',create)
        self.assertIn('APPROVED_CLIENT_PAYLOAD',create)
        bind=programs['ui_plain_client.py']
        self.assertIn("BindItemToSkeletonModel(saved['actor'],item,'root',False",bind)
        self.assertIn("saved['current'],False)",bind)
        self.assertIn("row['id'],'',False)",programs['remove_client.py'])
        self.assertNotIn('DestroyClientEntity',programs['destroy_client.py'])
        self.assertIn("saved['actor']!=saved['player']",programs['destroy_server.py'])
        self.assertIn("DestroyEntity(saved['actor'])",programs['destroy_server.py'])
        for name,source in programs.items():
            ast.parse(source,filename=name)

    def test_server_candidate_freeze_and_original_client_builder_are_independent(self):
        original=candidate.client_route.snippets
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'candidate'
            plan=candidate.prepare(path)
            self.assertFalse(plan['is_client_entity'])
            self.assertEqual(plan['server_actor_count'],1)
            self.assertEqual(candidate.verify(path),plan)
            self.assertIs(candidate.client_route.snippets,original)
            target=path/'create_server.py'
            target.write_bytes(target.read_bytes().replace(b'dimension,True,False',b'dimension,False,True'))
            with self.assertRaisesRegex(ValueError,'Frozen candidate bytes changed'):
                candidate.verify(path)

    def test_client_install_adopt_replication_set_model_and_server_destroy_order(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'candidate'
            candidate.prepare(bundle)
            codes={name:(bundle/name).read_text(encoding='ascii') for name in
                   ('install_client.py','destroy_client.py','replication_client.py','set_model_client.py')}
            events=[]
            initial={'nonce':'0'*32,'player':'player','position':[1.,2.,3.]}
            result={'completed':False,'restored':True,'cleanup_errors':[]}
            def native_client(source):
                if source==codes['install_client.py']:
                    events.append('client_save');return initial
                if source==codes['replication_client.py']:
                    events.append('replication');return {'ready':True}
                if source==codes['set_model_client.py']:
                    events.append('set_model');return {'actor':'exact-server-actor'}
                if source==codes['destroy_client.py']:
                    events.append('client_destroy_marker');return True
                if 'approved=' in source:
                    events.append('client_adopt');return True
                self.fail('Unexpected native client code')
            check=MagicMock()
            check.run=native_client
            guard=MagicMock()
            def native_server(client,source,is_client):
                self.assertFalse(is_client)
                if 'CreateEngineEntityByTypeStr' in source:
                    events.append('server_create');return dict(initial,actor='exact-server-actor')
                events.append('server_destroy');return {'destroyed':True}
            def finite_body(bundle,output,check,guard,deadline):
                self.assertEqual(check.run(codes['install_client.py']),{'actor':'exact-server-actor'})
                check.run(codes['destroy_client.py'])
                return result
            import client_anchor_depth_owner_r15 as owner
            with patch.object(owner,'execute',side_effect=native_server), \
                    patch.object(runtime.body_runtime.shared,'execute_probe',side_effect=finite_body), \
                    patch.object(runtime.dependencies()['execute_frame_item_translation'],'save_report'):
                returned=runtime.execute_probe(bundle,Path(directory)/'out.json',check,guard,runtime.time.monotonic()+120.)
            self.assertIs(returned,result)
            self.assertEqual(events,['client_save','server_create','client_adopt','replication','set_model','server_destroy','client_destroy_marker'])
            self.assertIs(check.run,native_client)


if __name__=='__main__':
    unittest.main()
