"""Diagnose one supported native door pair through documented SDK setters.

Requires an allocated protected owner-bound instance. No palette writes, input,
inventory, camera, player, settings or production transform changes occur.
"""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import time

import capture_native_state_transform_shapes as shapes
from projection.cell import thaw

MARKER = '_native_single_door_saved'

READ_SERVER = shapes.SERVER_BASE + '''saved=getattr(sys,%r)
observed=[]
for row in saved['rows']:
 pos=tuple(row['pos'])
 observed.append({'pos':pos,'value':info.GetBlockNew(pos,dimension),
  'states':state.GetBlockStates(pos,dimension)})
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'rows':observed})
'''

READ_CLIENT = '''import json
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
info=factory.CreateBlockInfo(level)
block=factory.CreateBlock(level)
observed=[]
for row in %r:
 pos=tuple(row['pos'])
 palette=block.GetBlockPaletteBetweenPos(pos,pos,False)
 assert palette is not None, ('native client palette unavailable',pos)
 data=palette.SerializeBlockPalette()
 common=data.get('common',{})
 assert len(common)<=1, ('ambiguous native client palette',pos)
 key=next(iter(common),None)
 observed.append({'pos':pos,'value':info.GetBlock(pos),
  'states':data.get('states',{}).get(key,{}) if key is not None else {}})
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'rows':observed})
'''

READ_CLIENT_PAIR = '''import json
import mod.client.extraClientApi as api
from modern_projection.projection.cell import freeze
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
info=factory.CreateBlockInfo(level)
block=factory.CreateBlock(level)
rows=%r
support=%r
dimension=%r
positions=[tuple(row['pos']) for row in rows]+[tuple(support)]
def fronts():return [{'pos':pos,'value':info.GetBlock(pos)} for pos in positions]
before=fronts()
palettes={}
for label,low,high in (('pair',positions[0],positions[1]),
                       ('lower',positions[0],positions[0]),
                       ('upper',positions[1],positions[1]),
                       ('support',positions[2],positions[2])):
 palette=block.GetBlockPaletteBetweenPos(low,high,False)
 palettes[label]={'low':low,'high':high,'available':palette is not None,
  'serialized':None if palette is None else freeze(palette.SerializeBlockPalette())}
system=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
loaded=getattr(system,'projection_loaded_chunks',None)
chunk=(dimension,positions[0][0]>>4,positions[0][2]>>4)
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'fronts_before':before,'fronts_after':fronts(),
 'palettes':palettes,'loaded_chunk_tracking':{'available':loaded is not None,'chunk':chunk,
  'present':None if loaded is None else chunk in loaded}})
'''

SETUP = shapes.SERVER_BASE + '''from modern_projection.server_system import WorldAdapter
marker=%r
rows=%r
support=%r
reserved=%r
assert not hasattr(sys,marker), 'Prior single-door fixture needs cleanup'
for pos in reserved:
 assert info.GetBlockNew(pos,dimension)=={'name':'minecraft:air','aux':0}, ('non-air reserve',pos)
 assert info.GetLiquidBlock(pos,dimension) is None, ('liquid reserve',pos)
saved={'player':player,'dimension':dimension,'rows':rows,'support':support,
 'reserved':reserved,'foot':factory.CreatePos(player).GetFootPos(),'steps':[]}
setattr(sys,marker,saved)
def snapshot():
 result=[]
 for row in rows:
  pos=tuple(row['pos'])
  result.append({'pos':pos,'value':info.GetBlockNew(pos,dimension),
   'states':state.GetBlockStates(pos,dimension)})
 return result
try:
 returned=info.SetBlockNew(support,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
 saved['support_write']={'returned':returned,'pos':support,
  'value':info.GetBlockNew(support,dimension),'states':state.GetBlockStates(support,dimension)}
 assert saved['support_write']['value']=={'name':'minecraft:stone','aux':0}, 'Support not stone'
 for row in rows:
  properties=WorldAdapter._native_tree(row['states'])
  native_aux=state.GetBlockAuxValueFromStates(row['value'][0].encode('utf8'),properties)
  assert native_aux is not None and native_aux>=0, ('invalid native legacy aux',row,native_aux)
  returned=info.SetBlockNew(tuple(row['pos']),{'name':row['value'][0].encode('utf8'),
   'aux':native_aux},0,dimension,True,False)
  saved['steps'].append({'method':'SetBlockNew','pos':row['pos'],
   'requested':row,'legacy_aux':native_aux,'returned':returned,'both_halves':snapshot()})
 for row in rows:
  returned=state.SetBlockStates(tuple(row['pos']),WorldAdapter._native_tree(row['states']),dimension)
  saved['steps'].append({'method':'SetBlockStates','pos':row['pos'],
   'requested':row,'returned':returned,'both_halves':snapshot()})
except Exception as error:
 saved['error']='%%s: %%s' %% (type(error).__name__,error)
saved['after']={'runtime':api.GetMinecraftVersion(),'rows':snapshot()}
_result=json.dumps({'support_write':saved.get('support_write'),'steps':saved['steps'],
 'error':saved.get('error'),'after':saved['after']})
'''

