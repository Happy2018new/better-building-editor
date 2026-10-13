"""Collect bounded semantic scaffold support states with native raw readbacks.

Eight isolated slots are reused in one owned world. Every sample keeps the
requested semantic state, conversion return, actual support states and actual
scaffold states. Unknown or changed states never become negative capability.
"""
import argparse
import json
from pathlib import Path
import uuid

import probe_scaffold_state_lifecycle as common
from scaffold_native_palette_readback import HELPER, encoding_from_observation

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 2
METHOD = '8 isolated semantic support states; true native states; .35s; explicit dual-layer cleanup; bounded-range-v3'
FULL_METHOD = METHOD + '; complete verified union'
MARKER = '_scaffold_semantic_support_catalogue_v3'
MAX_COUNT, SLOTS = 256, 8


def dump_states():
    return [(name, aux) for name in sorted(common.registry.BLOCKS) for aux in common.registry.aux_values(name)]


def plans(start, count):
    source = dump_states()
    if type(start) is not int or type(count) is not int or not 0 <= start < len(source) or not 0 < count <= MAX_COUNT:
        raise ValueError('Expected an existing dump index and count in 1..256')
    return [{'index': index, 'requested': [name, aux], 'expected_states': common.registry.states((name, aux))}
            for index, (name, aux) in enumerate(source[start:start + count], start)]


