"""Background acceptance of the public banner gallery on one owned 3.10 game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from audit_native_visual_r15 import Audit, ROOT, WGC, save
from audit_native_coordinates_r15 import LOAD, PROJECT, STATUS, OCCUPY
from capture_native_window import capture
from verify_debug_blueprints import CLIENT

FAMILY = ('minecraft:standing_banner', 'minecraft:wall_banner')
OWNED_SOURCES = (
    'behavior_pack/modern_projection/projection/native_render_profile.py',
    'behavior_pack/modern_projection/projection/debug_banner_blueprints.py',
    'behavior_pack/modern_projection/projection/banner_fixture_data.py',
    'behavior_pack/modern_projection/projection/entity_render.py',
    'resource_pack/shaders/glsl/modern_projection_native_preview_banner.vertex',
    'resource_pack/shaders/glsl/modern_projection_native_preview_banner.fragment')

DOCUMENT = CLIENT + '''from modern_projection.projection.cell import foreground,background,actor_data
from modern_projection.projection.entity_render import native_actor
rows=[]
for pos,value in sorted(s.editor.document.blocks.items()):
 for layer,material in enumerate((foreground(value),background(value))):
  if material[0] in %r:
   rows.append({'pos':pos,'layer':layer,'material':material,'actor':native_actor(material,actor_data(value))})
_result=json.dumps({'rows':rows,'saved_document':s.editor.document.to_data()})
'''


def document(transform='identity'):
    import sys
    sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
    from projection.debug_banner_blueprints import METADATA, populate
    from projection.debug_blueprints import Fixture
    from projection.model import Editor
    from projection.storage import Selection
    doc = populate(Fixture(METADATA))
    editor = Editor(doc)
    if transform != 'identity':
        editor.selection = Selection(editor.document.blocks)
        editor._transform(transform)
    return json.loads(json.dumps(editor.document.to_data()))


class BannerAudit(Audit):
    def settle(self, projection=False):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            result = self.execute('settle', STATUS)
            state = result['projection']
            if result['preview_error'] or state['error'] or state['failed']:
                raise ValueError('Banner geometry failed: ' + repr(result))
            ready = (state['active'] and not state['preparing'] and state['ready']) if projection else (
                result['ready'] and not result['pending'] and not result['tile_running'] and not result['dirty'])
            if ready:
                time.sleep(.6)
                return self.execute('settled', STATUS)
            time.sleep(.4)
        raise TimeoutError('Banner geometry did not settle')

    def frame(self, label):
        before = self.execute(label + '_before', STATUS)
        receipt = capture(self.args.session, self.args.owner, self.args.output / (label + '.png'), WGC)
        after = self.execute(label + '_after', STATUS)
        if before['camera'] != after['camera'] or before['editor_camera'] != after['editor_camera']:
            raise ValueError('Banner camera changed during capture')
        return {'before': before, 'capture': receipt, 'after': after}

    def load(self, transform='identity', candidate=True):
        data = document(transform)
        value = self.execute('load_' + transform, LOAD % (
            'model_local' if candidate else 'production', FAMILY, json.dumps(data)))
        state = self.settle()
        actual = self.execute('document_' + transform, DOCUMENT % (FAMILY,))
        if actual['saved_document'] != data:
            raise ValueError('Runtime load changed the saved banner payload')
        return {'loaded': value, 'ready': state, 'document': actual}

    def view(self, yaw=35., zoom=2., depth=0.):
        return self.execute('view', CLIENT +
            's.camera_view(%r,25.,%r)\ns.camera_depth=%r\ns.emit("view")\n_result=True' % (yaw, zoom, depth))

    def camera(self):
        return self.execute('world_camera', CLIENT + '''cam=b.factory.CreateCamera(b.level)
target=tuple(s.origin[i]+(7.5,1.2,5.)[i] for i in range(3))
position=tuple(s.origin[i]+(14.5,11.,-13.)[i] for i in range(3))
rot=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
''')


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    audit = BannerAudit(args)
    report = {'schema': 1, 'engine': '3.10.0.420447', 'fixture': 'test.entities.banners',
              'candidate': not args.production, 'completed': False, 'restored': False,
              'captures': {}, 'rows': {}, 'cleanup_errors': [], 'manual_pixel_acceptance': False,
              'source_sha256': {name: hashlib.sha256((args.project / name).read_bytes()).hexdigest()
                                for name in OWNED_SOURCES}}
    occupied = ()
    try:
        report['initial'] = audit.execute('initial', STATUS)
        if args.stage == 'editor':
            for transform in ('identity', 'rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_z'):
                report['rows'][transform] = audit.load(transform, candidate=not args.production)
                for yaw in (35., 215.):
                    audit.view(yaw)
                    time.sleep(1.)
                    label = 'editor_%s_yaw%d' % (transform, yaw)
                    report['captures'][label] = audit.frame(label)
                    save(args.output / 'report.json', report)
            report['rows']['identity'] = audit.load(candidate=not args.production)
            for zoom in (1., 2., 3.):
                audit.view(35., zoom)
                time.sleep(1.)
                label = 'editor_zoom%d' % zoom
                report['captures'][label] = audit.frame(label)
            for depth in (8.5, 0.):
                audit.view(35., 3., depth)
                time.sleep(1.)
                label = 'editor_depth' + str(depth).replace('.', '_')
                report['captures'][label] = audit.frame(label)
            audit.view()
            for mode, layer in (('single', 1), ('single', 2), ('section', 1), ('full', 1)):
                audit.execute('layers', CLIENT + 's.layer(%r)\ns.display_mode(%r)\n_result=True' % (layer, mode))
                audit.settle()
                label = 'editor_%s_layer%d' % (mode, layer)
                report['captures'][label] = audit.frame(label)
            audit.execute('hidden_layer', CLIENT + 's.toggle_layer("hide",1)\n_result=True')
            audit.settle()
            report['captures']['editor_hidden1'] = audit.frame('editor_hidden1')
            audit.execute('restore_layer', CLIENT + 's.toggle_layer("hide",1)\n_result=True')
            audit.settle()
            report['captures']['editor_restored1'] = audit.frame('editor_restored1')
            for layer in (2, 0, 1):
                audit.execute('edit_layer', CLIENT + 's.set_editor("edit_layer",%r)\n_result=True' % layer)
                time.sleep(.6)
                label = 'editor_edit_layer%d' % layer
                report['captures'][label] = audit.frame(label)
        elif args.stage == 'world':
            for transform in ('identity', 'rotate_y90', 'mirror_x', 'mirror_z'):
                report['rows'][transform] = audit.load(transform, candidate=not args.production)
                for missing in (False, True):
                    project_code = (PROJECT % missing).replace('s.origin=(0,-57,0)',
                        'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+32,int(foot[2]))')
                    audit.execute('project', project_code)
                    audit.settle(True)
                    origin = audit.execute('origin', CLIENT + '_result=json.dumps(s.origin)')
                    positions = [tuple(p['pos'][i] + origin[i] for i in range(3))
                                 for p in report['rows'][transform]['document']['rows']]
                    audit.camera()
                    time.sleep(.7)
                    label = '%s_%s' % ('missing' if missing else 'full', transform)
                    report['captures'][label] = audit.frame(label)
                    if missing:
                        occupied = tuple(positions[index] for index in (1, 4))
                        report['rows'][label + '_occupied'] = audit.execute('occupy', OCCUPY % (occupied, False), False)
                        time.sleep(4.)
                        report['captures'][label + '_occupied'] = audit.frame(label + '_occupied')
                        report['rows'][label + '_restored'] = audit.execute('restore', OCCUPY % (occupied, True), False)
                        occupied = ()
                        time.sleep(4.)
                        report['captures'][label + '_restored'] = audit.frame(label + '_restored')
                    audit.execute('stop_projection', CLIENT + 'b.stop_projection()\n_result=True')
                save(args.output / 'report.json', report)
        elif args.stage == 'opacity':
            report['rows']['identity'] = audit.load(candidate=not args.production)
            project_code = (PROJECT % False).replace('s.origin=(0,-57,0)',
                'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+32,int(foot[2]))')
            audit.execute('project', project_code)
            audit.settle(True)
            audit.camera()
            for opacity in (1., .45, 0.):
                audit.execute('opacity', CLIENT +
                    's.range_value("opacity",%r,False)\n'
                    '_result=json.dumps({"opacity":s.opacity,"uniforms":b.projection_shader.uniforms})' % opacity)
                time.sleep(1.)
                label = 'opacity_' + str(opacity).replace('.', '_')
                report['captures'][label] = audit.frame(label)
        else:
            raise ValueError('Unknown stage')
        report['completed'] = True
    finally:
        if occupied:
            try:
                audit.execute('restore_occupancy_final', OCCUPY % (occupied, True), False)
            except Exception as error:
                report['cleanup_errors'].append(str(error))
        try:
            report['restoration'] = audit.execute('cleanup', CLIENT + '''b.stop_projection()
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(False)
cam.LockModCameraYaw(False)
_result=True
''')
            report['restored'] = not report['cleanup_errors']
        except Exception as error:
            report['cleanup_errors'].append(str(error))
        report['source_unchanged'] = all(hashlib.sha256((args.project/name).read_bytes()).hexdigest() == value
                                       for name, value in report['source_sha256'].items())
        save(args.output / 'report.json', report)
    print(json.dumps({'completed': report['completed'], 'captures': len(report['captures']),
                      'restored': report['restored'], 'source_unchanged': report['source_unchanged']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=('editor', 'world', 'opacity'), required=True)
    parser.add_argument('--production', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
