"""Exercise registered transform fixtures through Session on one owned game.

Records runtime data equality separately from background editor/world captures.
No world, player, inventory, library, or archive writes are performed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code, editor_closeup, world_closeup
from verify_sign_visuals import SignCheck
from _session import load_session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.debug_transform_acceptance import CASES, PREFIX, prepare
from projection.debug_blueprints import build
from projection.model import Document, Editor, SMALL_VOLUME
from projection.cell import encode as encode_cell

READ = '''_result=json.dumps({'document':s.editor.document.to_data(),
 'selection':sorted(s.editor.selection),'start':s.editor.start,'end':s.editor.end,
 'undo':len(s.editor.undo_stack),'redo':len(s.editor.redo_stack),
 'revision':s.editor.revision,'locked_layers':sorted(s.editor.locked_layers),
 'busy':s.edit_job is not None,'message':s.editor.message,
 'job_error':sys._transform_r23_saved['job'].error
  if sys._transform_r23_saved['job'] is not None else ''})
'''

SAVE_TOOL = '''assert not hasattr(sys,'_transform_r23_saved')
sys._transform_r23_saved={'tool':s.tool,'performance':dict(s.performance),
 'job':None,'editor':None}
_result=True
'''

START_OPERATION = '''assert not s.busy and s.io_job is None and s.edit_job is None
s.tool=%r
saved=sys._transform_r23_saved
saved['job']=None
saved['editor']=s.editor
result=s.run()
saved['job']=s.edit_job
_result=json.dumps({'result':result,'asynchronous':s.edit_job is not None})
'''

# Detach only the task launched by this probe. A queued Session.advance checks
# identity before touching the editor, so it cannot publish after RESTORE.
CANCEL_JOB = '''saved=sys._transform_r23_saved
job=saved['job']
if job is not None and s.edit_job is job:
 job.cancel()
 s.edit_job=None
assert s.edit_job is None, 'An unrelated edit task must not be replaced'
_result=True
'''

RESTORE_TOOL = '''saved=sys._transform_r23_saved
s.tool=saved['tool']
s.performance.clear()
s.performance.update(saved['performance'])
_result=True
'''

RESTORE_VISUAL_FIELDS = '''saved=sys._blueprint_visual_saved
s.origin=saved['origin']
s.opacity=saved['opacity']
s.projection_missing=saved['missing']
s.projection_outline=saved['outline']
_result=True
'''

RESTORE_WORKSPACE = '''was_open=%r
if was_open:
 owner.open_workspace()
elif navigator.contains('modern_projection_workspace'):
 assert navigator.top.key=='modern_projection_workspace'
 navigator.pop()
_result=True
'''

ORACLE_MODULES = ('model', 'jobs', 'session', 'storage', 'cell', 'codec',
                  'semantic_wire', 'compact_chunk', 'packed', 'catalog',
                  'block_registry', 'block_registry_data', 'state_transform',
                  'nbt_spatial', 'block_groups', 'block_edits', 'block_neighbors',
                  'debug_transform_acceptance')


def bind_owned_session(session, owner, project):
    binding = load_session(session, owner, live=True)
    if binding is None or Path(binding['project']).resolve() != project.resolve(strict=True):
        raise ValueError('Owned session project differs from the requested diagnostic snapshot')
    # A conflicting inherited endpoint/PID is an error, not a request to route
    # silently to a different running game.
    values = {'MCDEV_SESSION_FILE': binding['session_file'], 'MCDEV_OWNER': binding['owner'],
              'MCDEV_MCP_URL': binding['mcp_url'], 'MCDEV_GAME_PID': str(binding['game_pid'])}
    for key, value in values.items():
        supplied = os.environ.get(key)
        same = (Path(supplied).resolve() == Path(value).resolve()
                if key == 'MCDEV_SESSION_FILE' and supplied else supplied == value)
        if supplied and not same:
            raise ValueError('Inherited instance binding conflicts with the request: ' + key)
    os.environ.update(values)
    return {key: binding[key] for key in ('session_file', 'owner', 'game_pid',
                                         'game_identity', 'project', 'mcp_url')}


def oracle_sources(project):
    rows = {}
    for module in ORACLE_MODULES:
        relative = Path('behavior_pack/modern_projection/projection') / (module + '.py')
        host = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        snapshot = hashlib.sha256((project / relative).read_bytes()).hexdigest()
        if host != snapshot:
            raise ValueError('Host oracle and diagnostic snapshot differ: ' + str(relative))
        rows[module] = host
    return rows


def normalized(value):
    return json.loads(json.dumps(value, sort_keys=True))


def expected(editor):
    return normalized({'document': editor.document.to_data(),
                       'selection': sorted(editor.selection),
                       'start': editor.start, 'end': editor.end,
                       'undo': len(editor.undo_stack), 'redo': len(editor.redo_stack),
                       'revision': editor.revision, 'locked_layers': sorted(editor.locked_layers)})


def document_semantics(data):
    """Decode validated wire data without depending on palette/chunk order.

    Cell is a tuple subclass whose tuple view omits background and actor data.
    encode_cell retains both layers and the complete typed immutable actor tree.
    Sorting positions does not reorder any list/tuple inside that actor tree.
    """
    document = Document.from_data(data)
    return normalized({'size': document.size, 'name': document.name, 'biome': document.biome,
                       'cells': [[position, encode_cell(value)]
                                 for position, value in sorted(document.blocks.items())]})


def json_diff(actual, target, path='$'):
    """Keep original array order and scalar types in an uncapped JSON diff."""
    if type(actual) is not type(target):
        return [{'path': path, 'kind': 'type', 'actual': actual, 'expected': target}]
    rows = []
    if isinstance(actual, dict):
        for key in sorted(set(actual) | set(target)):
            child = path + '[' + json.dumps(key, ensure_ascii=False) + ']'
            if key not in actual:
                rows.append({'path': child, 'kind': 'missing_actual', 'expected': target[key]})
            elif key not in target:
                rows.append({'path': child, 'kind': 'missing_expected', 'actual': actual[key]})
            else:
                rows.extend(json_diff(actual[key], target[key], child))
    elif isinstance(actual, list):
        for index in range(max(len(actual), len(target))):
            child = '%s[%d]' % (path, index)
            if index >= len(actual):
                rows.append({'path': child, 'kind': 'missing_actual', 'expected': target[index]})
            elif index >= len(target):
                rows.append({'path': child, 'kind': 'missing_expected', 'actual': actual[index]})
            else:
                rows.extend(json_diff(actual[index], target[index], child))
    elif actual != target:
        rows.append({'path': path, 'kind': 'value', 'actual': actual, 'expected': target})
    return rows


def verify(check, editor, stage, evidence=None):
    actual = check.wait(stage, lambda row: not row['busy'], lambda: check.run(READ))
    target = expected(editor)
    raw_diff = json_diff(actual['document'], target['document'])
    comparison = {'stage': stage, 'encoded_equal': not raw_diff,
                  'semantic_equal': False, 'raw_document_json_diff': raw_diff}
    semantics, decode_errors = {}, {}
    for side, value in (('actual', actual['document']), ('expected', target['document'])):
        try:
            semantics[side] = document_semantics(value)
        except Exception as error:
            decode_errors[side] = '%s: %s' % (type(error).__name__, error)
    if decode_errors:
        comparison['decode_errors'] = decode_errors
    else:
        comparison['semantic_json_diff'] = json_diff(semantics['actual'], semantics['expected'])
        comparison['semantic_equal'] = not comparison['semantic_json_diff']
    if raw_diff:
        comparison.update(actual_document=actual['document'], expected_document=target['document'])
        if evidence is not None:
            evidence.setdefault('document_encoding_differences', []).append(comparison)
            write_json(check.output, evidence)
    fields = [key for key in target if key != 'document' and json_diff(actual[key], target[key])]
    if not comparison['semantic_equal']:
        fields.insert(0, 'document')
    if fields:
        if evidence is not None:
            evidence.setdefault('mismatches', []).append({
                'stage': stage, 'different_fields': fields,
                'actual': actual, 'expected': target,
                'document_comparison': comparison,
                'comparison': 'Validated decoded document semantics; all other fields remain strict.'})
            write_json(check.output, evidence)
        raise AssertionError('Runtime transform differs from host expectation at %s: %s' %
                             (stage, ', '.join(fields)) +
                             ('; document decode failed: ' + repr(decode_errors) if decode_errors else ''))
    semantic_state = dict(target, document=semantics['expected'])
    encoded = json.dumps(semantic_state, sort_keys=True, separators=(',', ':')).encode('utf8')
    return {'stage': stage, 'equal': True, 'state_sha256': hashlib.sha256(encoded).hexdigest(),
            'state_sha256_scope': 'Decoded document semantics and strict editor state.',
            'encoded_equal': comparison['encoded_equal'], 'document_semantic_equal': True,
            'undo': actual['undo'], 'redo': actual['redo'], 'message': actual['message'],
            'job_error': actual['job_error']}


def transform(check, editor, operation, stage=None, rejected=False, evidence=None):
    error = None
    before = expected(editor)
    try:
        editor.run(operation)
    except ValueError as failure:
        error = str(failure)
    if rejected:
        if not error or expected(editor) != before:
            raise AssertionError('Host lock oracle must reject without changing state')
    elif error:
        raise AssertionError('Host operation failed: ' + error)
    started = check.run(START_OPERATION % operation)
    row = verify(check, editor, stage or operation, evidence)
    row['started'] = started
    asynchronous = editor.document.volume > SMALL_VOLUME
    if started['asynchronous'] != asynchronous:
        raise AssertionError('Session did not use the expected synchronous/asynchronous path')
    if rejected:
        actual_error = row['job_error'] if asynchronous else row['message']
        if actual_error != error or (not asynchronous and started['result'] is not False):
            raise AssertionError('The unchanged state was not rejected for the expected lock: %r' % row)
        row.update(rejected=True, expected_error=error)
    elif started['result'] is False or row['job_error']:
        raise AssertionError('Session rejected or failed the requested transform: %r' % row)
    return row


def cleanup(check, evidence, installed, visual_saved, tool_saved, was_open, detached=False):
    actions = []
    if tool_saved:
        actions.extend((('cancel_edit', lambda: check.run(CANCEL_JOB)),
                        ('tool', lambda: check.run(RESTORE_TOOL))))
    if visual_saved:
        actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                        ('camera', lambda: check.run(camera_restore_code(detached))),
                        ('visual_fields', lambda: check.run(RESTORE_VISUAL_FIELDS))))
    if installed:
        actions.extend((('editor', lambda: check.run(RESTORE)),
                        ('workspace', lambda: restore_workspace(check, was_open))))
    errors = []
    for label, action in actions:
        try:
            action()
        except Exception as error:
            errors.append({'step': label, 'error': '%s: %s' % (type(error).__name__, error)})
    # Failed restoration keeps its saved marker available for a manual retry.
    for label, saved, marker, dependencies in (
            ('tool_marker', tool_saved, '_transform_r23_saved', ('cancel_edit', 'tool')),
            ('visual_marker', visual_saved, '_blueprint_visual_saved', ('camera', 'visual_fields'))):
        if saved and not any(row['step'] in dependencies for row in errors):
            try:
                check.run('del sys.%s\n_result=True' % marker)
            except Exception as error:
                errors.append({'step': label, 'error': '%s: %s' % (type(error).__name__, error)})
    evidence.update(restored=installed and not errors, cleanup_errors=errors)
    return errors


def restore_workspace(check, was_open):
    check.run(RESTORE_WORKSPACE % was_open)
    check.wait('original workspace state',
               lambda row: row['open'] == was_open and not row['transition'], check.navigation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--restore-detached', action='store_true')
    parser.add_argument('--fixture', action='append', choices=('t01', 't04', 't05', 't08'))
    parser.add_argument('--missing', action='store_true', help='Also observe bounded missing occupancy stages without world writes')
    parser.add_argument('--timeout', type=float, default=60.)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    if args.output.exists():
        parser.error('Use a fresh evidence output path')
    binding = bind_owned_session(args.session, args.owner, args.project)
    hashes = oracle_sources(args.project)
    if args.missing:
        import transform_missing_r23 as missing_probe
        for relative in missing_probe.SOURCE_PATHS:
            source = (ROOT / relative).read_bytes()
            if (args.project / relative).read_bytes() != source:
                raise ValueError('Host missing oracle and diagnostic snapshot differ: ' + relative)
            hashes[relative] = hashlib.sha256(source).hexdigest()
    evidence = {'schema': 2, 'completed': False, 'restored': False,
                'world_untouched': True, 'manual_acceptance': False,
                'missing_projection_checked': False, 'cases': [],
                'session': binding, 'oracle_source_sha256': hashes,
                'oracle_scope': 'Same-source host/runtime data parity; independent matrix checks remain offline.',
                'document_comparison': 'Validated size/name/biome and each positioned complete cell, '
                                       'including foreground/background and typed actor; '
                                       'raw encoding equality and original-order JSON differences are retained.',
                'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'tool_dependencies_sha256': {
                    'tools/verify_debug_blueprints.py': hashlib.sha256(
                        (ROOT / 'tools/verify_debug_blueprints.py').read_bytes()).hexdigest()}}
    if args.missing:
        evidence['tool_dependencies_sha256']['tools/transform_missing_r23.py'] = hashlib.sha256(
            (ROOT / 'tools/transform_missing_r23.py').read_bytes()).hexdigest()
    installed = visual_saved = tool_saved = False
    was_open = None
    try:
        with Client(timeout=30) as client:
            check = SignCheck(client, args.output, args.timeout, native_resolution=True,
                              background_only=True, native_capture_helper=ROOT/'tools/capture_native_window.py')
            was_open = check.navigation()['open']
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run("assert not hasattr(sys,'_blueprint_visual_saved')\n_result=True")
                check.run(SAVE_VISUAL)
                visual_saved = True
                check.run(SAVE_TOOL)
                tool_saved = True
                check.page()
                for short in args.fixture or ('t01', 't04', 't05', 't08'):
                    identity = PREFIX + short
                    oracle = Editor(build(identity))
                    prepare(oracle, identity)
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('workspace opens', lambda row: row['open'] and not row['transition'], check.navigation)
                    baseline = check.fixture(identity)
                    row = {'fixture': identity, 'baseline': baseline,
                           'data': [verify(check, oracle, 'loaded', evidence)], 'captures': {}}
                    evidence['cases'].append(row)
                    focus = tuple(CASES[identity]['focus'])
                    row['captures']['before'] = editor_closeup(check, short+'_before', focus, 2.)
                    operation = 'mirror_x' if short == 't04' else 'rotate_y90'
                    row['data'].append(transform(check, oracle, operation, evidence=evidence))
                    row['preview_after'] = check.editor_preview('transformed ' + short)
                    row['captures']['after'] = editor_closeup(check, short+'_after', focus, 2.)
                    row['captures']['full_projection'] = world_closeup(
                        check, short+'_after', focus, (-6., 4., -9.), 1.)
                    if args.missing:
                        row['missing'] = {}
                        missing_probe.run(check, short, CASES, PREFIX, oracle, document_semantics,
                                          lambda stage: verify(check, oracle, stage, evidence), row['missing'])
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(False))
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('workspace reopens', lambda state: state['open'] and not state['transition'], check.navigation)
                    oracle.undo()
                    check.run('assert s.action(s.editor.undo)\n_result=True')
                    row['data'].append(verify(check, oracle, 'undo', evidence))
                    oracle.redo()
                    check.run('assert s.action(s.editor.redo)\n_result=True')
                    row['data'].append(verify(check, oracle, 'redo', evidence))
                    oracle.undo()
                    check.run('assert s.action(s.editor.undo)\n_result=True')
                    row['data'].append(verify(check, oracle, 'undo_again', evidence))
                    if short == 't08':
                        layer = CASES[identity]['locked_layer']
                        oracle.locked_layers.add(layer)
                        check.run('s.editor.locked_layers.add(%d)\n_result=True' % layer)
                        row['data'].append(transform(check, oracle, 'rotate_y90',
                                                     'locked_partner_rejected', rejected=True,
                                                     evidence=evidence))
                        oracle.locked_layers.remove(layer)
                        check.run('s.editor.locked_layers.remove(%d)\n_result=True' % layer)
                    write_json(args.output, evidence)
                evidence['completed'] = True
                evidence['missing_projection_checked'] = args.missing
            finally:
                errors = cleanup(check, evidence, installed, visual_saved, tool_saved,
                                 was_open, args.restore_detached)
                if errors and sys.exc_info()[0] is None:
                    raise RuntimeError('Transform cleanup failed: ' + repr(errors))
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'completed': evidence['completed'], 'restored': evidence['restored'],
                      'cases': len(evidence['cases']), 'output': str(args.output.resolve())}))


if __name__ == '__main__':
    main()
