"""Probe native skull renderer types with a matched stone and empty control.

Only a temporary render adapter is changed. Saved entity NBT stays unchanged,
and native fixtures, lighting, camera and workspace are restored independently.
Use run_live_check.py with an owned disposable game instance.
"""
import argparse
import copy
import json
import time
from pathlib import Path

from PIL import Image, ImageChops
from verify_debug_blueprints import BlueprintCheck,Client,INSTALL_PROBE,RESTORE,write_json
from verify_debug_visuals import SAVE_VISUAL,camera_restore_code
from verify_native_entity_appearances import execute,replicated_palettes
from verify_native_sign_fields import POSE_SETUP,CLEANUP
from verify_shulker_orientations import viewport_crop
from verify_sign_visuals import world_sample,refresh
from visual_environment import SETUP_DAYLIGHT,RESTORE_DAYLIGHT

ROOT=Path(__file__).resolve().parents[1]
FOCUS=(1,1,1)
OFFSET=(-2.5,1.5,-3.5)

READ='''import json,sys
import mod.client.extraClientApi as api
row=sys._native_sign_probe_rows[0]
pos=tuple(row['pos'])
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(pos,pos,False)
data=palette.SerializeBlockPalette() if palette else None
ready=data is not None and next(iter(data.get('common',{})),None)==(row['name'],row['aux'])
if ready:sys._skull_probe_palette=data
_result=json.dumps({'ready':ready,'common':list(data.get('common',{})) if data else None,
 'actor':data.get('actor') if data else None,'states':list(data.get('states',{}).items()) if data else None,
 'volume':data.get('volume') if data else None})
'''

SAVE_ADAPTER='''import modern_projection.projection.geometry_palette as gp
import modern_projection.projection.entity_render as er
from modern_projection.projection.native_appearance import SKULL_NAMES
from modern_projection.projection.cell import freeze,thaw
from modern_projection.projection.nbt_spatial import set_scalar
assert not hasattr(sys,'_skull_mesh_probe')
saved={'native_actor':gp.native_actor,'static_proxy':er.static_proxy,'enum':None,'geometry':b.geometry,'serial':0,
 'model_prefix':'skull_mesh_probe_'+str(int(time.time()*1000000))}
sys._skull_mesh_probe=saved
def skull_mesh_probe_static(material,actor,inferred_part=None):
 if material[0] in SKULL_NAMES:return None
 return saved['static_proxy'](material,actor,inferred_part)
er.static_proxy=skull_mesh_probe_static
def skull_mesh_probe_actor(material,actor):
 result=saved['native_actor'](material,actor)
 if material[0] not in SKULL_NAMES or saved['enum'] is None:return result
 result=thaw(freeze(result)) if result is not None else {}
 set_scalar(result,'skullType',saved['enum'])
 return result
gp.native_actor=skull_mesh_probe_actor
def skull_mesh_probe_geometry(document,visible=None,name=None,context_document=None,prepared=None):
 saved['serial']+=1
 name=saved['model_prefix']+'_'+str(saved['serial'])
 return saved['geometry'](document,visible,name,context_document,prepared)
b.geometry=skull_mesh_probe_geometry
_result=True
'''

