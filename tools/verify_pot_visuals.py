"""Compare public pottery artwork with real native pots at identical cameras."""
import argparse
import json
import math
import sys
import time
from pathlib import Path

from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, PROJECTION_STATUS, camera_restore_code
from verify_native_entity_appearances import execute, replicated_palettes
from verify_native_pot_fields import SETUP, WRITE, READ, CLEANUP, SHERDS
from verify_sign_visuals import refresh, SignCheck
from verify_shulker_orientations import viewport_crop, wait_camera_pose
from PIL import Image, ImageChops
from verify_copper_chest_render import object_frame, world_alignment, maximum, largest_component
from shulker_pixels import _prepared_pair
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

NEAR_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._native_pot_fields
f=api.GetEngineCompFactory()
position=f.CreatePos(saved['player'])
if 'player_foot_before' not in saved:saved['player_foot_before']=position.GetFootPos()
target=saved['target']
offset=%r
platform=(target[0]+(3 if offset[0]>0 else -2),target[1]-1,
          target[2]+(3 if offset[2]>0 else -3))
info=f.CreateBlockInfo(saved['player'])
platforms=saved.setdefault('platforms',[])
if platform not in platforms:
 assert info.GetBlockNew(platform,saved['dimension'])['name']=='minecraft:air'
 platforms.append(platform)
info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
foot=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
assert position.SetFootPos(foot)
_result=json.dumps({'expected':foot,'before':saved['player_foot_before'],'platform':platform})
'''

RESTORE_PLAYER = '''import sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_native_pot_fields',{})
f=api.GetEngineCompFactory()
if 'player_foot_before' in saved:
 assert f.CreatePos(saved['player']).SetFootPos(tuple(saved['player_foot_before']))
