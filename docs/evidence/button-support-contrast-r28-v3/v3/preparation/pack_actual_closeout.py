"""Build a small private archive candidate; preserve failed V2 and actual V3."""
from datetime import datetime, timezone
import copy
import hashlib
import json
import lzma
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.with_name('button-support-contrast-v2')
OUT = HERE / 'closeout-v1'
PACKAGE = OUT / 'candidate-evidence'
PACKAGE.mkdir(exist_ok=False)
MAX_FILE = 240000
records = {}
redactions = []
SENSITIVE = {'token', 'api_key', 'apikey', 'authorization', 'password', 'secret',
    'access_key', 'mcp_url', 'access_token', 'refresh_token', 'client_secret'}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode('ascii')


def wire_values(value, found=None):
    found = [] if found is None else found
    if isinstance(value, dict):
        if value.get('codec', '').startswith(('cell.freeze-', 'python2-repr-')):
            found.append(json.dumps(value, sort_keys=True))
        else:
            for child in value.values():
                wire_values(child, found)
    elif isinstance(value, list):
        for child in value:
            wire_values(child, found)
    return found


def sanitize(value, prefix=''):
    if isinstance(value, dict):
        if value.get('codec', '').startswith(('cell.freeze-', 'python2-repr-')):
            return copy.deepcopy(value)
        result = {}
        for key, child in value.items():
            folded = key.lower().replace('-', '_')
            if folded in SENSITIVE:
                result[key] = '[REDACTED]'
                redactions.append(prefix + '/' + key)
            else:
                result[key] = sanitize(child, prefix + '/' + key)
        return result
    if isinstance(value, list):
        return [sanitize(child, prefix + '/' + str(i)) for i, child in enumerate(value)]
    return value


def store(name, data, source, sanitized=False, compress=False, extra=None):
    original_data = Path(source).read_bytes()
    stored = lzma.compress(data, preset=6) if compress else data
    path = PACKAGE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists() and len(stored) < MAX_FILE, (name, len(stored))
    with path.open('xb') as output:
        output.write(stored)
    assert (lzma.decompress(path.read_bytes()) if compress else path.read_bytes()) == data
    record = {'source_path': str(Path(source).resolve()), 'source_sha256': sha_bytes(original_data),
        'stored_sha256': sha_bytes(stored), 'bytes': len(stored),
        'content_sha256': sha_bytes(data), 'lossless_storage': 'xz' if compress else 'unchanged bytes',
        'sanitized_JSON_copy_not_original': sanitized}
    if extra:
        record.update(extra)
    records[name] = record


def raw(name, source):
    data = Path(source).read_bytes()
    compress = len(data) >= MAX_FILE
    store(name + ('.xz' if compress else ''), data, source, compress=compress)


def structured(name, source):
    value = json.loads(Path(source).read_bytes())
    sanitized = sanitize(value, name)
    assert wire_values(value) == wire_values(sanitized)
    data = json_bytes(sanitized)
    extra = {'typed_native_wire_values_unchanged': True, 'typed_wire_object_count': len(wire_values(value))}
    if len(lzma.compress(data, preset=6)) < MAX_FILE:
        store(name + '.xz', data, source, sanitized=True, compress=True, extra=extra)
        return
    chunk_size = 192 * 1024
    chunks = [data[offset:offset + chunk_size] for offset in range(0, len(data), chunk_size)]
    for index, chunk in enumerate(chunks):
        store(name + '.part-%02d.xz' % index, chunk, source, sanitized=True, compress=True,
            extra=dict(extra, chunked_JSON_name=name, chunk_index=index, chunk_count=len(chunks),
                complete_JSON_content_sha256=sha_bytes(data), uncompressed_offset=index * chunk_size,
                uncompressed_bytes=len(chunk), reassemble_before_JSON_parse=True))
    assert b''.join(lzma.decompress((PACKAGE / (name + '.part-%02d.xz' % index)).read_bytes())
        for index in range(len(chunks))) == data


assert sha(OLD / 'closeout-v1/candidate-evidence/index.json') == 'd630fe28d05f443b94e0f0420e9319f8bcdb03d1f6bf4d7ea64e31978d167d1b'
old_index = json.loads((OLD / 'closeout-v1/candidate-evidence/index.json').read_bytes())
for name, record in old_index['files'].items():
    source = OLD / 'closeout-v1/candidate-evidence' / name
    assert sha(source) == record['stored_sha256']
    raw('v2-failed/' + name, source)
