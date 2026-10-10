"""Read native water probe evidence, including failed-state diagnostics."""
import json
import sys

state = getattr(sys, '_p0_native_probe', None)
if state is None:
    raise ValueError('No native water capability probe has been started')
_result = json.dumps(dict((key, state.get(key)) for key in (
    'schema', 'game_version', 'palette_sha256', 'method', 'blocks',
    'tested_states', 'total_states', 'verified_states', 'failure',
    'cleanup_failure', 'readback_states', 'state_mismatches',
    'elapsed_seconds', 'running', 'done', 'states_per_subchunk',
    'block_entities', 'block_entity_names')), sort_keys=True)
