"""Compare pure context preparation in one owned client without scene changes."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import statistics

from verify_debug_blueprints import CLIENT, Client, return_value, write_json
from _session import desktop_lock, load_session

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'behavior_pack/modern_projection/projection/render_context.py'

CODE = '''import base64,json,time,types
from modern_projection.projection import render_context as baseline
from modern_projection.projection.debug_blueprints import build,material
from modern_projection.projection.model import Document
assert not s.busy and s.edit_job is None and s.io_job is None
assert not s.projection_active and not b.preparing_entity
assert navigator.top is None and not navigator.is_transitioning
saved=(id(s.editor),id(s.editor.document),s.camera_pose,s.origin,b.entity)
source=base64.b64decode(%r)
assert base64.b64encode(source)==%r
candidate=types.ModuleType('modern_projection.projection._context_cache_benchmark')
candidate.__package__='modern_projection.projection'
exec compile(source,'context-cache-benchmark-candidate','exec') in candidate.__dict__
case=%r
if isinstance(case,int):
 doc=Document((case,case,case),dict(((x,y,z),material('stone'))
  for x in range(case) for y in range(case) for z in range(case)))
else:
 doc=build(case)
targets=doc.palette_data()
saved_document=doc.to_data()
saved_targets=dict((key,value.copy() if isinstance(value,dict) else value)
 for key,value in targets.items())
results={}
timings={}
functions=[('baseline',baseline.prepare_context_batches),
 ('candidate',candidate.prepare_context_batches)]
if %r:functions.reverse()
for label,function in functions:
 started=time.clock()
 results[label]=function(doc,targets)
 timings[label]=time.clock()-started
 assert doc.to_data()==saved_document,('document changed',label)
 assert targets==saved_targets,('targets changed',label)
assert results['baseline']==results['candidate'],'context outputs differ'
assert (id(s.editor),id(s.editor.document),s.camera_pose,s.origin,b.entity)==saved
_result=json.dumps({'case':case,'runtime':api.GetMinecraftVersion(),
 'size':doc.size,'blocks':len(doc.blocks),'equivalent':True,
 'workspace_unchanged':True,'timing_seconds':timings,
 'candidate_source_sha256':%r,'candidate_bytes':len(source),
 'candidate_roundtrip_verified':True,
 'loaded_baseline_module_file':baseline.__file__,
 'loaded_baseline_function_line':baseline.prepare_context_batches.func_code.co_firstlineno})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 3:
        parser.error('--repeats must be between 1 and 3')
    os.environ['MCDEV_SESSION_FILE'] = str(args.session.resolve())
    os.environ['MCDEV_OWNER'] = args.owner
    source = SOURCE.read_bytes()
    fingerprint = hashlib.sha256(source).hexdigest()
    report = {'schema_version': 1, 'completed': False, 'passed': False,
              'scope': 'Client Python 2 context preparation only; no geometry calls or visual acceptance.',
              'world_writes': False, 'camera_changes': False, 'window_activation': False,
              'resource_reload': False, 'candidate_source_sha256': fingerprint, 'samples': []}
    try:
        binding = load_session(live=True)
        if binding is None or Path(binding['project']).resolve() != args.project.resolve():
            raise ValueError('Benchmark project does not match the managed session')
        report['binding'] = {key: binding[key] for key in
            ('id', 'owner', 'project', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')}
        encoded = base64.b64encode(source).decode('ascii')
        with desktop_lock(), Client(timeout=30) as client:
            for case in ('test.layers.water', 'test.entities.signs', 16, 24, 32):
                for number in range(args.repeats if isinstance(case, int) else 1):
                    code = CLIENT + CODE % (encoded, encoded, case, bool(number % 2), fingerprint)
                    result = return_value(client.call('execute_code', {
                        'code': code, 'is_client': True, 'direct_return': True}))
                    if isinstance(result, str):
                        result = json.loads(result)
                    report['samples'].append(result)
                    write_json(args.output, report)
        report['median_seconds'] = {}
        for size in (16, 24, 32):
            rows = [row for row in report['samples'] if row['case'] == size]
            report['median_seconds'][str(size)] = {
                key: statistics.median(row['timing_seconds'][key] for row in rows)
                for key in ('baseline', 'candidate')}
        report['completed'] = report['passed'] = True
    except (OSError, ValueError, AssertionError, RuntimeError) as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
