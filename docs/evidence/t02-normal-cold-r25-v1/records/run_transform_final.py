"""R25 bounded captures using the existing strict transform runtime driver."""
from pathlib import Path
import sys,time,json,os,hashlib
ROOT=Path(__file__).resolve().parents[3]
PROJECT=Path('D:\\Happy2018newの个人文件\\GitHub\\better-building-editor\\.runtime\\projects\\r25-t02-normal-v1')
sys.path.insert(0,str(PROJECT/'tools'))
CAPTURE=ROOT/'.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
assert hashlib.sha256(CAPTURE.read_bytes()).hexdigest()=='cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
os.environ['MCDEV_NATIVE_CAPTURE_EXE']=str(CAPTURE)
os.environ['MCDEV_ALLOW_USER_FOREGROUND']='0'
import verify_transform_runtime_r23 as base
from verify_sign_visuals import SignCheck
from verify_debug_visuals import world_closeup as original_world
class BoundedCheck(SignCheck):
    def capture(self,label,tree=None):
        return SignCheck.capture(self,label,None)
def bounded_editor(check,label,focus,zoom):
    check.run('s.focused=%r\ns.locate_selected()\n_result=True' % (tuple(focus),))
    check.wait('focus consumed',lambda row:row['request'] is None and row['pivot'] is not None,
               lambda:check.run('_result=json.dumps({"request":s.camera_focus_request,"pivot":s.camera_pivot})'))
    check.run('s.camera_view(35.,25.,%r)\n_result=True' % zoom)
    pose=check.wait('editor pose',lambda row:abs(row['pose'][2]-zoom)<.01,
                    lambda:check.run('_result=json.dumps({"pose":s.camera_pose,"pivot":s.camera_pivot,"focus":s.focused})'))
    time.sleep(.3)
    pose['screenshot']=check.capture(label+'_editor_closeup')
    pose['bounded_tree_capture']=True
    return pose
def bounded_world(check,label,focus,offset,opacity,projection_height=64):
    if label.startswith('t05'):
        focus=(13,2,7)
        offset=(-28.,22.,-35.)
    return original_world(check,label,focus,offset,opacity,projection_height=projection_height)
base.SignCheck=BoundedCheck
base.editor_closeup=bounded_editor
base.world_closeup=bounded_world
if __name__=='__main__':base.main()
