"""Repackage original immutable inputs with standard, recursive redaction."""
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
from PIL import Image

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
OLD = ROOT / 'docs/evidence/water-size720-r27-v3'
OUT = ROOT / 'docs/evidence/water-size720-r27-v4'
LIMIT = 240000
KEYS = {'token', 'api_key', 'apikey', 'authorization', 'mcp_url', 'secret',
        'access_token', 'refresh_token'}
PLACEHOLDERS = {'[REDACTED]', '[REDACTED_SESSION_TOKEN]'}
PATTERN = re.compile(r'\bsk-[A-Za-z0-9_-]{20,}|\bBearer\s+[A-Za-z0-9._-]{16,}')
secrets = set()
SECRET_PATTERN = None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sensitive(key):
    key = key.lower()
    return key in KEYS or ('token' in key and not key.endswith('sha256'))


def nested(text):
    try:
        return json.loads(text), 'json'
    except ValueError:
        if len(text) >= 32 and len(text) % 4 == 0 and re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', text):
            try:
                return base64.b64decode(text, validate=True).decode('utf8'), 'base64'
            except (ValueError, UnicodeError):
                return None, None
    return None, None


def discover(value, depth=0):
    assert depth < 48
    if isinstance(value, dict):
        for key, child in value.items():
            if sensitive(key) and isinstance(child, str) and child and child not in PLACEHOLDERS:
                secrets.add(child)
            else:
                discover(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            discover(child, depth + 1)
    elif isinstance(value, str):
        inner, kind = nested(value)
        if kind and inner != value:
            discover(inner, depth + 1)


def sanitize(value, found, location='$', depth=0):
    assert depth < 48
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            label = location + '.' + key
            if sensitive(key) and child not in (None, '', '[REDACTED]'):
                result[key] = '[REDACTED]'
                found.append(label)
            else:
                result[key] = sanitize(child, found, label, depth + 1)
        return result
    if isinstance(value, list):
        return [sanitize(child, found, location + '[%d]' % i, depth + 1)
                for i, child in enumerate(value)]
    if isinstance(value, str):
        inner, kind = nested(value)
        if kind and inner != value:
            revised = sanitize(inner, found, location + ':' + kind, depth + 1)
            if revised != inner:
                value = (base64.b64encode(revised.encode('utf8')).decode('ascii')
                         if kind == 'base64' else json.dumps(revised, ensure_ascii=False))
        if SECRET_PATTERN.search(value):
            found.append(location + ':exact')
            value = SECRET_PATTERN.sub('[REDACTED]', value)
        if PATTERN.search(value):
            found.append(location + ':credential_pattern')
            value = PATTERN.sub('[REDACTED]', value)
        unescaped = unescape(value)
        if unescaped != value:
            revised = sanitize(unescaped, found, location + ':unescaped', depth + 1)
            if revised != unescaped:
                value = revised
    return value


def sanitize_raw(raw):
    text = raw.decode('utf-8-sig')
    found = []
    revised = sanitize(text, found)
    return (raw if revised == text else revised.encode('utf8')), found



def unescape(value):
    value = re.sub(r'\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})',
                   lambda match: chr(int(match[1] or match[2], 16)), value)
    return value.replace('\\"', '"').replace("\\'", "'")


def compile_secret_pattern(values):
    """Exact match using a prefix trie, without repeatedly sorting 972 registries."""
    trie = {}
    for value in values:
        for variant in {value, json.dumps(value, ensure_ascii=True)[1:-1]}:
            node = trie
            for char in variant:
                node = node.setdefault(char, {})
            node[None] = True

    def expression(node):
        parts = [re.escape(char) + expression(child)
                 for char, child in sorted(node.items(), key=lambda row: row[0] or '')
                 if char is not None]
        result = parts[0] if len(parts) == 1 else '(?:' + '|'.join(parts) + ')'
        if None in node:
            return '(?:' + result + ')?' if parts else ''
        return result

    return re.compile(expression(trie) if values else r'(?!)')


def exact_credentials(raw):
    """Same decoded JSON/base64/escape views as root scanner; exact checks batched."""
    seen = set()
    found = False

    def visit(data, depth=0):
        nonlocal found
        assert depth < 48
        fingerprint = sha(data)
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        text = data.decode('utf8')
        if SECRET_PATTERN.search(text):
            found = True
        try:
            value = json.loads(text)
        except ValueError:
            value = None
        if isinstance(value, (dict, list)):
            walk(value, depth + 1)
        if len(text) >= 32 and len(text) % 4 == 0 and re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', text):
            try:
                visit(base64.b64decode(text, validate=True), depth + 1)
            except UnicodeDecodeError:
                pass
        revised = unescape(text)
        if revised != text:
            visit(revised.encode('utf8'), depth + 1)

    def walk(value, depth):
        assert depth < 48
        if isinstance(value, dict):
            for item in value.values():
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)
        elif isinstance(value, str):
            visit(value.encode('utf8'), depth + 1)

    visit(raw)
    return ['exact local credential'] if found else []