LOAD='''from copy import deepcopy
from modern_projection.projection.model import Document
from modern_projection.projection.world_capture import merge_palette
from modern_projection.projection.cell import foreground,background,actor_data,make_cell
from modern_projection.projection.visible_actor import compose_actor,render_actor
from modern_projection.projection.nbt_spatial import rebase as rebase_nbt
from modern_projection.projection.geometry_palette import prepare_palette
variant,enum=%r,%r
focus=%r
doc=Document((3,3,3),name='Skull native mesh '+variant)
sys._skull_mesh_probe['enum']=enum
if variant=='stone':doc.blocks[focus]=('minecraft:stone',0)
elif variant!='empty':
 row=sys._native_sign_probe_rows[0]
 origin=tuple(row['pos'][axis]-focus[axis] for axis in range(3))
 merge_palette(doc,deepcopy(sys._skull_probe_palette),focus,(1,1,1),origin)
 value=doc.get(focus)
 actor=compose_actor(render_actor(actor_data(value)),rebase_nbt(row['nbt'],tuple(-v for v in origin)))
 doc.blocks[focus]=make_cell(foreground(value),background(value),actor)
 before=deepcopy(doc.blocks)
 data=prepare_palette(doc.palette_data())
 assert doc.blocks==before,'Render adapter mutated saved data'
sys._blueprint_qa_identity='skull.mesh.'+variant
sys._blueprint_qa_nonce+=1
metadata={'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)}
sys._blueprint_qa_expected={'metadata':metadata,'editor_id':None,'previous_document_id':id(s.editor.document)}
s.tiles.parts={}
s.tiles.context=None
s.tiles.region_source=None
s.tiles.document_size=None
s.tiles.generation+=1
s.model_revision=None
s._loaded(doc)
s.grid=False
s.camera_depth=0.
s.camera_depth_pose=0.
s.camera_pan=(0.,0.)
s.camera_pivot=(1.5,1.5,1.5)
s.camera_view(32.,24.,5.)
s.emit()
owner.open_workspace()
_result=json.dumps({'metadata':metadata,'editor_id':id(s.editor),'document_id':id(doc),
 'render_actor':data.get('actor') if variant not in ('empty','stone') else None,
 'saved_actor':actor_data(doc.get(focus)) if variant not in ('empty','stone') else None,
 'material':foreground(doc.get(focus)) if variant!='empty' else None})
'''


def changed_pixels(first,second,threshold=25):
    if first.size!=second.size:raise AssertionError('Matched viewport dimensions changed')
    width,height=first.size
    crop=(width//4,height//8,width*3//4,height*7//8)
    first,second=first.crop(crop),second.crop(crop)
    channels=ImageChops.difference(first,second).split()
    maximum=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2])
    return sum(maximum.histogram()[threshold+1:])


