"""Importing later diagnostic variants cannot change earlier tools' contracts."""
from pathlib import Path
import subprocess
import sys
import unittest


class DiagnosticIsolation(unittest.TestCase):
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
