"""Observe native item bindings on a temporary anchor in world and PaperDoll.

Run through run_live_check.py in an owned isolated instance. No world blocks,
inventories or library files are changed. Pixel deltas establish API rendering
capabilities only; they do not calibrate frame placement or banner dimensions.
"""
import argparse
import json
import time
from pathlib import Path

from PIL import Image, ImageChops
from verify_debug_blueprints import BlueprintCheck, Client, write_json
from verify_shulker_orientations import viewport_crop
from verify_survey_visuals import camera

SAVE = '''from modern_projection.projection.model import Document
assert not hasattr(sys,'_bound_item_probe')
assert not s.projection_active and not s.busy and s.edit_job is None and s.io_job is None
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not navigator.is_transitioning and s.pending_confirm is None and s.pending_rename is None
assert not s.sharing.opened
foot=b.factory.CreatePos(b.player).GetFootPos()
fields=('page','name','view','focus_view','section','solo_layer','focused','box_anchor',
 'canvas_x','canvas_z','paste_origin','paste_pinned','camera_pose','camera_yaw',
 'camera_pitch','zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose',
 'camera_focus_request','camera_reset_animated','progress','direct_mode','grid')
saved={'editor':s.editor,'workspace':navigator.contains('modern_projection_workspace'),
 'fields':dict((key,getattr(s,key)) for key in fields),
 'foot':foot,'entity':None,'cow':None,'item':None,'doll':None}
sys._bound_item_probe=saved
doc=Document((3,3,3),name='Temporary bound item probe')
doc.blocks[(1,1,1)]=('minecraft:stone',0)
s._loaded(doc)
s.grid=False
s.camera_pivot=(1.5,1.5,1.5)
s.camera_view(0.,0.,4.)
owner.open_workspace()
from modern_projection.projection import block_registry
_result=json.dumps({'saved':True,'foot':foot,'game_version':block_registry.source_version(),
 'palette_sha256':block_registry.fingerprint()})
'''

ACTOR = '''saved=sys._bound_item_probe
pos=(saved['foot'][0]+2.,saved['foot'][1]+1.,saved['foot'][2]+2.)
saved['entity']=b.system.CreateClientEntityByTypeStr(b'modern_projection:anchor',pos,(0.,0.))
assert saved['entity'],'Could not create temporary anchor'
saved['cow']=b.system.CreateClientEntityByTypeStr(b'minecraft:cow',(pos[0]+8.,pos[1],pos[2]),(0.,0.))
assert saved['cow'],'Could not create temporary cow'
_result=json.dumps({'entity':saved['entity'],'position':pos})
'''

DOLL = '''from modern_projection.pyreact import host
root=host._ACTIVE_HOST[0]._root_fiber
def first_tile(node):
 if getattr(node.comp_type,'__name__',None)=='PreviewTile':return node
 for child in node.child_fibers:
  found=first_tile(child)
  if found is not None:return found
tile=first_tile(root)
assert tile is not None,'No preview tile is mounted'
refs=[tile.hooks[0]['value'].current,tile.hooks[1]['value'].current]
buffer=tile.hooks[4]['value'].current
doll=refs[buffer.front].asNeteasePaperDoll()
sys._bound_item_probe['doll']=doll
_result=json.dumps({'front':buffer.front,'model_before':doll.GetModelId(),
 'position':refs[buffer.front].GetPosition(),'size':refs[buffer.front].GetSize()})
'''

STATE = '''saved=sys._bound_item_probe
item=b.factory.CreateItem(b.level)
enabled=%r
opacity=%r
if enabled and saved['item'] is None:
 saved['item']=item.BindItemToMinecraftModel(saved['entity'],
  {'newItemName':b'minecraft:diamond_sword','newAuxValue':0,'isEnchanted':False,'userData':{}},
  b'root',True,(0.,0.,0.),(0.,0.,0.),1.)
 assert saved['item']!=-1,'BindItemToMinecraftModel failed'
if not enabled and saved['item'] is not None:
 assert item.SetBindBoneForBindItem(saved['entity'],saved['item'],b'',True),'Could not remove bound item'
 saved['item']=None
b.factory.CreateModel(saved['entity']).SetEntityShadowShow(False)
b.factory.CreateModel(saved['entity']).SetEntityOpacity(opacity)
result=saved['doll'].RenderEntity({'entity_id':saved['entity'],'scale':4.,
 'render_depth':-50,'init_rot_x':0.,'init_rot_y':0.,'init_rot_z':0.}) if saved['doll'] is not None else None
cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'render_entity':result,'item':saved['item'],'opacity_requested':opacity,
 'camera_position':cam.GetPosition(),'camera_rotation':cam.GetCameraRotation(),
 'offset':item.GetBindItemOffset(saved['entity'],saved['item'],True) if enabled else None,
 'rotation':item.GetBindItemRotation(saved['entity'],saved['item'],True) if enabled else None,
 'scale':item.GetBindItemScale(saved['entity'],saved['item'],True) if enabled else None})
'''

