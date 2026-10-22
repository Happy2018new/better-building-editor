"""Opt-in observed occupancy stages for the bounded transform acceptance set."""
import sys
import time
import uuid

from verify_debug_visuals import projection_pixels

SOURCE_PATHS = tuple('behavior_pack/modern_projection/projection/' + name + '.py'
                     for name in ('world_projection', 'occupancy', 'occupancy_shader', 'render_context',
                                  'render_layout', 'rail_render_profile'))

INSTALL = '''import modern_projection.projection.occupancy as transform_occupancy
assert not hasattr(sys,'_transform_missing_r23_saved')
sys._transform_missing_r23_saved={'class':transform_occupancy.ProjectionOccupancy,
 'document':s.editor.document.blocks.copy(),'points':%r,'missing':s.projection_missing,
 'editor_id':id(s.editor),'document_id':id(s.editor.document),'revision':s.editor.revision,'token':%r}
sys._transform_missing_r23_occupied=set()
class TransformObservedOccupancy(transform_occupancy.ProjectionOccupancy):
 def __init__(self,*args,**kwargs):
  sys._transform_missing_r23_saved['class'].__init__(self,*args,**kwargs)
  self.bulk=None
  self.bulk_job=None
 def read(self,pos,initial=False):
  self.reads+=1
  return self.observe(self.index(pos),2 if pos in sys._transform_missing_r23_occupied else 1,initial)
transform_occupancy.ProjectionOccupancy=TransformObservedOccupancy
_result=True
'''

STATE = '''t=b.projection_occupancy
work=b.projection_work
saved=sys._transform_missing_r23_saved
_result=json.dumps({'active':s.projection_active,'actor':b.entity,
 'ready':work is not None and work.ready,'error':work.error if work is not None else None,
 'preparing':bool(b.preparing_entity),'missing':s.projection_missing,
 'failed':t.failed if t is not None else None,
 'building':t is not None and (t.build is not None or t.pending_model is not None or t.attaching),
 'changed':len(t.changed) if t is not None else 0,
 'commits':t.commits if t is not None else 0,
 'observations':[t.state[t.index(pos)] for pos in saved['points']] if t is not None else [],
 'document_preserved':s.editor.document.blocks==saved['document'],
 'snapshot_preserved':work is not None and work.document.blocks==saved['document'],
 'editor_id':id(s.editor),'document_id':id(s.editor.document),'revision':s.editor.revision,
 'source_current':id(s.editor)==saved['editor_id'] and id(s.editor.document)==saved['document_id'] and
  s.editor.revision==saved['revision'],
 'snapshot_document':work.document.to_data() if work is not None else None,
 'occupancy_snapshot_document':t.document.to_data() if t is not None else None,
 'player':b.player_position.GetFootPos()})
'''

SOURCE = '''t=b.projection_occupancy
mesh=b.projection_mesh
model=mesh[1] if mesh else None
parts=b.context_models.get(model,())
_result=json.dumps({'serial':b.projection_serial,'model':model,'parts':parts,
 'owner_current':t is not None and t.serial==b.projection_serial and t.entity==b.entity,
 'work_current':b.projection_work is not None and b.projection_work.serial==b.projection_serial,
 'snapshot_current':t is not None and t.document.blocks==sys._transform_missing_r23_saved['document'],
 'cache_current':t is not None and model==t.shader.names[t.shader.bank] and bool(parts) and
  all(name in t.shader.parts[t.shader.bank] for name,origin,context in parts),
 'origin_current':mesh is not None and tuple(mesh[2])==tuple(s.origin) and
  t is not None and tuple(t.origin)==tuple(s.origin)})
'''

RESTORE = '''import modern_projection.projection.occupancy as transform_occupancy
saved=sys._transform_missing_r23_saved
transform_occupancy.ProjectionOccupancy=saved['class']
s.projection_missing=saved['missing']
del sys._transform_missing_r23_saved
del sys._transform_missing_r23_occupied
_result=True
'''


def restore_owned(token):
    return ("if hasattr(sys,'_transform_missing_r23_saved'):\n"
            " assert sys._transform_missing_r23_saved.get('token')==%r, 'Unrelated observer must not be restored'\n "
            % token + '\n '.join(RESTORE.splitlines()) + '\nelse:\n _result=True\n')


def plan(short, cases, prefix):
    """Map a few named fixture subjects with an independent coordinate matrix."""
    case = cases[prefix + short]
    operation = 'mirror_x' if short == 't04' else 'rotate_y90'
    originals = {
        't01': ((2, 5, 2),),
        't04': case.get('pairs', (((15, 2, 4), (16, 2, 4)),))[0],
        't05': case.get('slope_top_pairs', (((4, 2, 3), (5, 3, 3)),))[0],
        't08': case.get('door', ((15, 15, 15), (15, 16, 15))),
    }[short]
    lo, hi = case['selection']
    points = tuple((hi[0] + lo[0] - pos[0], pos[1], pos[2])
                   if operation == 'mirror_x' else
                   (lo[0] + hi[2] - pos[2], pos[1], lo[2] + pos[0] - lo[0])
                   for pos in originals)
    stages = [('empty', ())]
    if len(points) > 1:
        stages.append(('single_half', points[:1]))
    stages.extend((('occupied', points), ('restored', ())))
    return {'points': points, 'original_points': originals, 'operation': operation,
            'stages': stages, 'native_world_occupancy': False}