START = '''def _scaffold_semantic_catalogue(config):
 import math,sys,json,traceback
 import mod.server.extraServerApi as api
 from modern_projection.projection import block_registry as registry
 marker=config['marker']
 assert not hasattr(sys,marker),'Previous semantic support probe needs cleanup'
 assert api.GetMinecraftVersion()==config['runtime'],'Runtime differs'
 assert (registry.SOURCE_VERSION,registry.SOURCE_SHA256)==(config['game_version'],config['palette_sha256']),'Registry differs'
 assert config['fresh_owned_flow_allowed'] is True,'Fresh owned flow baseline required'
 assert 0<len(config['plans'])<=256,'Range exceeds budget'
 players=api.GetPlayerList()
 assert len(players)==1,'Owned single player required'
 factory=api.GetEngineCompFactory()
 level=api.GetLevelId()
 player=players[0]
 foot=factory.CreatePos(player).GetFootPos()
 dimension=factory.CreateDimension(player).GetEntityDimensionId()
 assert dimension==0 and foot is not None and -64<=foot[1]<=320,'World not initialized'
 origin=(int(math.floor(foot[0]))+4,int(math.floor(foot[1]))+2,int(math.floor(foot[2]))+4)
 slots=[(origin[0]+(i%4)*3,origin[1],origin[2]+(i//4)*3) for i in range(8)]
 offsets=config['offsets']
 reserved=sorted(set(tuple(slot[i]+offset[i] for i in range(3)) for slot in slots for offset in offsets))
 info=factory.CreateBlockInfo(level)
 state=factory.CreateBlockState(level)
 block=factory.CreateBlock(level)
 game=factory.CreateGame(level)
 __PALETTE_HELPER__
 def read(pos):
  return {'pos':pos,'front':info.GetBlockNew(pos,dimension),'states':state.GetBlockStates(pos,dimension),
          'liquid':info.GetLiquidBlock(pos,dimension),'palette':palette_read(pos)}
 def dry(value):
  front,liquid=value['front'],value['liquid']
  return (front=={'name':'minecraft:air','aux':0} and type(front.get('aux')) is int
   and (value['states'] is None or value['states']=={}) and palette_air(value['palette'])
   and (liquid is None or liquid.get('name')=='minecraft:air' and type(liquid.get('aux',0)) is int and liquid.get('aux',0)==0))
 baseline=[read(pos) for pos in reserved]
 assert all(dry(row) for row in baseline),'Reserve not dry air'
 air=block.GetBlankBlockPalette()
 assert air is not None and air.DeserializeBlockPalette({
  'volume':(1,1,1),'common':{('minecraft:air',0):[0]},'states':{},
  'extra':{('minecraft:air',0):[0]},'extraStates':{},'actor':{},'void':False,'eliminateAir':False}) is True,'Air palette rejected'
 rules=game.GetGameRulesInfoServer()
 assert isinstance(rules,dict) and type(rules['option_info']['tile_drops']) is bool,'Tile drops baseline unavailable'
 probe={'config':config,'info':info,'state':state,'block':block,'game':game,'air':air,'dimension':dimension,
  'reserved':reserved,'origin':origin,'slots':slots,'original_tile_drops':rules['option_info']['tile_drops'],
  'active':True,'done':False,'timer_pending':False,'index':0,'rows':[],'batches':[],
  'pending':[],'error':None,'stage':'setup','initial':baseline,'setup':{},'start':None}
 setattr(sys,marker,probe)
 def fail(error):
  probe['active']=False
  probe['timer_pending']=False
  probe['error']={'stage':probe['stage'],'index':probe['index'],'message':repr(error),'traceback':traceback.format_exc()}
 def clear():
  returns=[]
  for pos in reversed(reserved):
   returned=block.SetBlockByBlockPalette(air,dimension,pos,0,0)
   returns.append({'pos':pos,'returned':returned})
   assert type(returned) is bool,('Invalid clear return',pos,returned)
  actual=[read(pos) for pos in reserved]
  assert all(dry(row) for row in actual),'Dual-layer clear left visible blocks or fluid'
  return {'returns':returns,'readbacks':actual}
 def write(pos,name,aux,updates):
  before=read(pos)
  returned=info.SetBlockNew(pos,{'name':name,'aux':aux},0,dimension,True,updates)
  assert type(returned) is bool,('Invalid block write return',name,aux,returned)
  return {'pos':pos,'name':name,'aux':aux,'before':before,'returned':returned,
          'is_legacy':True,'update_neighbors':updates}
 def advance():
  if not probe['active'] or getattr(sys,marker,None) is not probe:return
  if probe['index']>=len(config['plans']):
   probe['stage']='done'
   probe['active']=False
   probe['done']=True
   return
  probe['stage']='batch_clear'
  batch={'start':probe['index'],'reset':clear(),'rows':[]}
  probe['batches'].append(batch)
  probe['pending']=[]
  for slot,plan in zip(slots,config['plans'][probe['index']:probe['index']+8]):
   pair,expected=plan['requested'],plan['expected_states']
   row={'index':plan['index'],'requested':pair,'expected_states':expected,'slot':slot,
        'converted_aux':None,'conversion_states':None,'writes':[],
        'semantic_set_returned':None,'support_written':None,'scaffold_written':None}
   batch['rows'].append(row)
   probe['pending'].append(row)
   probe['stage']='support_conversion'
   converted=state.GetBlockAuxValueFromStates(pair[0],expected)
   row['converted_aux']=converted
   if type(converted) is not int or converted<0:
    row['conversion_failed']=True
    continue
   row['conversion_states']=state.GetBlockStatesFromAuxValue(pair[0],converted)
   row['writes'].append(write((slot[0],slot[1]-1,slot[2]),'minecraft:stone',0,False))
   row['writes'].append(write(slot,pair[0],converted,False))
   probe['stage']='semantic_set'
   row['semantic_set_returned']=state.SetBlockStates(slot,expected,dimension)
   assert type(row['semantic_set_returned']) is bool,'Invalid semantic write return'
   row['support_written']=read(slot)
   row['upper_before_scaffold']=read((slot[0],slot[1]+1,slot[2]))
   row['writes'].append(write((slot[0],slot[1]+1,slot[2]),'minecraft:scaffolding',0,True))
   row['scaffold_written']={'support':read(slot),'scaffold':read((slot[0],slot[1]+1,slot[2]))}
  probe['stage']='await_delayed_035'
  probe['timer_pending']=True
  game.AddTimer(.35,lambda current=probe,number=probe['index']:observe(current,number))
 def observe(current,number):
  if current is not probe or not current['active'] or current['index']!=number or getattr(sys,marker,None) is not current:return
  try:
   current['timer_pending']=False
   current['stage']='delayed_035'
   for row in current['pending']:
    slot=row['slot']
    row['delayed']={'support':read(slot),'scaffold':read((slot[0],slot[1]+1,slot[2]))}
    current['rows'].append(row)
   current['stage']='batch_final_clear'
   current['batches'][-1]['after']=clear()
   current['index']+=len(current['pending'])
   advance()
  except Exception as error:fail(error)
 try:
  probe['setup']['rules_returned']=game.SetGameRulesInfoServer({'option_info':{'tile_drops':False}})
  probe['setup']['rules_actual']=game.GetGameRulesInfoServer()['option_info']['tile_drops']
  assert probe['setup']['rules_returned'] is True and probe['setup']['rules_actual'] is False,'Rules setup failed'
  probe['setup']['flow_returned']=game.ForbidLiquidFlow(True)
  assert probe['setup']['flow_returned'] is True,'Flow setup failed'
  advance()
 except Exception as error:fail(error)
 probe['start']={'origin':origin,'slots':slots,'reserved':len(reserved),'runtime':api.GetMinecraftVersion(),
  'game_version':registry.SOURCE_VERSION,'palette_sha256':registry.SOURCE_SHA256,'identity':config['identity'],
  'source_sha256':config['source_sha256'],'range':config['range'],'controls':len(config['plans']),
  'original_tile_drops':probe['original_tile_drops'],'fresh_owned_flow_allowed':True,
  'baseline':baseline,'setup':probe['setup']}
 return json.dumps(probe['start'])
_result=_scaffold_semantic_catalogue(__CONFIG__)
del _scaffold_semantic_catalogue
'''

