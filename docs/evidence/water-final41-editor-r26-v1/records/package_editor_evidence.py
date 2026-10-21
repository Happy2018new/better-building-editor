"""Create bounded sanitized evidence, retaining original raw hashes separately."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
OUT = ROOT / 'docs/evidence/water-final41-editor-r26-v1'
LIMIT = 240000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    registry = Path(launch['session_file'])
    session = json.loads(registry.read_bytes())
    extras = {'registry/session.json': registry, 'registry/mcdk.log': Path(session['log'])}
    files = {p.relative_to(WORK).as_posix(): p for p in WORK.rglob('*')
             if p.is_file() and p.suffix in ('.json', '.txt', '.py', '.patch', '.png')}
    files.update(extras)
    secrets = set()
    secret_paths = {}

    def discover(value, path, found):
        if isinstance(value, dict):
            for key, item in value.items():
                location = path + '.' + key
                if isinstance(item, str) and len(item) >= 8 and ('token' in key.lower() or
                        key.lower() in ('authorization', 'api_key', 'apikey', 'secret')) and not key.lower().endswith('sha256'):
                    secrets.add(item)
                    found.append(location)
                else:
                    discover(item, location, found)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                discover(item, path + '[%d]' % index, found)
        elif isinstance(value, str) and value.lstrip().startswith(('{', '[')):
            try:
                nested = json.loads(value)
            except ValueError:
                return
            discover(nested, path + ':decoded_json', found)

    for name, path in files.items():
        if path.suffix == '.json':
            found = []
            discover(json.loads(path.read_bytes()), '$', found)
            secret_paths[name] = found
    entries = []
    for name, path in sorted(files.items()):
        raw = path.read_bytes()
        row = {'original_raw_path': str(path.resolve()), 'original_raw_sha256': digest(raw),
               'original_raw_bytes': len(raw), 'redacted_fields': secret_paths.get(name, [])}
        if path.suffix == '.png':
            picture = Image.open(io.BytesIO(raw)).convert('RGB')
            target = OUT / 'images' / (Path(name).stem + '.jpg')
            target.parent.mkdir(exist_ok=True)
            quality = 90
            while True:
                buffer = io.BytesIO()
                picture.save(buffer, format='JPEG', quality=quality, optimize=True, subsampling=0)
                data = buffer.getvalue()
                if len(data) < LIMIT:
                    break
                quality -= 5
                assert quality >= 50
            target.write_bytes(data)
            row.update(encoding='jpeg', full_resolution=list(picture.size), jpeg_quality=quality,
                       lossy_visual_reference=True, original_png_retained_in_runtime=True,
                       original_bytes_reconstructable=False, redaction_occurrences=0,
                       derived_parts=[{'path': target.relative_to(OUT).as_posix(), 'sha256': digest(data), 'bytes': len(data)}])
        else:
            text = raw.decode('utf-8-sig')
            occurrences = 0
            for secret in sorted(secrets, key=len, reverse=True):
                occurrences += text.count(secret)
                text = text.replace(secret, '[REDACTED_SESSION_TOKEN]')
            sanitized = text.encode('utf-8')
            compressed = gzip.compress(sanitized, mtime=0) if len(sanitized) > 100000 else sanitized
            is_gzip = len(sanitized) > 100000
            base = OUT / 'records' / (name + ('.gz' if is_gzip else ''))
            base.parent.mkdir(parents=True, exist_ok=True)
            chunks = [compressed[offset:offset+LIMIT] for offset in range(0, len(compressed), LIMIT)] or [b'']
            parts = []
            for index, chunk in enumerate(chunks):
                target = Path(str(base) + ('.%03d' % (index+1) if len(chunks)>1 else ''))
                target.write_bytes(chunk)
                parts.append({'path': target.relative_to(OUT).as_posix(), 'sha256': digest(chunk), 'bytes': len(chunk)})
            row.update(encoding='gzip-split' if is_gzip and len(chunks)>1 else 'gzip' if is_gzip else 'utf8',
                       decoded_sanitized_sha256=digest(sanitized), decoded_sanitized_bytes=len(sanitized),
                       redaction_occurrences=occurrences, original_bytes_reconstructable=sanitized==raw,
                       derived_parts=parts)
        entries.append(row)
    F = json.loads((WORK / 'product-v2-f-editor-v1.json').read_bytes())
    G = json.loads((WORK / 'product-v2-g-v1.json').read_bytes())
    host = json.loads((WORK / 'product-v2-f-editor-v1-host.json').read_bytes())
    group = json.loads((WORK / 'group-execution-v1.json').read_bytes())
    guard = json.loads((WORK / 'continuous-handle-guard-v1.json').read_bytes())
    restore = json.loads((WORK / 'independent-restore-v1.json').read_bytes())
    helper = json.loads((WORK / 'helper-retirement-v1.json').read_bytes())
    assert group['completed'] and F['completed'] and F['restored'] and G['completed'] and G['restored']
    assert not F['cleanup_errors'] and not G['cleanup_errors'] and restore['passed']
    assert helper['all_owned_helper_identities_absent'] and session['state']=='stopped'
    resource = {}
    for kind in ('game', 'mcdk'):
        values = [sample[kind]['handles'] for sample in guard['samples'] if sample[kind]['handles'] is not None]
        resource[kind] = {'maximum_handles': max(values), 'maximum_sample_step_growth': max([b-a for a,b in zip(values, values[1:])], default=0)}
    result = {'schema': 1, 'owner': launch['owner'], 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'candidate_only': True, 'new_manual_closures': 0, 'A_or_D_or_default_qualification_granted': False,
              'original_raws_modified': False, 'archive_decodes_to_original_raw': False,
              'secret_values_discovered': len(secrets), 'secret_values_in_output': 0,
              'entry_count': len(entries), 'entries': entries,
              'result': {'group_completed': True, 'source_unchanged': F['source_unchanged'] and G['source_unchanged'],
                         'bootstrap_exact_function_restored_and_terminal_marker_retired': True,
                         'G_capture_count': len(G['captures']), 'G_visual_limit': 'Default 90% gallery view is too small for per-face acceptance',
                         'F_case_count': len(F['cases']), 'F_cases': F['cases'], 'F_report_rows': list(F['rows']),
                         'F_actual_report_row_count': len(F['rows']), 'F_host_transition_counter': host['finished_rows'],
                         'F_capture_count': len(F['captures']), 'F_native_acceptance_flags_all_false': True,
                         'independent_runtime_restore_passed': restore['passed'], 'all_exact_game_mcdk_identities_absent': all(group['exact_identities_absent_after_stop'].values()),
                         'first_ordinary_stop_exit_code': group['ordinary_stop']['exit_code'],
                         'registry_finalize_exit_code': group['registry_finalize']['exit_code'],
                         'same_handle_game_exit_code_hex': '0xC0000409', 'same_handle_mcdk_exit_code': 0,
                         'assertion_recoveries_observed': 0, 'guard_samples': len(guard['samples']), 'resources': resource,
                         'commit_guard_coverage': '6GiB before each command, not continuous memory coverage',
                         'idle_helper_retirement': 'Only exact assigned idle Python assertion watcher was terminated; game/MCDK not forced',
                         'helpers_exact_identities_absent': helper['all_owned_helper_identities_absent']}}
    index = OUT / 'index.json'
    index.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    for row in entries:
        for part in row['derived_parts']:
            assert (OUT / part['path']).stat().st_size < 300000
    for path in OUT.rglob('*'):
        if path.is_file():
            data = path.read_bytes()
            assert len(data)<300000
            assert not any(secret.encode('utf-8') in data for secret in secrets)
    print(json.dumps({'index': str(index), 'index_sha256': digest(index.read_bytes()),
                      'entries': len(entries), 'maximum_item_bytes': max(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),
                      'secret_values_discovered': len(secrets), 'total_bytes': sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())}))


if __name__ == '__main__':
    main()
