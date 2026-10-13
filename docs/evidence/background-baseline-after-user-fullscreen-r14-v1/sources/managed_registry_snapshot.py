"""Read owner-bound startup manifests while Windows may replace their files."""
import json
from pathlib import Path
import time


def find_owner_session(registry, owner, project, timeout=1.0, on_retry=None):
    """Retry only PermissionError; never substitute cached data or relax binding."""
    if type(timeout) not in (int, float) or not 0 < timeout <= 2:
        raise ValueError('Registry read timeout must be positive and at most two seconds')
    project = Path(project).resolve()
    deadline = time.monotonic() + timeout
    matches = []
    for path in sorted(Path(registry).glob('*/session.json')):
        attempt = 0
        while True:
            attempt += 1
            try:
                raw = path.read_bytes()
                break
            except PermissionError as error:
                if on_retry is not None:
                    on_retry({'stage': 'read_session_manifest', 'manifest_id': path.parent.name,
                              'attempt': attempt, 'errno': error.errno,
                              'winerror': getattr(error, 'winerror', None)})
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise
                time.sleep(min(.05, remaining))
        row = json.loads(raw)
        if not isinstance(row, dict):
            raise ValueError('Session manifest must be an object: ' + str(path))
        if row.get('owner') == owner and Path(row.get('project', '')).resolve() == project:
            if row.get('schema') != 1 or Path(row.get('session_file', '')).resolve() != path.resolve():
                raise ValueError('Invalid owner-bound session manifest: ' + str(path))
            matches.append(row)
    if len(matches) > 1:
        raise RuntimeError('Ambiguous owner-bound sessions')
    return matches[0] if matches else None