def ready(state):
    if state['error'] or state['failed']:
        raise AssertionError(state)
    if not state['document_preserved'] or not state['snapshot_preserved'] or not state['source_current']:
        raise AssertionError('Observed occupancy mutated its document or snapshot')
    return (state['active'] and state['actor'] and state['ready'] and state['missing'] and
            not state['preparing'] and not state['building'] and not state['changed'])


def snapshot_document(document):
    """Reproduce the production snapshot contract without discarding metadata."""
    from projection.model import Document
    snapshot = Document(document.size, biome=document.biome)
    snapshot.blocks = document.blocks.copy()
    return snapshot.to_data()


def capture(check, label, expected, document_semantics, target_document, evidence=None):
    if evidence is None:
        evidence = {}
    state = check.wait(label, lambda value: ready(value) and value['observations'] == expected,
                       lambda: check.run(STATE))
    evidence['state'] = state
    evidence['expected_snapshot_semantics'] = target_document
    if (document_semantics(state['snapshot_document']) != target_document or
            document_semantics(state['occupancy_snapshot_document']) != target_document):
        raise AssertionError('Missing projection snapshot differs from the transformed typed document')
    time.sleep(.3)
    shown = check.capture(label)
    try:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
        time.sleep(.3)
        hidden = check.capture(label + '_hidden')
    finally:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
    difference = projection_pixels(shown['path'], hidden['path'],
                                   check.output.parent / (check.output.stem + '_' + label + '_delta.png'))
    after = check.run(STATE)
    if (not ready(after) or after['observations'] != expected or state['player'] != after['player'] or
            document_semantics(after['snapshot_document']) != target_document or
            document_semantics(after['occupancy_snapshot_document']) != target_document):
        raise AssertionError('Missing capture changed observation, player, or typed snapshot')
    source = check.run(SOURCE)
    if not all(source[key] for key in ('owner_current', 'work_current', 'snapshot_current', 'cache_current', 'origin_current')):
        raise AssertionError(source)
    evidence.update(final=after, shown=shown, hidden=hidden, difference=difference,
                    source=source, pixels_accepted=False)
    return evidence


def run(check, short, cases, prefix, oracle, document_semantics, verify_document, output_row):
    subject = plan(short, cases, prefix)
    if any(oracle.document.get(pos) == ('minecraft:air', 0) for pos in subject['points']):
        raise AssertionError('A mapped missing target is absent after its transform')
    expected_snapshot = snapshot_document(oracle.document)
    target_document = document_semantics(expected_snapshot)
    output_row.update(plan=subject, observer_restored=False, stages=[])
    output_row['snapshot_contract'] = {
        'constructor': 'Document(source.size, biome=source.biome); blocks=source.blocks.copy()',
        'document': expected_snapshot,
        'editor_name_checked_separately': oracle.document.name}
    installed = attempted = False
    token = uuid.uuid4().hex
    try:
        check.run('b.stop_projection()\n_result=True')
        attempted = True
        check.run(INSTALL % (subject['points'], token))
        installed = True
        check.run('s.projection_missing=True\nb.project()\n_result=True')
        previous_commits = None
        for label, occupied in subject['stages']:
            expected = [2 if pos in occupied else 1 for pos in subject['points']]
            if label != 'empty':
                check.run('sys._transform_missing_r23_occupied.clear()\n'
                          'sys._transform_missing_r23_occupied.update(%r)\n'
                          'for pos in sys._transform_missing_r23_saved["points"]:b.projection_occupancy.read(pos)\n'
                          '_result=True' % (occupied,))
                check.wait('missing occupancy commits ' + short + ':' + label,
                           lambda value: ready(value) and value['commits'] > previous_commits and
                           value['observations'] == expected, lambda: check.run(STATE))
            row = {'label': label, 'expected_observations': expected}
            output_row['stages'].append(row)
            capture(check, short + '_missing_' + label, expected, document_semantics, target_document, row)
            row['document_verification'] = verify_document('missing:' + short + ':' + label)
            previous_commits = row['final']['commits']
        output_row['completed'] = True
    finally:
        errors = []
        for name, code in [('projection', 'b.stop_projection()\n_result=True')] + (
                [('observer', restore_owned(token))] if attempted else []):
            try:
                check.run(code)
            except Exception as error:
                errors.append({'step': name, 'error': '%s: %s' % (type(error).__name__, error)})
        output_row['cleanup_errors'] = errors
        output_row['observer_restored'] = installed and not errors
        if errors and sys.exc_info()[0] is None:
            raise RuntimeError('Missing observer cleanup failed: ' + repr(errors))
