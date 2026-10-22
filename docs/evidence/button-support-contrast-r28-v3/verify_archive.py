"""Read-only independent archive integrity/JSON/shard/original-wire validation."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--check-originals', action='store_true')
args = parser.parse_args()
assert args.output.parent.is_dir() and not args.output.exists()
package = HERE / 'candidate-evidence'
index = json.loads((package / 'index.json').read_bytes())
sha = lambda data: hashlib.sha256(data).hexdigest()
groups, json_values, wire_objects, nonce_paths = {}, {}, 0, []


def wires(value, result=None):
    result = [] if result is None else result
    if isinstance(value, dict):
        if isinstance(value.get('codec'), str) and value['codec'].startswith(('cell.freeze-', 'python2-repr-')):
            result.append(json.dumps(value, sort_keys=True))
        else:
            for item in value.values():
                wires(item, result)
    elif isinstance(value, list):
        for item in value:
            wires(item, result)
    return result


def check_secrets(value, prefix=''):
    if isinstance(value, dict):
        if isinstance(value.get('codec'), str) and value['codec'].startswith(('cell.freeze-', 'python2-repr-')):
            return
        for key, child in value.items():
            # This is the noncredential diagnostic observer nonce, part of source provenance.
            if key == 'host_run_token':
                assert isinstance(child, str) and re.fullmatch('[0-9a-f]{32,64}', child)
                nonce_paths.append(prefix + '/' + key)
            elif key.lower().replace('-', '_') in {
                    'token', 'api_key', 'apikey', 'authorization', 'password', 'secret',
                    'access_key', 'mcp_url', 'access_token', 'refresh_token', 'client_secret'}:
                assert child == '[REDACTED]', prefix + '/' + key
            check_secrets(child, prefix + '/' + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            check_secrets(item, prefix + '/' + str(i))


assert len(index['files']) == index['file_count'] == 104
assert sum(record['bytes'] for record in index['files'].values()) == index['stored_total_bytes']
for name, record in index['files'].items():
    path = package / name
    assert path.resolve().is_relative_to(package.resolve()) and path.is_file()
    raw = path.read_bytes()
    assert len(raw) == record['bytes'] < index['max_file_bytes_exclusive']
    assert sha(raw) == record['stored_sha256']
    content = lzma.decompress(raw) if record['lossless_storage'] == 'xz' else raw
    assert sha(content) == record['content_sha256']
    if args.check_originals:
        assert sha(Path(record['source_path']).read_bytes()) == record['source_sha256']
    if record.get('chunked_JSON_name'):
        groups.setdefault(record['chunked_JSON_name'], []).append((record, content))
    elif record['sanitized_JSON_copy_not_original']:
        json_values[name] = (record, json.loads(content))
for name, chunks in groups.items():
    chunks.sort(key=lambda item: item[0]['chunk_index'])
    assert [record['chunk_index'] for record, content in chunks] == list(range(chunks[0][0]['chunk_count']))
    offset = 0
    for record, content in chunks:
        assert record['uncompressed_offset'] == offset and record['uncompressed_bytes'] == len(content)
        offset += len(content)
    joined = b''.join(content for record, content in chunks)
    assert all(sha(joined) == record['complete_JSON_content_sha256'] for record, content in chunks)
    json_values[name] = (chunks[0][0], json.loads(joined))
for name, (record, value) in json_values.items():
    check_secrets(value, name)
    current_wires = wires(value)
    assert len(current_wires) == record['typed_wire_object_count']
    wire_objects += len(current_wires)
    if args.check_originals:
        assert current_wires == wires(json.loads(Path(record['source_path']).read_bytes()))

old_index = json.loads((package / 'v2-failed/original-package-index.json').read_bytes())
for name, record in old_index['files'].items():
    assert sha((package / 'v2-failed' / name).read_bytes()) == record['stored_sha256']
analysis = json.loads((package / 'v3/analysis/pixel-analysis.json').read_bytes())
for record in analysis['originals'].values():
    original = package / 'v3/originals' / Path(record['path']).name
    assert sha(original.read_bytes()) == record['sha256']
result = {'passed': True, 'scope': 'READ_ONLY_ARCHIVE_INDEX_BYTES_SHARDS_JSON_AND_TYPED_WIRE_CHECK',
    'package_index_sha256': sha((package / 'index.json').read_bytes()), 'indexed_files_checked': 104,
    'stored_total_bytes': index['stored_total_bytes'],
    'maximum_stored_file_bytes': max(record['bytes'] for record in index['files'].values()),
    'chunked_JSON_groups_reassembled': len(groups), 'complete_sanitized_JSON_objects_checked': len(json_values),
    'typed_wire_objects_compared_to_originals': wire_objects if args.check_originals else None,
    'original_source_file_hashes_checked': args.check_originals,
    'failed_V2_package_artifacts_checked': len(old_index['files']),
    'analysis_original_image_hashes_checked': len(analysis['originals']),
    'noncredential_source_observer_nonce_fields_intentionally_preserved': len(nonce_paths),
    'credential_named_fields_are_redacted': True,
    'MC_started': False, 'RPC_executed': False, 'canonical_docs_changed': False,
    'pixels_qualified': False, 'manual_issues_closed': 0}
with args.output.open('x', encoding='utf8') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps(result))
