"""Compare native world copper chests and static proxies at identical cameras.

The owned instance reserves only confirmed air cells, uses native item placement,
reads client palettes only, and restores its world, inventory, camera and editor.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

from PIL import Image, ImageChops

from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, PROJECTION_STATUS, camera_restore_code
from verify_missing_neighbor_visuals import camera_matches, maximum
from verify_shulker_orientations import server_run
from verify_camera_projection import largest_component
from shulker_pixels import _prepared_pair

SETUP = '''import json,sys,math
import mod.server.extraServerApi as api
assert not hasattr(sys,'_copper_native_probe')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(player)
items=factory.CreateItem(player)
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=None
for candidate in range(36):
 current=items.GetPlayerItem(kind,candidate,True)
 if not current or not current.get('count'):
  slot=candidate
  break
assert slot is not None
foot=factory.CreatePos(player).GetFootPos()
target=(int(math.floor(foot[0]))+6,int(math.floor(foot[1]))+16,int(math.floor(foot[2]))+6)
reserved=[(target[0]+x,target[1]+y,target[2]+z) for x in (-1,0,1) for y in (-1,0) for z in (-1,0,1)]
for pos in reserved:assert info.GetBlockNew(pos,dimension)['name']=='minecraft:air',(pos,info.GetBlockNew(pos,dimension))
sys._copper_native_probe={'player':player,'dimension':dimension,'slot':slot,'target':target,
 'reserved':reserved,'rotation':factory.CreateRot(player).GetRot(),'cells':[]}
for pos in reserved:
 if pos[1]==target[1]-1:assert info.SetBlockNew(pos,{'name':'minecraft:stone','aux':0},0,dimension,True,True)
_result=json.dumps(sys._copper_native_probe)
'''

PLACE = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.projection.block_registry import states
saved=sys._copper_native_probe
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
items=factory.CreateItem(saved['player'])
rotation=factory.CreateRot(saved['player'])
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
name=%r
direction=%r
paired=%r
target=tuple(saved['target'])
offset={'north':(1,0,0),'south':(-1,0,0),'east':(0,0,1),'west':(0,0,-1)}[direction]
cells=[target,tuple(target[i]+offset[i] for i in range(3))] if paired else [target]
saved['cells']=cells
for pos in cells:
 support=(pos[0],pos[1]-1,pos[2])
 if info.GetBlockNew(support,saved['dimension'])['name']!='minecraft:stone':
  assert info.SetBlockNew(support,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
 assert rotation.SetRot((0.,{'north':0.,'east':90.,'south':180.,'west':270.}[direction]))
 items.SetInvItemNum(saved['slot'],0)
 items.SpawnItemToPlayerInv({'itemName':name,'count':1,'auxValue':0},saved['player'],saved['slot'])
 assert info.PlayerUseItemToPos(support,kind,saved['slot'],1)
 block=info.GetBlockNew(pos,saved['dimension'])
 assert block['name']==name and states((block['name'],block['aux']))[u'minecraft:cardinal_direction']==direction,block
items.SetInvItemNum(saved['slot'],0)
assert rotation.SetRot(saved['rotation'])
for support in saved['reserved']:
 if support[1]==target[1]-1 and info.GetBlockNew(tuple(support),saved['dimension'])['name']!='minecraft:air':
  assert info.SetBlockNew(tuple(support),{'name':'minecraft:air','aux':0},0,saved['dimension'],False,False)
_result=json.dumps({'name':name,'direction':direction,'paired':paired,'cells':cells})
'''

CLEAR = '''import sys
import mod.server.extraServerApi as api
saved=sys._copper_native_probe
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
for pos in saved['cells']:
 info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],False,False)
for pos in saved['cells']:assert info.GetBlockNew(tuple(pos),saved['dimension'])['name']=='minecraft:air'
_result=True
'''

CLEANUP = '''import sys
import mod.server.extraServerApi as api
saved=sys._copper_native_probe
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
for unused in range(2):
 for pos in saved['reserved']:info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],False,False)
for pos in saved['reserved']:assert info.GetBlockNew(tuple(pos),saved['dimension'])['name']=='minecraft:air'
items=factory.CreateItem(saved['player'])
items.SetInvItemNum(saved['slot'],0)
remaining=items.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.INVENTORY,saved['slot'],True)
assert not remaining or not remaining.get('count')
assert factory.CreateRot(saved['player']).SetRot(saved['rotation'])
del sys._copper_native_probe
_result=True
'''

CAPTURE = '''from modern_projection.projection.model import Document
from modern_projection.projection.world_capture import merge_palette
from modern_projection.projection.cell import foreground,actor_data
from modern_projection.projection.visible_actor import render_actor
cells=%r
lo=tuple(min(pos[i] for pos in cells) for i in range(3))
hi=tuple(max(pos[i] for pos in cells) for i in range(3))
size=tuple(hi[i]-lo[i]+1 for i in range(3))
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(lo,hi,False)
assert palette is not None
data=palette.SerializeBlockPalette()
doc=Document((4,3,4),name='Copper native world pixel acceptance')
origin=tuple(lo[i]-1 for i in range(3))
merge_palette(doc,data,(1,1,1),size,origin)
assert len(doc.blocks)==len(cells)
sys._copper_native_document=doc
sys._copper_native_origin=origin
sys._blueprint_qa_identity='copper.native.reference'
target=tuple((lo[i]+hi[i]+1.)/2. for i in range(3))
position=tuple(target[i]+(-3.5,-3.,-5.)[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'target':target,'rotation':rotation,'origin':origin,
 'cells':[{'pos':pos,'material':foreground(value),'actor':render_actor(actor_data(value))} for pos,value in doc.blocks.items()]})
'''

PROJECT = '''s._loaded(sys._copper_native_document)
s.origin=sys._copper_native_origin
s.opacity=1.
s.projection_missing=False
s.projection_outline=False
b.project()
_result=True
'''

CAMERA = '''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})'''


def object_frame(shown, empty, output):
    with Image.open(shown).convert('RGB') as image, Image.open(empty).convert('RGB') as background:
        if image.size != background.size:
            raise AssertionError('Native and proxy viewport differ')
        width, height = image.size
        crop = (int(width * .25), int(height * .2), int(width * .75), int(height * .8))
        first = image.crop(crop)
        delta = maximum(ImageChops.difference(image, background)).crop(crop)
    mask = largest_component(delta.point(lambda value: 255 if value > 25 else 0))
    count = mask.histogram()[255]
    bounds = mask.getbbox()
    if count < 1000 or bounds is None:
        raise AssertionError('No central chest model contributes 1000 pixels: %r' % count)
    selected = Image.new('RGB', first.size)
    selected.paste(first, mask=mask)
    selected.save(output)
    resampling = getattr(Image, 'Resampling', Image)
    return (selected.crop(bounds).resize((64, 64), resampling.BILINEAR),
            mask.crop(bounds).resize((64, 64), resampling.NEAREST),
            {'bbox': bounds, 'world_bounds': [value + crop[axis % 2] for axis, value in enumerate(bounds)],
             'pixels': count, 'crop': crop, 'mask': str(output.resolve())})


def world_alignment(native, proxy):
    first, second = native['world_bounds'], proxy['world_bounds']
    delta = [(second[axis] + second[axis + 2] - first[axis] - first[axis + 2]) / 2.
             for axis in range(2)]
    rms = math.sqrt(sum((left - right) ** 2 for left, right in zip(first, second)) / 4.)
    return {'native_world_bounds': first, 'proxy_world_bounds': second,
            'center_delta_pixels': delta, 'center_distance_pixels': math.hypot(*delta),
            'boundary_rms_pixels': rms,
            'passed': math.hypot(*delta) <= 3 and rms <= 4,
            'limits': {'center_distance_pixels': 3, 'boundary_rms_pixels': 4}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--case-limit', type=int)
    parser.add_argument('--case-start', type=int, default=0)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plans = [('chest', 'north', paired) for paired in (False, True)]
    plans += [('copper_chest', direction, paired) for direction in ('north', 'east', 'south', 'west')
             for paired in (False, True)]
    plans += [(name, 'north', paired) for name in ('exposed_copper_chest', 'weathered_copper_chest',
              'oxidized_copper_chest', 'waxed_copper_chest', 'waxed_exposed_copper_chest',
              'waxed_weathered_copper_chest', 'waxed_oxidized_copper_chest') for paired in (False, True)]
    plans = plans[args.case_start:]
    if args.case_limit:
        plans = plans[:args.case_limit]
    evidence = {'schema': 1, 'completed': False, 'restored': False, 'cases': [],
                'scope': 'Native player-placed real world chest versus actual projection at identical position/camera; client palette data only'}
    installed = visual = setup = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual = True
                if check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('close workspace', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                evidence['native_setup'] = server_run(client, SETUP)
                setup = True
                time.sleep(1.)
                for index, (name, direction, paired) in enumerate(plans):
                    native = server_run(client, PLACE % ('minecraft:' + name, direction, paired))
                    time.sleep(2.)
                    pose = check.run(CAPTURE % (native['cells'],))
                    check.wait('native camera settles', lambda value: camera_matches(value, pose), lambda: check.run(CAMERA))
                    time.sleep(.35)
                    real = check.capture('%d_native' % index)
                    server_run(client, CLEAR)
                    time.sleep(.4)
                    empty = check.capture('%d_empty' % index)
                    check.run(PROJECT)
                    state = check.wait('proxy projection ready', lambda value: value['active'] and value['ready'] and not value['preparing'],
                                       lambda: check.run(PROJECTION_STATUS))
                    if state['error']:
                        raise AssertionError(state)
                    time.sleep(.5)
                    projected = check.capture('%d_proxy' % index)
                    row = dict(native, pose=pose, native=real, empty=empty, proxy=projected, projection=state)
                    evidence['cases'].append(row)
                    try:
                        reference = object_frame(real['path'], empty['path'], args.output.with_name(args.output.stem + '_%d_native_signal.png' % index))
                        proxy = object_frame(projected['path'], empty['path'], args.output.with_name(args.output.stem + '_%d_proxy_signal.png' % index))
                        comparison = _prepared_pair(reference, proxy)
                        comparison['world_alignment'] = world_alignment(reference[2], proxy[2])
                        comparison['passed'] = (comparison['shape_iou'] >= .82 and comparison['scale_relative_error'] <= .2
                                                and comparison['texture_cosine'] is not None and comparison['texture_cosine'] >= .45
                                                and comparison['world_alignment']['passed'])
                        row.update(comparison=comparison, native_signal=reference[2], proxy_signal=proxy[2])
                    except AssertionError as error:
                        row['comparison'] = {'passed': False, 'error': str(error)}
                    write_json(args.output, evidence)
                    print(json.dumps({'case': index, 'name': name, 'direction': direction, 'paired': paired, 'comparison': row['comparison']}), flush=True)
                    check.run('b.stop_projection()\n_result=True')
                evidence['completed'] = True
                evidence['passed'] = all(row['comparison']['passed'] for row in evidence['cases'])
            finally:
                errors = []
                if visual:
                    for label, code in (('projection', 'b.stop_projection()\n_result=True'),
                                        ('camera', camera_restore_code(False)),
                                        ('fields', 'saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True')):
                        try:
                            check.run(code)
                        except Exception as error:
                            errors.append('%s: %s' % (label, error))
                if installed:
                    try:
                        was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                        check.run(RESTORE)
                        if was_open:
                            check.run('owner.open_workspace()\n_result=True')
                            check.wait('restore workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                    except Exception as error:
                        errors.append('editor: %s' % error)
                if setup:
                    try:
                        server_run(client, CLEANUP)
                    except Exception as error:
                        errors.append('native_fixture: %s' % error)
                check.run('''for name in ('_copper_native_document','_copper_native_origin'):
 if hasattr(sys,name):delattr(sys,name)
_result=True''')
                evidence['cleanup_errors'] = errors
                evidence['restored'] = not errors
                if errors and sys.exc_info()[0] is None:
                    raise AssertionError(errors)
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'completed': evidence['completed'], 'restored': evidence['restored'],
                      'passed': evidence['passed'], 'cases': len(evidence['cases'])}))
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
