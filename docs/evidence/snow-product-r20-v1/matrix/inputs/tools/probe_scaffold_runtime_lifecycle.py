"""Native lifecycle v2: preserve raw air None and require real nonair states.

The native sequence reuses the independently archived v1 fixture. The narrow
changes below are checked before code generation; neither raw states nor the
legacy evidence are rewritten. This tool does not qualify rendered pixels.
"""
import argparse
import json
from pathlib import Path
import uuid

import probe_scaffold_state_lifecycle as base
from scaffold_native_palette_readback import HELPER, valid as valid_air_palette, encoding_from_observation, valid_encoding

ROOT = Path(__file__).resolve().parents[1]
KIND = 'scaffold_runtime_state_lifecycle_diagnostic'
METHOD = ('17 sequential scaffold lifecycle SDK controls; near reserve; '
          'explicit dual-layer cleanup with native palette proof; raw air None; true nonair states; v2')
MARKER = '_scaffold_runtime_state_lifecycle_v2'
RUNTIME, PHASES, OFFSETS = base.RUNTIME, base.PHASES, base.OFFSETS
ACCEPTANCE = {'editor': 'pending', 'full': 'pending', 'missing': 'pending'}


def _replace_once(code, previous, current):
    if code.count(previous) != 1:
        raise ValueError('Archived lifecycle template changed; review v2 adapter')
    return code.replace(previous, current, 1)


def native_start():
    code = _replace_once(base.START, 'int(math.floor(foot[1]))+18', 'int(math.floor(foot[1]))+2')
    helper = '\n'.join(' ' + line if line else '' for line in HELPER.splitlines())
    code = _replace_once(code, ' def read(pos):', helper + '\n def read(pos):')
    code = _replace_once(code, "return {'front':front,'states':states,'liquid':info.GetLiquidBlock(pos,dimension)}",
                         "return {'front':front,'states':states,'liquid':info.GetLiquidBlock(pos,dimension),'palette':palette_read(pos)}")
    code = _replace_once(code, "value['states']=={}", "(value['states'] is None or value['states']=={}) and palette_air(value['palette'])")
    code = _replace_once(code, "if not isinstance(cell['states'],dict):",
                         "if cell['front']['name']!='minecraft:air' and not isinstance(cell['states'],dict):")
    code = _replace_once(code, "if returned is not True:row['reset_errors'].append({'pos':pos,'returned':returned})",
                         "if type(returned) is not bool:row['reset_errors'].append({'pos':pos,'returned':returned})")
    return _replace_once(code, '  begin(0)', '''  probe['setup']['explicit_air_resets']=[]
  probe['setup']['explicit_air_readbacks']=[]
  for pos in reversed(reserved):
   returned=block.SetBlockByBlockPalette(air,dimension,pos,0,0)
   probe['setup']['explicit_air_resets'].append({'pos':pos,'returned':returned})
   assert type(returned) is bool,('Invalid dual-layer reset return',pos,returned)
  for offset in offsets:
   pos=tuple(origin[i]+offset[i] for i in range(3))
   actual=dict(read(pos),offset=offset)
   probe['setup']['explicit_air_readbacks'].append(actual)
   assert dry_air(actual),('Initial dual-layer reset readback failed',pos,actual)
  begin(0)''')


def native_restore():
    code = _replace_once(base.RESTORE, 'or states!={} or liquid',
                         'or (states is not None and states!={}) or liquid')
    code = _replace_once(code, "if returned is not True:errors.append({'operation':'air_reset','pos':pos,'returned':returned})",
                         "if type(returned) is not bool:errors.append({'operation':'air_reset','pos':pos,'returned':returned})")
    helper = '\n'.join(' ' + line if line else '' for line in HELPER.splitlines())
    code = _replace_once(code, " probe['active']=False", " block=probe['block']\n dimension=probe['dimension']\n config=probe['config']\n" + helper + "\n probe['active']=False")
    code = _replace_once(code, "'states':states,'liquid':liquid}", "'states':states,'liquid':liquid,'palette':palette_read(pos)}")
    return _replace_once(code, "if front!={'name':'minecraft:air','aux':0}",
                         "if not palette_air(readback['palette']) or front!={'name':'minecraft:air','aux':0}")


def start_payload(identity, source_sha256, fresh_owned_flow_allowed, air_encoding):
    config = {'marker': MARKER, 'runtime': RUNTIME, 'game_version': base.registry.SOURCE_VERSION,
              'palette_sha256': base.registry.SOURCE_SHA256, 'plans': base.plans(), 'offsets': OFFSETS,
              'reserved_cells': len(OFFSETS), 'identity': identity, 'source_sha256': source_sha256,
              'fresh_owned_flow_allowed': fresh_owned_flow_allowed, 'actor_data': base.ACTOR_SCOPE,
              'air_encoding': air_encoding}
    return native_start().replace('__CONFIG__', repr(config))


