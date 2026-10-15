"""Compare public portal fixtures against real blocks at the same world camera.

This diagnostic does not qualify the renderer. All world writes have an owned
server journal; captures use WGC without activating the game.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from PIL import Image

from audit_native_visual_r15 import save, WGC
from capture_native_window import capture
from probe_portal_product_r16 import document, SOURCES, RESOURCES
from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, return_value
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code

SERVER = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(player)
assert dimension==0
'''
PLACE = SERVER + '''assert not hasattr(sys,'_portal_reference_r19'), 'Restore the previous native fixture'
rows=%r
saved=[]
sys._portal_reference_r19=saved
for pos,material in rows:
 before=info.GetBlockNew(pos,dimension)
 assert before and before['name']=='minecraft:air',(pos,before)
 saved.append({'pos':pos,'block':before,'nbt':info.GetBlockEntityData(dimension,pos)})
 info.SetBlockNew(pos,{'name':material[0],'aux':material[1]},0,dimension,True,False)
 actual=info.GetBlockNew(pos,dimension)
 assert actual['name']==material[0] and actual['aux']==material[1],(pos,actual,material)
_result=json.dumps([dict(row,actual=info.GetBlockNew(row['pos'],dimension),
 nbt_actual=info.GetBlockEntityData(dimension,row['pos'])) for row in saved])
'''
RESTORE_NATIVE = SERVER + '''rows=getattr(sys,'_portal_reference_r19',[])
result=[]
for row in reversed(rows):
 info.SetBlockNew(row['pos'],row['block'],0,dimension,True,False)
 if row['nbt']:assert info.SetBlockEntityData(dimension,row['pos'],row['nbt'])
 actual=info.GetBlockNew(row['pos'],dimension)
 assert actual==row['block'],(row['pos'],actual,row['block'])
 result.append({'pos':row['pos'],'actual':actual})
if hasattr(sys,'_portal_reference_r19'):del sys._portal_reference_r19
_result=json.dumps(result)
'''


def server(check, code):
    result = return_value(check.client.call('execute_code', {
        'code': code, 'is_client': False, 'direct_return': True}))
    if not isinstance(result, str):
        raise ValueError('Server diagnostic did not return its structured result')
    return json.loads(result)


def world_ready(check):
    return check.wait('portal world owner',
        lambda row: row['active'] and row['ready'] and not row['preparing'] and not row['error'],
        lambda: check.run('''work=b.projection_work
_result={'active':s.projection_active,'ready':work is not None and work.ready,
 'preparing':bool(b.preparing_entity),'error':str(work.error or '') if work else ''}
'''))


def view(check, offset):
    requested = check.run('''cam=b.factory.CreateCamera(b.level)
target=tuple(s.origin[i]+(3.8,3.6,3.5)[i] for i in range(3))
position=tuple(target[i]+%r[i] for i in range(3))
rotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result={'position':position,'rotation':(rotation[0],rotation[1]+180.,0.)}
''' % (offset,))
    def current():
        return check.run('''cam=b.factory.CreateCamera(b.level)
_result={'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),
 'face_points':[(face,[cam.WorldToScreenPoint(*(tuple(s.origin[i]+p[i] for i in range(3))))
  for p in points]) for face,points in (
  ('north',((3.,3.,3.),(4.,3.,3.),(4.,4.,3.),(3.,4.,3.))),
  ('top',((3.,4.,3.),(4.,4.,3.),(4.,4.,4.),(3.,4.,4.))))]}
''')
    check.wait('requested native portal camera',
        lambda row: all(abs(row['position'][i]-requested['position'][i]) < .002 for i in range(3)) and
        all(abs((row['rotation'][i]-requested['rotation'][i]+180.) % 360.-180.) < .05 for i in range(2)), current)
    result = current()
    result['requested'] = requested
    return result


def portal_pixels(path):
    """Reject blank/old sky captures before treating them as a reference."""
    with Image.open(path) as image:
        values = np.asarray(image.convert('RGB'))
    height, width = values.shape[:2]
    region = values[round(height*.2):round(height*.75), round(width*.3):round(width*.7)]
    dark = region.max(axis=2) < 95
    color = region.max(axis=2).astype(int)-region.min(axis=2).astype(int)
    stars = dark & (color > 8)
    return {'dark_pixels': int(dark.sum()), 'colored_dark_pixels': int(stars.sum()),
            'visible': bool(dark.sum() > 2000 and stars.sum() > 100)}


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ.update(MCDEV_SESSION_FILE=args.session, MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema': 1, 'fixture': 'test.dynamic.portals', 'completed': False,
              'restored': False, 'pixel_acceptance': False, 'cleanup_errors': [],
              'captures': {}, 'rows': {}, 'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source_sha256': {p: hashlib.sha256((args.project / p).read_bytes()).hexdigest()
                                for p in SOURCES + RESOURCES},
              'native_adapter': args.native_adapter}
    installed = visual = native = False
    with Client(timeout=30) as client:
        check = BlueprintCheck(client, args.output / 'report.json', 40.)
        try:
            check.run(INSTALL_PROBE)
            installed = True
            check.run(SAVE_VISUAL)
            visual = True
            if args.native_adapter:
                report['adapter'] = check.run('''from modern_projection.projection.portal_profile import candidate_profile
sys._portal_reference_profile=s.portal_profile
profile=candidate_profile()
profile.world_models=dict((key,'r19_native_portal_'+key+'_world') for key in profile.world_models)
s.portal_profile=profile
_result=profile.world_models
''')
            for family in args.families:
                data = document(family)
                check.run('''from modern_projection.projection.model import Document
s._loaded(Document.from_data(json.loads(%r)))
foot=b.player_origin()
s.origin=(foot[0],foot[1]+12,foot[2]);s.opacity=1.
s.projection_missing=False;s.projection_outline=False
b.project()
if navigator.top is not None:navigator.pop()
_result={'origin':s.origin,'source':s.editor.document.to_data()}
''' % json.dumps(data))
                report['rows'][family] = {'ready': world_ready(check)}
                native_rows = check.run('''from modern_projection.projection.cell import foreground
_result=[(tuple(s.origin[i]+p[i] for i in range(3)),foreground(value))
 for p,value in sorted(s.editor.document.blocks.items())]
''')
                native_rows = [(tuple(pos), tuple(material)) for pos, material in native_rows]
                for route in ('candidate', 'native'):
                    if route == 'native':
                        check.run('b.stop_projection()\n_result=True')
                        native = True
                        report['rows'][family]['native_blocks'] = server(check, PLACE % (native_rows,))
                    for name, offset in (('front', (0., 0., -4.5)),
                                         ('oblique', (3.2, 2.2, -4.5)),
                                         ('far', (6.4, 4.4, -9.))):
                        label = family + '_' + route + '_' + name
                        camera = view(check, offset)
                        time.sleep(.6)
                        receipt = capture(args.session, args.owner, args.output / (label + '.png'), WGC)
                        pixels = portal_pixels(args.output / (label + '.png'))
                        report['captures'][label] = {'capture': receipt, 'camera': camera, 'visibility': pixels}
                        save(args.output / 'report.json', report)
                        # A low portal plane can be edge-on in the front sentinel.
                        if family == 'end_gateway' and not pixels['visible']:
                            raise ValueError('Portal surface is absent from the actual capture: '+label)
                report['rows'][family]['restore_native'] = server(check, RESTORE_NATIVE)
                native = False
            report['completed'] = True
        finally:
            if native:
                try:
                    report['native_finally'] = server(check, RESTORE_NATIVE)
                except Exception as error:
                    report['cleanup_errors'].append('native: ' + str(error))
            if visual:
                try:
                    check.run('b.stop_projection()\n_result=True')
                    if args.native_adapter:
                        check.run('s.portal_profile=sys._portal_reference_profile\ndel sys._portal_reference_profile\n_result=True')
                    check.run(camera_restore_code(False))
                    check.run('''saved=sys._blueprint_visual_saved
s.origin=saved['origin'];s.opacity=saved['opacity']
s.projection_missing=saved['missing'];s.projection_outline=saved['outline']
del sys._blueprint_visual_saved
_result=True
''')
                except Exception as error:
                    report['cleanup_errors'].append('visual: ' + str(error))
            if installed:
                try:
                    opened = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    if not opened and check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                except Exception as error:
                    report['cleanup_errors'].append('editor: ' + str(error))
            report['restored'] = not report['cleanup_errors']
            report['source_unchanged'] = all(hashlib.sha256((args.project / p).read_bytes()).hexdigest() == sha
                                           for p, sha in report['source_sha256'].items())
            save(args.output / 'report.json', report)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged', 'cleanup_errors')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--families', nargs='+', choices=('end_gateway', 'end_portal'),
                        default=('end_gateway', 'end_portal'))
    parser.add_argument('--native-adapter', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