CLEAR = shapes.SERVER_BASE + '''marker=%r
saved=getattr(sys,marker,None)
result={'restored':True,'marker_present':saved is not None,'errors':[]}
if saved is not None:
 assert saved['player']==player and saved['dimension']==dimension, 'Fixture owner changed'
 for pos in sorted(saved['reserved'],key=lambda p:p[1],reverse=True):
  info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,dimension,True,False)
 for pos in saved['reserved']:
  if info.GetBlockNew(pos,dimension)!={'name':'minecraft:air','aux':0} or info.GetLiquidBlock(pos,dimension) is not None:
   result['errors'].append(['residue',pos])
 foot=factory.CreatePos(player).GetFootPos()
 result['player_unchanged']=all(abs(foot[i]-saved['foot'][i])<.01 for i in range(3))
 result['restored']=not result['errors'] and result['player_unchanged']
 if result['restored']:delattr(sys,marker)
_result=json.dumps(result)
'''


def single_pair(origin):
    rows, supports = shapes.matrix(('minecraft:wooden_door',), origin)
    pair = rows[:2]
    support = supports[0][0]
    return pair, support, shapes.reserve_positions(pair, [(support, ('minecraft:stone', 0))])


def palette_rows(observation, rows):
    pair = observation['palettes']['pair']
    if tuple(pair['low']) != tuple(rows[0]['pos']) or tuple(pair['high']) != tuple(rows[1]['pos']):
        raise ValueError('Pair palette bounds changed')
    if pair['available'] is False:
        if pair['serialized'] is not None:
            raise ValueError('Unavailable pair palette contains data')
        return None
    if pair['available'] is not True:
        raise ValueError('Pair palette availability is malformed')
    data = thaw(pair['serialized'])
    if not isinstance(data, dict) or tuple(data.get('volume', ())) != (1, 1, 2):
        raise ValueError('Pair palette volume must be (1,1,2)')
    common, states = data.get('common', {}), data.get('states', {})
    if not isinstance(common, dict) or not isinstance(states, dict):
        raise ValueError('Pair palette layers are malformed')
    observed = {}
    for value, indices in common.items():
        material = shapes.pair(value)
        if not material or len(material) != 2 or type(material[1]) is not int or not isinstance(material[0], (str, bytes)):
            raise ValueError('Pair palette material is malformed')
        name = material[0].decode('utf8') if isinstance(material[0], bytes) else material[0]
        properties = states.get(value)
        if properties is not None:
            if not isinstance(properties, dict):
                raise ValueError('Pair palette states are malformed')
            properties = {key.decode('utf8') if isinstance(key, bytes) else key:
                          item.decode('utf8') if isinstance(item, bytes) else item
                          for key, item in properties.items()}
        if not isinstance(indices, (list, tuple)):
            raise ValueError('Pair palette indices are malformed')
        for index in indices:
            if type(index) is not int or index not in (0, 1) or index in observed:
                raise ValueError('Pair palette index is duplicate or outside the pair')
            observed[index] = {'pos': rows[index]['pos'], 'value': (name, material[1]),
                               'states': properties, 'state_source': 'pair_palette'}
    return observed


def front_pair_matches(observation, expected):
    return (isinstance(observation, list) and len(observation) == len(expected) and
            len({tuple(row['pos']) for row in observation}) == len(expected) and
            {tuple(row['pos']): shapes.pair(row['value']) for row in observation} == expected)