def readback_valid(value):
    if not isinstance(value, dict) or 'states' not in value or 'liquid' not in value:
        return False
    front, liquid = value.get('front'), value.get('liquid')
    if (not isinstance(front, dict) or not isinstance(front.get('name'), str)
            or front['name'] == 'minecraft:unknown' or type(front.get('aux')) is not int):
        return False
    if front['name'] == 'minecraft:air':
        if value['states'] is not None and value['states'] != {}:
            return False
    elif not isinstance(value['states'], dict):
        return False
    return (liquid is None or isinstance(liquid, dict) and isinstance(liquid.get('name'), str)
            and type(liquid.get('aux', 0)) is int)


def dry_air(value):
    if not readback_valid(value) or value['front'] != {'name': 'minecraft:air', 'aux': 0}:
        return False
    liquid = value['liquid']
    return liquid is None or liquid['name'] == 'minecraft:air' and liquid.get('aux', 0) == 0


def check_sample(sample, phase, dry=False, air_encoding=None):
    cells = sample.get('cells', [])
    if (sample.get('phase') != phase or type(sample.get('sequence')) is not int
            or len(cells) != len(OFFSETS) or {tuple(row.get('offset', ())) for row in cells} != set(OFFSETS)
            or sample.get('read_errors', []) != [] or any(not readback_valid(row) for row in cells)
            or dry and any(not dry_air(row) or not valid_air_palette(row.get('palette'), air_encoding) for row in cells)):
        raise ValueError('Runtime lifecycle needs raw air values and true nonair states')


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def check_resets(rows, positions):
    if (len(rows) != len(positions) or {tuple(row.get('pos', ())) for row in rows} != positions
            or any(type(row.get('returned')) is not bool for row in rows)):
        raise ValueError('Runtime cleanup needs every boolean setter return and actual palette proof')


