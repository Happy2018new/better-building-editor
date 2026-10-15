"""Checkpoint bounded default-state tessellation diagnostics on an owned instance.

Run through run_live_check.py. No world/window operation or pixel acceptance is
performed. Defaults cover foreground only, not every state, group or neighbor.
No generated-geometry cache release API is documented; one invocation defaults
to 64 names and at most 128 distinct model names. A timeout is never replayed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
import uuid

from verify_debug_blueprints import BlueprintCheck, Client, write_json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry

BATCH_SIZE = 64
KINDS = ('state_only', 'prepared_public_cell')
CATALOGUE = '''from modern_projection.projection import block_registry as registry
_result=json.dumps({'materials':registry.catalogue_values(),
 'runtime':api.GetMinecraftVersion(),'game_version':registry.source_version(),
 'palette_sha256':registry.fingerprint()})
'''
PROBE = '''from modern_projection.projection import block_registry as registry
from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.model import Document
from modern_projection.projection.cell import foreground,rebase,freeze
from modern_projection.projection.geometry_palette import prepare_palette
from modern_projection.projection.bridge import _native_palette
import traceback
requested,prefix=%r,%r
rows=[]
stage='public_fixture'
failure=None
try:
 fixture=build('test.registry.vanilla')
 expected=dict(registry.catalogue_values())
 assert all(name.startswith('minecraft:') and name in expected for name in requested),requested
 source={}
 for pos,cell in sorted(fixture.blocks.items()):
  front=foreground(cell)
  if front[0] in expected and front[1]==expected[front[0]]:
   source.setdefault(front,(pos,cell))
 stage='components'
 block=b.factory.CreateBlock(b.level)
 geometry=b.factory.CreateBlockGeometry(b.level)
 assert block is not None and geometry is not None,'missing components'
 for ordinal,material in enumerate(requested):
  stage='material_states:'+material
  value=(material,expected[material])
  entry={'material':value,'states':registry.states(value),'paths':[]}
  rows.append(entry)
  for kind in ('state_only','prepared_public_cell'):
   path={'kind':kind,'stage':'public_source','status':'pending',
         'api_supported':None,'unsupported_mode':1}
   entry['paths'].append(path)
   try:
    pos,cell=source[value]
    entry['public_position']=pos
    path['stage']='document'
    data=Document((1,1,1),{(0,0,0):value if kind=='state_only' else
     rebase(cell,tuple(-axis for axis in pos))}).palette_data()
    if kind=='prepared_public_cell':
     path['stage']='prepare_palette'
     data=prepare_palette(data)
    path['stage']='input_snapshot'
    path['input']=freeze(data)
    materials=tuple(sorted(set(key[0] for group in ('common','extra')
                               for key in data.get(group,{}))))
    path['submission']={'materials':materials,'volume':data.get('volume'),
     'proxy_materials':tuple(name for name in materials if name.startswith('modern_projection:')),
     'original_material_retained':material in materials,
     'actor_cells':sum(len(values) for values in data.get('actor',{}).values()),
     'background_cells':sum(len(values) for values in data.get('extra',{}).values())}
    path['stage']='blank_palette'
    palette=block.GetBlankBlockPalette()
    assert palette is not None,'missing palette'
    path['stage']='native_palette_conversion'
    native=_native_palette(data)
    path['stage']='deserialize'
    path['deserialized']=palette.DeserializeBlockPalette(native)
    assert path['deserialized'],'deserialize returned false'
    path['stage']='roundtrip'
    path['roundtrip']=freeze(palette.SerializeBlockPalette())
    name=prefix+'_'+str(ordinal)+'_'+kind
    path['requested_name']=name
    path['stage']='combine'
    result=geometry.CombineBlockPaletteToGeometry(palette,name,1)
    path['stage']='return_value'
    assert result in (None,name),'unexpected result: '+repr(result)
    path.update(returned=result,api_supported=result==name,
                status='supported' if result==name else 'unsupported',stage='recorded')
   except Exception as error:
    path.update(status='failed',error_type=type(error).__name__,error=str(error),
                traceback=traceback.format_exc())
  entry['status']='failed' if any(path['status']=='failed' for path in entry['paths']) else 'recorded'
except Exception as error:
 failure={'stage':stage,'error_type':type(error).__name__,'error':str(error),
          'traceback':traceback.format_exc()}
_result=json.dumps({'rows':rows,'failure':failure,'prefix':prefix})
'''


def catalogue():
    return {'materials': [list(value) for value in registry.catalogue_values()
                          if value[0].startswith('minecraft:') and value[0] != 'minecraft:air'],
            'game_version': registry.source_version(), 'palette_sha256': registry.fingerprint()}


def checkpoint(output, report):
    temporary = output.with_name(output.name + '.' + uuid.uuid4().hex + '.tmp')
    write_json(temporary, report)
    os.replace(str(temporary), str(output))


def session_identity():
    path = os.environ.get('MCDEV_SESSION_FILE')
    return {'session_file': path, 'owner': os.environ.get('MCDEV_OWNER'),
            'manifest_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest() if path else None,
            'game_pid': os.environ.get('MCDEV_GAME_PID'),
            'endpoint': os.environ.get('MCDEV_MCP_URL')}


def refresh(report):
    observed = {row['material'][0]: row for row in report['rows']}
    report['failed_names'] = [name for name in report['selected_names']
                              if name in observed and observed[name]['status'] == 'failed']
    report['unexecuted_names'] = [name for name in report['selected_names']
                                  if name not in observed and name not in report['uncertain_names']]
    report['completed'] = not (report['failed_names'] or report['unexecuted_names']
                              or report['uncertain_names'] or report['errors'])
    report['all_catalogue_names'] = report['completed'] and set(observed) == set(report['expected_names'])
    report['observed_names_sha256'] = hashlib.sha256(
        json.dumps(sorted(observed), separators=(',', ':')).encode('utf8')).hexdigest()
    report['successful_model_names'] = sum(path.get('api_supported') is True
        for row in report['rows'] for path in row['paths'])


def new_report(names):
    native = catalogue()
    expected = [value[0] for value in native['materials']]
    unknown = set(names) - set(expected)
    if unknown:
        raise ValueError('Unknown catalogue names: ' + ', '.join(sorted(unknown)))
    selected = [name for name in expected if not names or name in names]
    report = {'schema_version': 2, 'fixture': 'test.registry.vanilla',
              'coverage': 'default catalogue state per vanilla name',
              'scope': {'all_states': False, 'foreground_only': True, 'background_layer': False,
                        'complete_groups': False, 'neighbor_context': False, 'pixels': False,
                        'prepared_path': 'production prepare_palette may replace materials and actors'},
              'host_catalogue': native, 'expected_names': expected, 'selected_names': selected,
              'requested_names': list(names), 'rows': [], 'batches': [], 'errors': [],
              'uncertain_names': [], 'world_untouched': True, 'visual_acceptance': False,
              'batch_size': BATCH_SIZE, 'model_names_dispatched_upper_bound': 0,
              'cache': {'release_api_verified': False, 'memory_bytes': None,
                        'actor_delete_is_cache_release': False,
                        'policy': 'one 64-name batch by default; unique names, no automatic replay'},
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'session_identity': session_identity()}
    refresh(report)
    return report


def load_report(output, names):
    report = json.loads(output.read_text(encoding='utf8'))
    fresh = new_report(names)
    for field in ('schema_version', 'host_catalogue', 'requested_names', 'source_sha256',
                  'session_identity'):
        if report.get(field) != fresh[field]:
            raise ValueError('Checkpoint resume mismatch: ' + field)
    refresh(report)
    return report


def validate_batch(result, names, prefix):
    if not isinstance(result, dict) or result.get('prefix') != prefix:
        raise ValueError('Batch response identity mismatch')
    observed = [row['material'][0] for row in result['rows']]
    if observed != list(names[:len(observed)]):
        raise ValueError('Batch response material mismatch')
    defaults = dict(catalogue()['materials'])
    for ordinal, row in enumerate(result['rows']):
        name = row['material'][0]
        value = (name, defaults[name])
        if tuple(row['material']) != value or row['states'] != registry.states(value):
            raise ValueError('Batch response default state mismatch')
        if tuple(path['kind'] for path in row['paths']) != KINDS:
            raise ValueError('Batch response path coverage mismatch')
        if row['status'] not in ('recorded', 'failed'):
            raise ValueError('Batch response row status mismatch')
        if (row['status'] == 'failed') != any(path['status'] == 'failed' for path in row['paths']):
            raise ValueError('Batch response failure classification mismatch')
        for path in row['paths']:
            if path.get('unsupported_mode') != 1:
                raise ValueError('Batch response must use strict unsupported mode')
            if path['status'] not in ('supported', 'unsupported', 'failed'):
                raise ValueError('Batch response path status mismatch')
            if path['status'] == 'failed' and path.get('api_supported') is not None:
                raise ValueError('Failed path cannot establish API support')
            if path['status'] != 'failed' and path.get('requested_name') != (
                    prefix + '_' + str(ordinal) + '_' + path['kind']):
                raise ValueError('Batch response model identity mismatch')
            if path['status'] == 'supported' and not (path.get('api_supported') is True and
                    path.get('returned') == path.get('requested_name')):
                raise ValueError('Supported path return mismatch')
            if path['status'] == 'unsupported' and not (path.get('api_supported') is False and
                                                       path.get('returned') is None):
                raise ValueError('Unsupported path return mismatch')
    if not result.get('failure') and observed != list(names):
        raise ValueError('Completed batch response is incomplete')


def scan(check, output, report, max_batches=1):
    stage = 'catalogue'
    batch = None
    try:
        actual = check.run(CATALOGUE)
        actual['materials'] = [value for value in actual['materials']
                                if value[0].startswith('minecraft:') and value[0] != 'minecraft:air']
        if any(actual[field] != report['host_catalogue'][field] for field in report['host_catalogue']):
            raise ValueError('Loaded catalogue differs from the host source')
        if report.get('runtime') is not None and report['runtime'] != actual['runtime']:
            raise ValueError('Loaded API runtime differs from the checkpoint')
        report['runtime'] = actual['runtime']
        for unused in range(max_batches):
            names = tuple(report['unexecuted_names'][:BATCH_SIZE])
            if not names:
                break
            prefix = 'registry_support_' + uuid.uuid4().hex
            batch = {'names': names, 'prefix': prefix, 'status': 'dispatched'}
            report['batches'].append(batch)
            report['uncertain_names'].extend(names)
            report['model_names_dispatched_upper_bound'] += len(names) * len(KINDS)
            refresh(report)
            stage = 'checkpoint_before_dispatch'
            checkpoint(output, report)
            stage = 'batch_request'
            result = check.run(PROBE % (names, prefix))
            stage = 'batch_response'
            validate_batch(result, names, prefix)
            report['rows'].extend(result['rows'])
            report['uncertain_names'] = [name for name in report['uncertain_names'] if name not in names]
            batch['status'] = 'recorded'
            if result.get('failure'):
                batch['failure'] = result['failure']
                report['errors'].append(result['failure'])
            refresh(report)
            stage = 'checkpoint_response'
            checkpoint(output, report)
            if result.get('failure') or any(row['status'] == 'failed' for row in result['rows']):
                break
    except Exception as error:
        failure = {'stage': stage, 'error_type': type(error).__name__, 'error': str(error),
                   'traceback': traceback.format_exc()}
        report['errors'].append(failure)
        if batch is not None and stage in ('batch_request', 'batch_response'):
            batch.update(status='uncertain', failure=failure)
        elif batch is not None and stage == 'checkpoint_before_dispatch':
            batch.update(status='unexecuted', failure=failure)
            report['uncertain_names'] = [name for name in report['uncertain_names']
                                          if name not in batch['names']]
            report['model_names_dispatched_upper_bound'] -= len(batch['names']) * len(KINDS)
    finally:
        refresh(report)
        checkpoint(output, report)
    return report


def summarize(report):
    return {'completed': report['completed'], 'all_catalogue_names': report['all_catalogue_names'],
            'expected_names': len(report['expected_names']), 'observed_names': len(report['rows']),
            'failed_names': report['failed_names'], 'uncertain_names': report['uncertain_names'],
            'unexecuted_names': len(report['unexecuted_names']), 'world_untouched': True,
            'visual_acceptance': False, 'scope': report['scope'],
            'model_names_dispatched_upper_bound': report['model_names_dispatched_upper_bound'],
            'unsupported': {kind: [row['material'][0] for row in report['rows']
                                  if any(path['kind'] == kind and path.get('api_supported') is False
                                         for path in row['paths'])] for kind in KINDS}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--names', nargs='+', help='Optional default-state subset')
    parser.add_argument('--resume', action='store_true', help='Continue unexecuted names; never retry uncertain calls')
    parser.add_argument('--max-batches', type=int, default=1, help='64-name batches this invocation (default: one)')
    args = parser.parse_args(argv)
    if args.max_batches < 1:
        parser.error('--max-batches must be positive')
    names = tuple(sorted(set(name if ':' in name else 'minecraft:' + name for name in args.names or ())))
    if args.output.exists() and not args.resume:
        parser.error('Output exists; choose a fresh file or explicitly --resume')
    report = load_report(args.output, names) if args.resume else new_report(names)
    checkpoint(args.output, report)
    try:
        if not report['session_identity']['manifest_sha256'] or not report['session_identity']['owner']:
            raise ValueError('An owned MCDEV session is required; run through run_live_check.py')
        with Client(timeout=180) as client:
            scan(BlueprintCheck(client, args.output, 180), args.output, report, args.max_batches)
    except Exception as error:
        report['errors'].append({'stage': 'client_session', 'error_type': type(error).__name__,
                                 'error': str(error), 'traceback': traceback.format_exc()})
        refresh(report)
        checkpoint(args.output, report)
    print(json.dumps(summarize(report)))
    return 1 if report['failed_names'] or report['uncertain_names'] or report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
