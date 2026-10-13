"""Importing later diagnostic variants cannot change earlier tools' contracts."""
from pathlib import Path
import subprocess
import sys
import unittest


class DiagnosticIsolation(unittest.TestCase):
    def test_owner_entrypoint_and_contract_stay_bound_to_each_variant(self):
        root=Path(__file__).resolve().parents[1]
        script='''
import sys
sys.path.insert(0,'tools')
import client_anchor_depth_owner_r15 as old
fields=('runtime','OWNER','ENTRYPOINT','PREFIX','CANDIDATE','owner_contract','OwnerGuard','READINESS')
before={field:getattr(old,field) for field in fields}
import item_skeleton_owner_r13 as body
body_before={field:getattr(body.shared,field) for field in fields}
import item_server_skeleton_owner_r13 as server
server_before={field:getattr(server.shared,field) for field in fields}
import item_glint_owner_r13 as glint
glint_before={field:getattr(glint.shared,field) for field in fields}
import item_world_glint_owner_r13 as world
world_before={field:getattr(world.shared,field) for field in fields}
import item_scaffold_readonly_owner_r13 as read
import probe_item_model_resolution_r13 as resolve
for module,values in ((old,before),(body.shared,body_before),(server.shared,server_before),(glint.shared,glint_before),(world.shared,world_before)):
 assert all(getattr(module,field)==value for field,value in values.items()),module.__name__
owners=(old,body.shared,server.shared,glint.shared,world.shared,read.shared,resolve.shared)
assert len({id(module) for module in owners})==len(owners)
for module in owners:
 assert sys.modules[module.__name__] is module
assert str(body.shared.ENTRYPOINT).endswith('item_skeleton_owner_r13.py')
assert str(server.shared.ENTRYPOINT).endswith('item_server_skeleton_owner_r13.py')
assert str(glint.shared.ENTRYPOINT).endswith('item_glint_owner_r13.py')
assert str(world.shared.ENTRYPOINT).endswith('item_world_glint_owner_r13.py')
assert body.shared.runtime is body.runtime and server.shared.runtime is server.runtime
assert glint.shared.runtime is glint.runtime and world.shared.runtime is world.runtime
assert read.shared.runtime is read.runtime
'''
        result=subprocess.run([sys.executable,'-c',script],cwd=str(root),capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_all_r13_variant_imports_leave_prior_runtime_functions_and_candidates_unchanged(self):
        root=Path(__file__).resolve().parents[1]
        script='''
import sys
sys.path.insert(0,'tools')
import execute_client_anchor_depth_candidate_r15 as old
before={name:getattr(old,name) for name in ('candidate','execute_probe','validate_state','score_probe','layout_readback')}
import execute_item_skeleton_candidate_r13 as body
body_before=(body.candidate,body.shared.candidate,body.shared.validate_state,body.shared.score_probe)
import execute_item_server_skeleton_r13 as server
server_before=(server.candidate,server.body_runtime.candidate,server.body_runtime.shared.candidate)
import prepare_item_glint_r13 as ui_candidate
ui_before=(ui_candidate.PHASE,ui_candidate.POSE,ui_candidate.ITEM_SCALE,ui_candidate.STATES)
import execute_item_glint_r13 as glint
glint_before=(glint.candidate,glint.shared.candidate,glint.shared.validate_state,glint.shared.score_probe)
import execute_item_world_glint_r13 as world
assert all(getattr(old,name) is value for name,value in before.items())
assert body_before==(body.candidate,body.shared.candidate,body.shared.validate_state,body.shared.score_probe)
assert server_before==(server.candidate,server.body_runtime.candidate,server.body_runtime.shared.candidate)
assert ui_before==(ui_candidate.PHASE,ui_candidate.POSE,ui_candidate.ITEM_SCALE,ui_candidate.STATES)
assert glint_before==(glint.candidate,glint.shared.candidate,glint.shared.validate_state,glint.shared.score_probe)
assert len({id(old),id(body.shared),id(server.body_runtime.shared),id(glint.shared),id(world.shared)})==5
for module in (body.shared,server.body_runtime,server.body_runtime.shared,glint.server,glint.shared,world.ui,world.shared):
 assert sys.modules[module.__name__] is module
'''
        result=subprocess.run([sys.executable,'-c',script],cwd=str(root),capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