def validate_report(report, source_sha256=None, base_sha256=None):
    source = source_sha256 or base.digest(Path(__file__).read_bytes())
    template = base_sha256 or base.digest(Path(base.__file__).read_bytes())
    start, native, cleanup = report.get('start', {}), report.get('native', {}), report.get('cleanup', {})
    if (report.get('schema') != 2 or report.get('kind') != KIND or report.get('method') != METHOD
            or report.get('source_sha256') != source or report.get('template_sha256') != template
            or report.get('completed') is not True or report.get('restored') is not True
            or report.get('error') or report.get('cleanup_error') or report.get('acceptance') != ACCEPTANCE
            or start.get('runtime') != RUNTIME or start.get('game_version') != base.registry.SOURCE_VERSION
            or start.get('palette_sha256') != base.registry.SOURCE_SHA256 or start.get('source_sha256') != source
            or start.get('reserved') != len(OFFSETS) or start.get('controls') != 17
            or start.get('fresh_owned_flow_allowed') is not True or type(start.get('original_tile_drops')) is not bool
            or start.get('actor_data') != base.ACTOR_SCOPE or report.get('actor_data') != base.ACTOR_SCOPE
            or native.get('done') is not True or native.get('observed') != 17 or native.get('index') != 17
            or native.get('timer_pending') is not False or native.get('stage') != 'done'
            or native.get('start') != start or native.get('error')):
        raise ValueError('Incomplete runtime lifecycle or source identity')
    plans = base.plans()
    if base.state_key(start.get('identity')) != base.state_key(report.get('identity')):
        raise ValueError('Runtime lifecycle identity changed')
    identity = report.get('identity', {})
    if not all(identity.get(key) for key in ('session_id', 'owner', 'game_pid', 'game_identity', 'run_id')):
        raise ValueError('Runtime lifecycle session identity is missing')
    air_encoding = report.get('air_encoding')
    if not valid_encoding(air_encoding) or not _hash(report.get('air_observation_sha256')):
        raise ValueError('Independent native two-layer air encoding is missing')
    hashes = report.get('payload_sha256', {})
    expected_hashes = {'start': base.digest(start_payload(identity, source, True, air_encoding).encode('utf8')),
                       'status': base.digest((base.STATUS % (MARKER, identity)).encode('utf8')),
                       'restore': base.digest((native_restore() % (MARKER, identity)).encode('utf8'))}
    if hashes != expected_hashes or not _hash(report.get('game_executable_sha256')):
        raise ValueError('Runtime lifecycle payload or executable changed')
    origin = start.get('origin', [])
    if len(origin) != 3 or any(type(value) is not int for value in origin):
        raise ValueError('Runtime lifecycle origin is missing')
    absolute = {tuple(origin[i] + offset[i] for i in range(3)) for offset in OFFSETS}
    setup = start.get('setup', {})
    if (setup.get('air_palette_returned') is not True or setup.get('rules_returned') is not True
            or setup.get('rules_actual') is not False or setup.get('flow_returned') is not True
            or native.get('setup') != setup):
        raise ValueError('Runtime lifecycle setup failed')
    check_resets(setup.get('explicit_air_resets', []), absolute)
    check_sample({'phase': 'explicit_air', 'sequence': 0, 'cells': setup.get('explicit_air_readbacks', [])},
                 'explicit_air', dry=True, air_encoding=air_encoding)
    check_sample({'phase': 'natural_air', 'sequence': 0, 'cells': start.get('baseline', [])}, 'natural_air', dry=True, air_encoding=air_encoding)
    if (cleanup.get('restored') is not True or cleanup.get('rules_restored') is not True
            or cleanup.get('flow_restored') is not True or cleanup.get('rules_returned') is not True
            or cleanup.get('flow_returned') is not True or cleanup.get('rules_actual') is not start['original_tile_drops']
            or cleanup.get('reserved_air') != len(OFFSETS) or cleanup.get('remaining') != []
            or cleanup.get('errors') != [] or cleanup.get('flow_baseline') != 'declared_fresh_owned_allowed'):
        raise ValueError('Runtime lifecycle recovery incomplete')
    check_resets(cleanup.get('air_reset_returns', []), absolute)
    readbacks = cleanup.get('air_readbacks', [])
    if len(readbacks) != len(absolute) or {tuple(row.get('pos', ())) for row in readbacks} != absolute:
        raise ValueError('Runtime lifecycle cleanup readback incomplete')
    check_sample({'phase': 'cleanup', 'sequence': 0, 'cells': [dict(row, offset=tuple(row['pos'][i] - origin[i]
                  for i in range(3))) for row in readbacks]}, 'cleanup', dry=True, air_encoding=air_encoding)
    rows = native.get('rows', [])
    if len(rows) != len(plans) or [row.get('id') for row in rows] != [row['id'] for row in plans]:
        raise ValueError('Runtime lifecycle controls reordered')
    findings, previous = [], 0
    for row, plan in zip(rows, plans):
        if (row.get('requested') != plan['requested'] or row.get('method') != plan['method']
                or row.get('case_index') != plan['case_index'] or row.get('actor_data') != base.ACTOR_SCOPE
                or base.state_key(row.get('expected_states')) != base.state_key(plan['expected_states'])
                or type(row.get('native_aux')) is not int or row['native_aux'] < 0):
            raise ValueError('Runtime lifecycle state plan differs')
        writes, samples = row.get('writes', []), row.get('samples', [])
        support = [plan['requested'][0], row['native_aux'] if plan['method'] == base.SEMANTIC else plan['requested'][1]]
        if (len(writes) != 3 or [list(write.get('requested', ())) for write in writes]
                != [['minecraft:stone', 0], support, ['minecraft:scaffolding', 0]]
                or [write.get('update_neighbors') for write in writes] != [False, False, True]
                or any(write.get('is_legacy') is not True or type(write.get('returned')) is not bool
                       or not readback_valid(write.get('before')) for write in writes)
                or len(samples) != len(PHASES)):
            raise ValueError('Runtime lifecycle writes differ')
        semantic = row.get('semantic_set_returned')
        if (plan['method'] == base.SEMANTIC and type(semantic) is not bool
                or plan['method'] != base.SEMANTIC and semantic is not None):
            raise ValueError('Runtime lifecycle semantic result missing')
        for sample, phase in zip(samples, PHASES):
            check_sample(sample, phase)
        check_sample(row.get('baseline', {}), 'case_dry_air', dry=True, air_encoding=air_encoding)
        check_sample(row.get('after_case', {}), 'case_cleared', dry=True, air_encoding=air_encoding)
        check_resets(row.get('air_reset_returns', []), absolute)
        timer = row.get('timer', {})
        if row.get('reset_errors') != [] or timer.get('delay') != .35:
            raise ValueError('Runtime lifecycle reset or timer differs')
        order = [row['baseline']['sequence'], writes[0]['sequence'], writes[1]['sequence'], samples[0]['sequence'],
                 writes[2]['sequence'], samples[1]['sequence'], timer['sequence'], samples[2]['sequence'],
                 row['after_case']['sequence']]
        if order != list(range(previous + 1, previous + 10)):
            raise ValueError('Runtime lifecycle sequence differs')
        previous = order[-1]
        exact = [base.cell_at(sample, (0, 0, 0))['front']['name'] == plan['requested'][0]
                 and base.state_key(base.cell_at(sample, (0, 0, 0))['states']) == base.state_key(plan['expected_states'])
                 for sample in samples]
        findings.append({'id': row['id'], 'native_aux_equals_dump': row['native_aux'] == plan['requested'][1],
                         'semantic_matches': dict(zip(PHASES, exact))})
    if native.get('sequence') != previous:
        raise ValueError('Runtime lifecycle sequence incomplete')
    support_cell, scaffold = (base.cell_at(rows[-1]['samples'][-1], offset) for offset in ((0, 0, 0), (0, 1, 0)))
    positive = (support_cell['front'] == {'name': 'minecraft:stone', 'aux': 0} and support_cell['states'] == {}
                and scaffold['front']['name'] == 'minecraft:scaffolding'
                and type(scaffold['states'].get('stability')) is int and scaffold['states']['stability'] == 0
                and base.registry.from_states('minecraft:scaffolding', scaffold['states']) is not None)
    return {'positive_control_matched': positive, 'rows': findings,
            'acceptance': ACCEPTANCE, 'scope': 'native state lifecycle; capability remains unknown'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fresh-owned-flow-allowed', action='store_true')
    parser.add_argument('--air-observation', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or not args.fresh_owned_flow_allowed:
        parser.error('Use a new output and explicitly declare the fresh owned flow baseline')
    session_file, owner, session = base.owned_session()
    identity = {'session_id': session['id'], 'owner': owner, 'game_pid': session['game_pid'],
                'game_identity': session['game_identity'], 'run_id': uuid.uuid4().hex}
    source = base.digest(Path(__file__).read_bytes())
    observation_raw = args.air_observation.read_bytes()
    air_encoding = encoding_from_observation(json.loads(observation_raw))
    payload = start_payload(identity, source, True, air_encoding)
    status, restore = base.STATUS % (MARKER, identity), native_restore() % (MARKER, identity)
    report = {'schema': 2, 'kind': KIND, 'method': METHOD, 'source_sha256': source,
              'template_sha256': base.digest(Path(base.__file__).read_bytes()), 'identity': identity,
              'session_file': session_file, 'completed': False, 'restored': False,
              'air_encoding': air_encoding, 'air_observation_sha256': base.digest(observation_raw),
              'game_executable_sha256': base.digest(Path(session['game_executable']).read_bytes()),
              'payload_sha256': {name: base.digest(code.encode('utf8')) for name, code in
                                 (('start', payload), ('status', status), ('restore', restore))},
              'actor_data': base.ACTOR_SCOPE, 'acceptance': ACCEPTANCE}
    base.checkpoint(args.output, report, exclusive=True)
    try:
        with base.Client(timeout=15) as client:
            check = base.BlueprintCheck(client, args.output, 30)
            try:
                report['start'] = base.run(client, payload)
                base.checkpoint(args.output, report)
                def progress():
                    report['native'] = base.run(client, status)
                    base.checkpoint(args.output, report)
                    return report['native']
                report['native'] = check.wait('17 raw lifecycle controls', lambda value: value['done'] or value['error'], progress)
                if report['native']['error']:
                    raise RuntimeError(report['native']['error'])
            except Exception as error:
                report['error'] = '%s: %s' % (type(error).__name__, error)
            finally:
                try:
                    report['native'] = base.run(client, status)
                    report['start'] = report['native']['start']
                except Exception as error:
                    report['final_status_error'] = '%s: %s' % (type(error).__name__, error)
                try:
                    report['cleanup'] = base.run(client, restore)
                    report['restored'] = report['cleanup']['restored']
                except Exception as error:
                    report['cleanup_error'] = '%s: %s' % (type(error).__name__, error)
        report['completed'] = not report.get('error') and report['restored'] is True
        report['diagnostic'] = validate_report(report, source)
        if not report['diagnostic']['positive_control_matched']:
            raise ValueError('Independent native stone/scaffold control failed')
    except Exception as error:
        report['completed'] = False
        report.setdefault('error', '%s: %s' % (type(error).__name__, error))
    finally:
        base.checkpoint(args.output, report)
    print(json.dumps({key: report.get(key) for key in ('completed', 'restored', 'error', 'cleanup_error')}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