STATUS = '''def _scaffold_semantic_status():
 import sys,json
 probe=getattr(sys,%r)
 assert probe['config']['identity']==%r,'Semantic catalogue identity differs'
 return json.dumps(dict((key,probe[key]) for key in ('done','error','index','stage','timer_pending','rows','batches','start')))
_result=_scaffold_semantic_status()
del _scaffold_semantic_status
'''

def restore_payload(identity):
    import probe_scaffold_runtime_lifecycle
    return probe_scaffold_runtime_lifecycle.native_restore() % (MARKER, identity)


def start_payload(start, count, identity, source_sha256, allowed, air_encoding):
    selected = plans(start, count)
    config = {'marker': MARKER, 'runtime': common.RUNTIME, 'game_version': common.registry.SOURCE_VERSION,
              'palette_sha256': common.registry.SOURCE_SHA256, 'plans': selected,
              'range': [start, start + len(selected)], 'offsets': common.OFFSETS,
              'identity': identity, 'source_sha256': source_sha256, 'fresh_owned_flow_allowed': allowed,
              'air_encoding': air_encoding}
    code = START.replace('__PALETTE_HELPER__', '\n'.join(line if number == 0 else ' ' + line
                         for number, line in enumerate(HELPER.splitlines())))
    return code.replace('__CONFIG__', repr(config))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--start-index', type=int, default=0)
    parser.add_argument('--count', type=int, default=MAX_COUNT)
    parser.add_argument('--fresh-owned-flow-allowed', action='store_true')
    parser.add_argument('--air-observation', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.fresh_owned_flow_allowed:
        parser.error('Use a new output and declare the fresh owned flow baseline')
    selected = plans(args.start_index, args.count)
    session_file, owner, session = common.owned_session()
    identity = {'session_id': session['id'], 'owner': owner, 'game_pid': session['game_pid'],
                'game_identity': session['game_identity'], 'run_id': uuid.uuid4().hex}
    source = common.digest(Path(__file__).read_bytes())
    observation_raw = args.air_observation.read_bytes()
    air_encoding = encoding_from_observation(json.loads(observation_raw))
    payload = start_payload(args.start_index, args.count, identity, source, True, air_encoding)
    status, restore = STATUS % (MARKER, identity), restore_payload(identity)
    report = {'schema': SCHEMA, 'method': METHOD, 'source_sha256': source,
              'template_sha256': common.digest(Path(common.__file__).read_bytes()), 'identity': identity,
              'game_executable_sha256': common.digest(Path(session['game_executable']).read_bytes()),
              'session_file': session_file, 'game_version': common.registry.SOURCE_VERSION,
              'palette_sha256': common.registry.SOURCE_SHA256, 'plans': selected,
              'range': [args.start_index, args.start_index + len(selected)],
              'completed': False, 'restored': False, 'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
              'air_encoding': air_encoding, 'air_observation_sha256': common.digest(observation_raw),
              'payload_sha256': {key: common.digest(code.encode('utf8')) for key, code in
                                 (('start', payload), ('status', status), ('restore', restore))}}
    common.checkpoint(args.output, report, exclusive=True)
    try:
        with common.Client(timeout=15) as client:
            check = common.BlueprintCheck(client, args.output, 90)
            try:
                report['start'] = common.run(client, payload)
                def progress():
                    report['native'] = common.run(client, status)
                    common.checkpoint(args.output, report)
                    return report['native']
                report['native'] = check.wait('bounded semantic support states', lambda value: value['done'] or value['error'], progress)
                if report['native']['error']:
                    raise RuntimeError(report['native']['error'])
            except Exception as error:
                report['error'] = repr(error)
            finally:
                try:
                    report['native'] = common.run(client, status)
                except Exception as error:
                    report['final_status_error'] = repr(error)
                try:
                    report['cleanup'] = common.run(client, restore)
                    report['restored'] = report['cleanup']['restored']
                except Exception as error:
                    report['cleanup_error'] = repr(error)
        report['completed'] = report['native'].get('done') is True and not report.get('error') and report['restored'] is True
    except Exception as error:
        report.setdefault('error', repr(error))
    finally:
        common.checkpoint(args.output, report)
    print(json.dumps({key: report.get(key) for key in ('completed', 'restored', 'error', 'cleanup_error')}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
