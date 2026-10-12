"""Compare typed native states separately from version-specific aux numbers."""
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
        name, aux = row['name'], row['data']
        if not isinstance(name, str) or not name or type(aux) is not int or aux < 0:
            raise ValueError('Invalid native block name or aux')
        if (name, aux) in result:
            raise ValueError('Duplicate native block name/aux: %s [%d]' % (name, aux))
        state = []
        names = set()
        for item in row['states']:
            key, kind, value = item['name'], item['type'], item['value']
            if not isinstance(key, str) or not key or key in names:
                raise ValueError('Invalid or duplicate native state key')
            if kind == 'byte' and type(value) in (int, bool) and value in (0, 1):
                value = int(value)
            elif ((kind == 'int' and type(value) is int)
                  or (kind == 'string' and isinstance(value, str))):
                pass
            else:
                raise ValueError('Invalid native state type or value: %s' % key)
            names.add(key)
            state.append((key, kind, value))
        result[(name, aux)] = tuple(sorted(state))
        keys.update(names)
    return hashlib.sha256(raw).hexdigest().upper(), result, keys


def _semantic_index(rows):
    result = {}
    for (name, aux), state in rows.items():
        result.setdefault((name, state), []).append(aux)
    return dict((key, sorted(values)) for key, values in result.items())


def compare(old_path, new_path):
    old_sha, old, old_keys = records(old_path)
    new_sha, new, new_keys = records(new_path)
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    changed = sorted(key for key in old.keys() & new.keys() if old[key] != new[key])
    old_semantic, new_semantic = _semantic_index(old), _semantic_index(new)
    shared = old_semantic.keys() & new_semantic.keys()
    old_names, new_names = {key[0] for key in old}, {key[0] for key in new}
    state_row = lambda key, source: {'name': key[0], 'states': key[1], 'data': source[key]}
    semantic_added = sorted(new_semantic.keys() - old_semantic.keys())
    semantic_removed = sorted(old_semantic.keys() - new_semantic.keys())
    remapped = sorted(key for key in shared if old_semantic[key] != new_semantic[key])
    return {
        'schema_version': 2,
        'old_source': str(old_path.resolve()),
        'new_source': str(new_path.resolve()),
        'old_sha256': old_sha,
        'new_sha256': new_sha,
        'old_records': len(old),
        'new_records': len(new),
        'added_records': len(added),
        'removed_records': len(removed),
        'changed_records': len(changed),
        'added_state_keys': sorted(new_keys - old_keys),
        'removed_state_keys': sorted(old_keys - new_keys),
        'added_names': sorted(new_names - old_names),
        'removed_names': sorted(old_names - new_names),
        'added_semantic_states': [state_row(key, new_semantic) for key in semantic_added],
        'removed_semantic_states': [state_row(key, old_semantic) for key in semantic_removed],
        'remapped_semantic_states': [
            {'name': key[0], 'states': key[1], 'old_data': old_semantic[key],
             'new_data': new_semantic[key]} for key in remapped
        ],
        'added': added,
        'removed': removed,
        'changed': [
            {'name': key[0], 'data': key[1], 'old_states': old[key], 'new_states': new[key]}
            for key in changed
        ],
    }


def main(old_path, new_path, output=None):
    if output is not None and output.resolve() in (old_path.resolve(), new_path.resolve()):
        raise ValueError('Diff output must not overwrite a source dump')
    summary = compare(old_path, new_path)
    text = json.dumps(summary, ensure_ascii=True, indent=2) + '\n'
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding='ascii')
        print(json.dumps({key: summary[key] for key in (
            'schema_version', 'old_records', 'new_records', 'added_records',
            'removed_records', 'changed_records', 'added_state_keys', 'removed_state_keys')},
            sort_keys=True))
    else:
        print(text, end='')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old', type=Path)
    parser.add_argument('new', type=Path)
    parser.add_argument('--output', type=Path, help='Preserve a versioned JSON diff without modifying the dumps')
    args = parser.parse_args()
    main(args.old, args.new, args.output)
