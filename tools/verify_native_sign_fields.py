"""Capture native two-sided sign text/style and actual client palette fields.

Run only through run_live_check.py in an owned disposable development instance.
No inventory or document writes are needed. Temporary cells are checked empty
and always restored. Data evidence is separate from editor/projection pixels.
"""
import argparse
import json
import time
from pathlib import Path

from verify_native_entity_appearances import execute
from verify_debug_blueprints import Client, write_json

POSE_SETUP = '''import json,math,sys
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry
assert not hasattr(sys,'_native_sign_probe')
f=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dim=f.CreateDimension(player).GetEntityDimensionId()
info=f.CreateBlockInfo(player)
foot=f.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))-30,int(math.floor(foot[1]))+60,int(math.floor(foot[2]))-30)
plans=%r
rows=[]
reserved=set()
normals=((0,-1,0),(0,1,0),(0,0,-1),(0,0,1),(-1,0,0),(1,0,0))
for index,(name,aux) in enumerate(plans):
 pos=(origin[0]+index%%20*3,origin[1],origin[2]+index//20*3)
 supports=[tuple(pos[axis]+normal[axis] for axis in range(3)) for normal in normals]
 for cell in [pos]+supports:
  before=info.GetBlockNew(cell,dim)
  assert before and before.get('name')=='minecraft:air',(cell,before)
  reserved.add(cell)
 rows.append({'name':name,'aux':aux,'pos':pos,'supports':supports})
saved={'rows':rows,'reserved':sorted(reserved),'dimension':dim,'player':player,
 'game_version':block_registry.source_version(),'palette_sha256':block_registry.fingerprint()}
sys._native_sign_probe=saved
for row in rows:
 for support in row['supports']:
  assert info.SetBlockNew(support,{'name':'minecraft:stone','aux':0},0,dim,True,False)
 assert info.SetBlockNew(row['pos'],{'name':row['name'],'aux':row['aux']},0,dim,True,False)
 row['block']=info.GetBlockNew(row['pos'],dim)
 row['nbt']=info.GetBlockEntityData(dim,row['pos'])
 assert row['nbt'],row
_result=json.dumps(saved)
'''

SETUP = '''import json,math,sys
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry
assert not hasattr(sys,'_native_sign_probe')
f=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dim=f.CreateDimension(player).GetEntityDimensionId()
info=f.CreateBlockInfo(player)
entity=f.CreateBlockEntity(api.GetLevelId())
foot=f.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))+12,int(math.floor(foot[1]))+40,int(math.floor(foot[2]))+12)
rows=[]
reserved=set()
for index,name in enumerate(('minecraft:standing_sign','minecraft:oak_hanging_sign')):
 pos=(origin[0]+index*5,origin[1],origin[2])
 support=(pos[0],pos[1]-1 if index==0 else pos[1]+1,pos[2])
 for cell in (pos,support):
  before=info.GetBlockNew(cell,dim)
  assert before and before.get('name')=='minecraft:air',(cell,before)
  reserved.add(cell)
 rows.append({'name':name,'pos':pos,'support':support,'sides':[]})
saved={'rows':rows,'reserved':sorted(reserved),'dimension':dim,'player':player,
 'game_version':block_registry.source_version(),'palette_sha256':block_registry.fingerprint()}
sys._native_sign_probe=saved
for row in rows:
 assert info.SetBlockNew(row['support'],{'name':'minecraft:stone','aux':0},0,dim,True,False)
 assert info.SetBlockNew(row['pos'],{'name':row['name'],'aux':0},0,dim,True,False)
 for side,text,color,glow in ((0,'Front\\nNative',(0.,1.,0.,1.),True),
                             (1,'Back\\nNative',(1.,0.,0.,.5),False)):
  text_set=info.SetSignBlockText(row['pos'],text,dim,side)
  style_set=entity.SetSignTextStyle(row['pos'],dim,color,glow,side)
  assert text_set and style_set,(row['name'],side,text_set,style_set)
  row['sides'].append({'side':side,'text':text,'color':color,'glowing':glow})
 row['block']=info.GetBlockNew(row['pos'],dim)
 row['nbt']=info.GetBlockEntityData(dim,row['pos'])
 assert row['nbt'],row
_result=json.dumps(saved)
'''

