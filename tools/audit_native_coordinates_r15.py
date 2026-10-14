"""Exercise explicit 3.10 native body routes in one assigned production world.

Uses existing production editor/full/missing entry points and background WGC.
Does not start games, activate windows, or write outside the disposable fixture.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from audit_native_visual_r15 import Audit, ROOT, save, WGC
from capture_native_window import capture
from verify_debug_blueprints import CLIENT
from verify_debug_visuals import PROJECTION_STATUS

NAMES = ('chest', 'copper_chest', 'ender_chest', 'bed', 'flower_pot')
POSITIONS = ((1, 1, 1), (4, 1, 1), (7, 1, 1), (10, 1, 1), (13, 1, 1))


def document_data(names=NAMES, positions=POSITIONS):
    sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
    from projection.debug_blueprints import material
    from projection.model import Document
    from projection.cell import make_cell
    from projection.visible_actor import compose_actor
    from projection.nbt_spatial import rebase
    captures = json.loads((ROOT / 'tests/data/native_actor_310_r15.json').read_text(encoding='utf8'))
    captures.update(json.loads((ROOT / 'tests/data/native_banner_310_r15.json').read_text(encoding='utf8')))
    doc = Document((16, 4, 4), name='R15 native body coordinates')
    associations = []
    for name, position in zip(names, positions):
        record = captures['minecraft:' + name]
        report = json.loads((ROOT / record['source']).read_text(encoding='utf8'))
        row = next(row for row in report['readback']['rows'] if row['name'] == 'minecraft:' + name)
        states = dict(row['states'])
        if name == 'bed':
            states['head_piece_bit'] = False
        delta = tuple(position[i] - row['pos'][i] for i in range(3))
        actor = compose_actor(record['actor'], rebase(row['nbt'], delta))
        doc.blocks[position] = make_cell(material(name, states), nbt=actor)
        if name == 'bed':
            states['head_piece_bit'] = True
            head = (position[0], position[1], position[2] + 1)
            doc.blocks[head] = make_cell(material(name, states), nbt=rebase(actor, (0, 0, 1)))
        for z in range(3):
            doc.blocks[(position[0], 0, z)] = material('stone')
        doc.blocks[(position[0] + 1, 1, 2)] = material('oak_fence')
        if name == 'wall_banner':
            doc.blocks[(position[0], position[1], 2)] = material('stone')
        associations.append({'name': name, 'position': position, 'source': record['source'],
                             'public_blueprint': ('test.connections.context' if name == 'copper_chest'
                                                  else 'test.entities.appearances' if 'banner' in name
                                                  else 'test.entities.classic')})
    return doc.to_data(), associations


LOAD = CLIENT + '''from modern_projection.projection.model import Document
from modern_projection.projection.native_render_profile import NativeRenderProfile, production_profile
from modern_projection.projection.geometry_palette import prepare_palette
assert api.GetEngineVersion()=='3.10.0.420447'
if hasattr(sys,'_native_r15_factory'):
 b.factory=sys._native_r15_factory
if True:
 sys._native_r15_factory=b.factory
 class NativeGeometryReceipt(object):
  def __init__(self,target):self.target=target
  def __getattr__(self,name):return getattr(self.target,name)
  def CombineBlockPaletteToGeometry(self,palette,name,mode=0):
   data=palette.SerializeBlockPalette()
   requested=name
   name=name+'_r15_'+str(int(time.time()*1000000))
   result=self.target.CombineBlockPaletteToGeometry(palette,name,mode)
   sys._native_r15_geometry.append({'name':name,'materials':sorted(data['common']),
    'actors':sorted(data.get('actor',{})),'result':result,'requested_name':requested})
   return result
 class NativeFactoryReceipt(object):
  def __init__(self,target):self.target=target
  def __getattr__(self,name):return getattr(self.target,name)
  def CreateBlockGeometry(self,level):
   return NativeGeometryReceipt(self.target.CreateBlockGeometry(level))
 b.factory=NativeFactoryReceipt(b.factory)
sys._native_r15_geometry=[]
if s.projection_active:b.stop_projection()
profile=%r
names=%r
if profile=='production':
 assert s.native_render_profile==production_profile(api.GetEngineVersion())
else:
 s.native_render_profile=(None if profile=='fallback' else
  NativeRenderProfile(model_local=names) if profile=='model_local' else
  NativeRenderProfile(model_local=names[:-1],context=names[-1:]) if profile=='mixed' else
  NativeRenderProfile(context=names))
doc=Document.from_data(json.loads(%r))
# Each evidence run must exercise a real upload, including equivalent fixtures.
s.tiles.cancel()
s.tiles.parts.clear()
s.tiles.context=None
s._loaded(doc)
s.camera_view(35.,25.,2.)
s.grid=False
s.emit()
owner.open_workspace()
rendered=prepare_palette(doc.palette_data(),native_render_profile=s.native_render_profile)
_result=json.dumps({'profile':profile,'engine':api.GetEngineVersion(),'size':doc.size,
 'materials':sorted(rendered['common']),'actors':sorted(rendered['actor']),
 'identity':s.native_render_profile.identity if s.native_render_profile else None})
'''

STATUS = CLIENT + '''cam=b.factory.CreateCamera(b.level)
work=b.projection_work
tracker=b.projection_occupancy
_result=json.dumps({'ready':s.ready,'preview_error':s.preview_error,'pending':s.preview_pending,
 'tile_running':s.tiles.running,'dirty':len(s.tiles.dirty),'model':s.model_name,
 'editor_camera':s.camera_pose,
 'bridge_engine_version':getattr(b,'engine_version',None),
 'geometry_receipts':getattr(sys,'_native_r15_geometry',[]),
 'profile':s.native_render_profile.identity if s.native_render_profile else None,
 'camera':cam.GetPosition(),'rotation':cam.GetCameraRotation(),'screen':b.factory.CreateGame(b.level).GetScreenSize(),
 'top_ui':api.GetTopUI(),'engine':api.GetEngineVersion(),'foot':b.player_position.GetFootPos(),
 'projection':{'active':s.projection_active,'actor':b.entity,'preparing':bool(b.preparing_entity),
  'error':work.error if work else None,'ready':work.ready if work else None,
  'parts':b.context_models.get(b.projection_mesh[1],()) if b.projection_mesh else (),
  'missing':s.projection_missing,'bank':tracker.shader.bank if tracker else None,
  'builds':tracker.builds if tracker else None,'failed':tracker.failed if tracker else None}})
'''

PROJECT = CLIENT + '''if navigator.top is not None:navigator.pop()
s.origin=(0,-57,0)
s.opacity=1.
s.projection_outline=False
s.projection_missing=%r
b.project()
_result=True
'''

CAMERA = CLIENT + '''cam=b.factory.CreateCamera(b.level)
target=(7.5,-55.8,1.5)
position=(9.5,-49.,-15.5)
rotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result=json.dumps({'camera':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
'''

ROI = CLIENT + '''cam=b.factory.CreateCamera(b.level)
rows=[]
for name,local in zip(%r,%r):
 pos=tuple(s.origin[i]+local[i] for i in range(3))
 points=[cam.WorldToScreenPoint(pos[0]+x,pos[1]+y,pos[2]+z)
  for x in (0.,1.) for y in (0.,1.) for z in (0.,2. if name=='bed' else 1.)]
 rows.append({'name':name,'position':pos,'points':points})
_result=json.dumps(rows)
'''

OCCUPY = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(player)
assert dimension==0
positions=%r
restore=%r
if not hasattr(sys,'_native_r15_occupied'):sys._native_r15_occupied={}
saved=sys._native_r15_occupied
rows=[]
for pos in positions:
 if restore:
  before=saved.pop(pos)
  info.SetBlockNew(pos,before,0,dimension,True,False)
 else:
  assert pos not in saved
  before=info.GetBlockNew(pos,dimension)
  assert before['name']=='minecraft:air',before
  saved[pos]=before
  info.SetBlockNew(pos,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
 rows.append({'pos':pos,'before':before,'after':info.GetBlockNew(pos,dimension)})
_result=json.dumps(rows)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('load', 'status', 'project', 'camera', 'capture',
                                         'hide', 'show', 'occupy', 'restore', 'view'))
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--route', choices=('fallback', 'model_local', 'context', 'mixed', 'production'), default='production')
    parser.add_argument('--missing', action='store_true')
    parser.add_argument('--yaw', type=float, default=35.)
    parser.add_argument('--pitch', type=float, default=25.)
    parser.add_argument('--zoom', type=float, default=2.)
    parser.add_argument('--bed-half', choices=('head', 'foot'))
    parser.add_argument('--family', choices=('containers', 'banners'), default='containers')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    audit = Audit(args)
    audit.env = dict(os.environ)
    report = {'action': args.action, 'session': args.session, 'owner': args.owner,
              'manual_pixel_acceptance': False}
    names, positions = NAMES, POSITIONS
    if args.family == 'banners':
        names, positions = ('standing_banner', 'wall_banner'), ((4, 1, 1), (10, 2, 1))
    if args.action == 'load':
        data, associations = document_data(names, positions)
        report['associations'] = associations
        report['result'] = audit.execute('load', LOAD % (args.route, tuple('minecraft:' + n for n in names),
                                                        json.dumps(data)))
    elif args.action == 'project':
        report['result'] = audit.execute('project', PROJECT % args.missing)
    elif args.action == 'camera':
        report['result'] = audit.execute('camera', CAMERA)
    elif args.action == 'view':
        report['result'] = audit.execute('view', CLIENT +
            's.camera_view(%r,%r,%r)\ns.emit()\n_result=s.camera_pose' %
            (args.yaw, args.pitch, args.zoom))
    elif args.action in ('hide', 'show'):
        report['result'] = audit.execute('visibility', CLIENT +
            '_result=b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(%r)' % (args.action == 'hide'))
    elif args.action in ('occupy', 'restore'):
        positions = tuple((p[0], p[1] - 57, p[2]) for p in positions)
        if args.bed_half:
            positions = ((10, -56, 2 if args.bed_half == 'head' else 1),)
        report['result'] = audit.execute('occupancy', OCCUPY % (positions, args.action == 'restore'), False)
    elif args.action == 'capture':
        report['before'] = audit.execute('before', STATUS)
        report['capture'] = capture(args.session, args.owner, args.output / 'frame.png', WGC)
        report['rois'] = audit.execute('rois', ROI % (names, positions))
        report['after'] = audit.execute('after', STATUS)
    else:
        report['result'] = audit.execute('status', STATUS)
    save(args.output / 'report.json', report)
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
