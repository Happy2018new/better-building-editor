"""Compare palette-seeded and item-placed wet actor bodies at one camera.

Run through run_live_check.py in the owner's disposable world. Native world
cells, inventory slot and rotation are restored by the existing wet harness.
This keeps original pixel acceptance and records the placement positive control.
"""
import json
import sys
import time
from PIL import Image, ImageChops, ImageDraw

import verify_wet_actor_visuals as wet
from verify_sign_visuals import SignCheck

native = wet.native
world = wet.world

PLACE = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import decode,foreground,background,actor_data
from modern_projection.projection.visible_actor import entity_nbt
from modern_projection.projection.nbt_spatial import rebase
from modern_projection.projection.block_registry import states
saved=sys._neighbor_world_saved
player=saved['player']
factory=api.GetEngineCompFactory()
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(player)
items=factory.CreateItem(player)
rotation=factory.CreateRot(player)
blockstate=factory.CreateBlockState(api.GetLevelId())
slot_kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=next((slot for slot in range(36) if not items.GetPlayerItem(slot_kind,slot,True) or
           not items.GetPlayerItem(slot_kind,slot,True).get('count')),None)
assert slot is not None,'Native item probe needs one empty inventory slot'
before=rotation.GetRot()
rows=[]
origin=%r
method=%r
dry_only=%r
apply_fixture_nbt=%r
try:
 for position,wire in saved['cells']:
  value=decode(wire)
  name,aux=foreground(value)
  if name not in ('minecraft:decorated_pot','minecraft:standing_sign'):continue
  if dry_only and background(value)[0]!='minecraft:air':
   rows.append({'position':position,'requested':wire,'method':'palette_preserved',
    'skipped_native_write':True,'placed':info.GetBlockNew(position,dimension),
    'liquid':info.GetLiquidBlock(position,dimension),'nbt':info.GetBlockEntityData(dimension,position)})
   continue
  support=(position[0],position[1]-1,position[2])
  assert info.GetBlockNew(support,dimension)['name']!='minecraft:air',(position,support)
  record=states((name,aux))
  assert record is not None,(name,aux)
  native_aux=blockstate.GetBlockAuxValueFromStates(name.encode('utf8'),record)
  assert native_aux is not None and native_aux>=0,(name,record,native_aux)
  info.SetBlockNew(position,{'name':'minecraft:air','aux':0},0,dimension,True,False)
  if method=='SetBlockNew':
   assert info.SetBlockNew(position,{'name':name.encode('utf8'),'aux':native_aux},0,dimension,True,False)
  else:
   assert method=='PlayerUseItemToPos',method
   assert rotation.SetRot((0.,180.))
   item='minecraft:oak_sign' if name=='minecraft:standing_sign' else name
   assert items.SpawnItemToPlayerInv({'itemName':item.encode('utf8'),'count':1,'auxValue':0},player,slot)
   assert info.PlayerUseItemToPos(support,slot_kind,slot,1),(name,support)
  placed=info.GetBlockNew(position,dimension)
  assert placed['name']==name,placed
  assert blockstate.SetBlockStates(position,record,dimension)
  liquid=background(value)
  liquid_result=info.SetLiquidBlock(position,{'name':liquid[0].encode('utf8'),'aux':liquid[1]},dimension)
  liquid_raw=info.GetLiquidBlock(position,dimension)
  liquid_readback=liquid_raw or {'name':'minecraft:air','aux':0}
  assert liquid_readback['name']==liquid[0] and liquid_readback.get('aux',0)==liquid[1],(position,liquid_result,liquid_readback,liquid)
  nbt=entity_nbt(actor_data(value))
  assert nbt is not None,(name,position)
  if apply_fixture_nbt:
   assert info.SetBlockEntityData(dimension,position,WorldAdapter._native_tree(rebase(nbt,origin)))
  rows.append({'position':position,'requested':wire,'method':method,'native_aux':native_aux,'placed':placed,
   'liquid_result':liquid_result,'liquid_raw':liquid_raw,
   'aligned':info.GetBlockNew(position,dimension),'liquid':liquid_readback,
   'fixture_nbt_applied':apply_fixture_nbt,'nbt':info.GetBlockEntityData(dimension,position)})
  items.SetInvItemNum(slot,0)