READ = '''import json,sys
import mod.client.extraClientApi as api
f=api.GetEngineCompFactory()
block=f.CreateBlock(api.GetLevelId())
rows=[]
ready=True
for source in sys._native_sign_probe_rows:
 pos=tuple(source['pos'])
 palette=block.GetBlockPaletteBetweenPos(pos,pos,False)
 data=palette.SerializeBlockPalette() if palette is not None else None
 row=dict(source)
 if data is not None:
  row['palette']=dict((key,value) for key,value in data.items() if key not in ('common','extra','states','extraStates'))
  for field in ('common','extra','states','extraStates'):
   row['palette'][field]=[{'material':material,'value':value} for material,value in data.get(field,{}).items()]
  payloads=data.get('actor',{}).get(source['name'],{})
  actor=next(iter(payloads.values()),None)
  expected=(source['block']['name'],source['block']['aux'])
  actual=next(iter(data.get('common',{})),None)
  if (not source.get('allow_empty_actor') and not actor) or actual!=expected:ready=False
  if source.get('sides') and (actor.get('signRealText')!='Front\\nNative' or actor.get('signRealTextBack')!='Back\\nNative'):ready=False
 else:ready=False
 rows.append(row)
_result=json.dumps({'ready':ready,'rows':rows})
'''

CLEANUP = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._native_sign_probe
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
errors=[]
for unused in range(2):
 for pos in saved['reserved']:
  try:
   result=info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
   if not result and info.GetBlockNew(tuple(pos),saved['dimension']).get('name')!='minecraft:air':errors.append((pos,'set false'))
  except Exception as error:errors.append((pos,str(error)))
remaining=[(pos,info.GetBlockNew(tuple(pos),saved['dimension'])) for pos in saved['reserved']
 if info.GetBlockNew(tuple(pos),saved['dimension']).get('name')!='minecraft:air']
if not remaining:del sys._native_sign_probe
_result=json.dumps({'cleaned':not remaining,'errors':errors,'remaining':remaining})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--poses', action='store_true', help='Capture species defaults and all oak hanging-sign states')
    parser.add_argument('--entities', action='store_true', help='Capture default client render schemas for every observed block entity')
    parser.add_argument('--states', action='append', default=[], help='Capture every state of an observed native block entity name')
    parser.add_argument('--defaults', type=Path, default=Path(__file__).resolve().parents[1]/'tools/data/native_block_entity_defaults_nemc_3.9.0.401155.json')
    args = parser.parse_args()
    report = {'schema':1,'completed':False,'scope':'native field mapping only; GPU acceptance separate'}
    with Client(timeout=30) as client:
        try:
            code = SETUP
            if args.poses or args.entities or args.states:
                import sys
                root = Path(__file__).resolve().parents[1]
                sys.path.insert(0,str(root/'behavior_pack/modern_projection'))
                from projection import block_registry
                from projection.nbt_spatial import scalar
                data = json.loads(args.defaults.read_text())
                names = list(args.states) if args.states else [name for name,row in data['block_entities'].items() if args.entities or scalar(row['nbt'],'id') in ('Sign','HangingSign')]
                plans = [(name,data['block_entities'][name]['aux']) for name in sorted(names)]
                if args.poses:plans.extend(('minecraft:oak_hanging_sign',aux) for aux in block_registry.aux_values('minecraft:oak_hanging_sign') if aux!=data['block_entities']['minecraft:oak_hanging_sign']['aux'])
                for name in args.states:plans.extend((name,aux) for aux in block_registry.aux_values(name) if aux!=data['block_entities'][name]['aux'])
                code = POSE_SETUP % plans
            report['native'] = execute(client, code)
            if args.entities:
                report['scope']='native default renderer fields; nondefault appearance and GPU acceptance separate'
                for row in report['native']['rows']:row['allow_empty_actor']=True
            execute(client, 'import sys\nsys._native_sign_probe_rows=%r\n_result=True' % report['native']['rows'], True)
            deadline = time.monotonic()+12
            while True:
                report['client'] = execute(client, READ, True)
                if report['client']['ready'] or time.monotonic()>=deadline:
                    break
                time.sleep(.2)
            report['completed'] = report['client']['ready']
        finally:
            saved = execute(client,'import sys\n_result=hasattr(sys,"_native_sign_probe")')
            if saved:
                report['cleanup'] = execute(client,CLEANUP)
                report['completed'] = report['completed'] and report['cleanup']['cleaned']
            execute(client,'import sys\nif hasattr(sys,"_native_sign_probe_rows"):del sys._native_sign_probe_rows\n_result=True',True)
            write_json(args.output,report)
    print(json.dumps({'completed':report['completed'],'rows':len(report.get('native',{}).get('rows',())),
                     'cleaned':report.get('cleanup',{}).get('cleaned'),
                     'report':str(args.output.resolve())},ensure_ascii=False))


if __name__=='__main__':
    main()
