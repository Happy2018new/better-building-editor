"""Read bounded liquid-only profiler records from completed owner jobs."""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '.runtime/water-r20-state-v7/profiler-cpu-wall-v1'
saved = json.loads((OUTPUT / 'report.json').read_bytes())
binding = json.loads((OUTPUT.parent / 'start.json').read_bytes())
os.environ.update(MCDEV_SESSION_FILE=binding['session_file'], MCDEV_OWNER='water-r20-v7',
                  MCDEV_ALLOW_USER_FOREGROUND='1')
sys.path.insert(0, str(ROOT / '.runtime/projects/water-r20/.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client

target = OUTPUT / 'liquid-query.json'
assert not target.exists()
report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
          'capture_started': False, 'window_actions': [],
          'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'source_contract_sha256': saved['source_contract_sha256'], 'profiles': {}}
with Client(timeout=45) as client:
    for clock, profile in saved['profiles'].items():
        phase = report['profiles'][clock] = {'job_id': profile['job_id']}
        for view in ('hotspots', 'calls'):
            arguments = {'job_id': profile['job_id'], 'view': view,
                         'filter': 'liquid_', 'limit': 50}
            responses = phase[view] = []
            while True:
                result = client.call('mc_profiler', {'op': '/query', 'args': arguments})
                responses.append(result)
                data = result['structuredContent']['data']
                cursor = data.get('next_cursor')
                if not cursor:
                    break
                assert len(responses) < 10
                arguments['cursor'] = cursor
target.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='ascii')
for clock, phase in report['profiles'].items():
    print(json.dumps({'clock': clock, 'job_id': phase['job_id'], 'hotspots': [
        {key: row['fields'][key]['value'] for key in
         ('module', 'name', 'calls', 'self_time', 'total_time')}
        for page in phase['hotspots'] for row in page['structuredContent']['data']['records']
    ]}))