for platform in saved.get('platforms',[]):
 info=f.CreateBlockInfo(saved['player'])
 info.SetBlockNew(tuple(platform),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
 assert info.GetBlockNew(tuple(platform),saved['dimension'])['name']=='minecraft:air'
_result=True
'''

CLEAR_POT = '''import sys
import mod.server.extraServerApi as api
saved=sys._native_pot_fields
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
info.SetBlockNew(saved['target'],{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
assert info.GetBlockNew(saved['target'],saved['dimension'])['name']=='minecraft:air'
_result=True
'''

LOAD = '''from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
from modern_projection.projection.cell import rebase,transform
from modern_projection.projection.model import Document
case=VISUAL_CASES['pot_artwork']
identity=%r
row=next(row for row in case['cases'] if row['id']==identity)
focus=case['focus']
delta=tuple(focus[axis]-row['position'][axis] for axis in range(3))
doc=Document(case['isolated_size'],name='Pot artwork '+identity)
doc.blocks[focus]=rebase(build(case['fixture']).get(row['position']),delta)
operation=%r
if operation:doc.blocks[focus]=transform(doc.blocks[focus],operation)
if %r:doc.blocks[focus]=('minecraft:air',0)
sys._blueprint_qa_identity=case['fixture']+'.'+identity
sys._blueprint_qa_nonce+=1
s._loaded(doc)
s.editor._restore_selection(s.editor._selection_state(()))
s.touch_mode=True
metadata={'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)}
sys._blueprint_qa_expected={'metadata':metadata,'editor_id':id(s.editor),
 'document_id':id(doc),'previous_document_id':None}
s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*case['camera']['editor'])
s.grid=False
s.emit()
_result=json.dumps({'metadata':metadata,'editor_id':id(s.editor),'document_id':id(doc)})
'''

CAMERA = '''target,offset=%r,%r
center=tuple(v+.5 for v in target)
position=tuple(center[axis]+offset[axis] for axis in range(3))
rotation=api.GetRotFromDir(tuple(center[axis]-position[axis] for axis in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'position':position,'rotation':rotation,'target':center})
'''


def close_workspace(check):
    if check.navigation()['open']:
        check.run('navigator.pop()\n_result=True')
        check.wait('workspace closes',lambda row:not row['open'] and not row['transition'],check.navigation)


def reflected_reference(direction,operation,sherds):
    if operation is None:return direction,sherds
    faces=((0,-1),(-1,0),(1,0),(0,1))
    fronts=((0,1),(-1,0),(0,-1),(1,0))
    def rotate(normal,turns):
        x,z=normal
        for unused in range(turns):x,z=-z,x
        return x,z
    def reflect(normal):
        x,z=normal
        return (-x,z) if operation=='mirror_x' else (x,-z)
    expected_direction=fronts.index(reflect(fronts[direction]))
    artwork={reflect(rotate(face,direction)):name for face,name in zip(faces,sherds)}
    return expected_direction,tuple(artwork[rotate(face,expected_direction)] for face in faces)


def editor_offset(angles, distance):
    yaw, pitch = (math.radians(value) for value in angles[:2])
    return (distance*math.sin(yaw)*math.cos(pitch), distance*math.sin(pitch),
            distance*math.cos(yaw)*math.cos(pitch))


def editor_object_frame(shown, empty, output):
    if shown['crop'] != empty['crop']:
        raise AssertionError('Actual editor viewport changed between shown and empty')
    with Image.open(shown['path']) as shown_image, Image.open(empty['path']) as empty_image:
        first = shown_image.convert('RGB').crop(shown['crop'])
        second = empty_image.convert('RGB').crop(empty['crop'])
    delta = maximum(ImageChops.difference(first, second))
    mask = largest_component(delta.point(lambda value: 255 if value > 25 else 0))
    pixels, bounds = mask.histogram()[255], mask.getbbox()
    if pixels < 1000 or bounds is None:
        raise AssertionError('Editor pot does not contribute 1000 viewport pixels: %r' % pixels)
    selected = Image.new('RGB', first.size)
    selected.paste(first, mask=mask)
    selected.save(output)
    return (selected.crop(bounds).resize((64,64),Image.Resampling.BILINEAR),
            mask.crop(bounds).resize((64,64),Image.Resampling.NEAREST),
            {'bbox':bounds,'pixels':pixels,'crop':shown['crop'],'mask':str(output.resolve())})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--direction',type=int,action='append',choices=range(4))
    parser.add_argument('--refresh',action='store_true')
    parser.add_argument('--native-resolution', action='store_true',
                        help='Use the owner-bound native background PNG capture helper')
    parser.add_argument('--operation',choices=('mirror_x','mirror_z'),
                        help='Compare transformed blueprint with independently reflected native artwork')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    report={'schema':1,'completed':False,'passed':False,'cases':[],
            'scope':'Public NBT-only fixture; native/editor/projection body and artwork, native/projection identical-camera alignment.'}
    installed=visual=daylight=native=False
    with Client(timeout=30) as client:
        check=SignCheck(client,args.output/'report.json',45,native_resolution=args.native_resolution)
        try:
            if args.refresh:refresh(check)
            report['visual_case']=check.run('from modern_projection.projection.debug_blueprints import VISUAL_CASES\n'
                                            '_result=json.dumps(VISUAL_CASES["pot_artwork"])')
            report['workspace_before']=check.navigation()['open']
            check.run(INSTALL_PROBE)
            installed=True
            check.run(SAVE_VISUAL+'sys._blueprint_visual_saved["grid"]=s.grid\n'
                      'sys._blueprint_visual_saved["touch_mode"]=s.touch_mode\n_result=True')
            visual=True
            execute(client,SETUP_DAYLIGHT)
            daylight=True
            close_workspace(check)
            report['native_setup']=execute(client,SETUP)
            native=True
            report['near_player']=execute(client,NEAR_PLAYER % (tuple(report['visual_case']['camera']['world_offset']),))
            expected=report['near_player']['expected']
            check.wait('player near pot',lambda foot:all(abs(a-b)<.1 for a,b in zip(foot,expected)),
                       lambda:check.run('_result=json.dumps(b.player_position.GetFootPos())'))
            target=tuple(report['native_setup']['target'])
            metadata=report['visual_case']
            for direction in args.direction or range(4):
                identity='direction_'+str(direction)
                state=check.run(LOAD % (identity,args.operation,False))
                check.run('owner.open_workspace()\n_result=True')
                check.wait('workspace opens',lambda row:row['open'] and not row['transition'],check.navigation)
                check.editor_preview(identity,state['metadata'],state['editor_id'],state['document_id'])
                editor=check.capture(identity+'_editor')
                editor['crop']=viewport_crop(check,editor)
                blank_state=check.run(LOAD % (identity,args.operation,True))
                check.editor_preview(identity,blank_state['metadata'],blank_state['editor_id'],blank_state['document_id'])
                editor_empty=check.capture(identity+'_editor_empty')
                editor_empty['crop']=viewport_crop(check,editor_empty)
                state=check.run(LOAD % (identity,args.operation,False))
                check.editor_preview(identity,state['metadata'],state['editor_id'],state['document_id'])
                close_workspace(check)
                row={'id':identity,'direction':direction,'editor':editor,'editor_empty':editor_empty,'views':[]}
                expected_direction,expected_sherds=reflected_reference(direction,args.operation,SHERDS)
                row.update(operation=args.operation,expected_direction=expected_direction,expected_sherds=expected_sherds)
                report['cases'].append(row)
                for sign in (1,-1):
                    label=identity+('_front' if sign==1 else '_back')
                    offset=tuple(value*sign for value in metadata['camera']['world_offset'])
                    near=execute(client,NEAR_PLAYER % (offset,))
                    check.wait('player on camera side',lambda foot:all(abs(a-b)<.1 for a,b in zip(foot,near['expected'])),
                               lambda:check.run('_result=json.dumps(b.player_position.GetFootPos())'))
                    row['native_data']=execute(client,WRITE % (expected_direction,expected_sherds))
                    row['native_palette']=replicated_palettes(client,READ % (target,expected_direction,expected_sherds))
                    pose=check.run(CAMERA % (target,offset))
                    pose['settled']=wait_camera_pose(check,pose)
                    time.sleep(.5)
                    shown=check.capture(label+'_native')
                    execute(client,CLEAR_POT)
                    check.wait('native pot cleared',lambda names:all(name=='minecraft:air' for name in names),
                               lambda:check.run('data=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(%r,%r,False).SerializeBlockPalette()\n'
                                                '_result=json.dumps([value[0] for value in data.get("common",{})])' % (target,target)))
                    time.sleep(.35)
                    empty=check.capture(label+'_empty')
                    focus=metadata['focus']
                    origin=tuple(target[axis]-focus[axis] for axis in range(3))
                    check.run('s.origin=%r\ns.opacity=1.\ns.projection_missing=False\n'
                              's.projection_outline=False\nb.project()\n_result=True' % (origin,))
                    projection=check.wait('pot projection ready',lambda value:value['active'] and value['ready'] and not value['preparing'],
                                          lambda:check.run(PROJECTION_STATUS))
                    assert not projection['error'],projection
                    time.sleep(.35)
                    actual=check.capture(label+'_projection')
                    sample={'sign':sign,'pose':pose,'native':shown,'empty':empty,'projection':actual,'state':projection}
                    try:
                        first=object_frame(shown['path'],empty['path'],args.output/(label+'_native_signal.png'))
                        second=object_frame(actual['path'],empty['path'],args.output/(label+'_projection_signal.png'))
                        comparison=_prepared_pair(first,second)
                        comparison['alignment']=world_alignment(first[2],second[2])
                        comparison['passed']=(comparison['shape_iou']>=.82 and comparison['scale_relative_error']<=.2 and
                                              comparison['texture_cosine'] is not None and comparison['texture_cosine']>=.45 and
                                              comparison['interior_missing_fraction']<=.02 and comparison['alignment']['passed'])
                        sample.update(native_signal=first[2],projection_signal=second[2],comparison=comparison)
                    except AssertionError as error:
                        sample['comparison']={'passed':False,'error':str(error)}
                    row['views'].append(sample)
                    check.run('b.stop_projection()\n_result=True')
                    write_json(args.output/'report.json',report)
                offset=editor_offset(metadata['camera']['editor'],math.sqrt(sum(v*v for v in metadata['camera']['world_offset'])))
                near=execute(client,NEAR_PLAYER % (offset,))
                check.wait('player on editor reference side',lambda foot:all(abs(a-b)<.1 for a,b in zip(foot,near['expected'])),
                           lambda:check.run('_result=json.dumps(b.player_position.GetFootPos())'))
                row['native_data']=execute(client,WRITE % (expected_direction,expected_sherds))
                row['native_palette']=replicated_palettes(client,READ % (target,expected_direction,expected_sherds))
                pose=check.run(CAMERA % (target,offset))
                pose['settled']=wait_camera_pose(check,pose)
                time.sleep(.5)
                editor_native=check.capture(identity+'_editor_reference_native')
                execute(client,CLEAR_POT)
                time.sleep(.35)
                editor_native_empty=check.capture(identity+'_editor_reference_empty')
                row.update(editor_reference={'camera':pose,'offset':offset,
                            'near_player':near,
                            'method':'Declared editor OrbitCamera.basis toward vector; fixed native distance, no pixel fit',
                            'shown':editor_native,'empty':editor_native_empty})
                try:
                    reference=object_frame(editor_native['path'],editor_native_empty['path'],args.output/(identity+'_editor_reference_signal.png'))
                    editor_frame=editor_object_frame(editor,editor_empty,args.output/(identity+'_editor_signal.png'))
                    editor_match=_prepared_pair(reference,editor_frame)
                    editor_match['passed']=(editor_match['shape_iou']>=.82 and
                        editor_match['texture_cosine'] is not None and editor_match['texture_cosine']>=.45 and
                        editor_match['interior_missing_fraction']<=.02)
                    row.update(editor_signal=editor_frame[2],editor_comparison=editor_match)
                except AssertionError as error:
                    row['editor_comparison']={'passed':False,'error':str(error)}
                row['world_passed']=all(sample['comparison']['passed'] for sample in row['views'])
                row['editor_passed']=row.get('editor_comparison',{}).get('passed',False)
                row['passed']=row['world_passed'] and row['editor_passed']
            report['completed']=True
            report['world_passed']=all(row['world_passed'] for row in report['cases'])
            report['editor_passed']=all(row['editor_passed'] for row in report['cases'])
            report['passed']=all(row['passed'] for row in report['cases'])
        finally:
            errors=[]
            actions=[]
            if native:actions.extend((('player',lambda:execute(client,RESTORE_PLAYER)),('native',lambda:execute(client,CLEANUP))))
            if daylight:actions.append(('daylight',lambda:execute(client,RESTORE_DAYLIGHT)))
            if visual:
                actions.extend((('projection',lambda:check.run('b.stop_projection()\n_result=True')),
                                ('camera',lambda:check.run(camera_restore_code(False))),
                                ('fields',lambda:check.run('saved=sys._blueprint_visual_saved\ns.grid=saved["grid"]\n'
                                     's.touch_mode=saved["touch_mode"]\n'
                                     's.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\n'
                                     's.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True'))))
            if installed:actions.append(('editor',lambda:check.run(RESTORE)))
            actions.append(('workspace',lambda:check.run('owner.open_workspace()\n_result=True' if report.get('workspace_before') else
                                                       "if navigator.contains('modern_projection_workspace'):navigator.pop()\n_result=True")))
            for name,action in actions:
                try:
                    result=action()
                    report['cleanup_'+name]=result
                    if name=='native' and not result.get('restored',False):
                        errors.append('native: remaining '+repr(result.get('remaining')))
                except Exception as error:errors.append(name+': '+str(error))
            report['cleanup_errors']=errors
            report['restored']=not errors
            report['passed']=report['passed'] and report['restored']
            write_json(args.output/'report.json',report)
    print(json.dumps({'completed':report['completed'],'passed':report['passed'],'restored':report['restored'],
                      'cases':[{key:row.get(key) for key in ('id','passed')} for row in report['cases']]}))


if __name__=='__main__':
    main()