raw('v2-failed/original-package-index.json', OLD / 'closeout-v1/candidate-evidence/index.json')
raw('v2-failed/closeout-sanitized.json', OLD / 'closeout-v1/closeout-sanitized.json')
manifest = json.loads((HERE / 'source-manifest.json').read_bytes())
report = json.loads((HERE / 'check/report.json').read_bytes())
pair = report['button_separate']
release = json.loads((HERE / 'owned-release.json').read_bytes())
assert report['completed'] and report['restored'] and report['source_unchanged']
assert pair['completed'] and len(pair['creations']) == 4 and len(pair['stages']) == 6
assert pair['diagnostic_restore']['restore']['restored'] and not pair['diagnostic_restore']['restore']['errors']
assert pair['all60_restored']['blocks'] == 60 and pair['after_diagnostic']['blocks'] == 2
assert release['completed'] and release['registry_state'] == 'stopped'
assert all(row['current'] is None for row in release['independent_identities'].values())
assert release['actual_exit_codes'] == {'game': 3221226505, 'mcdk': 0}
assert not release['normal_shutdown_qualified'] and not release['force_game_executed']
assert release['watcher_exit_code'] == 0
config = json.loads((HERE / 'prelaunch-config.json').read_bytes())
assert len(config['host_assets']) == 36
for path, digest in config['host_assets'].items():
    path = Path(path)
    assert sha(path) == digest
    if path.parent == HERE:
        name = 'v3/hosts/' + path.name
    elif Path(manifest['project']) in path.parents:
        name = 'v3/frozen-helpers/' + path.relative_to(Path(manifest['project'])).as_posix()
    else:
        name = 'v3/external-hosts/' + path.parent.name + '/' + path.name
    raw(name, path)
for source in sorted((HERE / 'check').glob('*.png')):
    raw('v3/originals/' + source.name, source)
for name in ('source-manifest.json', 'prelaunch-config.json', 'ready-index-v1.json',
        'host-derivation-v1.json', 'root-offline-review-v1.json', 'root-review-and-slot-v1.json',
        'root-instance-py2-v1.json', 'root-instance-py3-v1.json', 'root-seal-check-v1.json',
        'face-restore-before.json', 'face-restore-after1.json', 'face-restore-after2.json',
        'owned-release.json', 'sequence-receipt.json', 'assert-watch-start.json', 'assert-watch-close.json'):
    structured('v3/records/' + name, HERE / name)
structured('v3/records/actual-report.json', HERE / 'check/report.json')
structured('v3/records/exact-exit.json', HERE / 'launch/exact-exit.json')
structured('v3/records/ordinary-stop.json', HERE / 'stop/report.json')
for label, source in (
        ('original-source-raw', Path(pair['source_link']['raw_path'])),
        ('original-source-certificate', Path(pair['source_link']['certificate_path'])),
        ('restored-two-cell-raw', Path(pair['after_diagnostic']['strict_lineage_raw_path'])),
        ('all60-undo-raw', Path(pair['all60_restored']['strict_lineage_raw_path']))):
    structured('v3/records/' + label + '.json', source)
    if label.endswith('-raw') and label != 'original-source-raw':
        structured('v3/records/' + label.replace('-raw', '-certificate') + '.json', source.with_suffix('.certificate.json'))
analysis = json.loads((OUT / 'analysis/pixel-analysis.json').read_bytes())
raw('v3/analysis/pixel-analysis.json', OUT / 'analysis/pixel-analysis.json')
for name in ('b_combined_white-ROI-nearest3x.png', 'b_support_white-ROI-nearest3x.png',
        'a_combined_stone-ROI-nearest3x.png'):
    raw('v3/analysis/' + name, OUT / 'analysis' / name)
for name in ('client-key-only.patch', 'client-derivation.json', 'verify_instance_path_replay.py',
        'analyze_actual_v3.py', 'pack_actual_closeout.py'):
    raw('v3/preparation/' + name, HERE / name)
audits = {}
for phase in ('after1', 'after2'):
    audit = json.loads((HERE / ('face-restore-' + phase + '.json')).read_bytes())
    assert audit['completed'] and audit['changed_keys'] == [] and audit['source_unchanged']
    audits[phase] = {'completed': True, 'changed_keys': [], 'source_unchanged': True}