def object_pixels(frame):
    # Empty documents have a placeholder that disappears for blank meshes.
    # Sample the quiet viewport corner instead of treating its text as a mesh.
    background=Image.new('RGB',frame.size,frame.getpixel((0,0)))
    return changed_pixels(frame,background)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--all-types',action='store_true')
    parser.add_argument('--native-only',action='store_true',
                        help='Keep observed native fields; do not probe renderer enum overrides')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    evidence={'schema':1,'completed':False,'rows':[],'scope':'Diagnostic renderer enum probe; no production remapping or saved NBT change'}
    installed=visual_saved=daylight_saved=adapter_saved=False
    with Client(timeout=30) as client:
        check=BlueprintCheck(client,args.output/'report.json',40)
        try:
            refresh(check)
            check.run(INSTALL_PROBE)
            installed=True
            check.run(SAVE_VISUAL+'sys._blueprint_visual_saved["grid"]=s.grid\n_result=True')
            visual_saved=True
            evidence['daylight']=execute(client,SETUP_DAYLIGHT)
            daylight_saved=True
            aux=check.run('from modern_projection.projection.debug_blueprints import material\n_result=material("skeleton_skull",{"facing_direction":1})[1]')
            evidence['native']=execute(client,POSE_SETUP % [('minecraft:skeleton_skull',aux)])
            execute(client,'import sys\nsys._native_sign_probe_rows=%r\n_result=True' % evidence['native']['rows'],True)
            evidence['native_palette']=replicated_palettes(client,READ.replace('b.factory','api.GetEngineCompFactory()').replace('b.level','api.GetLevelId()'))
            check.run(SAVE_ADAPTER)
            adapter_saved=True
            variants=[('empty',None),('stone',None),('native',None)]
            if not args.native_only:
                variants.extend(('enum'+str(value),value) for value in (range(7) if args.all_types else (0,)))
            blank=None
            for label,enum in variants:
                loaded=check.run(LOAD % (label,enum,FOCUS))
                check.editor_preview(label,loaded['metadata'],loaded['editor_id'],loaded['document_id'])
                check.wait('workspace opens',lambda row:row['open'] and not row['transition'],check.navigation)
                time.sleep(.3)
                shot=check.capture(label+'_editor')
                crop=viewport_crop(check,shot)
                with Image.open(shot['path']) as image:frame=image.convert('RGB').crop(crop)
                frame.save(args.output/(label+'_editor_crop.png'))
                row={'id':label,'loaded':loaded,'editor':{'screenshot':shot,'crop':crop,
                     'analysis_crop':(frame.width//4,frame.height//8,frame.width*3//4,frame.height*7//8)},
                     'native_calls':check.run('_result=json.dumps([row for row in sys._blueprint_qa_records if row["nonce"]==sys._blueprint_qa_nonce])')}
                if blank is None:blank=frame
                else:
                    row['editor']['pixels']=changed_pixels(frame,blank)
                    row['editor']['object_pixels']=object_pixels(frame)
                    row['editor']['visibly_nonblank']=row['editor']['object_pixels']>=100
                    row['projection']=world_sample(check,label,FOCUS,OFFSET)
                    check.run('b.stop_projection()\n_result=True')
                evidence['rows'].append(row)
                write_json(args.output/'report.json',evidence)
                if label=='stone':
                    evidence['positive_control']=all(row[scope]['visibly_nonblank'] for scope in ('editor','projection'))
                    if not evidence['positive_control']:
                        raise AssertionError('The matched stone control has no visible geometry')
            evidence['positive_control']=all(evidence['rows'][1][scope]['visibly_nonblank'] for scope in ('editor','projection'))
            native=next(row for row in evidence['rows'] if row['id']=='native')
            evidence['native_renderer_nonblank']=all(native[scope]['visibly_nonblank'] for scope in ('editor','projection'))
            evidence['completed']=True
        finally:
            errors=[]
            actions=[('projection',lambda:check.run('b.stop_projection()\n_result=True'))]
            if adapter_saved:
                actions.append(('adapter',lambda:check.run('import modern_projection.projection.geometry_palette as gp\nimport modern_projection.projection.entity_render as er\ngp.native_actor=sys._skull_mesh_probe["native_actor"]\ner.static_proxy=sys._skull_mesh_probe["static_proxy"]\nb.geometry=sys._skull_mesh_probe["geometry"]\ndel sys._skull_mesh_probe\n_result=True')))
            actions.append(('native',lambda:execute(client,CLEANUP) if execute(client,'import sys\n_result=hasattr(sys,"_native_sign_probe")') else True))
            actions.append(('native_client',lambda:execute(client,'import sys\nfor name in ("_native_sign_probe_rows","_skull_probe_palette"):\n if hasattr(sys,name):delattr(sys,name)\n_result=True',True)))
            if daylight_saved:actions.append(('daylight',lambda:execute(client,RESTORE_DAYLIGHT)))
            if visual_saved:
                actions.append(('camera',lambda:check.run(camera_restore_code(False))))
                actions.append(('visual',lambda:check.run('saved=sys._blueprint_visual_saved\ns.grid=saved["grid"]\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True')))
            if installed:
                def restore_editor():
                    opened=check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    check.run('owner.open_workspace()\n_result=True' if opened else "if navigator.contains('modern_projection_workspace'):navigator.pop()\n_result=True")
                actions.append(('editor',restore_editor))
            for label,action in actions:
                try:action()
                except Exception as error:errors.append(label+': '+str(error))
            evidence['cleanup_errors']=errors
            evidence['restored']=not errors
            write_json(args.output/'report.json',evidence)
    print(json.dumps({'completed':evidence['completed'],'positive_control':evidence.get('positive_control'),
                     'restored':evidence['restored'],'report':str((args.output/'report.json').resolve())}))


if __name__=='__main__':main()