finally:
 items.SetInvItemNum(slot,0)
 assert rotation.SetRot(before)
assert rows,'No supported native block actor was placed'
_result=json.dumps({'rows':rows,'slot_restored':True,'rotation_restored':True})
'''

APPLY_NBT = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import decode,actor_data
from modern_projection.projection.visible_actor import entity_nbt
from modern_projection.projection.nbt_spatial import rebase
player=sys._neighbor_world_saved['player']
factory=api.GetEngineCompFactory()
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(player)
origin=%r
rows=json.loads(%r)
applied=[]
for row in rows:
 if row.get('skipped_native_write'):continue
 position=tuple(row['position'])
 nbt=entity_nbt(actor_data(decode(row['requested'])))
 assert nbt is not None,position
 assert info.SetBlockEntityData(dimension,position,WorldAdapter._native_tree(rebase(nbt,origin)))
 applied.append({'position':position,'nbt':info.GetBlockEntityData(dimension,position)})
_result=json.dumps({'rows':applied,'fixture_nbt_applied':True})
'''

PROBES = []
DRY_ONLY = False
CAPTURE_BEFORE_NBT = False
_camera_capture = world.camera_capture
_write_report = world.write_json


class NativeWorldCheck(SignCheck):
    def __init__(self, client, output, timeout):
        SignCheck.__init__(self, client, output, timeout, native_resolution=True)


def camera_capture(check, label, keep, occupied, view):
    if not label.endswith('_world'):
        return _camera_capture(check, label, keep, occupied, view)
    before_pose, before = _camera_capture(check, label + '_palette', keep, occupied, view)
    origin = check.run('_result=json.dumps(tuple(s.origin))')
    record = {'label': label, 'palette_camera': before_pose, 'palette_capture': before,
              'completed': False, 'dry_only': DRY_ONLY,
              'capture_before_nbt': CAPTURE_BEFORE_NBT,
              'scope': ('Native writes only to dry cells; wet cells remain palette-seeded' if DRY_ONLY else
                        'Same cells, NBT and camera after palette, SetBlockNew and native item placement')}
    PROBES.append(record)
    for key, method in (('set_block', 'SetBlockNew'), ('item', 'PlayerUseItemToPos')):
        placement = world.run(check.client, PLACE % (tuple(origin), method, DRY_ONLY, not CAPTURE_BEFORE_NBT))
        record[key + '_placement'] = placement
        if method == 'PlayerUseItemToPos' and any(not row.get('skipped_native_write') and
                                                row['placed']['name'] == 'minecraft:standing_sign'
                                                for row in placement['rows']):
            placement['dismiss_native_editor'] = check.client.call('mc_input', {'op': '/run', 'args': {
                'steps': [{'do': 'key', 'keys': 'esc'}, {'do': 'wait', 'ms': 250}]}})
        cells = [(tuple(row['position']), row['requested']) for row in placement['rows']]
        if CAPTURE_BEFORE_NBT:
            record[key + '_before_nbt_placement'] = placement
            record[key + '_before_nbt_replication'] = check.wait(
                'native layers and actor ownership before fixture NBT', lambda value: value['matches'],
                lambda: check.run(wet.PALETTE_PROBE % (wet.wire_json(cells), False)))
            time.sleep(1.)
            pose, capture = _camera_capture(check, label + '_' + key + '_before_nbt', keep, occupied, view)
            record[key + '_before_nbt_camera'], record[key + '_before_nbt_capture'] = pose, capture
            assert native.camera_matches(before_pose['stable'], pose['stable']), record
            after_nbt = world.run(check.client, APPLY_NBT % (tuple(origin), wet.wire_json(placement['rows'])))
            record[key + '_fixture_nbt_assignment'] = after_nbt
        diagnostics = {}
        record[key + '_client_replication'] = wet.replication(check, cells, diagnostics=diagnostics)
        record[key + '_client_replication_diagnostics'] = diagnostics
        time.sleep(1.)
        after_pose, after = _camera_capture(check, label if key == 'item' else label + '_' + key,
                                          keep, occupied, view)
        record[key + '_camera'] = after_pose
        record[key + '_capture'] = after
        assert native.camera_matches(before_pose['stable'], after_pose['stable']), record
    record.update(item_camera=after_pose, item_capture=after, completed=True)
    record['same_camera'] = native.camera_matches(before_pose['stable'], after_pose['stable'])
    assert record['same_camera'], record
    return after_pose, after


