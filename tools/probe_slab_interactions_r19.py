"""Background slab checks through the public fixture and Scene pointer callbacks.

Pointer callbacks exercise the live camera/picking/transaction path without
desktop input. They do not establish physical mouse or touch delivery.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from audit_native_visual_r15 import save, WGC
from capture_native_window import capture
from verify_debug_blueprints import CLIENT, INSTALL_PROBE, RESTORE, BlueprintCheck, Client, walk
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code

SOURCES = tuple('behavior_pack/modern_projection/projection/' + name + '.py' for name in (
    'slab_placement', 'camera', 'scene', 'session', 'model', 'debug_slab_blueprints',
    'debug_blueprints', 'cell', 'block_registry'))


class SlabCheck(BlueprintCheck):
    def dispatch(self, cmd, node, value):
        request = {'cmd': cmd, 'seq': uuid.uuid4().hex, 'id': node, 'value': value}
        result = self.run('scope={}\n'
            'eval(compile(%r,"<slab-pointer>","exec"),scope)\n'
            '_result=json.dumps(scope["pyreact_request"](json.loads(%r),'
            '"modern_projection.pyreact"))' % (self.bridge_source, json.dumps(request)))
        if not result.get('pyreact_ack') or result.get('error'):
            raise RuntimeError(result)
        return result

    def tap(self, point):
        tree = self.command('dump_tree')['tree']
        scene = next(node for node in walk(tree) if node.get('type') == 'Scene')
        pointer = next(node for node in walk(scene) if node.get('type') == 'Pointer')
        layout = pointer['layout']
        state = self.run('''from modern_projection.projection.camera import OrbitCamera
camera=OrbitCamera(*s.camera_pose)
camera.pan=s.camera_pan;camera.pivot=s.camera_pivot;camera.depth=s.camera_depth_pose
width,height=%r
point=tuple(%r[i]-s.scene_origin[i] for i in range(3))
unit=min(width,height)*camera.zoom*.72/max(s.scene_size)
xy=camera.project(point,s.scene_size,width,height,unit)
_result={'xy':xy,'pose':s.camera_pose,'pan':s.camera_pan,'pivot':s.camera_pivot,
 'revision':s.editor.revision,'pointer_stats':s.pointer_stats}
''' % ((layout['width'], layout['height']), tuple(point)))
        x, y = state['xy']
        if not 0 <= x < layout['width'] or not 0 <= y < layout['height']:
            raise ValueError('Slab click outside the live viewport')
        for phase in ('down', 'up'):
            self.dispatch('pointer', pointer['id'], {'phase': phase, 'x': x, 'y': y})
        state['after'] = self.run('''from modern_projection.projection.cell import encode
_result={'revision':s.editor.revision,'pointer_stats':s.pointer_stats,
 'focused':s.focused,'message':s.editor.message,
 'cells':[(pos,encode(value)) for pos,value in sorted(s.editor.document.blocks.items())]}
''')
        return state

    def settle(self):
        return self.wait('slab native preview',
            lambda row: row['ready'] and not row['pending'] and not row['running'] and
                        not row['dirty'] and not row['error'],
            lambda: self.run('''_result={'ready':s.ready,'pending':s.preview_pending,
 'running':s.tiles.running,'dirty':len(s.tiles.dirty),'error':s.preview_error}
'''))

    def pose(self, yaw, pitch, zoom=2.):
        self.run('s.camera_view(%r,%r,%r)\ns.grid=False\ns.emit()\n_result=True' % (yaw,pitch,zoom))
        self.wait('slab camera settles',
            lambda row: all(abs(row[i]-target)<.005 for i,target in enumerate((yaw,pitch,zoom))),
            lambda: self.run('_result=s.camera_pose'))
        self.settle()
        time.sleep(.2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--routes', nargs='+', choices=('editor','full','missing'),
                        default=('editor','full','missing'))
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh output directory')
    args.output.mkdir(parents=True)
    os.environ.update(MCDEV_SESSION_FILE=args.session, MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema':1,'fixture':'test.groups.slabs','completed':False,'restored':False,
              'physical_input_verified':False,'pixel_acceptance':False,
              'source_sha256':{name:hashlib.sha256((args.project/name).read_bytes()).hexdigest()
                               for name in SOURCES},'captures':{},'cases':{},'cleanup_errors':[]}
    installed = visual = False
    with Client(timeout=40) as client:
        check = SlabCheck(client,args.output/'report.json',40.)
        try:
            check.run(INSTALL_PROBE);installed=True
            check.run(SAVE_VISUAL);visual=True
            check.run('owner.open_workspace()\n_result=True')
            check.wait('open workspace',lambda row:row['open'] and not row['transition'],check.navigation)
            report['fixture_baseline'] = check.fixture(report['fixture'])
            report['captures']['gallery'] = capture(args.session,args.owner,args.output/'gallery.png',WGC)
            if 'editor' in args.routes:
                cases = (
                    ('top_face',(0.,90.),(3.5,2.5,4.5),(3,2,4),'minecraft:oak_double_slab',0),
                    ('bottom_face',(0.,-45.),(8.5,2.5,4.5),(8,2,4),'minecraft:oak_double_slab',0),
                    ('side_low',(90.,0.),(4.,1.25,4.5),(4,1,4),'minecraft:oak_slab',0),
                    ('side_high',(90.,0.),(4.,1.75,4.5),(4,1,4),'minecraft:oak_slab',1),
                    ('wet_merge',(0.,90.),(3.5,2.5,14.5),(3,2,14),'minecraft:oak_double_slab',0),
                )
                for identity,pose,point,target,name,aux in cases:
                    check.fixture(report['fixture'])
                    check.run('''s.grid=False
s.editor.material=('minecraft:oak_slab',0)
s.editor.edit_layer=2
s.choose_mode('place')
_result=True
''')
                    check.pose(*pose)
                    before = check.run('_result=s.editor.document.to_data()')
                    row=report['cases'][identity]={'target':target,'expected':(name,aux),
                                                  'tap':check.tap(point)}
                    row['result']=check.run('''from modern_projection.projection.cell import foreground,background,AIR
value=s.editor.document.get(%r)
assert foreground(value)==%r,(foreground(value),s.editor.message)
assert background(value)==AIR
_result={'foreground':foreground(value),'background':background(value),'undo':len(s.editor.undo_stack)}
''' % (target,(name,aux)))
                    check.settle()
                    report['captures'][identity]=capture(args.session,args.owner,args.output/(identity+'.png'),WGC)
                    row['undo']=check.run('s.action(s.editor.undo)\n_result=s.editor.document.to_data()')
                    if row['undo']!=before:
                        raise ValueError('Undo did not restore the complete slab document: '+identity)
                    check.run('s.action(s.editor.redo)\n_result=True')
                    check.settle()
                    row['redo']=check.run('_result=s.editor.document.to_data()')
                    save(args.output/'report.json',report)
                # Erasing a merged double is one operation, with full undo data.
                check.run('s.choose_mode("erase")\ns.erase_scope="single"\n_result=True')
                check.settle()
                before=check.run('_result=s.editor.document.to_data()')
                report['cases']['double_erase']={'tap':check.tap((3.5,3.,14.5))}
                check.run('assert s.editor.document.get((3,2,14))==("minecraft:air",0)\n_result=True')
                check.run('s.action(s.editor.undo)\n_result=True')
                if check.run('_result=s.editor.document.to_data()')!=before:
                    raise ValueError('Double-slab erase undo did not restore exact data')
            # Independent full/missing projections use the unmodified public gallery.
            for route in (route for route in args.routes if route!='editor'):
                check.fixture(report['fixture'])
                check.run('''foot=b.player_origin()
s.origin=(foot[0]-3,foot[1]+12,foot[2]-4)
s.opacity=1.;s.projection_missing=%r;s.projection_outline=False
b.project()
if navigator.top is not None:navigator.pop()
_result=True
''' % (route=='missing'))
                check.wait('slab world ready',lambda row:row['active'] and row['ready'] and not row['preparing']
                           and not row['error'],lambda:check.run('''work=b.projection_work
_result={'active':s.projection_active,'ready':work is not None and work.ready,
 'preparing':bool(b.preparing_entity),'error':work.error if work else None}
'''))
                check.run('''cam=b.factory.CreateCamera(b.level)
target=tuple(s.origin[i]+(8.,2.4,8.)[i] for i in range(3))
position=tuple(target[i]+(12.,10.,-15.)[i] for i in range(3))
rotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=True
''')
                time.sleep(.6)
                report['captures'][route]=capture(args.session,args.owner,args.output/(route+'.png'),WGC)
                check.run('b.stop_projection()\nowner.open_workspace()\n_result=True')
                check.wait('return editor',lambda row:row['open'] and not row['transition'],check.navigation)
            report['completed']=True
        finally:
            if visual:
                try:
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(False))
                    check.run('''saved=sys._blueprint_visual_saved
s.origin=saved['origin'];s.opacity=saved['opacity']
s.projection_missing=saved['missing'];s.projection_outline=saved['outline']
del sys._blueprint_visual_saved
_result=True
''')
                except Exception as error:
                    report['cleanup_errors'].append(str(error))
            if installed:
                try:
                    opened=check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    if not opened and check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                except Exception as error:
                    report['cleanup_errors'].append(str(error))
            report['restored']=not report['cleanup_errors']
            report['source_unchanged']=all(hashlib.sha256((args.project/name).read_bytes()).hexdigest()==digest
                                         for name,digest in report['source_sha256'].items())
            save(args.output/'report.json',report)
    print(json.dumps({key:report[key] for key in ('completed','restored','source_unchanged','cleanup_errors')}))


if __name__=='__main__':
    main()
