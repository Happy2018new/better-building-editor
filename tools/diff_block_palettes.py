"""Show record-level changes between two native block_palette.json exports."""
import argparse
import hashlib
import json
from pathlib import Path


def records(path):
    raw = path.read_bytes()
    rows = json.loads(raw)['blocks']
    result = {}
    keys = set()
    for row in rows:
        state = tuple(sorted((item['name'], item['type'], item['value'])
                             for item in row['states']))
        result[(row['name'], row['data'])] = state
        keys.update(item['name'] for item in row['states'])
    return hashlib.sha256(raw).hexdigest().upper(), result, keys


def main(old_path, new_path):
    old_sha, old, old_keys = records(old_path)
    new_sha, new, new_keys = records(new_path)
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(key for key in old.keys() & new.keys() if old[key] != new[key])
    summary = {
        'old_sha256': old_sha,
        'new_sha256': new_sha,
        'old_records': len(old),
        'new_records': len(new),
        'added_records': len(added),
        'removed_records': len(removed),
        'changed_records': len(changed),
        'added_state_keys': sorted(new_keys - old_keys),
        'removed_state_keys': sorted(old_keys - new_keys),
        'added': added,
        'removed': removed,
        'changed': [
            {'name': key[0], 'data': key[1], 'old_states': old[key], 'new_states': new[key]}
            for key in changed
        ],
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old', type=Path)
    parser.add_argument('new', type=Path)
    args = parser.parse_args()
    main(args.old, args.new)