RESTORE = '''saved=sys._bound_item_probe
if saved['item'] is not None and saved['item']!=-1:
 assert b.factory.CreateItem(b.level).SetBindBoneForBindItem(saved['entity'],saved['item'],b'',True),'Could not remove bound item'
if saved['entity']:
 b.system.DestroyClientEntity(saved['entity'])
if saved['cow']:
 b.system.DestroyClientEntity(saved['cow'])
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
s.tiles.cancel()
s.editor=saved['editor']
for key,value in saved['fields'].items():setattr(s,key,value)
s.model_revision=None
s.camera_reset_revision+=1
s.refresh_preview()
s.emit()
if not saved['workspace'] and navigator.contains('modern_projection_workspace'):navigator.pop()
del sys._bound_item_probe
_result=True
'''


def differences(left, right, threshold=24):
    if left.size != right.size:
        raise ValueError('Pixel samples need matching dimensions')
    delta = ImageChops.difference(left, right)
    maximum = ImageChops.lighter(ImageChops.lighter(*delta.split()[:2]), delta.split()[2])
    return sum(maximum.histogram()[threshold+1:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'schema':1,'completed':False,'world_read_only':True,'states':{},
        'method':'native window capture; temporary client actors; native binding and PaperDoll controls',
        'limits':['Pixel deltas do not certify pose calibration or full native item coverage.',
                  'World animation can contribute to small image deltas.',
                  'PaperDoll client entity id controls are separate from identifier controls.']}
    images = {}
    with Client(timeout=30) as client:
        check = BlueprintCheck(client,args.output/'report.json',20)
        try:
            report['saved'] = check.run(SAVE)
            report['game_version'] = report['saved']['game_version']
            report['palette_sha256'] = report['saved']['palette_sha256']
            check.wait('preview is mounted',lambda r:r['ready'],lambda:check.run(
                '_result=json.dumps({"ready":not s.preview_pending and not s.tiles.mounting and bool(s.tiles.parts)})'))
            report['actor'] = check.run(ACTOR)
            time.sleep(.5)
            pos = report['actor']['position']
            for scope in ('world','editor'):
                if scope=='world':
                    check.run("if navigator.contains('modern_projection_workspace'):navigator.pop()\n_result=True")
                    check.wait('workspace closes',lambda r:not r['open'] and not r['transition'],check.navigation)
                    camera((pos[0],pos[1],pos[2]-2.5),pos)
                    time.sleep(.5)
                else:
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('workspace opens',lambda r:r['open'] and not r['transition'],check.navigation)
                    time.sleep(.5)
                    report['doll'] = check.run(DOLL)
                for label,enabled,opacity in (('empty',False,1.),('bound',True,1.),('alpha02',True,.2),('alpha0',True,0.)):
                    report['states'][scope+'_'+label] = check.run(STATE % (enabled,opacity))
                    time.sleep(.5)
                    shot=check.capture(scope+'_'+label)
                    width,height=shot['size']
                    crop=viewport_crop(check,shot) if scope=='editor' else (width//4,height//4,3*width//4,3*height//4)
                    with Image.open(shot['path']) as source:images[scope+'_'+label]=source.convert('RGB').crop(crop)
                    images[scope+'_'+label].save(args.output/(scope+'_'+label+'_crop.png'))
                    report['states'][scope+'_'+label]['screenshot']=shot
                report[scope]={'binding_changed_pixels':differences(images[scope+'_empty'],images[scope+'_bound']),
                    'alpha02_changed_pixels':differences(images[scope+'_bound'],images[scope+'_alpha02']),
                    'alpha0_changed_pixels':differences(images[scope+'_bound'],images[scope+'_alpha0'])}
            report['controls']={}
            for name,params in (
                    ('cow_identifier',{'entity_identifier':b'minecraft:cow','scale':1.,'render_depth':-50}),
                    ('cow_client_id',{'entity_id':report['actor'].get('cow'),'scale':1.,'render_depth':-50}),
                    ('anchor_identifier',{'entity_identifier':b'modern_projection:anchor','scale':4.,'render_depth':-50}),
                    ('anchor_geometry',{'entity_id':report['actor']['entity'],'scale':4.,'render_depth':-50})):
                if name=='cow_client_id':
                    params['entity_id']=check.run("_result=sys._bound_item_probe['cow']")
                if name=='anchor_geometry':
                    report['control_geometry']=check.run('''from modern_projection.projection.model import Document
doc=Document((1,1,1))
doc.blocks[(0,0,0)]=('minecraft:stone',0)
model=b.geometry(doc)
render=b.factory.CreateActorRender(sys._bound_item_probe['entity'])
result=render.AddActorBlockGeometry(model,(-.5,0.,-.5),(0.,180.,0.))
_result=json.dumps({'model':model,'attached':result})''')
                    time.sleep(.5)
                result=check.run("saved=sys._bound_item_probe\n_result=saved['doll'].RenderEntity(%r)"%params)
                time.sleep(.6)
                shot=check.capture('control_'+name)
                crop=viewport_crop(check,shot)
                with Image.open(shot['path']) as source:frame=source.convert('RGB').crop(crop)
                frame.save(args.output/('control_'+name+'_crop.png'))
                report['controls'][name]={'result':result,'screenshot':shot,
                    'delta_from_empty':differences(images['editor_empty'],frame)}
            report['completed']=True
        finally:
            report['cleaned']=check.run(RESTORE)
            write_json(args.output/'report.json',report)
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
