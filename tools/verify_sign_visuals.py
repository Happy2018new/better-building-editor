"""Compare built-in two-sided sign text in native MC, editor and projection.

Each colored glyph sample is compared with the same sign after clearing only
its text. Native temporary signs use documented text/style APIs and are always
removed. Run through run_live_check.py with owned desktop routing.
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image,ImageChops,ImageStat
from verify_debug_blueprints import BlueprintCheck,Client,INSTALL_PROBE,RESTORE,write_json
from verify_debug_visuals import SAVE_VISUAL,camera_restore_code,PROJECTION_STATUS,projection_pixels
from verify_native_entity_appearances import execute,replicated_palettes
from verify_native_sign_fields import SETUP,READ,CLEANUP
from verify_shulker_orientations import viewport_crop,wait_camera_pose,opacity_comparison
from context_test_environment import SETUP as SETUP_DAYLIGHT,RESTORE as RESTORE_DAYLIGHT
from verify_neighbor_world_visuals import CAPTURE_OPTIONS,RESTORE_OPTIONS

ROOT=Path(__file__).resolve().parents[1]


class SignCheck(BlueprintCheck):
    def __init__(self,client,output,timeout,native_resolution=False,background_only=True,native_capture_helper=None):
        BlueprintCheck.__init__(self,client,output,timeout)
        self.native_resolution=native_resolution
        self.background_only=background_only
        self.native_capture_helper=native_capture_helper or os.environ.get('MCDEV_NATIVE_CAPTURE_HELPER')

    def capture(self,label,tree=None):
        compact=(None if self.background_only and self.native_resolution else
                 BlueprintCheck.capture(self,label,tree))
        if not self.native_resolution:
            return compact
        path=self.output.parent/(self.output.stem+'_'+label+'_native.png')
        helper=getattr(self,'native_capture_helper',None)
        if helper:
            helper=Path(helper).resolve(strict=True)
        else:
            helper=ROOT/'tools/pyreact_legacy/capture_screen.py'
        completed=subprocess.run([sys.executable,'-X','utf8',
            str(helper),'--output',str(path)],
            capture_output=True,text=True,check=True)
        capture=json.loads(completed.stdout)
        assert capture['ok'],capture
        payload=path.read_bytes()
        with Image.open(path) as image:
            blank=max(ImageStat.Stat(image.convert('RGB')).var)<=1.
        if blank:
            if self.background_only:
                failure={'label':label,'background_only':True,'reliable':False,
                         'reason':'Native background capture is blank; foreground activation is disabled',
                         'path':str(path.resolve()),'sha256':hashlib.sha256(payload).hexdigest(),
                         'capture':capture}
                diagnostic=path.with_suffix('.capture_error.json')
                write_json(diagnostic,failure)
                raise RuntimeError('%s: %s; evidence %s' %
                                   (label,failure['reason'],diagnostic))
            # GPU swap chains can return a black PrintWindow. Activate only
            # this routed instance while run_live_check owns the desktop.
            activated_window=subprocess.run([sys.executable,'-X','utf8',
                str(ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                '--size','%dx%d' % (capture['width'],capture['height']),
                '--no-center','--settle','.1'],capture_output=True,text=True,check=True)
            window=json.loads(activated_window.stdout)
            assert window['ok'] and window['activated'],window
            assert window['actualClient']==[capture['width'],capture['height']],window
            assert window['window']['pid']==capture['window']['pid'],window
            activated=self.client.call('mc_input',{'op':'/run','args':{
                'steps':[{'do':'wait','ms':100}]}})
            state=activated.get('structuredContent',{})
            assert state.get('ok') and state['data']['window']['foreground'],activated
            completed=subprocess.run([sys.executable,'-X','utf8',
                str(ROOT/'tools/pyreact_legacy/capture_screen.py'),'--output',str(path),
                '--region',','.join(str(value) for value in capture['region'])],
                capture_output=True,text=True,check=True)
            region_capture=json.loads(completed.stdout)
            assert region_capture['ok'],region_capture
            region_capture['window']=capture['window']
            region_capture['activation']=activated
            region_capture['managed_activation']=window
            capture=region_capture
            payload=path.read_bytes()
        with Image.open(path) as image:
            variance=ImageStat.Stat(image.convert('RGB')).var
            assert max(variance)>1.,'Native resolution game capture is blank'
            record={'path':str(path.resolve()),'bytes':len(payload),
                    'sha256':hashlib.sha256(payload).hexdigest(),'mime':'image/png',
                    'size':image.size,'variance':variance,'compact_screenshot':compact,
                    'capture':capture}
            record['background_only']=self.background_only
        if tree is not None and self.background_only:
            tree_path=path.with_suffix('.tree.json')
            write_json(tree_path,tree)
            record['tree']=str(tree_path.resolve())
        return record

LOAD = '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import rebase,actor_data,make_cell,foreground,background
from modern_projection.projection.nbt_spatial import root_payload,set_scalar
from modern_projection.projection.visible_actor import entity_nbt
from modern_projection.projection.entity_render import native_actor
from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_sign_blueprints import VISUAL_CASE
identity,blank,view=%r,%r,%r
case=next(row for row in VISUAL_CASE['cases'] if row['id']==identity)
source=build(VISUAL_CASE['fixture'])
focus=VISUAL_CASE['focus']
delta=tuple(focus[axis]-case['position'][axis] for axis in range(3))
doc=Document(VISUAL_CASE['isolated_size'],name='Native sign '+identity)
for point in (case['position'],case['support']):
 position=tuple(point[axis]+delta[axis] for axis in range(3))
 doc.blocks[position]=rebase(source.get(point),delta)
if blank:
 value=doc.get(focus)
 actor=actor_data(value)
 root=root_payload(entity_nbt(actor))
 for side in ('FrontText','BackText'):set_scalar(root_payload(root[side]),'Text','')
 doc.blocks[focus]=make_cell(foreground(value),background(value),actor)
value=doc.get(focus)
renderer=native_actor(foreground(value),actor_data(value))
assert renderer['signRealText']==('' if blank else 'Front\\nNative'),renderer
assert renderer['signRealTextBack']==('' if blank else 'Back\\nNative'),renderer
sys._blueprint_qa_identity=VISUAL_CASE['fixture']+'.'+identity
sys._blueprint_qa_nonce+=1
s._loaded(doc)
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'editor_id':id(s.editor),'document_id':id(doc),'previous_document_id':None}
s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*view['editor'])
s.grid=False
s.emit()
owner.open_workspace()
_result=json.dumps({'metadata':sys._blueprint_qa_expected['metadata'],'editor_id':id(s.editor),
 'document_id':id(doc),'renderer':renderer})
'''

NATIVE_TEXT = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._native_sign_probe
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
name,blank=%r,%r
row=next(row for row in saved['rows'] if row['name']==name)
for side in row['sides']:
 assert info.SetSignBlockText(tuple(row['pos']),'' if blank else side['text'],saved['dimension'],side['side'])
_result=True
'''

NATIVE_NEAR_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._native_sign_probe
f=api.GetEngineCompFactory()
pos=f.CreatePos(saved['player'])
if 'player_foot_before' not in saved:saved['player_foot_before']=pos.GetFootPos()
target,offset=%r,%r
platform=(target[0]+(3 if offset[0]>0 else -2),target[1]-1,
          target[2]+(3 if offset[2]>0 else -3))
info=f.CreateBlockInfo(saved['player'])
if platform not in saved['reserved']:
 assert info.GetBlockNew(platform,saved['dimension'])['name']=='minecraft:air'
 saved['reserved'].append(platform)
info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
foot=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
assert pos.SetFootPos(foot)
_result=json.dumps({'before':saved['player_foot_before'],'expected':foot,'after':pos.GetFootPos(),'platform':platform})
'''

NATIVE_RESTORE_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_native_sign_probe',{})
if 'player_foot_before' in saved:
 pos=api.GetEngineCompFactory().CreatePos(saved['player'])
 assert pos.SetFootPos(tuple(saved['player_foot_before']))
_result=True
'''

NATIVE_ITEM_REPLACE = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry
saved=sys._native_sign_probe
f=api.GetEngineCompFactory()
info=f.CreateBlockInfo(saved['player'])
items=f.CreateItem(saved['player'])
rotation=f.CreateRot(saved['player'])
name=%r
row=next(row for row in saved['rows'] if row['name']==name)
kind=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=next((slot for slot in range(36) if not items.GetPlayerItem(kind,slot,True) or
           not items.GetPlayerItem(kind,slot,True).get('count')),None)
assert slot is not None,'Native sign probe needs an empty inventory slot'
before=rotation.GetRot()
try:
 info.SetBlockNew(tuple(row['pos']),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
 assert rotation.SetRot((0.,180.))
 item='minecraft:oak_sign' if name=='minecraft:standing_sign' else 'minecraft:oak_hanging_sign'
 items.SpawnItemToPlayerInv({'itemName':item,'count':1,'auxValue':0},saved['player'],slot)
 assert info.PlayerUseItemToPos(tuple(row['support']),kind,slot,1 if name=='minecraft:standing_sign' else 0)
 placed=info.GetBlockNew(tuple(row['pos']),saved['dimension'])
 assert placed['name']==name,placed
 state=f.CreateBlockState(api.GetLevelId())
 assert state.SetBlockStates(tuple(row['pos']),block_registry.states((name,row['block']['aux'])),saved['dimension'])
 after=info.GetBlockNew(tuple(row['pos']),saved['dimension'])
 assert after==row['block'],after
finally:
 items.SetInvItemNum(slot,0)
 assert rotation.SetRot(before)
_result=json.dumps({'method':'PlayerUseItemToPos','placed':placed,'aligned':after,'slot_restored':True})
'''

NATIVE_STYLE = '''import sys
import mod.server.extraServerApi as api
saved=sys._native_sign_probe
f=api.GetEngineCompFactory()
info=f.CreateBlockInfo(saved['player'])
entity=f.CreateBlockEntity(api.GetLevelId())
name=%r
row=next(row for row in saved['rows'] if row['name']==name)
for side in row['sides']:
 assert info.SetSignBlockText(tuple(row['pos']),side['text'],saved['dimension'],side['side'])
 assert entity.SetSignTextStyle(tuple(row['pos']),saved['dimension'],tuple(side['color']),side['glowing'],side['side'])
_result=True
'''


def colored_text(shown,blank,crop,color,output,relative=False):
    with Image.open(shown) as first,Image.open(blank) as second:
        image=first.convert('RGB').crop(crop)
        baseline=second.convert('RGB').crop(crop)
    if image.size!=baseline.size:raise AssertionError('Sign image dimensions changed')
    delta=ImageChops.difference(image,baseline)
    mask=Image.new('L',image.size)
    rows=[]
    for pixel,base,difference in zip(image.getdata(),baseline.getdata(),delta.getdata()):
        if relative:
            selected_index=1 if color=='green' else 0
            selected=pixel[selected_index]
            # Nonselected channels contain only the retained blank wood for a
            # pure red/green glyph. Their ratios cancel neutral lighting and
            # expose the source color of the alpha composite.
            coverage=min(1.-pixel[axis]/float(max(base[axis],1))
                         for axis in range(3) if axis!=selected_index)
            emission=selected-(1.-coverage)*base[selected_index]
            response=emission/coverage if coverage>0. else 0.
        else:
            red,green,blue=(value-before for value,before in zip(pixel,base))
            selected=green if color=='green' else red
            other=red if color=='green' else green
            response=selected-max(other,blue)
        rows.append(255 if max(difference)>20 and response>20 else 0)
    mask.putdata(rows)
    mask.save(output)
    return mask,{'pixels':sum(mask.histogram()[1:]),'bounds':mask.getbbox(),
                 'color':color,'mask':str(output.resolve()),'crop':crop,
                 'response':'wood_composite' if relative else 'absolute_delta',
                 'minimum_difference':20,'minimum_color_response':20}


def shape_match(native,actual):
    boxes=native.getbbox(),actual.getbbox()
    if not all(boxes):return {'determinate':False,'passed':False,'reason':'No native or rendered colored text pixels'}
    size=(180,90)
    first=native.crop(boxes[0]).resize(size,Image.Resampling.NEAREST)
    second=actual.crop(boxes[1]).resize(size,Image.Resampling.NEAREST)
    intersection=sum(ImageChops.multiply(first,second).histogram()[1:])
    union=sum(ImageChops.lighter(first,second).histogram()[1:])
    overlap=intersection/max(1,union)
    return {'determinate':True,'passed':overlap>=.45,'normalized_glyph_iou':overlap,
            'minimum_iou':.45,'normalized_size':size}


def panel_bounds(blank,crop):
    """Find the broad wooden panel, excluding its stem and separated top bar."""
    with Image.open(blank) as image:
        board=image.convert('RGB').crop(crop)
    spans=[]
    for y in range(board.height):
        xs=[x for x in range(board.width) if
            (lambda rgb:rgb[0]>rgb[1]*1.10 and rgb[1]>rgb[2]*1.10 and rgb[0]>35)(board.getpixel((x,y)))]
        spans.append((min(xs),max(xs)+1) if xs else None)
    width=max((right-left for span in spans if span for left,right in (span,)),default=0)
    if not width:return None
    groups=[]
    start=None
    for y,span in enumerate(spans+[None]):
        wide=span is not None and span[1]-span[0]>=width*.70
        if wide and start is None:start=y
        if not wide and start is not None:
            rows=spans[start:y]
            groups.append((min(row[0] for row in rows),start,max(row[1] for row in rows),y))
            start=None
    return max(groups,key=lambda box:(box[2]-box[0])*(box[3]-box[1])) if groups else None


def layout_match(native_text,native_panel,actual_text,actual_panel,tolerance):
    def relative(text,panel):
        width,height=panel[2]-panel[0],panel[3]-panel[1]
        return ((text[0]+text[2]-2*panel[0])/(2*width),
                (text[1]+text[3]-2*panel[1])/(2*height),
                (text[2]-text[0])/width,(text[3]-text[1])/height)
    if not all((native_text,native_panel,actual_text,actual_panel)):
        return {'determinate':False,'passed':False,'reason':'Missing colored glyphs or wooden panel'}
    first,second=relative(native_text,native_panel),relative(actual_text,actual_panel)
    center=max(abs(first[axis]-second[axis]) for axis in (0,1))
    size=max(abs(first[axis]-second[axis])/max(first[axis],.001) for axis in (2,3))
    return {'determinate':True,'passed':center<=tolerance['center'] and size<=tolerance['size'],
            'native_relative':first,'actual_relative':second,'center_error':center,
            'size_relative_error':size,'tolerance':tolerance}


def refresh(check):
    for name in ('nbt_spatial','native_sign_data','native_sign','native_pot_sherd_data','native_pot',
                 'debug_sign_blueprints','debug_pot_blueprints','entity_render',
                 'geometry_palette','render_context','debug_blueprints'):
        path=ROOT/('behavior_pack/modern_projection/projection/'+name+'.py')
        encoded=base64.b64encode(path.read_bytes()).decode('ascii')
        check.run('import base64\nimport modern_projection.projection.%s as module\n'
                  'eval(compile(base64.b64decode(%r),%r,"exec"),module.__dict__)\n_result=True' %
                  (name,encoded,str(path)))


def load(check,identity,blank,view):
    result=check.run(LOAD % (identity,blank,view))
    check.editor_preview(identity,result['metadata'],result['editor_id'],result['document_id'])
    check.wait('workspace opens',lambda row:row['open'] and not row['transition'],check.navigation)
    time.sleep(.2)
    return result


def world_sample(check,label,focus,offset,opacity=1.,height_offset=32,missing=False,untagged=False):
    """Collect a blank mesh as evidence so later control samples still run."""
    before=check.run('_result=len(sys._blueprint_qa_records)')
    check.run('''focus=%r
foot=b.player_origin()
s.origin=(foot[0]+6-focus[0],foot[1]+%r-focus[1],foot[2]+6-focus[2])
s.opacity=%r
s.projection_missing=%r
s.projection_outline=False
b.project()
_result=True''' % (tuple(focus),height_offset,opacity,missing))
    def ready(state):
        if state['error']:raise AssertionError(state)
        return state['active'] and state['ready'] and not state['preparing'] and state['actors']==1 and state['mesh'] and state['scale'] is not None
    state=check.wait('world mesh attaches',ready,lambda:check.run(PROJECTION_STATUS))
    if untagged:
        state['native_material_control']=check.run('''shader=b.projection_shader
assert shader is not None
assert shader.render.SetEntityExtraUniforms(4,(1.,1.,1.,1.))
changes=[]
for bank,parts in enumerate(shader.parts):
 for name in parts:
  value=%r if bank==shader.bank else 0.
  assert shader.render.EnableActorBlockGeometryTransparent(name,True)
  assert shader.render.SetActorBlockGeometryTransparency(name,value)
  changes.append((name,bank,value))
_result=json.dumps({'tagged':False,'active_bank':shader.bank,'parts':changes})
''' % opacity)
    if check.navigation()['open']:
        check.run('navigator.pop()\n_result=True')
        check.wait('workspace closes',lambda row:not row['open'] and not row['transition'],check.navigation)
    pose=check.run('''focus=%r
offset=%r
target=tuple(s.origin[axis]+focus[axis]+.5 for axis in range(3))
position=tuple(target[axis]+offset[axis] for axis in range(3))
rotation=api.GetRotFromDir(tuple(target[axis]-position[axis] for axis in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'position':position,'rotation':rotation,'target':target})
''' % (tuple(focus),tuple(offset)))
    pose['settled']=wait_camera_pose(check,pose)
    time.sleep(.25)
    shown=check.capture(label+'_world_shown')
    try:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
        time.sleep(.25)
        hidden=check.capture(label+'_world_hidden')
    finally:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
    delta=projection_pixels(shown['path'],hidden['path'],check.output.parent/(label+'_delta.png'))
    calls=check.run('_result=json.dumps(sys._blueprint_qa_records[%d:])' % before)
    state.update(pose=pose,screenshot=shown,hidden_screenshot=hidden,pixel_difference=delta,native_calls=calls,
                 visibly_nonblank=delta['changed_pixels']>150,requested_opacity=opacity,
                 projection_missing=missing,untagged_material=untagged)
    return state


def masked_difference(shown,reference,crop,mask,output):
    with Image.open(shown) as first,Image.open(reference) as second:
        delta=ImageChops.difference(first.convert('RGB').crop(crop),second.convert('RGB').crop(crop))
    channels=delta.split()
    signal=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2])
    changed=ImageChops.multiply(signal.point(lambda value:255 if value>12 else 0),mask)
    changed.save(output)
    return {'changed_pixels':sum(changed.histogram()[1:]),'threshold':12,
            'crop':crop,'mask_pixels':sum(mask.histogram()[1:]),'image':str(output.resolve())}


def alpha_samples(check,label,case,view,metadata,height,missing=False,untagged=False):
    samples={}
    for key,opacity in (('full',1.),('half',.5),('zero',0.)):
        load(check,case['id'],True,view)
        samples[key]=world_sample(check,label+'_'+key,metadata['focus'],
            view['world_offset'],opacity,height,missing,untagged)
    full=samples['full']['screenshot']
    width,height=full['size']
    crop=tuple(round(value*(width if axis%2==0 else height))
               for axis,value in enumerate(metadata['world_text_roi']))
    panel=panel_bounds(full['path'],crop)
    assert panel,'Alpha check needs a native wooden panel positive control'
    mask=Image.new('L',(crop[2]-crop[0],crop[3]-crop[1]))
    from PIL import ImageDraw
    ImageDraw.Draw(mask).rectangle((panel[0],panel[1],panel[2]-1,panel[3]-1),fill=255)
    compared=opacity_comparison(full['path'],samples['half']['screenshot']['path'],
        samples['full']['hidden_screenshot']['path'],crop,mask)
    zero=projection_pixels(samples['zero']['screenshot']['path'],
        samples['zero']['hidden_screenshot']['path'],check.output.parent/(label+'_zero_delta.png'))
    panel_zero=masked_difference(samples['zero']['screenshot']['path'],
        samples['zero']['hidden_screenshot']['path'],crop,mask,
        check.output.parent/(label+'_zero_panel_delta.png'))
    native_contract=None
    if untagged:
        native_contract={'source':'vanilla sign:entity_static has no ENABLE_SET_TRANSPARENCY',
                         'expected':'Native unmarked sign body keeps texture alpha and ignores geometry transparency',
                         'samples':{}}
        for key in ('half','zero'):
            native_contract['samples'][key]=masked_difference(full['path'],samples[key]['screenshot']['path'],
                crop,mask,check.output.parent/(label+'_'+key+'_native_unchanged.png'))
        native_contract['passed']=all(row['changed_pixels']==0 for row in native_contract['samples'].values())
    return {'samples':samples,'comparison':compared,'zero_difference':zero,
            'zero_panel_difference':panel_zero,'native_contract':native_contract,
            'positive_control':samples['full']['visibly_nonblank'],
            'passed':native_contract['passed'] if untagged else compared['passed'] and panel_zero['changed_pixels']==0}


def native_sample(check,row,view,blank,label,item_placement=False):
    check.run('b.stop_projection()\n_result=True')
    near=execute(check.client,NATIVE_NEAR_PLAYER % (tuple(row['pos']),tuple(view['world_offset'])))
    check.wait('player reaches native fixture',lambda foot:all(abs(a-b)<.1 for a,b in zip(foot,near['expected'])),
               lambda:check.run('_result=json.dumps(b.player_position.GetFootPos())'))
    placement=None
    if item_placement and not blank:
        placement=execute(check.client,NATIVE_ITEM_REPLACE % row['name'])
        time.sleep(.5)
        placement['dismiss_editor']=check.client.call('mc_input',{'op':'/run','args':{
            'steps':[{'do':'key','keys':'esc'},{'do':'wait','ms':250}]}})
    execute(check.client,NATIVE_STYLE % row['name'])
    execute(check.client,NATIVE_TEXT % (row['name'],blank))
    expected='' if blank else ('Front\nNative' if view['id']=='front' else 'Back\nNative')
    suffix='' if view['id']=='front' else 'Back'
    check.wait('native text replication',lambda value:value==expected,lambda:check.run(
        "data=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(%r,%r,False).SerializeBlockPalette()\n"
        "_result=json.dumps(next(iter(data['actor'][%r].values()))[%r])" %
        (tuple(row['pos']),tuple(row['pos']),row['name'],'signRealText'+suffix)))
    pose=check.run('''position=%r
offset=%r
target=tuple(v+.5 for v in position)
camera=tuple(target[axis]+offset[axis] for axis in range(3))
rotation=api.GetRotFromDir(tuple(target[axis]-camera[axis] for axis in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(camera)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'position':camera,'rotation':rotation,'target':target})
''' % (tuple(row['pos']),tuple(view['world_offset'])))
    pose['settled']=wait_camera_pose(check,pose)
    time.sleep(1.)
    result=check.capture(label)
    result['near_player']=near
    result['item_placement']=placement
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--refresh',action='store_true')
    parser.add_argument('--case',action='append',choices=('standing_front_back','hanging_front_back'))
    parser.add_argument('--view',action='append',choices=('front','back'))
    parser.add_argument('--timeout',type=float,default=30)
    parser.add_argument('--height-offset',type=int,default=32,
                        help='Native and projected fixture height above the player')
    parser.add_argument('--native-item',action='store_true',
                        help='Replace native references using actual player item placement before styling')
    parser.add_argument('--reload-shaders',action='store_true',help='Reload only the candidate actor and text shaders')
    parser.add_argument('--native-resolution',action='store_true',
                        help='Keep routed MCDK evidence and compare lossless client-area pixels before JPEG downsampling')
    parser.add_argument('--response',choices=('absolute_delta','wood_composite'),default='absolute_delta',
                        help='Diagnostic mask response; original fixed cutoffs and shape threshold stay unchanged')
    parser.add_argument('--projection-mode',choices=('full','missing'),default='full')
    parser.add_argument('--alpha-regression',action='store_true',
                        help='Measure opaque, half-transparent and zero-opacity wooden panels')
    parser.add_argument('--untagged-regression',action='store_true',
                        help='Also measure native material transparency without the projection packet marker')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    report={'schema':3,'completed':False,'passed':False,'cases':[],
            'scope':'Static colored two-sided glyph shape/layout; optional panel opacity and original unmarked sign material contract.',
            'glyph_acceptance':'Original fixed 20-channel-delta/color cutoffs, minimum .45 shape IoU and public layout tolerance',
            'alpha_acceptance':'Wooden panel only: contrast gain .35-.65, half blend residual <=.15; zero panel has no changed pixels >12',
            'native_material_acceptance':'Original sign material ignores geometry transparency; unmarked wood must remain unchanged'}
    report.update(projection_mode=args.projection_mode,response=args.response,
                  native_resolution=args.native_resolution,alpha_cases=[])
    installed=False
    visual_saved=False
    daylight_saved=False
    options_saved=False
    masks={}
    with Client(timeout=30) as client:
        check=SignCheck(client,args.output/'report.json',args.timeout,args.native_resolution)
        try:
            report['workspace_ready']=check.wait('workspace initializes',bool,lambda:execute(client,
                "import mod.client.extraClientApi as api\n"
                "owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n"
                "_result=owner is not None and owner.session is not None",True))
            if args.reload_shaders:
                report['shader_reload']=check.run('''_result=json.dumps(dict((name,api.ReloadOneShader(name)) for name in
 ('modern_projection_native_actor.fragment','modern_projection_sign_text.vertex','modern_projection_sign_text.fragment')))''')
            if args.refresh:refresh(check)
            metadata=check.run('from modern_projection.projection.debug_sign_blueprints import VISUAL_CASE\n'
                               '_result=json.dumps(VISUAL_CASE)')
            report['visual_case']=metadata
            report['workspace_before']=check.navigation()['open']
            check.run(INSTALL_PROBE)
            installed=True
            check.run(SAVE_VISUAL+'sys._blueprint_visual_saved["grid"]=s.grid\n_result=True')
            visual_saved=True
            report['daylight']=execute(client,SETUP_DAYLIGHT)
            daylight_saved=True
            report['capture_options']=check.run(CAPTURE_OPTIONS)
            options_saved=True
            report['height_offset']=args.height_offset
            report['native']=execute(client,'_native_sign_height_offset=%r\n' % args.height_offset+SETUP)
            execute(client,'import sys\nsys._native_sign_probe_rows=%r\n_result=True' % report['native']['rows'],True)
            report['native_client']=replicated_palettes(client,READ)
            cases=[row for row in metadata['cases'] if not args.case or row['id'] in args.case]
            views=[row for row in metadata['views'] if not args.view or row['id'] in args.view]
            report['selected_cases']=[row['id'] for row in cases]
            report['selected_views']=[row['id'] for row in views]
            for case in cases:
                row=next(row for row in report['native']['rows'] if row['name']==case['name'])
                for view in views:
                    label=case['id']+'_'+view['id']
                    result={'id':case['id'],'view':view['id'],'samples':{}}
                    editor={}
                    world={}
                    for blank in (False,True):
                        state=load(check,case['id'],blank,view)
                        key='blank' if blank else 'shown'
                        shot=check.capture(label+'_editor_'+key)
                        shot['crop']=viewport_crop(check,shot)
                        editor[key]=shot
                        result['samples']['editor_'+key]={'screenshot':shot,'renderer':state['renderer']}
                    for blank in (False,True):
                        load(check,case['id'],blank,view)
                        key='blank' if blank else 'shown'
                        world[key]=world_sample(check,label+'_projection_'+key,metadata['focus'],view['world_offset'],.85,args.height_offset,
                                                args.projection_mode=='missing')
                        result['samples']['projection_'+key]=world[key]
                    native={key:native_sample(check,row,view,blank,label+'_native_'+key,args.native_item)
                            for key,blank in (('shown',False),('blank',True))}
                    execute(client,NATIVE_RESTORE_PLAYER)
                    result['samples'].update(('native_'+key,value) for key,value in native.items())
                    for scope,shots in (('native',native),('editor',editor),('projection',{key:value['screenshot'] for key,value in world.items()})):
                        width,height=shots['shown']['size']
                        crop=(shots['shown']['crop'] if scope=='editor' else
                              tuple(round(value*(width if axis%2==0 else height))
                                    for axis,value in enumerate(metadata['world_text_roi'])))
                        mask,pixels=colored_text(shots['shown']['path'],shots['blank']['path'],crop,view['color'],args.output/(label+'_'+scope+'_text.png'),
                                                 args.response=='wood_composite')
                        masks[(label,scope)]=mask
                        result[scope]=pixels
                        result[scope]['panel_bounds']=panel_bounds(shots['blank']['path'],crop)
                    for scope in ('editor','projection'):
                        result[scope]['native_comparison']=shape_match(masks[(label,'native')],masks[(label,scope)])
                        result[scope]['layout_comparison']=layout_match(
                            result['native']['bounds'],result['native']['panel_bounds'],
                            result[scope]['bounds'],result[scope]['panel_bounds'],metadata['text_layout_tolerance'])
                    result['passed']=all(result[scope]['pixels']>=8 and result[scope]['native_comparison']['passed'] and
                                         result[scope]['layout_comparison']['passed'] for scope in ('editor','projection'))
                    report['cases'].append(result)
                    write_json(args.output/'report.json',report)
                    for untagged in ([False] if args.alpha_regression else [])+([True] if args.untagged_regression else []):
                        alpha_label=label+('_native_material' if untagged else '_projection_alpha')
                        alpha=alpha_samples(check,alpha_label,case,view,metadata,args.height_offset,
                                            args.projection_mode=='missing',untagged)
                        alpha.update(id=case['id'],view=view['id'],untagged_material=untagged,
                                     projection_mode=args.projection_mode)
                        report['alpha_cases'].append(alpha)
                        write_json(args.output/'report.json',report)
            report['completed']=True
            report['passed']=all(row['passed'] for row in report['cases']+report['alpha_cases'])
        finally:
            cleanup_errors=[]
            for label,action in (
                    ('player',lambda:execute(client,NATIVE_RESTORE_PLAYER)),
                    ('native',lambda:execute(client,CLEANUP) if execute(client,'import sys\n_result=hasattr(sys,"_native_sign_probe")') else {'cleaned':True}),
                    ('native_client',lambda:execute(client,'import sys\nif hasattr(sys,"_native_sign_probe_rows"):del sys._native_sign_probe_rows\n_result=True',True)),
                    ('daylight',lambda:execute(client,RESTORE_DAYLIGHT) if daylight_saved else True),
                    ('capture_options',lambda:check.run(RESTORE_OPTIONS) if options_saved else True),
                    ('projection',lambda:check.run('b.stop_projection()\n_result=True')),
                    ('camera',lambda:check.run(camera_restore_code(False)) if visual_saved else True),
                    ('visual_fields',lambda:check.run('saved=sys._blueprint_visual_saved\ns.grid=saved["grid"]\n'
                         's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                         's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n_result=True') if visual_saved else True),
                    ('editor',lambda:check.run(RESTORE) if installed else True),
                    ('workspace',lambda:check.run('owner.open_workspace()\n_result=True' if report.get('workspace_before') else
                         "if navigator.contains('modern_projection_workspace'):navigator.pop()\n_result=True")),
                    ('visual_marker',lambda:check.run('del sys._blueprint_visual_saved\n_result=True') if visual_saved else True)):
                try:
                    result=action()
                    if label=='native':report['native_cleanup']=result
                except Exception as error:
                    cleanup_errors.append(label+': '+str(error))
            report['cleanup_errors']=cleanup_errors
            report['client_restored']=installed and not cleanup_errors
            report['passed']=report['passed'] and not cleanup_errors and report.get('native_cleanup',{}).get('cleaned',False)
            write_json(args.output/'report.json',report)
    print(json.dumps({'completed':report['completed'],'passed':report['passed'],
                     'cases':[{key:row[key] for key in ('id','view','passed')} for row in report['cases']],
                     'report':str((args.output/'report.json').resolve())}))


if __name__=='__main__':
    main()