def write_report(path, report):
    probes = PROBES or report.get('native_item_world_probes', [])
    for row in report.get('cases', []):
        for view, frames in row.get('views', {}).items():
            if not frames.get('empty') or not frames.get('roi'):
                continue
            label = row['case'] + '_' + view + '_world'
            record = next((probe for probe in probes if probe['label'] == label), None)
            if record is None or not record['completed']:
                continue
            if 'native_body_controls' in record:
                continue
            metrics = {}
            keys = ('palette', 'set_block', 'item') + tuple(
                key for key in ('set_block_before_nbt', 'item_before_nbt') if key + '_capture' in record)
            for key in keys:
                capture = record[key + '_capture']
                signal = native.signal(capture['path'], frames['empty']['path'])
                cell_masks = {}
                for cell in ('keep', 'occupied'):
                    cell_mask = Image.new('L', signal.size)
                    ImageDraw.Draw(cell_mask).polygon([tuple(point) for point in frames['roi'][cell]], fill=255)
                    cell_masks[cell] = cell_mask
                roi = ImageChops.lighter(cell_masks['keep'], cell_masks['occupied'])
                with Image.open(capture['path']) as image:
                    actor = Image.new('L', signal.size)
                    actor.putdata([255 if r > b * 1.1 and r > g * .9 else 0
                                   for r, g, b in image.convert('RGB').getdata()])
                presence = native.binary(native.maximum(signal), 16)
                actor = ImageChops.multiply(ImageChops.multiply(actor, presence), roi)
                mask_path = path.with_name(path.stem + '_' + label + '_' + key + '_body.png')
                actor.save(mask_path)
                metrics[key] = {'actor_pixels_above_16': native.count(actor),
                                'cell_actor_pixels_above_16': dict((cell, native.count(
                                    ImageChops.multiply(actor, cell_mask))) for cell, cell_mask in cell_masks.items()),
                                'mask': str(mask_path.resolve())}
            record['native_body_controls'] = metrics
            record['body_control_limits'] = ('Original brown actor color mask, union of calibrated keep/occupied cells; '
                                              'glass supports and water are outside this color control.')
    report['native_item_world_probes'] = probes
    report['native_body_capture'] = {'class': 'SignCheck', 'native_resolution': True,
                                    'format': 'Lossless client-area PNG with per-capture SHA256'}
    return _write_report(path, report)


if __name__ == '__main__':
    DRY_ONLY = '--native-dry-only' in sys.argv
    if DRY_ONLY:
        sys.argv.remove('--native-dry-only')
    CAPTURE_BEFORE_NBT = '--capture-before-nbt' in sys.argv
    if CAPTURE_BEFORE_NBT:
        sys.argv.remove('--capture-before-nbt')
    world.camera_capture = camera_capture
    world.write_json = write_report
    world.BlueprintCheck = NativeWorldCheck
    if len(sys.argv) > 1 and sys.argv[1] == '--calibrate':
        del sys.argv[1]
        import verify_camera_projection as calibration
        calibration.BlueprintCheck = NativeWorldCheck
        raise SystemExit(calibration.main())
    raise SystemExit(world.main())
