"""Read-only archive integrity/derivation/token audit of the two final r26 packs."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
NAMES = ('water-final41-editor-r26-v1', 't02-face-missing-r26-v1')
TOKEN_KEYS = ('token', 'session_token', 'access_token', 'api_key', 'authorization')


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def parse(blob):
    try:
        return json.loads(blob)
    except (ValueError, UnicodeError):
        return None


def live(value):
    return isinstance(value, str) and len(value.strip()) >= 12 and not any(
        tag in value.lower() for tag in ('redact', 'removed', 'placeholder', 'example',
                                        '[hidden]', '<hidden>', '${', '{token}'))


def token_leaves(value, path=''):
    leaves = {}
    if isinstance(value, dict):
        for key, item in value.items():
            child = path + '.' + str(key) if path else str(key)
            if str(key).lower().replace('-', '_') in TOKEN_KEYS and isinstance(item, str):
                leaves[child] = item
            leaves.update(token_leaves(item, child))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            leaves.update(token_leaves(item, path + '[%d]' % i))
    return leaves


def derivative_changes(original, derived):
    before, after = token_leaves(original), token_leaves(derived)
    replacements = {}
    for path, value in before.items():
        if live(value) and path in after and not live(after[path]) and value != after[path]:
            replacements[value] = after[path]
    changes = []

    def check(a, b, path=''):
        assert type(a) is type(b), 'Derivative value type differs at ' + path
        if isinstance(a, dict):
            assert a.keys() == b.keys(), 'Derivative keys differ at ' + path
            for key in a:
                check(a[key], b[key], (path + '.' if path else '') + str(key))
        elif isinstance(a, list):
            assert len(a) == len(b), 'Derivative list length differs at ' + path
            for i, value in enumerate(a):
                check(value, b[i], path + '[%d]' % i)
        elif a != b:
            assert isinstance(a, str), 'Derivative non-string differs at ' + path
            replaced = a
            for token, marker in replacements.items():
                replaced = replaced.replace(token, marker)
            assert replaced == b, 'Derivative has non-token content change at ' + path
            changes.append(path)

    check(original, derived)
    assert replacements and changes, 'No explicit token-only derivation found'
    return changes, len(replacements)


def audit_entries(folder, index, decoded, originals, known_tokens):
    from PIL import Image
    stats = {'index_sha256': sha((folder / 'index.json').read_bytes()),
             'entries': len(index['entries']), 'exact_archives': 0,
             'gzip_archives': 0, 'split_gzip_archives': 0, 'part_hashes_verified': 0,
             'derivatives': [], 'images': 0, 'images_hash_verified': 0}
    assert index['entry_count'] == len(index['entries'])
    for row in index['entries']:
        raw = Path(row['original_raw_path']).read_bytes()
        assert sha(raw) == row['original_raw_sha256'] and len(raw) == row['original_raw_bytes'], 'Original hash/length differs'
        parts = []
        for part in row['derived_parts']:
            content = (folder / part['path']).read_bytes()
            assert sha(content) == part['sha256'] and len(content) == part['bytes'], 'Derived part hash/length differs: ' + part['path']
            parts.append(content)
            stats['part_hashes_verified'] += 1
        packed = b''.join(parts)
        rel = row['derived_parts'][0]['path']
        if row['encoding'] == 'jpeg':
            assert row['lossy_visual_reference'] and not row['original_bytes_reconstructable']
            with Image.open(io.BytesIO(raw)) as image:
                raw_size = image.size
                image.verify()
            with Image.open(io.BytesIO(packed)) as image:
                assert image.format == 'JPEG' and image.size == raw_size == tuple(row['full_resolution'])
                image.verify()
            stats['images'] += 1
            stats['images_hash_verified'] += 1
            continue
        content = gzip.decompress(packed) if row['encoding'] in ('gzip', 'gzip-split') else packed
        stats['gzip_archives'] += int(row['encoding'] in ('gzip', 'gzip-split'))
        stats['split_gzip_archives'] += int(row['encoding'] == 'gzip-split')
        assert sha(content) == row['decoded_sanitized_sha256'] and len(content) == row['decoded_sanitized_bytes'], 'Decoded SHA/length differs: ' + rel
        decoded[rel], originals[rel] = content, raw
        value = parse(raw)
        if value is not None:
            known_tokens.update(token for token in token_leaves(value).values() if live(token))
        if row['original_bytes_reconstructable']:
            assert content == raw and row['redaction_occurrences'] == 0
            stats['exact_archives'] += 1
        else:
            assert row['redaction_occurrences'] > 0 and row['redacted_fields']
            changes, mappings = derivative_changes(json.loads(raw), json.loads(content))
            stats['derivatives'].append({'path': rel, 'original_raw_sha256': sha(raw),
                'decoded_derivative_sha256': sha(content), 'changed_string_fields': changes,
                'known_token_mappings': mappings, 'only_known_token_substitution': True})
    return stats


def main():
    expected = dict(arg.split('=', 1) for arg in sys.argv[1:])
    names = tuple(expected) or NAMES
    issues, known_tokens, decoded, originals, snapshots = [], set(), {}, {}, {}
    report = {'schema_version': 1, 'reviewer': '/root/integration_resume',
              'started_at_utc': datetime.now(timezone.utc).isoformat(), 'packs': {},
              'issues': issues, 'read_only': True, 'manual_issues_closed': 0,
              'scope': 'Indexes, every indexed original/archive/image hash, token-only derivations and credential residue. No MC/RPC/source rescan/visual acceptance.'}
    for name in names:
        folder = ROOT / 'docs/evidence' / name
        snapshots[name] = {p.relative_to(folder).as_posix(): sha(p.read_bytes())
                           for p in folder.rglob('*') if p.is_file()}
        index_blob = (folder / 'index.json').read_bytes()
        index = json.loads(index_blob)
        assert name not in expected or sha(index_blob) == expected[name], 'Producer index SHA differs: ' + name
        if 'entries' in index:
            decoded[name], originals[name] = {}, {}
            report['packs'][name] = audit_entries(folder, index, decoded[name], originals[name], known_tokens)
            continue
        stats = {'index_sha256': sha(index_blob), 'records': len(index['records']),
                 'exact_archives': 0, 'gzip_archives': 0, 'derivatives': [],
                 'images': len(index.get('images', [])), 'images_hash_verified': 0}
        decoded[name], originals[name] = {}, {}
        for row in index['records']:
            rel = row.get('archived', row.get('archive'))
            archive = folder / rel
            packed = archive.read_bytes()
            content = gzip.decompress(packed) if archive.suffix == '.gz' else packed
            stats['gzip_archives'] += int(archive.suffix == '.gz')
            decoded[name][rel] = content
            if 'archive_sha256' in row:
                assert sha(packed) == row['archive_sha256'], 'Archive hash differs: ' + rel
            if 'archive_bytes' in row:
                assert len(packed) == row['archive_bytes'], 'Archive length differs: ' + rel
            raw = (ROOT / row['raw']).read_bytes()
            raw_sha = row.get('sha256', row.get('raw_sha256'))
            raw_bytes = row.get('bytes', row.get('raw_bytes'))
            assert sha(raw) == raw_sha and len(raw) == raw_bytes, 'Original hash/length differs: ' + row['raw']
            originals[name][rel] = raw
            value = parse(raw)
            if value is not None:
                known_tokens.update(value for value in token_leaves(value).values() if live(value))
            if row.get('archive_decodes_to_original_raw') is False:
                assert content != raw and (row.get('redacted_fields') or row.get('credential_redacted_derived_archive')), 'Invalid derivative declaration: ' + rel
                assert sha(content) == row['archive_decoded_sha256'], 'Decoded derivative SHA differs: ' + rel
                changes, mappings = derivative_changes(json.loads(raw), json.loads(content))
                stats['derivatives'].append({'path': rel, 'original_raw_sha256': sha(raw),
                    'archive_sha256': sha(packed), 'decoded_derivative_sha256': sha(content),
                    'changed_string_fields': changes, 'known_token_mappings': mappings,
                    'only_known_token_substitution': True})
            else:
                assert content == raw and sha(content) == raw_sha, 'Exact archived bytes differ: ' + rel
                stats['exact_archives'] += 1
        for row in index.get('images', []):
            raw = (ROOT / row['raw']).read_bytes()
            assert sha(raw) == row['raw_sha256'], 'Raw image hash differs: ' + row['raw']
            rel = row.get('review_jpeg', row.get('archived'))
            packed = (folder / rel).read_bytes()
            assert sha(packed) == row.get('review_sha256', row.get('archive_sha256')), 'Review image hash differs: ' + rel
            if 'bytes' in row:
                assert len(packed) == row['bytes'], 'Review image size differs: ' + rel
            stats['images_hash_verified'] += 1
        if 'summary_sha256' in index:
            assert sha((folder / 'summary.json').read_bytes()) == index['summary_sha256'], 'Summary SHA differs: ' + name
        local_trees = index.get('local_only_ui_trees', [])
        for row in local_trees:
            blob = (ROOT / row['raw']).read_bytes()
            assert sha(blob) == row['raw_sha256'] and len(blob) == row['raw_bytes'], 'Local-only raw SHA/length differs: ' + row['raw']
            assert row['local_only'] and row['not_archived_reason']
        stats['local_only_raw_ui_trees_hash_verified'] = len(local_trees)
        report['packs'][name] = stats
    token_hits, field_hits, pattern_hits = [], [], []
    patterns = (rb'\bsk-[A-Za-z0-9_-]{20,}', rb'\bBearer\s+[A-Za-z0-9._~-]{20,}',
                rb'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}')
    for name in names:
        folder = ROOT / 'docs/evidence' / name
        contents = {p.relative_to(folder).as_posix(): p.read_bytes()
                    for p in folder.rglob('*') if p.is_file() and p.suffix.lower() not in ('.jpg', '.jpeg', '.png')}
        contents.update({rel + ' [decoded]': blob for rel, blob in decoded[name].items()})
        for path, blob in contents.items():
            if any(value.encode('utf8') in blob for value in known_tokens):
                token_hits.append({'pack': name, 'path': path})
            value = parse(blob)
            if value is not None:
                count = sum(live(token) for token in token_leaves(value).values())
                if count:
                    field_hits.append({'pack': name, 'path': path, 'count': count})
            count = sum(len(re.findall(pattern, blob)) for pattern in patterns)
            if count:
                pattern_hits.append({'pack': name, 'path': path, 'count': count})
        after = {p.relative_to(folder).as_posix(): sha(p.read_bytes())
                 for p in folder.rglob('*') if p.is_file()}
        report['packs'][name]['unchanged_during_review'] = after == snapshots[name]
        assert after == snapshots[name], 'Evidence package changed during review: ' + name
    report['token_scan'] = {'known_raw_value_count': len(known_tokens), 'token_contents_output': False,
                            'known_token_hits': token_hits, 'structured_live_field_hits': field_hits,
                            'common_credential_pattern_hits': pattern_hits}
    if token_hits or field_hits or pattern_hits:
        issues.append('Potential credential residue; see path-only findings')
    report['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
    report['passed'] = not issues
    output_name = 'archive-review.json' if len(names) > 1 else names[0] + '.archive-review.json'
    (OUT / output_name).write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
