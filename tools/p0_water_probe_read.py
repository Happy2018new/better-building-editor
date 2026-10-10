"""Read progress or the completed versioned native water capability export."""
import json
import sys

state = getattr(sys, '_p0_native_probe', None)
if state is None:
    raise ValueError('No native water capability probe has been started')
if state.get('failure'):
    raise ValueError('Native water capability probe failed: %s' % state['failure'])
if state.get('cleanup_failure'):
    raise ValueError('Native probe cleanup failed: %s' % state['cleanup_failure'])
if state.get('done'):
    result = dict((key, state[key]) for key in (
        'schema', 'game_version', 'palette_sha256', 'blocks', 'tested_states',
        'total_states', 'method', 'elapsed_seconds', 'verified_states',
        'states_per_subchunk', 'readback_states'))
else:
    result = dict((key, state.get(key)) for key in (
        'running', 'done', 'progress', 'tested_states', 'total_states',
        'completed_blocks', 'total_blocks', 'current_name', 'current_aux', 'elapsed_seconds',
        'verified_states', 'subchunk_index'))
_result = json.dumps(result, sort_keys=True)
