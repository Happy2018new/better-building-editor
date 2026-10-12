"""Isolate custom-model placement from palette, overlay, and shader transforms."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from camera_projection import project_points
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, PROJECTION_STATUS, camera_restore_code
from verify_entity_appearance_visuals import require_bed_calibration
from verify_native_entity_appearances import execute
from verify_shulker_orientations import wait_camera_pose
from verify_sign_visuals import SignCheck, SAVE_HUD, RESTORE_HUD
from verify_snow_plant_visibility import changed, count, convex_hull
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

ROOT = Path(__file__).resolve().parents[1]
SETUP = '''import json,math,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
position=factory.CreatePos(player)
foot=position.GetFootPos()
dimension=factory.CreateDimension(player).GetEntityDimensionId()
base=(int(math.floor(foot[0]))+20,int(math.floor(foot[1]))+16,int(math.floor(foot[2]))-20)
platform=(base[0],base[1]-1,base[2]-4)
info=factory.CreateBlockInfo(player)
assert not hasattr(sys,'_flat_coordinate_probe')
support=(base[0],base[1],base[2]+1)
cells=[base,platform,support]
before=[info.GetBlockNew(point,dimension) for point in cells]
assert all(row and row['name']=='minecraft:air' for row in before),(cells,before)
sys._flat_coordinate_probe={'player':player,'dimension':dimension,'foot':foot,'cells':cells,'before':before,'base':base}
info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
assert info.GetBlockNew(platform,dimension)['name']=='minecraft:stone'
assert position.SetFootPos((platform[0]+.5,platform[1]+1.,platform[2]+.5))
_result=json.dumps({'base':base,'platform':platform,'support':support,'foot_before':foot,'foot_during':position.GetFootPos()})
'''
FRAME = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.projection.nbt_spatial import root_payload,scalar
saved=sys._flat_coordinate_probe
factory=api.GetEngineCompFactory()
items,info=factory.CreateItem(saved['player']),factory.CreateBlockInfo(saved['player'])
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=next((i for i in range(36) if not items.GetPlayerItem(item_type,i,True)),None)
assert slot is not None
support=(saved['base'][0],saved['base'][1],saved['base'][2]+1)
kind=%r
try:
 if kind=='empty':
  info.SetBlockNew(support,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
 name='minecraft:frame' if kind=='empty' else 'minecraft:diamond_sword'
 items.SpawnItemToPlayerInv({'itemName':name,'auxValue':0,'count':1},saved['player'],slot)
 temporary=items.GetPlayerItem(item_type,slot,True)
 assert temporary and temporary.get('count'),temporary
 use=info.PlayerUseItemToPos(support if kind=='empty' else tuple(saved['base']),item_type,slot,2)
 block=info.GetBlockNew(tuple(saved['base']),saved['dimension'])
 assert block=={'name':'minecraft:frame','aux':2},block
 nbt=info.GetBlockEntityData(saved['dimension'],tuple(saved['base']))
 root=root_payload(nbt)
 filled=bool(root.get('Item',root.get('item')))
 assert filled==(kind=='filled'),(kind,nbt)
finally:
 items.SetInvItemNum(slot,0)
 assert not items.GetPlayerItem(item_type,slot,True)
_result=json.dumps({'player_use_return':use,'block':block,'entity_nbt':nbt,'filled':filled,
 'rotation':scalar(root,'ItemRotation'),'support':support})
'''
MUTATE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._flat_coordinate_probe
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
name=%r
written=info.SetBlockNew(tuple(saved['base']),{'name':name,'aux':0},0,saved['dimension'],True,False)
readback=info.GetBlockNew(tuple(saved['base']),saved['dimension'])
assert readback['name']==name and readback['aux']==0,readback
_result=json.dumps({'write':written,'readback':readback,'base':saved['base']})
'''
CLEANUP = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._flat_coordinate_probe
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
rows=[]
for point,prior in zip(saved['cells'],saved['before']):
 info.SetBlockNew(tuple(point),prior,0,saved['dimension'],True,False)
 readback=info.GetBlockNew(tuple(point),saved['dimension'])
 rows.append({'pos':point,'expected':prior,'actual':readback,'restored':readback==prior})
assert all(row['restored'] for row in rows),rows
position=factory.CreatePos(saved['player'])
assert position.SetFootPos(tuple(saved['foot']))
assert max(abs(position.GetFootPos()[i]-saved['foot'][i]) for i in range(3))<.002
del sys._flat_coordinate_probe
_result=json.dumps(rows)
'''


def polygon(points, pose, size, fov):
    rows = project_points(points, pose['position'], pose['target'], size, fov)
    result = Image.new('L', size)
    ImageDraw.Draw(result).polygon(convex_hull((row['screenX'], row['screenY']) for row in rows), fill=255)
    return result


def read_native(check, base, name):
    return check.wait('native coordinate block replication', lambda value: value and value[0] == name,
        lambda: check.run('_result=json.dumps(b.factory.CreateBlockInfo(b.level).GetBlock(%r))' % (tuple(base),)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--camera-calibration', required=True, type=Path)
    parser.add_argument('--palette-check', action='store_true',
                        help='Also render the proxy as an ordinary logical document cell')
    parser.add_argument('--vanilla-frame', action='store_true',
                        help='Capture independently placed empty and filled vanilla frames at the same cell')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh coordinate probe report')
    calibration = json.loads(args.camera_calibration.read_text(encoding='utf8'))
    report = {'schema': 1, 'completed': False, 'passed': False, 'production_rendering_accepted': False,
              'scope': 'Actual native custom block and stone at identical integer world cell; no palette or projection actor',
              'camera_calibration': str(args.camera_calibration), 'rows': [],
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    installed = saved = daylight = hud = created = False
    try:
        with Client(timeout=30) as client:
            check = SignCheck(client, args.output, 60, native_resolution=True, background_only=True)
            require_bed_calibration(calibration)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                saved = True
                report['daylight'] = execute(client, SETUP_DAYLIGHT)
                daylight = True
                report['hud'] = check.run(SAVE_HUD)
                hud = True
                if check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('coordinate workspace closes', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                created = True
                report['fixture'] = execute(client, SETUP)
                base = report['fixture']['base']
                proxy = check.run("from modern_projection.projection import static_frame_item_data\n"
                    "_result=json.dumps(static_frame_item_data.FRAME_ITEMS[('minecraft:diamond_sword',0)]['proxies'][(2,0)])")
                report['proxy'] = proxy
                for view, offset in (('front', (0., 0., -4.)), ('tilted', (-3., -1., -4.))):
                    pose = check.run('''base=%r
offset=%r
target=tuple(v+.5 for v in base)
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((direction[0],direction[1]+180.,0.))
_result=json.dumps({'position':position,'rotation':direction,'target':target})
''' % (tuple(base), offset))
                    pose['settled'] = wait_camera_pose(check, pose)
                    captures, writes = {}, {}
                    for kind, name in (('stone', 'minecraft:stone'), ('proxy', proxy), ('air', 'minecraft:air')):
                        writes[kind] = execute(client, MUTATE % name)
                        read_native(check, base, name)
                        time.sleep(.4)
                        captures[kind] = check.capture(view + '_actual_' + kind)
                    size = captures['air']['size']
                    with Image.open(captures['air']['path']) as blank:
                        masks = {kind: changed(Image.open(captures[kind]['path']).convert('RGB'), blank.convert('RGB'), 25)
                                 for kind in ('stone', 'proxy')}
                    crop = Image.new('L', size)
                    ImageDraw.Draw(crop).rectangle((size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4), fill=255)
                    masks = {key: ImageChops.multiply(value, crop) for key, value in masks.items()}
                    cube = polygon([tuple(base[i]+d[i] for i in range(3)) for d in
                                    ((x,y,z) for x in (0.,1.) for y in (0.,1.) for z in (0.,1.))],
                                   pose, size, calibration['vertical_fov'])
                    plane = polygon([tuple(base[i]+d[i] for i in range(3)) for d in
                                     ((x,y,z) for x in (.25,.75) for y in (.25,.75) for z in (.0625,.09375))],
                                    pose, size, calibration['vertical_fov'])
                    stone_bounds, predicted = masks['stone'].getbbox(), cube.getbbox()
                    error = max(abs(stone_bounds[i]-predicted[i]) for i in range(4)) if stone_bounds else None
                    proxy_pixels = count(masks['proxy'])
                    fraction = count(ImageChops.multiply(masks['proxy'], plane.filter(ImageFilter.MaxFilter(5)))) / float(max(1, proxy_pixels))
                    row = {'view': view, 'pose': pose, 'writes': writes, 'captures': captures,
                           'stone': {'bounds': stone_bounds, 'predicted_bounds': predicted, 'max_boundary_error_pixels': error,
                                     'passed': error is not None and error <= 3},
                           'proxy': {'pixels': proxy_pixels, 'bounds': masks['proxy'].getbbox(),
                                     'expected_plane_bounds': plane.getbbox(), 'fraction_inside_expected_plane': fraction,
                                     'passed': proxy_pixels >= 80 and fraction >= .98}}
                    row['passed'] = row['stone']['passed'] and row['proxy']['passed']
                    if args.vanilla_frame:
                        vanilla = {'scope': 'Independent native PlayerUseItemToPos frame and inserted vanilla sword'}
                        for kind in ('empty', 'filled'):
                            vanilla[kind + '_input'] = execute(client, FRAME % kind)
                            read_native(check, base, 'minecraft:frame')
                            time.sleep(.5)
                            vanilla[kind] = check.capture(view + '_vanilla_frame_' + kind)
                        with Image.open(vanilla['filled']['path']) as shown, Image.open(vanilla['empty']['path']) as empty:
                            item_mask = ImageChops.multiply(changed(shown.convert('RGB'), empty.convert('RGB'), 25), crop)
                        vanilla['item_pixels'] = count(item_mask)
                        vanilla['item_bounds'] = item_mask.getbbox()
                        path = args.output.with_name(args.output.stem + '_' + view + '_vanilla_item_mask.png')
                        item_mask.save(path)
                        vanilla['mask'] = str(path)
                        row['vanilla'] = vanilla
                        execute(client, MUTATE % 'minecraft:air')
                        read_native(check, base, 'minecraft:air')
                    if args.palette_check:
                        loaded = check.run('''from modern_projection.projection.model import Document
doc=Document((8,8,8),{(3,3,3):(%r,0)},name='Ordinary custom item coordinate diagnostic')
sys._blueprint_qa_identity='flat.item.ordinary.coordinate'
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':1},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
s.origin=tuple(%r[i]-3 for i in range(3))
s.opacity=1.
s.projection_missing=False
s.projection_outline=False
b.project()
_result=json.dumps({'document_id':id(doc),'origin':s.origin,'logical_cell':(3,3,3),'proxy':%r})
''' % (proxy, tuple(base), proxy))
                        state = check.wait('ordinary custom item projection', lambda value: value['active'] and value['ready']
                            and not value['preparing'] and value['actors'] == 1 and value['mesh'],
                            lambda: check.run(PROJECTION_STATUS))
                        time.sleep(.4)
                        shot = check.capture(view + '_ordinary_palette_proxy')
                        with Image.open(shot['path']) as image, Image.open(captures['air']['path']) as blank:
                            mask = ImageChops.multiply(changed(image.convert('RGB'), blank.convert('RGB'), 25), crop)
                        pixels = count(mask)
                        fraction = count(ImageChops.multiply(mask, plane.filter(ImageFilter.MaxFilter(5)))) / float(max(1, pixels))
                        row['ordinary_palette'] = {'loaded': loaded, 'state': state, 'capture': shot,
                            'pixels': pixels, 'bounds': mask.getbbox(), 'fraction_inside_expected_plane': fraction,
                            'passed': pixels >= 80 and fraction >= .98}
                        check.run('b.stop_projection()\n_result=True')
                        row['passed'] = row['passed'] and row['ordinary_palette']['passed']
                    report['rows'].append(row)
                    write_json(args.output, report)
                report['completed'] = True
                report['passed'] = all(row['passed'] for row in report['rows'])
            finally:
                errors = []
                for label, action in (
                    ('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                    ('native', lambda: execute(client, CLEANUP) if created else True),
                    ('hud', lambda: check.run(RESTORE_HUD) if hud else True),
                    ('daylight', lambda: execute(client, RESTORE_DAYLIGHT) if daylight else True),
                    ('camera', lambda: check.run(camera_restore_code(False)) if saved else True),
                    ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                        's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True') if saved else True),
                    ('workspace', lambda: check.run(RESTORE) if installed else True)):
                    try:
                        report[label + '_restored'] = action()
                    except Exception as error:
                        errors.append(label + ': ' + str(error))
                report['cleanup_errors'] = errors
                report['restored'] = not errors
                report['passed'] = report['passed'] and report['restored']
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'passed': report['passed'], 'restored': report['restored'],
                      'rows': [{key: row[key] for key in ('view','stone','proxy','passed')} for row in report['rows']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