from frozen_guard import verify
assert verify() == manifest
for name, record in json.loads((HERE / 'ready-index-v1.json').read_bytes())['files'].items():
    assert sha(HERE / name) == record['sha256']
summary = {'scope': 'ACTUAL_T02_V2_FAILED_AND_V3_SINGLE_ATTEMPT_CLOSEOUT',
    'at': datetime.now(timezone.utc).isoformat(), 'owner': manifest['owner'],
    'source_commit': manifest['source_commit'], 'source_manifest_sha256': sha(HERE / 'source-manifest.json'),
    'prelaunch_config_sha256': sha(HERE / 'prelaunch-config.json'),
    'actual_report_sha256': sha(HERE / 'check/report.json'), 'release_sha256': sha(HERE / 'owned-release.json'),
    'V2_preserved_failure': {'completed_stages': 0, 'private_models_created': 0,
        'first_failure': 'KeyError combined in actual freeze/guard',
        'old_release_sha256': sha(OLD / 'owned-release.json'), 'old_game_exit_code': 3221226505,
        'normal_shutdown_qualified': False, 'no_white_result_exists': True},
    'V3_actual': {'completed': True, 'models_created': 4, 'stages_completed': 6,
        'single_new_owner_attempt': True, 'actual_Render_calls_bound_to_unique_model_names': True,
        'native_Deserialize_inputs_equal_Serialize_results': True,
        'only_client_change': 'combined -> combined_stone key in guard',
        'source_and_hosts_unchanged': True, 'original_seal_145_files_unchanged': True,
        'local_restore_passed': True, 'local_restore_errors': [], 'original_native_submissions_restored': 2,
        'original_two_cell_source_recertified': True, 'all60_undo_restored': True,
        'global_restore_passed': True, 'global_restore_audits': len(report['restore_audits']),
        'independent_restore_audits': audits, 'release': release},
    'pixel_analysis': {'ROI': analysis['ROI'], 'comparisons': analysis['comparisons'],
        'button_net_contribution_visible_in_one_fixed_view': True,
        'white_combined_stone_texture_is_local_button_rectangle_not_full_support': True,
        'native_material_UV_vertex_or_GPU_tint_readback': False},
    'earlier_visual_wording_correction': 'B combined still has stone texture means its local button rectangle; quantitative A/B support shows support material did change',
    'same_owner_retry_performed': False, 'further_MC_started': False,
    'production_changed': False, 'pixels_qualified': False, 'manual_issues_closed': 0,
    'canonical_docs_changed': False, 'MC_slot_explicitly_released': True,
    'credential_fields_redacted': sorted(set(redactions)), 'typed_native_wire_values_unchanged': True,
    'archive_candidate': 'candidate-evidence/index.json',
    'limitations': analysis['limitations']}
with (OUT / 'closeout-sanitized.json').open('x', encoding='utf8') as output:
    json.dump(summary, output, indent=2)
    output.write('\n')
raw('closeout-sanitized.json', OUT / 'closeout-sanitized.json')
raw('doc-draft.md', OUT / 'doc-draft.md')
index = {'scope': 'MINIMAL_V2_FAILED_AND_V3_ACTUAL_T02_ARCHIVE_CANDIDATE',
    'source_commit': manifest['source_commit'], 'manual_issues_closed': 0,
    'original_images_unchanged': True, 'typed_native_wire_values_unchanged': True,
    'credential_fields_redacted_in_JSON': True, 'lossless_compression': 'xz only when declared',
    'max_file_bytes_exclusive': MAX_FILE, 'file_count': len(records),
    'stored_total_bytes': sum(row['bytes'] for row in records.values()), 'files': records}
with (PACKAGE / 'index.json').open('x', encoding='utf8') as output:
    json.dump(index, output, indent=2)
    output.write('\n')
assert (PACKAGE / 'index.json').stat().st_size < MAX_FILE
print(json.dumps({'package_index': str(PACKAGE / 'index.json'), 'package_index_sha256': sha(PACKAGE / 'index.json'),
    'closeout_sha256': sha(OUT / 'closeout-sanitized.json'), 'files': len(records),
    'stored_total_bytes': index['stored_total_bytes'], 'max_stored_file_bytes': max(row['bytes'] for row in records.values()),
    'manual_issues_closed': 0, 'canonical_docs_changed': False}))