def diagnose_pair(server, client, rows, support, legacy_values):
    exact_server = shapes.replicated(server, rows)
    expected = {tuple(row['pos']): (row['value'][0], legacy_values[index])
                for index, row in enumerate(rows)}
    expected[tuple(support)] = ('minecraft:stone', 0)
    fronts_match = all(front_pair_matches(client.get(stage), expected)
                       for stage in ('fronts_before', 'fronts_after'))
    result = {'server_typed_pair_exact': exact_server, 'client_front_pair_and_support_exact': fronts_match,
              'data_replication_verified': False, 'client_typed_upper_verified': False,
              'palette_covered_indices': [], 'palette_omitted_indices': [0, 1],
              'loaded_chunk_tracking': client.get('loaded_chunk_tracking'), 'physical_orientation_accepted': False}
    try:
        covered = palette_rows(client, rows)
    except (IndexError, KeyError, TypeError, ValueError, UnicodeError) as error:
        result.update(classification='pair_palette_invalid', palette_error=str(error))
        return result
    result['palette_covered_indices'] = sorted(covered or {})
    result['palette_omitted_indices'] = [index for index in (0, 1) if not covered or index not in covered]
    if not exact_server:
        result['classification'] = 'server_pair_changed'
    elif not fronts_match:
        values = [shapes.pair(row.get('value')) for stage in ('fronts_before', 'fronts_after')
                  for row in client.get(stage, [])]
        unavailable = any(not value or value[0] == 'minecraft:unknown' for value in values)
        result['classification'] = ('client_front_unavailable_loading_unresolved' if unavailable else
                                    'client_front_not_replicated')
    elif covered is None:
        result['classification'] = 'pair_palette_unavailable'
    elif 0 not in covered:
        result['classification'] = 'pair_palette_lower_missing'
    elif not shapes.replicated({'rows': [covered[0]]}, [rows[0]]):
        result['classification'] = 'pair_palette_lower_mismatch'
    else:
        upper_exact = 1 in covered and covered[1]['states'] is not None and shapes.replicated(
            {'rows': [covered[1]]}, [rows[1]])
        result['client_typed_upper_verified'] = upper_exact
        if 1 in covered and not upper_exact:
            result['classification'] = 'pair_palette_upper_mismatch'
        else:
            result['data_replication_verified'] = True
            result['classification'] = ('complete_pair_palette' if upper_exact else
                'documented_upper_omission_observed' if client['palettes']['upper']['available'] is False else
                'pair_palette_upper_omission')
    return result


