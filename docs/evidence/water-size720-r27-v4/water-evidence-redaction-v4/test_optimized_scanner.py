"""Synthetic equivalence controls; no local credential values are emitted."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    optimized = module('optimized', HERE / 'package_v4_optimized.py')
    original = module('original', ROOT / '.runtime/round-20261022/root_review_wire_bundle_v3.py')
    credentials = {'alpha-synthetic-credential-12345', 'prefix', 'prefix-long-value', '测试凭据-value'}
    optimized.SECRET_PATTERN = optimized.compile_secret_pattern(credentials)
    exact = tuple(value.encode('utf8') for value in credentials)
    primary = 'alpha-synthetic-credential-12345'
    sources = [
        ('direct', primary.encode()),
        ('dict', json.dumps({'unrelated': primary}).encode()),
        ('list', json.dumps([primary, 17, None]).encode()),
        ('nested_json', json.dumps({'stdout': json.dumps({'unrelated': primary})}).encode()),
        ('base64', json.dumps({'payload': base64.b64encode(primary.encode()).decode()}).encode()),
        ('escaped_unicode', ('log:' + ''.join('\\u%04x' % ord(char) for char in primary)).encode()),
        ('escaped_hex', ('log:' + ''.join('\\x%02x' % ord(char) for char in primary)).encode()),
        ('sensitive_key', b'{"token":"synthetic-member-value"}'),
        ('old_placeholder', b'{"token":"[REDACTED_SESSION_TOKEN]"}'),
        ('sensitive_url', b'{"mcp_url":"http://localhost/private"}'),
        ('prefix_overlap', b'xx-prefix-long-value-xx'),
        ('unicode', json.dumps({'unrelated': '测试凭据-value'}).encode()),
        ('credential_pattern', ('sk-' + 'X' * 32).encode()),
    ]
    rows = []
    for label, raw in sources:
        expected = original.credentials(raw, exact)
        actual = optimized.combined_credentials(original, raw)
        assert actual == expected, label
        assert expected, label
        clean, fields = optimized.sanitize_raw(raw)
        assert fields and not original.credentials(clean, exact), label
        assert not optimized.combined_credentials(original, clean), label
        rows.append({'control': label, 'original_detected': True, 'optimized_detected': True, 'sanitized_passed': True})
    negatives = [
        b'{"sha256":"' + b'a' * 64 + b'","record_count":72}',
        b'{"token":"[REDACTED]","mcp_url":null}',
        b'No credential here; preserve quoted text \\" and x=72.',
    ]
    for ordinal, raw in enumerate(negatives, 1):
        assert not original.credentials(raw, exact)
        assert not optimized.combined_credentials(original, raw)
        assert optimized.sanitize_raw(raw)[0] == raw
        rows.append({'control': 'negative_%d' % ordinal, 'unchanged': True})
    report = {'passed': True, 'positive_controls': len(sources), 'negative_controls': len(negatives),
              'root_scanner_original_sha256': hashlib.sha256((ROOT / '.runtime/round-20261022/root_review_wire_bundle_v3.py').read_bytes()).hexdigest(),
              'no_local_credentials_emitted': True, 'rows': rows}
    output = (json.dumps(report, indent=2) + '\n').encode()
    (HERE / 'optimized-scanner-controls-v1.json').write_bytes(output)
    print(json.dumps({'passed': True, 'positive_controls': len(sources), 'negative_controls': len(negatives),
                      'report_sha256': hashlib.sha256(output).hexdigest()}))


if __name__ == '__main__':
    main()
