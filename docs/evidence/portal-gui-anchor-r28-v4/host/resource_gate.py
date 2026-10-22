"""Persist actual boundary measurements before evaluating private host guards."""
from datetime import datetime, timezone
import json
from pathlib import Path
from status_reader import read_json as read_status_json

MIN_HEADROOM = 6 * 1024 ** 3
MAX_HANDLES = 200000
MAX_GROWTH = 10000
MAX_WATCH_AGE = 60.


def snapshot_boundary(phase, watcher_path, memory_read, session=None,
                      identity_read=None, handles_read=None):
    row = {'phase': phase, 'recorded_at': datetime.now(timezone.utc).isoformat(),
           'watcher_path': str(watcher_path), 'processes': {}}
    try:
        row['memory'] = memory_read()
    except Exception as error:
        row['memory_error'] = {'type': type(error).__name__, 'error': str(error)}
    try:
        row['watcher'] = read_status_json(watcher_path)
    except Exception as error:
        row['watcher_error'] = {'type': type(error).__name__, 'error': str(error)}
    if session is not None:
        for key in ('game', 'mcdk'):
            pid, identity = session.get(key + '_pid'), session.get(key + '_identity')
            if not pid or not identity:
                continue
            process = {'pid': pid, 'identity': identity}
            row['processes'][key] = process
            try:
                process['identity_before'] = identity_read(pid)
                if process['identity_before'] == identity:
                    process['handles'] = handles_read(pid)
                process['identity_after'] = identity_read(pid)
            except Exception as error:
                process['query_error'] = {'type': type(error).__name__, 'error': str(error)}
    row['recorded_at'] = datetime.now(timezone.utc).isoformat()
    return row


def validate_boundary(sample, owner, watcher_sha, previous=None, require_game=False):
    mem = sample.get('memory', {})
    value = mem.get('headroom_bytes')
    assert type(value) is int and value >= MIN_HEADROOM, 'Commit headroom below 6 GiB or unavailable'
    watch = sample.get('watcher', {})
    assert watch.get('owners') == [owner], 'Assertion watcher owner mismatch or unavailable'
    assert watch.get('host_sha256') == watcher_sha, 'Assertion watcher host SHA mismatch'
    assert 'errors' in watch and 'other_assertions' in watch, 'Watcher error fields unavailable'
    assert not watch['errors'] and not watch['other_assertions'], 'Assertion watcher reported errors/assertions'
    age = (datetime.fromisoformat(sample['recorded_at']) - datetime.fromisoformat(watch['checked_at'])).total_seconds()
    assert 0. <= age < MAX_WATCH_AGE, 'Assertion watcher is stale or future dated'
    processes = sample['processes']
    assert not require_game or 'game' in processes, 'Published owned game identity is missing'
    previous = previous or {}
    for key, process in processes.items():
        assert process.get('identity_before') == process['identity'] == process.get('identity_after'), 'Owned process creation identity changed: ' + key
        handles = process.get('handles')
        assert type(handles) is int and 0 <= handles < MAX_HANDLES, 'Owned process handle budget exceeded/unavailable: ' + key
        prior = previous.get(key)
        if prior is not None and prior['identity'] == process['identity']:
            assert handles - prior['handles'] < MAX_GROWTH, 'Adjacent owned handle growth exceeded: ' + key
    return {key: {'identity': process['identity'], 'handles': process['handles']}
            for key, process in processes.items()}


def persist_boundary(path, sample, owner, watcher_sha, previous=None, require_game=False):
    """Failure files contain the unmodified measured sample, including low memory."""
    path = Path(path)
    assert not path.exists(), 'Boundary evidence path must be fresh'
    record = {'sample': sample, 'accepted': False, 'evaluated': False}
    save = lambda: path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
    save()
    try:
        result = validate_boundary(sample, owner, watcher_sha, previous, require_game)
        record.update(accepted=True, evaluated=True)
        return result
    except Exception as error:
        record.update(evaluated=True, error={'type': type(error).__name__, 'error': str(error)})
        raise
    finally:
        save()