def combined_credentials(scanner, raw):
    # Original independent scanner remains unchanged for JSON/pattern/escape checks.
    # The exact credential comparison is performed over the same decoded views
    # with a compiled prefix trie rather than N membership loops per JSON leaf.
    return sorted(set(scanner.credentials(raw) + exact_credentials(raw)))


def main():
    global SECRET_PATTERN
    assert not OUT.exists(), 'Preserve v3 and every prior package'
    indexraw = (OLD / 'index.json').read_bytes()
    assert sha(indexraw) == '410c9b5f71853e02ec0c23b67f38ed02168aa013c8ee03066ca87daa31ca265f'
    index = json.loads(indexraw)
    original_rows = []
    for page in index['entry_pages']:
        raw = (OLD / page['path']).read_bytes()
        assert sha(raw) == page['sha256']
        original_rows.extend(json.loads(raw)['entries'])
    inputs = {row['logical_name']: Path(row['original_raw_path']) for row in original_rows}
    for row in original_rows:
        assert sha(inputs[row['logical_name']].read_bytes()) == row['original_raw_sha256']
    # Include the small, EOL-preserving production proposal and this correction.
    proposal = WORK.with_name('water-gui-offset-merge-proposal-v2')
    for path in proposal.rglob('*'):
        if path.is_file() and path.suffix in ('.py', '.patch', '.json'):
            inputs[proposal.name + '/' + path.relative_to(proposal).as_posix()] = path
    for script in ('package_v4.py', 'package_v4_optimized.py', 'optimize_v4.py', 'aborted-slow-preflight.json', 'test_optimized_scanner.py', 'optimized-scanner-controls-v1.json'):
        inputs[WORK.name + '/' + script] = WORK / script
    next_a = WORK.with_name('water-next-A-workflow-v1')
    for path in next_a.iterdir():
        if path.is_file():
            inputs[next_a.name + '/' + path.name] = path
    for path in inputs.values():
        if path.suffix == '.json':
            discover(json.loads(path.read_bytes()))
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        discover(json.loads(path.read_bytes()))
    spec = importlib.util.spec_from_file_location('root_credential_scanner',
        ROOT / '.runtime/round-20261022/root_review_wire_bundle_v3.py')
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    SECRET_PATTERN = compile_secret_pattern(secrets)
    print(json.dumps({'phase': 'preflight', 'inputs': len(inputs), 'credential_values': len(secrets)}), flush=True)
    fixtures = [
        json.dumps({'stdout': json.dumps({'token': 'synthetic-token-value'})}).encode(),
        json.dumps({'payload': base64.b64encode(json.dumps({'mcp_url': 'http://localhost/private'}).encode()).decode()}).encode(),
        ('"' + ''.join('\\u%04x' % ord(c) for c in 'sk-' + 'X' * 32) + '"').encode(),
    ]
    for raw in fixtures:
        assert scanner.credentials(raw)
        clean, unused = sanitize_raw(raw)
        assert not combined_credentials(scanner, clean)
    negative = b'{"sha256":"' + b'a' * 64 + b'","record_count":72}'
    assert sanitize_raw(negative)[0] == negative
    sanitized = {}
    for ordinal, (label, path) in enumerate(inputs.items(), 1):
        if ordinal % 25 == 0:
            print(json.dumps({'phase': 'preflight', 'checked': ordinal}), flush=True)
        if path.suffix == '.png':
            continue
        clean, found = sanitize_raw(path.read_bytes())
        findings = combined_credentials(scanner, clean)
        assert not findings, (label, findings)
        sanitized[label] = clean, found
    OUT.mkdir(parents=True)
    entries = []
    for label, path in sorted(inputs.items()):
        raw = path.read_bytes()
        entry = {'logical_name': label, 'original_raw_path': str(path.resolve()),
                 'original_raw_sha256': sha(raw), 'original_raw_bytes': len(raw)}
        destination = OUT / label
        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == '.png':
            encoded, encoding = raw, 'png'
            entry['original_bytes_reconstructable'] = True
            if len(encoded) > LIMIT:
                source = Image.open(io.BytesIO(raw)).convert('RGB')
                for quality in range(95, 44, -5):
                    memory = io.BytesIO()
                    source.save(memory, 'JPEG', quality=quality, optimize=True, subsampling=0)
                    encoded = memory.getvalue()
                    if len(encoded) < LIMIT:
                        break
                assert len(encoded) < LIMIT
                destination = destination.with_suffix('.jpg')
                encoding = 'jpeg'
                entry.update(original_bytes_reconstructable=False, lossy_visual_reference=True,
                             jpeg_quality=quality, full_resolution=list(source.size))
        else:
            clean, found = sanitized[label]
            encoded, encoding = (gzip.compress(clean, mtime=0), 'gzip') if len(clean) > 100000 else (clean, 'utf8')
            if encoding == 'gzip':
                destination = Path(str(destination) + '.gz')
            entry.update(decoded_sanitized_sha256=sha(clean), decoded_sanitized_bytes=len(clean),
                         redacted_fields=found, redaction_occurrences=len(found),
                         original_bytes_reconstructable=clean == raw)
        entry['encoding'] = encoding
        pieces = [encoded[i:i + LIMIT] for i in range(0, len(encoded), LIMIT)] or [b'']
        parts = []
        for i, piece in enumerate(pieces):
            target = Path(str(destination) + ('.%03d' % (i + 1) if len(pieces) > 1 else ''))
            target.write_bytes(piece)
            parts.append({'path': target.relative_to(OUT).as_posix(), 'bytes': len(piece), 'sha256': sha(piece)})
        entry['derived_parts'] = parts
        entries.append(entry)
    pages = []
    for i, offset in enumerate(range(0, len(entries), 75), 1):
        rows = entries[offset:offset + 75]
        raw = (json.dumps({'schema': 1, 'entries': rows}, indent=2) + '\n').encode()
        assert len(raw) < LIMIT
        path = OUT / ('entries-%03d.json' % i)
        path.write_bytes(raw)
        pages.append({'path': path.name, 'sha256': sha(raw), 'bytes': len(raw), 'entries': len(rows)})
    output_index = dict(index, schema=3, created_at_utc=datetime.now(timezone.utc).isoformat(),
        entry_count=len(entries), entry_pages=pages,
        replaces_distribution_of_v3={'path': str((OLD / 'index.json').resolve()), 'sha256': sha(indexraw)},
        redaction_policy='[REDACTED] for sensitive JSON members including loopback mcp_url, recursive JSON/base64 and exact raw credentials in text',
        secret_values_discovered=len(secrets), independent_scanner_findings=0,
        redaction_positive_controls=3, redaction_negative_controls=1,
        original_v3_preserved=True, original_raws_modified=False,
        scanner_exact_optimization='prefix-trie over the same JSON/base64/unescape decoded views; root original scanner unchanged for other checks')
    raw = (json.dumps(output_index, indent=2) + '\n').encode()
    (OUT / 'index.json').write_bytes(raw)
    assert sha((OLD / 'index.json').read_bytes()) == sha(indexraw)
    sizes = [p.stat().st_size for p in OUT.rglob('*') if p.is_file()]
    assert max(sizes) <= LIMIT
    print(json.dumps({'index_sha256': sha(raw), 'entries': len(entries),
                      'largest_file_bytes': max(sizes), 'total_bytes': sum(sizes),
                      'credential_findings': 0, 'old_v3_preserved': True}))


if __name__ == '__main__':
    main()
