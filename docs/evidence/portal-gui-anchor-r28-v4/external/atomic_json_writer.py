"""Atomically publish complete ASCII JSON on the destination's filesystem.

Only actual Windows PermissionError codes 5/32/33 during rename receive five
bounded I/O attempts, using the committed session writer's .75s total backoff.
JSON/schema/other filesystem errors propagate without retry. Existing complete
JSON remains visible until replacement; no reader repair is added.
"""
import json
import os
from pathlib import Path
import tempfile
import time


def atomic_write_json(path, value, replace=os.replace, sleeper=time.sleep):
    path = Path(path)
    content = (json.dumps(value, indent=2) + '\n').encode('ascii')
    descriptor, name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=str(path.parent))
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        delays = (.05, .1, .2, .4)
        for attempt in range(len(delays) + 1):
            try:
                replace(temporary, path)
            except PermissionError as error:
                if getattr(error, 'winerror', None) not in (5, 32, 33) or attempt == len(delays):
                    raise
                sleeper(delays[attempt])
            else:
                return {'bytes': len(content), 'replace_attempts': attempt + 1}
    finally:
        if temporary.exists():
            temporary.unlink()
