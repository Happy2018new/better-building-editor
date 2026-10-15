"""Compare native closed chests and static adapters in the same native UI doll.

The baseline uses the original native material, actor and states directly;
only the candidate passes through prepare_palette. No real world is edited.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from chest_pixels import object_frame
from shulker_pixels import _prepared_pair

ROOT = Path(__file__).resolve().parents[1]
NATIVE_RENDERERS = ROOT / 'tools/data/native_entity_renderers_nemc_3.9.0.401155.json'

BUILD = '''import time
from modern_projection.projection.debug_blueprints import Fixture,material
from modern_projection.projection.block_groups import chest_pair_actor
from modern_projection.projection.geometry_palette import prepare_palette
from modern_projection.projection.bridge import _native_palette
from modern_projection.projection.visible_actor import render_actor
from modern_projection.projection import block_registry
assert not hasattr(sys,'_chest_ui_probe')
sys._chest_ui_probe={'rows':[],'ref':None,'nonce':str(int(time.time()*1000000))}
assert block_registry.source_version()==__RENDERER_VERSION__
assert block_registry.fingerprint()==__RENDERER_PALETTE_HASH__
for serial,(name,direction,paired) in enumerate(__CHEST_CASES__):
 fixture=Fixture(('probe','entities','Native chest UI',(4,3,4),'minecraft:'+name))
 value=material(name,{u'minecraft:cardinal_direction':unicode(direction)})
 first=(1,1,1)
 delta={'north':(1,0,0),'south':(-1,0,0),'east':(0,0,1),'west':(0,0,-1)}[direction]
 positions=(first,tuple(first[i]+delta[i] for i in range(3))) if paired else (first,)
 for pos in positions:
  renderer=dict(__ENDERCHEST_ACTOR__) if name=='ender_chest' else None
  if renderer is not None:renderer['facingDirection']={'north':2,'south':3,'west':4,'east':5}[direction]
  fixture.put(pos,value,entity='EnderChest' if name=='ender_chest' else 'Chest',render=renderer)
  partner=positions[1-positions.index(pos)] if paired else None
  fixture.document.blocks[pos]=chest_pair_actor(fixture.document.get(pos),pos,partner)
 source=fixture.document.palette_data()
 source['states']=dict((key,block_registry.states(key)) for key in source['common'])
 source['actor']=dict((key,dict((index,render_actor(actor)) for index,actor in entries.items())) for key,entries in source.get('actor',{}).items())
 row={'name':name,'direction':direction,'paired':paired,'models':{},'submissions':{}}
 for variant,data in (('native',source),('static',prepare_palette(source))):
  palette=b.factory.CreateBlock(b.level).GetBlankBlockPalette()
  assert palette.DeserializeBlockPalette(_native_palette(data))
  roundtrip=palette.SerializeBlockPalette()
  assert roundtrip['common']==_native_palette(data)['common'],(variant,roundtrip,data)
  identifier='modern_projection_chest_ui_%s_%s_%s'%(serial,variant,sys._chest_ui_probe['nonce'])
  model=b.factory.CreateBlockGeometry(b.level).CombineBlockPaletteToGeometry(palette,identifier,0)
  assert model
  row['models'][variant]=model
  row['submissions'][variant]={'volume':data['volume'],
   'common':[(key,entries) for key,entries in data['common'].items()],
   'states':[(key,record) for key,record in data['states'].items()],'actor':data['actor']}
 sys._chest_ui_probe['rows'].append(row)
_result=json.dumps(sys._chest_ui_probe['rows'])
'''

OPEN_UI = '''from modern_projection.pyreact import Component,Panel,Image,Color,Position,PaperDollRenderType,use_ref
from modern_projection.pyreact.hooks import use_animation_frame
from modern_projection.projection.widgets import Doll,S
@Component
def StaticChestUI():
 ref=use_ref(None)
 def ready(unused):sys._chest_ui_probe['ref']=ref
 use_animation_frame(ready)
 width,height=b.factory.CreateGame(b.level).GetScreenSize()
 return Panel(style=S(width=width,height=height),children=[
  Image(color=Color(0xF0F0F0FF),style=S(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Doll(ref=ref,managed=True,renderType=PaperDollRenderType.block_geometry,
   style=S(position=Position.absolute,left=width*.1,top=height*.1,width=width*.8,height=height*.8,zIndex=1))])
assert navigator.push(StaticChestUI(),key='static_chest_ui_probe')
_result=True
'''

DRAW = '''ref=sys._chest_ui_probe['ref'].current
ref.SetVisible(True,False)
args={'block_geometry_model_name':sys._chest_ui_probe['rows'][%d]['models'][%r],
 'scale':3.,'init_rot_x':-55.,'init_rot_y':0.,'init_rot_z':35.}
assert ref.asNeteasePaperDoll().RenderBlockGeometryModel(args)
_result=json.dumps(args)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--case-limit', type=int)
    parser.add_argument('--include-copper', action='store_true')
    parser.add_argument('--name', action='append', help='Restrict the native material name, e.g. ender_chest')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plans = [(name, direction, paired) for name in ('chest', 'trapped_chest', 'ender_chest')
             for direction in ('north', 'east', 'south', 'west')
             for paired in ((False,) if name == 'ender_chest' else (False, True))]
    if args.include_copper:
        plans += [(name, direction, paired) for name in ('copper_chest', 'exposed_copper_chest',
                  'weathered_copper_chest', 'oxidized_copper_chest')
                  for direction in ('north', 'east', 'south', 'west') for paired in (False, True)]
    if args.name:
        plans = [row for row in plans if row[0] in args.name]
        if not plans:
            parser.error('No cases match the selected names')
    native_source_bytes = NATIVE_RENDERERS.read_bytes()
    native_source = json.loads(native_source_bytes)
    ender = next(row for row in native_source['records'] if row['material'][0] == 'minecraft:ender_chest')
    assert native_source['schema_version'] == 1 and ender['verified_material_and_states']
    build = (BUILD.replace('__CHEST_CASES__', repr(plans[:args.case_limit]))
             .replace('__ENDERCHEST_ACTOR__', repr(ender['actor']))
             .replace('__RENDERER_VERSION__', repr(native_source['game_version']))
             .replace('__RENDERER_PALETTE_HASH__', repr(native_source['palette_sha256'])))
    report = {'schema': 1, 'completed': False, 'restored': False, 'cases': [],
              'native_defaults': {'path': str(NATIVE_RENDERERS),
                  'sha256': hashlib.sha256(native_source_bytes).hexdigest(),
                  'version': native_source['game_version'], 'palette_sha256': native_source['palette_sha256']},
              'scope': 'Identical native UI control and camera, original native palette versus prepared static palette. Shape and texture compare normalized visible bounds; native world alignment and control centering are not asserted. Copper native zero geometry is a recorded capability failure, not visual acceptance.'}
    installed = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                report['cases'] = check.run(build)
                check.run(OPEN_UI)
                check.wait('native chest UI reference', lambda value: value,
                           lambda: check.run('_result=bool(sys._chest_ui_probe["ref"] and sys._chest_ui_probe["ref"].current)'))
                for index, row in enumerate(report['cases']):
                    native_args = check.run(DRAW % (index, 'native'))
                    time.sleep(.35)
                    native = check.capture('case_%d_native' % index)
                    static_args = check.run(DRAW % (index, 'static'))
                    time.sleep(.35)
                    static = check.capture('case_%d_static' % index)
                    check.run('sys._chest_ui_probe["ref"].current.SetVisible(False,False)\n_result=True')
                    time.sleep(.2)
                    empty = check.capture('case_%d_empty' % index)
                    row['captures'] = {'native': native, 'static': static, 'empty': empty}
                    row['draw_args'] = {'native': native_args, 'static': static_args}
                    try:
                        first = object_frame(native['path'], empty['path'], args.output.with_name(
                            args.output.stem + '_%d_native_signal.png' % index))
                        second = object_frame(static['path'], empty['path'], args.output.with_name(
                            args.output.stem + '_%d_static_signal.png' % index))
                        comparison = _prepared_pair(first, second)
                        comparison['passed'] = (comparison['shape_iou'] >= .82 and
                            comparison['scale_relative_error'] <= .2 and
                            comparison['texture_cosine'] is not None and comparison['texture_cosine'] >= .45)
                        row['comparison'] = comparison
                    except AssertionError as error:
                        row['comparison'] = {'passed': False, 'error': str(error)}
                    write_json(args.output, report)
                report['runtime_minecraft_version'] = check.run('_result=json.dumps(api.GetMinecraftVersion())')
                report['completed'] = True
                report['passed'] = all(row['comparison']['passed'] for row in report['cases'])
            finally:
                if installed:
                    check.run('''if navigator.top is not None and navigator.top.key=='static_chest_ui_probe':navigator.pop()
if hasattr(sys,'_chest_ui_probe'):del sys._chest_ui_probe
_result=True''')
                    check.wait('close chest reference UI', lambda nav: not nav['transition'], check.navigation)
                    was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    if was_open:
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('restore workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                    elif check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('restore closed workspace', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                    report['restored'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