def probe(output, session, owner):
    if output.exists():
        raise ValueError('Single-door evidence requires a fresh output')
    os.environ.update(MCDEV_SESSION_FILE=str(session.resolve()), MCDEV_OWNER=owner)
    binding = shapes.load_session(live=True)
    if Path(binding['project']).resolve() != shapes.ROOT:
        raise ValueError('Session belongs to another project')
    report = {'schema': 2, 'scope': 'One supported native door pair; setter diagnosis only',
              'completed': False, 'restored': False, 'mutation_attempted': False,
              'exact_native_pair': False, 'observation_errors': [],
              'server_exact_native_pair': False, 'data_replication_verified': False,
              'client_typed_pair_verified': False, 'client_observation_method': 'whole_pair_and_fronts_v2',
              'background_only': True, 'desktop_input': False, 'physical_orientation_accepted': False,
              'game_version': shapes.registry.source_version(),
              'palette_sha256': shapes.registry.fingerprint(), 'experiment_limit_seconds': 150,
              'session_file': str(session.resolve()),
              'instance': {key: binding[key] for key in ('id', 'owner', 'project', 'game_pid',
                           'game_identity', 'mcdk_pid', 'mcdk_identity', 'mcp_url', 'game_executable')},
              'noactivation': binding.get('noactivation', {}),
              'host_sources': {'probe': shapes.source_record(__file__),
                               'shape_helpers': shapes.source_record(shapes.__file__),
                               'palette_freezer': shapes.source_record(shapes.ROOT /
                                    'behavior_pack/modern_projection/projection/cell.py'),
                               'mcp_wrapper': shapes.source_record(shapes.mcdk_wrapper.__file__),
                               'session_loader': shapes.source_record(shapes.session_wrapper.__file__)}}
    shapes.write(output, report)
    pending = False
    started = time.monotonic()
    with ExitStack() as stack:
        try:
            protection = report['noactivation']
            if not all(protection.get(key) is True for key in
                       ('requested', 'background_safe', 'window_noactivate')):
                raise ValueError('Requires a verified protected background session')
            for key in ('mcdk', 'dll'):
                source = protection[key]
                if shapes.source_record(source['path'])['sha256'] != source['sha256']:
                    raise ValueError('Protected binary changed: %s' % key)
            client = stack.enter_context(shapes.Client(timeout=6))
            report['preflight'] = shapes.execute(client, shapes.PREFLIGHT % MARKER, True)
            rows, support, reserved = single_pair(tuple(report['preflight']['origin']))
            report.update(requested=rows, support=support, reserved=reserved, mutation_attempted=True)
            pending = True
            shapes.write(output, report)
            report['setup'] = shapes.execute(client, SETUP % (MARKER, rows, support, reserved), True)
            shapes.write(output, report)
            if report['setup']['error']:
                raise RuntimeError(report['setup']['error'])
            server_code = READ_SERVER % MARKER
            client_code = READ_CLIENT_PAIR % (rows, support, report['preflight']['dimension'])
            for stage in ('after_200ms', 'later'):
                if time.monotonic() - started > 90:
                    raise RuntimeError('Single-door observation budget exhausted; enter cleanup')
                time.sleep(.2)
                report[stage] = {}
                for side, code in (('server', server_code), ('client', client_code)):
                    try:
                        report[stage][side] = shapes.execute(client, code, side == 'server')
                    except Exception as error:
                        report['observation_errors'].append({'stage': stage, 'side': side,
                            'type': type(error).__name__, 'message': str(error)})
                    finally:
                        shapes.write(output, report)
            server_snapshots = [report['setup']['after']] + [report[stage].get('server') for stage in
                                                           ('after_200ms', 'later')]
            report['server_exact_native_pair'] = all(snapshot is not None and shapes.replicated(snapshot, rows)
                                                     for snapshot in server_snapshots)
            if report['observation_errors']:
                raise RuntimeError('Native delayed observations incomplete; see observation_errors')
            legacy_values = [step['legacy_aux'] for step in report['setup']['steps']
                             if step['method'] == 'SetBlockNew']
            if len(legacy_values) != 2:
                raise ValueError('Both documented legacy aux observations are required')
            report['diagnosis'] = {stage: diagnose_pair(report[stage]['server'], report[stage]['client'],
                                  rows, support, legacy_values) for stage in ('after_200ms', 'later')}
            report['data_replication_verified'] = report['server_exact_native_pair'] and all(
                result['data_replication_verified'] for result in report['diagnosis'].values())
            report['client_typed_pair_verified'] = all(result['client_typed_upper_verified'] and
                result['data_replication_verified'] for result in report['diagnosis'].values())
            report['exact_native_pair'] = report['data_replication_verified'] and report['client_typed_pair_verified']
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
        finally:
            try:
                report['cleanup'] = (shapes.execute(client, CLEAR % MARKER, True) if pending else
                                     {'restored': True, 'mutation_attempted': False})
                report['restored'] = report['cleanup']['restored']
                if report['restored'] and pending:
                    air_rows = [{'pos': pos} for pos in reserved]
                    deadline = time.monotonic() + 10
                    while True:
                        report['client_after_cleanup'] = shapes.execute(client, READ_CLIENT % air_rows, False)
                        if all(shapes.pair(row['value']) == ('minecraft:air', 0)
                               for row in report['client_after_cleanup']['rows']):
                            break
                        if time.monotonic() >= deadline:
                            raise RuntimeError('Client reserved air did not replicate')
                        time.sleep(.2)
            except Exception as error:
                report['cleanup_error'] = '%s: %s' % (type(error).__name__, error)
                report['restored'] = False
            report['elapsed_seconds'] = time.monotonic() - started
            shapes.write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--owner', required=True)
    args = parser.parse_args()
    report = probe(args.output, args.session, args.owner)
    print(json.dumps({key: report.get(key) for key in
                      ('completed', 'restored', 'server_exact_native_pair', 'data_replication_verified',
                       'client_typed_pair_verified', 'exact_native_pair', 'error', 'elapsed_seconds')}))
    return 0 if report['completed'] and report['restored'] and report['data_replication_verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
