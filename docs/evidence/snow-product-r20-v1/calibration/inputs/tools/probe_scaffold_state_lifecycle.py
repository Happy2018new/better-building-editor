"""Owned short SDK diagnostics; never emits scaffold capability evidence.

Sequentially compare direct legacy aux writes with converted semantic writes at
eight fixed states in one 17-cell reserve. Record real GetBlockStates before
scaffold placement, immediately after placement and after .35 seconds. Run only
in a fresh owned allowed-flow session. Block-entity data remains unverified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

from context_test_environment import run
from verify_debug_blueprints import BlueprintCheck, Client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry

KIND = 'scaffold_state_lifecycle_diagnostic'
METHOD = '17 sequential scaffold lifecycle SDK controls; one 17-cell reserve; legacy versus semantic; true states; .35s; v1'
RUNTIME = '1.21.120.0'
MARKER = '_scaffold_state_lifecycle_v1'
DIRECT, SEMANTIC, POSITIVE = 'direct_legacy', 'converted_semantic', 'stone_positive'
PHASES = ('support_written', 'scaffold_written', 'delayed_035')
OFFSETS = tuple((x, y, z) for y in (-1, 0, 1)
                for x, z in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))) + ((0, 2, 0), (0, 3, 0))
ACTOR_SCOPE = 'unknown_not_supplied_or_read'
CONTROLS = (
    ('stone', 'minecraft:stone', 0),
    ('log', 'minecraft:acacia_log', 1),
    ('button', 'minecraft:acacia_button', 0),
    ('door', 'minecraft:acacia_door', 0),
    ('gate', 'minecraft:acacia_fence_gate', 8),
    ('wall', 'minecraft:andesite_wall', 256),
    ('bookshelf', 'minecraft:chiseled_bookshelf', 4),
    ('shelf', 'minecraft:acacia_shelf', 4),
)


def plans():
    rows = [{'id': name + '_' + method, 'control': name, 'method': method,
             'requested': [block, aux], 'expected_states': registry.states((block, aux))}
            for name, block, aux in CONTROLS for method in (DIRECT, SEMANTIC)]
    rows.append({'id': 'stone_positive', 'control': 'stone_positive', 'method': POSITIVE,
                 'requested': ['minecraft:stone', 0], 'expected_states': {}})
    for index, row in enumerate(rows):
        row['case_index'] = index
        row['slot'] = [0, 0, 0]
        row['actor_data'] = ACTOR_SCOPE
    return rows


def reserved_positions(selected):
    return sorted({tuple(row['slot'][i] + offset[i] for i in range(3))
                   for row in selected for offset in OFFSETS})


START = '''def _start_scaffold_lifecycle(config):
 import json,sys,math,traceback
 import mod.server.extraServerApi as api
 from modern_projection.projection import block_registry as registry
 marker=config['marker']
 assert not hasattr(sys,marker),'Previous lifecycle probe requires cleanup'
 assert api.GetMinecraftVersion()==config['runtime'],'Runtime mismatch'
 assert (registry.SOURCE_VERSION,registry.SOURCE_SHA256)==(config['game_version'],config['palette_sha256']),'Registry mismatch'
 assert config['fresh_owned_flow_allowed'] is True,'Owned allowed-flow baseline required'
 assert len(config['plans'])==17
 factory=api.GetEngineCompFactory()
 level=api.GetLevelId()
 player=api.GetPlayerList()[0]
 dimension=factory.CreateDimension(player).GetEntityDimensionId()
 foot=factory.CreatePos(player).GetFootPos()
 origin=(int(math.floor(foot[0]))+4,int(math.floor(foot[1]))+18,int(math.floor(foot[2]))+4)
 info=factory.CreateBlockInfo(level)
 block=factory.CreateBlock(level)
 state=factory.CreateBlockState(level)
 game=factory.CreateGame(level)
 offsets=config['offsets']
 reserved=sorted(tuple(origin[i]+offset[i] for i in range(3)) for offset in offsets)
 assert len(reserved)==config['reserved_cells']==17,'Reserve changed'
 def read(pos):
  front=info.GetBlockNew(pos,dimension)
  assert front is not None and front.get('name') not in (None,'minecraft:unknown'),('unloaded',pos,front)
  states=state.GetBlockStates(pos,dimension)
  return {'front':front,'states':states,'liquid':info.GetLiquidBlock(pos,dimension)}
 def dry_air(value):
  liquid=value['liquid']
  return value['front']=={'name':'minecraft:air','aux':0} and value['states']=={} and (liquid is None or liquid.get('name')=='minecraft:air' and liquid.get('aux',0)==0)
 baseline=[dict(read(tuple(origin[i]+offset[i] for i in range(3))),offset=offset) for offset in offsets]
 assert all(dry_air(value) for value in baseline),'Non-dry reserve'
 rules=game.GetGameRulesInfoServer()
 assert isinstance(rules,dict) and type(rules['option_info']['tile_drops']) is bool,'Unknown tile-drops baseline'
 air=block.GetBlankBlockPalette()
 assert air is not None,'Missing dual-layer air palette'
 air_return=air.DeserializeBlockPalette({
  'volume':(1,1,1),'common':{('minecraft:air',0):[0]},'states':{},
  'extra':{('minecraft:air',0):[0]},'extraStates':{},'actor':{},'void':False,'eliminateAir':False})
 assert air_return is True,'Dual-layer air palette rejected'
 probe={'config':config,'info':info,'block':block,'state':state,'game':game,'air':air,
        'reserved':reserved,'dimension':dimension,'original_tile_drops':rules['option_info']['tile_drops'],
        'active':True,'done':False,'error':None,'rows':[None]*17,'observed':0,'index':0,'sequence':0,
        'stage':'setup','setup':{'air_palette_returned':air_return},'timer_pending':False,
        'start':None}
 setattr(sys,marker,probe)
 def sequence():
  probe['sequence']+=1
  return probe['sequence']
 def snapshot(phase):
  value={'phase':phase,'sequence':sequence(),'cells':[],'read_errors':[]}
  for offset in offsets:
   pos=tuple(origin[i]+offset[i] for i in range(3))
   try:
    cell=dict(read(pos),offset=offset)
    value['cells'].append(cell)
    if not isinstance(cell['states'],dict):value['read_errors'].append({'offset':offset,'error':'Missing native states','returned':cell['states']})
   except Exception as error:value['read_errors'].append({'offset':offset,'error':repr(error)})
  return value
 def sampled(samples,phase):
  value=snapshot(phase)
  samples.append(value)
  assert not value['read_errors'],('native snapshot failed',phase,value['read_errors'])
  return value
 def write(pos,pair,updates):
  before=read(pos)
  ordinal=sequence()
  returned=info.SetBlockNew(pos,{'name':pair[0].encode('utf8'),'aux':pair[1]},0,dimension,True,updates)
  return {'requested':pair,'before':before,'is_legacy':True,'update_neighbors':updates,'returned':returned,'sequence':ordinal}
 def clear_case(row):
  row['air_reset_returns']=[]
  row['reset_errors']=[]
  for pos in reversed(reserved):
   try:
    returned=block.SetBlockByBlockPalette(air,dimension,pos,0,0)
    row['air_reset_returns'].append({'pos':pos,'returned':returned})
    if returned is not True:row['reset_errors'].append({'pos':pos,'returned':returned})
   except Exception as error:row['reset_errors'].append({'pos':pos,'error':repr(error)})
  row['after_case']=snapshot('case_cleared')
  assert not row['reset_errors'] and not row['after_case']['read_errors'] and all(dry_air(value) for value in row['after_case']['cells']),'Case dual-layer cleanup failed'
 def failed(error):
  probe['active']=False
  probe['timer_pending']=False
  probe['error']={'stage':probe['stage'],'case_index':probe['index'],'message':repr(error),'traceback':traceback.format_exc()}
 def observe(current,index):
  if not current['active'] or getattr(sys,marker,None) is not current or current['index']!=index:return
  try:
   current['timer_pending']=False
   current['stage']='delayed_035'
   row=current['rows'][index]
   sampled(row['samples'],'delayed_035')
   current['stage']='case_clear'
   clear_case(row)
   current['observed']+=1
   current['index']+=1
   if current['observed']==17:
    current['done']=True
    current['active']=False
    current['stage']='done'
   else:begin(current['index'])
  except Exception as error:failed(error)
 def begin(index):
  plan=config['plans'][index]
  probe['stage']='case_baseline'
  row={'id':plan['id'],'case_index':index,'method':plan['method'],'requested':plan['requested'],
       'expected_states':plan['expected_states'],'actor_data':plan['actor_data'],
       'native_aux':None,'semantic_set_returned':None,'writes':[],'samples':[]}
  probe['rows'][index]=row
  row['baseline']=snapshot('case_dry_air')
  assert not row['baseline']['read_errors'] and all(dry_air(value) for value in row['baseline']['cells']),'Case reserve is not dry air'
  probe['stage']='floor_write'
  row['writes'].append(write((origin[0],origin[1]-1,origin[2]),('minecraft:stone',0),False))
  pair=plan['requested']
  probe['stage']='native_conversion'
  native_aux=state.GetBlockAuxValueFromStates(pair[0].encode('utf8'),plan['expected_states'])
  row['native_aux']=native_aux
  assert type(native_aux) is int and native_aux>=0,('conversion failed',pair,native_aux)
  support_pair=(pair[0],native_aux if plan['method']=='converted_semantic' else pair[1])
  probe['stage']='support_write'
  row['writes'].append(write(origin,support_pair,False))
  if plan['method']=='converted_semantic':
   probe['stage']='semantic_set'
   row['semantic_set_returned']=state.SetBlockStates(origin,plan['expected_states'],dimension)
  probe['stage']='support_written'
  sampled(row['samples'],'support_written')
  probe['stage']='scaffold_write'
  row['writes'].append(write((origin[0],origin[1]+1,origin[2]),('minecraft:scaffolding',0),True))
  probe['stage']='scaffold_written'
  sampled(row['samples'],'scaffold_written')
  probe['stage']='timer_schedule'
  ordinal=sequence()
  returned=game.AddTimer(.35,lambda current=probe,number=index,callback=observe:callback(current,number))
  row['timer']={'delay':.35,'sequence':ordinal,'return_type':type(returned).__name__,'return_repr':repr(returned)}
  probe['timer_pending']=True
  probe['stage']='await_delayed_035'
 try:
  probe['setup']['rules_returned']=game.SetGameRulesInfoServer({'option_info':{'tile_drops':False}})
  probe['setup']['rules_actual']=game.GetGameRulesInfoServer()['option_info']['tile_drops']
  assert probe['setup']['rules_returned'] is True and probe['setup']['rules_actual'] is False,'Tile-drops setup failed'
  probe['setup']['flow_returned']=game.ForbidLiquidFlow(True)
  assert probe['setup']['flow_returned'] is True,'Flow setup failed'
  begin(0)
 except Exception as error:failed(error)
 probe['start']={'origin':origin,'dimension':dimension,'reserved':len(reserved),'runtime':api.GetMinecraftVersion(),
         'game_version':registry.SOURCE_VERSION,'palette_sha256':registry.SOURCE_SHA256,
         'controls':17,'source_sha256':config['source_sha256'],'identity':config['identity'],
         'original_tile_drops':probe['original_tile_drops'],'fresh_owned_flow_allowed':True,
         'baseline':baseline,'setup':probe['setup'],'actor_data':config['actor_data']}
 return json.dumps(probe['start'])
_result=_start_scaffold_lifecycle(__CONFIG__)
del _start_scaffold_lifecycle
'''

STATUS = '''def _scaffold_lifecycle_status():
 import json,sys
 probe=getattr(sys,%r)
 assert probe['config']['identity']==%r,'Lifecycle probe identity differs'
 return json.dumps(dict((key,probe[key]) for key in ('done','error','rows','observed','index','sequence','stage','timer_pending','setup','start')))
_result=_scaffold_lifecycle_status()
del _scaffold_lifecycle_status
'''

RESTORE = '''def _restore_scaffold_lifecycle():
 import json,sys
 marker=%r
 probe=getattr(sys,marker,None)
 if probe is None:return json.dumps({'restored':False,'missing_probe':True})
 assert probe['config']['identity']==%r,'Lifecycle probe identity differs'
 probe['active']=False
 errors=[]
 returns=[]
 remaining=[]
 readbacks=[]
 for pos in reversed(probe['reserved']):
  try:
   returned=probe['block'].SetBlockByBlockPalette(probe['air'],probe['dimension'],pos,0,0)
   returns.append({'pos':pos,'returned':returned})
   if returned is not True:errors.append({'operation':'air_reset','pos':pos,'returned':returned})
  except Exception as error:errors.append({'operation':'air_reset','pos':pos,'error':repr(error)})
 for pos in probe['reserved']:
  try:
   front=probe['info'].GetBlockNew(pos,probe['dimension'])
   states=probe['state'].GetBlockStates(pos,probe['dimension'])
   liquid=probe['info'].GetLiquidBlock(pos,probe['dimension'])
   readback={'pos':pos,'front':front,'states':states,'liquid':liquid}
   readbacks.append(readback)
   if front!={'name':'minecraft:air','aux':0} or states!={} or liquid is not None and (liquid.get('name')!='minecraft:air' or liquid.get('aux',0)!=0):
    remaining.append(readback)
  except Exception as error:errors.append({'operation':'air_readback','pos':pos,'error':repr(error)});remaining.append({'pos':pos})
 rules_return=None
 rules_actual=None
 flow_return=None
 try:
  rules_return=probe['game'].SetGameRulesInfoServer({'option_info':{'tile_drops':probe['original_tile_drops']}})
  rules_actual=probe['game'].GetGameRulesInfoServer()['option_info']['tile_drops']
 except Exception as error:errors.append({'operation':'restore_rules','error':repr(error)})
 try:flow_return=probe['game'].ForbidLiquidFlow(False)
 except Exception as error:errors.append({'operation':'restore_flow','error':repr(error)})
 rules_ok=rules_return is True and rules_actual is probe['original_tile_drops']
 flow_ok=flow_return is True
 restored=not errors and not remaining and rules_ok and flow_ok
 if restored:delattr(sys,marker)
 return json.dumps({'restored':restored,'reserved_air':len(probe['reserved'])-len(remaining),'remaining':remaining,
  'air_reset_returns':returns,'air_readbacks':readbacks,'errors':errors,'rules_returned':rules_return,'rules_actual':rules_actual,
  'rules_restored':rules_ok,'flow_returned':flow_return,'flow_restored':flow_ok,'flow_baseline':'declared_fresh_owned_allowed'})
_result=_restore_scaffold_lifecycle()
del _restore_scaffold_lifecycle
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def start_payload(identity, source_sha256, fresh_owned_flow_allowed):
    selected = plans()
    config = {'marker': MARKER, 'runtime': RUNTIME, 'game_version': registry.SOURCE_VERSION,
              'palette_sha256': registry.SOURCE_SHA256, 'plans': selected, 'offsets': OFFSETS,
              'reserved_cells': len(reserved_positions(selected)), 'identity': identity,
              'source_sha256': source_sha256, 'fresh_owned_flow_allowed': fresh_owned_flow_allowed,
              'actor_data': ACTOR_SCOPE}
    return START.replace('__CONFIG__', repr(config))


def owned_session(environ=os.environ):
    path, owner = environ.get('MCDEV_SESSION_FILE'), environ.get('MCDEV_OWNER')
    if not path or not owner:
        raise ValueError('Use instances.py exec with an explicit owned session and owner')
    session = json.loads(Path(path).read_bytes())
    if session.get('owner') != owner or Path(session.get('project', '')).resolve() != ROOT.resolve():
        raise ValueError('Owned session belongs to another project or owner')
    if not all(session.get(key) for key in ('id', 'game_pid', 'game_identity', 'game_executable')):
        raise ValueError('Owned session has no recorded game identity')
    return path, owner, session


def state_key(states):
    return None if states is None else tuple(sorted((key, type(value).__name__, value) for key, value in states.items()))


def cell_at(sample, offset):
    return next(cell for cell in sample['cells'] if tuple(cell['offset']) == offset)


def readback_valid(value):
    if not isinstance(value, dict) or not isinstance(value.get('states'), dict):
        return False
    front, liquid = value.get('front'), value.get('liquid')
    return (isinstance(front, dict) and isinstance(front.get('name'), str)
            and type(front.get('aux')) is int and 'liquid' in value
            and (liquid is None or isinstance(liquid, dict) and isinstance(liquid.get('name'), str)
                 and type(liquid.get('aux', 0)) is int))


def check_sample(sample, phase, dry=False):
    cells = sample.get('cells', [])
    if (sample.get('phase') != phase or type(sample.get('sequence')) is not int
            or len(cells) != len(OFFSETS) or {tuple(value.get('offset', ())) for value in cells} != set(OFFSETS)
            or sample.get('read_errors', []) != [] or any(not readback_valid(value) for value in cells)):
        raise ValueError('Lifecycle readback omitted native cells or true states')
    if dry and any(value['front'] != {'name': 'minecraft:air', 'aux': 0} or value['states'] != {}
                   or value['liquid'] is not None and (value['liquid']['name'] != 'minecraft:air'
                                                       or value['liquid'].get('aux', 0) != 0) for value in cells):
        raise ValueError('Lifecycle reused reserve was not dry air in both layers')


def check_resets(reset, absolute):
    if (len(reset) != len(absolute) or {tuple(row.get('pos', ())) for row in reset} != absolute
            or any(row.get('returned') is not True for row in reset)):
        raise ValueError('Lifecycle reset did not verify every owned cell')


def validate_report(report, source_sha256=None):
    expected_source = source_sha256 or digest(Path(__file__).read_bytes())
    selected = plans()
    start, native, cleanup = report.get('start', {}), report.get('native', {}), report.get('cleanup', {})
    if (report.get('schema') != 1 or report.get('kind') != KIND or report.get('method') != METHOD
            or report.get('source_sha256') != expected_source or report.get('completed') is not True
            or report.get('restored') is not True or report.get('error') or report.get('cleanup_error')
            or start.get('runtime') != RUNTIME or start.get('game_version') != registry.SOURCE_VERSION
            or start.get('palette_sha256') != registry.SOURCE_SHA256 or start.get('source_sha256') != expected_source
            or start.get('reserved') != len(reserved_positions(selected)) or start.get('controls') != 17
            or start.get('fresh_owned_flow_allowed') is not True or type(start.get('original_tile_drops')) is not bool
            or start.get('actor_data') != ACTOR_SCOPE or report.get('actor_data') != ACTOR_SCOPE
            or report.get('acceptance') != {'editor': 'pending', 'full': 'pending', 'missing': 'pending'}
            or native.get('done') is not True or native.get('observed') != 17 or native.get('index') != 17
            or native.get('timer_pending') is not False or native.get('stage') != 'done'
            or native.get('start') != start or native.get('error')):
        raise ValueError('Incomplete or mismatching lifecycle diagnostic')
    recorded_plans = report.get('plans', [])
    if (len(recorded_plans) != len(selected)
            or any({key: row.get(key) for key in ('id', 'control', 'method', 'requested', 'slot', 'case_index', 'actor_data')}
                   != {key: plan[key] for key in ('id', 'control', 'method', 'requested', 'slot', 'case_index', 'actor_data')}
                   or state_key(row.get('expected_states')) != state_key(plan['expected_states'])
                   for row, plan in zip(recorded_plans, selected))):
        raise ValueError('Lifecycle recorded plans differ')
    setup = start.get('setup', {})
    if (setup.get('air_palette_returned') is not True or setup.get('rules_returned') is not True
            or setup.get('rules_actual') is not False or setup.get('flow_returned') is not True
            or native.get('setup') != setup):
        raise ValueError('Lifecycle setup API returns are incomplete')
    provenance = report.get('provenance', {})
    identity = {key: provenance.get(key) for key in ('session_id', 'owner', 'game_pid', 'game_identity', 'run_id')}
    if not all(identity.values()) or start.get('identity') != identity:
        raise ValueError('Lifecycle session identity differs')
    payload = start_payload(identity, expected_source, True)
    if (provenance.get('native_payload_sha256') != digest(payload.encode('utf8'))
            or provenance.get('native_status_payload_sha256') != digest((STATUS % (MARKER, identity)).encode('utf8'))
            or provenance.get('native_restore_payload_sha256') != digest((RESTORE % (MARKER, identity)).encode('utf8'))):
        raise ValueError('Lifecycle payload fingerprint differs')
    executable_hash = provenance.get('game_executable_sha256')
    if (not isinstance(executable_hash, str) or len(executable_hash) != 64
            or any(character not in '0123456789abcdef' for character in executable_hash)):
        raise ValueError('Lifecycle game executable fingerprint is missing')
    if (cleanup.get('restored') is not True or cleanup.get('rules_restored') is not True
            or cleanup.get('flow_restored') is not True or cleanup.get('rules_returned') is not True
            or cleanup.get('flow_returned') is not True or cleanup.get('rules_actual') is not start['original_tile_drops']
            or cleanup.get('reserved_air') != start['reserved'] or cleanup.get('remaining') != []
            or cleanup.get('errors') != [] or cleanup.get('flow_baseline') != 'declared_fresh_owned_allowed'):
        raise ValueError('Lifecycle scratch space or policy restoration failed')
    reset = cleanup.get('air_reset_returns', [])
    origin = start.get('origin', [])
    if len(origin) != 3 or any(type(value) is not int for value in origin):
        raise ValueError('Invalid lifecycle origin')
    absolute = {tuple(origin[i] + pos[i] for i in range(3)) for pos in reserved_positions(selected)}
    check_resets(reset, absolute)
    cleanup_readbacks = cleanup.get('air_readbacks', [])
    if len(cleanup_readbacks) != len(absolute) or {tuple(value.get('pos', ())) for value in cleanup_readbacks} != absolute:
        raise ValueError('Lifecycle cleanup native readbacks are incomplete')
    check_sample({'phase': 'cleanup_dry_air', 'sequence': 0,
                  'cells': [dict(value, offset=tuple(value['pos'][i] - origin[i] for i in range(3)))
                            for value in cleanup_readbacks]}, 'cleanup_dry_air', dry=True)
    check_sample({'phase': 'initial_dry_air', 'sequence': 0, 'cells': start.get('baseline', [])}, 'initial_dry_air', dry=True)
    rows = native.get('rows', [])
    if len(rows) != 17 or [row.get('id') for row in rows] != [row['id'] for row in selected]:
        raise ValueError('Lifecycle needs the exact 17 controls in order')
    result, previous_sequence = [], 0
    for row, plan in zip(rows, selected):
        if (row.get('method') != plan['method'] or row.get('requested') != plan['requested']
                or state_key(row.get('expected_states')) != state_key(plan['expected_states'])
                or row.get('case_index') != plan['case_index'] or row.get('actor_data') != ACTOR_SCOPE
                or type(row.get('native_aux')) is not int or row['native_aux'] < 0):
            raise ValueError('Lifecycle requested control or conversion changed')
        semantic = row.get('semantic_set_returned')
        if (plan['method'] == SEMANTIC and type(semantic) is not bool
                or plan['method'] != SEMANTIC and semantic is not None):
            raise ValueError('Lifecycle semantic API return is missing')
        support = [plan['requested'][0], row['native_aux'] if plan['method'] == SEMANTIC else plan['requested'][1]]
        writes = row.get('writes', [])
        if (len(writes) != 3 or [list(value.get('requested', ())) for value in writes]
                != [['minecraft:stone', 0], support, ['minecraft:scaffolding', 0]]
                or [value.get('update_neighbors') for value in writes] != [False, False, True]
                or any(value.get('is_legacy') is not True or type(value.get('returned')) is not bool
                       or not readback_valid(value.get('before')) or type(value.get('sequence')) is not int for value in writes)):
            raise ValueError('Lifecycle write methods or flags changed')
        samples = row.get('samples', [])
        if [value.get('phase') for value in samples] != list(PHASES):
            raise ValueError('Lifecycle needs all three native readback phases')
        for sample, phase in zip(samples, PHASES):
            check_sample(sample, phase)
        baseline, after = row.get('baseline', {}), row.get('after_case', {})
        check_sample(baseline, 'case_dry_air', dry=True)
        check_sample(after, 'case_cleared', dry=True)
        check_resets(row.get('air_reset_returns', []), absolute)
        if row.get('reset_errors') != []:
            raise ValueError('Lifecycle case cleanup failed')
        timer = row.get('timer', {})
        if (timer.get('delay') != .35 or not isinstance(timer.get('return_type'), str)
                or not isinstance(timer.get('return_repr'), str) or type(timer.get('sequence')) is not int):
            raise ValueError('Lifecycle delayed observation scheduling is missing')
        order = [baseline['sequence'], writes[0]['sequence'], writes[1]['sequence'], samples[0]['sequence'],
                 writes[2]['sequence'], samples[1]['sequence'], timer['sequence'], samples[2]['sequence'], after['sequence']]
        if order != list(range(previous_sequence + 1, previous_sequence + 10)):
            raise ValueError('Lifecycle SDK progression was not sequential')
        previous_sequence = order[-1]
        matches = [cell_at(sample, (0, 0, 0))['front'] == {'name': plan['requested'][0], 'aux': plan['requested'][1]}
                   and state_key(cell_at(sample, (0, 0, 0))['states']) == state_key(plan['expected_states']) for sample in samples]
        result.append({'id': row['id'], 'native_aux_equals_dump': row['native_aux'] == plan['requested'][1],
                       'support_state_matches': dict(zip(PHASES, matches))})
    if native.get('sequence') != previous_sequence:
        raise ValueError('Lifecycle SDK progression is incomplete')
    positive = rows[-1]['samples'][-1]
    support, scaffold = cell_at(positive, (0, 0, 0)), cell_at(positive, (0, 1, 0))
    positive_matched = (support['front'] == {'name': 'minecraft:stone', 'aux': 0} and support['states'] == {}
                        and scaffold['front'].get('name') == 'minecraft:scaffolding'
                        and state_key(scaffold['states']) == state_key(registry.states(('minecraft:scaffolding', scaffold['front']['aux'])))
                        and type(scaffold['states'].get('stability')) is int and scaffold['states']['stability'] == 0)
    return {'scope': 'Lifecycle diagnostics only; changed supports remain unknown; no capability or image acceptance.',
            'actor_data': ACTOR_SCOPE,
            'positive_control_matched': positive_matched, 'rows': result}


def checkpoint(output, report, exclusive=False):
    output.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with output.open('x', encoding='utf8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf8', dir=output.parent,
                                         prefix='.' + output.name + '.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fresh-owned-flow-allowed', action='store_true',
                        help='Declare the fresh owned session baseline; the SDK has no flow-policy getter')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Existing lifecycle evidence must not be overwritten')
    if not args.fresh_owned_flow_allowed:
        parser.error('The fresh owned allowed-flow baseline must be declared explicitly')
    session_file, owner, session = owned_session()
    identity = {'session_id': session['id'], 'owner': owner, 'game_pid': session['game_pid'],
                'game_identity': session['game_identity'], 'run_id': uuid.uuid4().hex}
    source_sha256 = digest(Path(__file__).read_bytes())
    payload = start_payload(identity, source_sha256, True)
    report = {'schema': 1, 'kind': KIND, 'method': METHOD, 'source_sha256': source_sha256,
              'session_file': session_file, 'owner': owner, 'completed': False, 'restored': False,
              'plans': plans(), 'actor_data': ACTOR_SCOPE,
              'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
              'provenance': dict(identity, game_executable_sha256=digest(Path(session['game_executable']).read_bytes()),
                                 native_payload_sha256=digest(payload.encode('utf8')),
                                 native_status_payload_sha256=digest((STATUS % (MARKER, identity)).encode('utf8')),
                                 native_restore_payload_sha256=digest((RESTORE % (MARKER, identity)).encode('utf8')))}
    checkpoint(args.output, report, exclusive=True)
    try:
        with Client(timeout=30) as client:
            if (not client.binding or client.binding.get('owner') != owner
                    or any(client.binding.get(key) != session[key]
                           for key in ('id', 'game_pid', 'game_identity', 'game_executable'))):
                raise ValueError('MCDK client is not bound to the declared owned session')
            check = BlueprintCheck(client, args.output, 30)
            try:
                report['start'] = run(client, payload)
                checkpoint(args.output, report)
                def status():
                    value = run(client, STATUS % (MARKER, identity))
                    report['native'] = value
                    checkpoint(args.output, report)
                    return value
                report['native'] = check.wait('17 scaffold lifecycle diagnostics', lambda value: value['done'] or value['error'],
                                               status)
                if report['native']['error']:
                    raise RuntimeError(report['native']['error'])
            except Exception as error:
                report['error'] = '%s: %s' % (type(error).__name__, error)
            finally:
                try:
                    report['native'] = run(client, STATUS % (MARKER, identity))
                    if report['native'].get('start') is not None:
                        report['start'] = report['native']['start']
                    checkpoint(args.output, report)
                except Exception as error:
                    report['final_status_error'] = '%s: %s' % (type(error).__name__, error)
                try:
                    report['cleanup'] = run(client, RESTORE % (MARKER, identity))
                    report['restored'] = report['cleanup']['restored']
                except Exception as error:
                    report['cleanup_error'] = '%s: %s' % (type(error).__name__, error)
        report['completed'] = not report.get('error') and report['restored'] is True
        report['diagnostic'] = validate_report(report, source_sha256)
        if not report['diagnostic']['positive_control_matched']:
            report['completed'] = False
            report['error'] = 'Independent stone positive control did not match native scaffold states'
    except Exception as error:
        report['completed'] = False
        if not report.get('error'):
            report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        checkpoint(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'positive_control_matched': report.get('diagnostic', {}).get('positive_control_matched'),
                      'error': report.get('error'), 'cleanup_error': report.get('cleanup_error')}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
