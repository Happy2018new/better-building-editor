"""Build a small, source-preserving offline review bundle; never touch product files."""
from __future__ import annotations

import ast
import base64
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'review-bundle-v3-complete'
PART = 250000


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def credential_scan(raw, known=()):
    """Inspect raw bytes, parsed nested JSON, escaped strings and base64 members."""
    findings = set()
    seen = set()
    stats = {'views': 0, 'nested_json': 0, 'base64': 0, 'escaped': 0}
    credential = re.compile(r'(?i)(?:api[_-]?key|access[_-]?token|authorization|token)[\s\"\x27:=\\]+(?:bearer\s+)?([A-Za-z0-9_./+\-=]{16,})')
    key = re.compile(r'(?i)\bsk-[A-Za-z0-9_-]{20,}\b|\bBearer\s+[A-Za-z0-9._-]{16,}')
    sensitive = {'token', 'api_key', 'apikey', 'authorization', 'access_token', 'refresh_token'}

    def walk(value, depth):
        if depth > 32:
            raise AssertionError('Credential scanner depth budget exceeded')
        if isinstance(value, dict):
            for name, child in value.items():
                if str(name).lower() in sensitive and isinstance(child, str) and len(child) >= 16 and '[REDACTED]' not in child:
                    findings.add('credential-valued JSON member')
                walk(child, depth + 1)
        elif isinstance(value, (tuple, list)):
            for child in value:
                walk(child, depth + 1)
        elif isinstance(value, str):
            visit(value.encode('utf8'), depth + 1)

    def visit(data, depth):
        fingerprint = digest(data)
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        stats['views'] += 1
        if any(secret and secret in data for secret in known):
            findings.add('known local credential bytes')
        try:
            text = data.decode('utf8')
        except UnicodeDecodeError:
            return
        if key.search(text) or credential.search(text):
            findings.add('credential string pattern')
        try:
            value = json.loads(text)
        except (ValueError, RecursionError):
            value = None
        if value is not None and not (isinstance(value, str) and value == text):
            stats['nested_json'] += 1
            walk(value, depth + 1)
        if re.fullmatch(r'[A-Za-z0-9+/]{32,}={0,2}', text) and len(text) % 4 == 0:
            try:
                decoded = base64.b64decode(text, validate=True)
            except ValueError:
                pass
            else:
                stats['base64'] += 1
                visit(decoded, depth + 1)
        if '\\u' in text or '\\"' in text or '\\x' in text:
            unescaped = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), text)
            unescaped = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), unescaped)
            unescaped = unescaped.replace('\\"', '"').replace("\\'", "'")
            if unescaped != text:
                stats['escaped'] += 1
                visit(unescaped.encode('utf8'), depth + 1)

    visit(raw, 0)
    return sorted(findings), stats


def main():
    assert not OUT.exists(), 'Bundle output must be new'
    known = []
    registry = Path.home() / '.pyreact-debug/instances'
    for path in registry.glob('*/session.json'):
        value = json.loads(path.read_bytes()).get('token')
        if isinstance(value, str) and len(value) >= 16:
            known.append(value.encode('utf8'))
    # Positive controls prove nested JSON, base64, and escaped matching.
    synthetic = 'sk-' + 'Q' * 32
    controls = [json.dumps({'payload': json.dumps({'api_key': synthetic})}).encode(),
                json.dumps({'payload': base64.b64encode(json.dumps({'token': synthetic}).encode()).decode()}).encode(),
                ('{"payload":"' + ''.join('\\u%04x' % ord(c) for c in synthetic) + '"}').encode()]
    assert all(credential_scan(raw)[0] for raw in controls)
    assert not credential_scan(b'{"record_count":72,"sha256":"' + b'a' * 64 + b'"}')[0]
    OUT.mkdir()
    rows = []
    scans = []

    def add(name, raw, original=None, derived_from=(), transform='none'):
        findings, stats = credential_scan(raw, known)
        scans.append({'object': name, 'findings': findings, 'stats': stats})
        assert not findings, 'Credential finding in ' + name
        # Compress textual evidence losslessly; retain PNG byte streams verbatim.
        encoding = 'gzip' if len(raw) >= PART and not name.endswith('.png') else 'identity'
        stored = gzip.compress(raw, compresslevel=9, mtime=0) if encoding == 'gzip' else raw
        suffix = '.gz' if encoding == 'gzip' else ''
        chunks = []
        for index, offset in enumerate(range(0, max(len(stored), 1), PART), 1):
            part_name = name + suffix + ('.part%03d' % index if len(stored) > PART else '')
            path = OUT / part_name
            path.parent.mkdir(parents=True, exist_ok=True)
            chunk = stored[offset:offset + PART]
            path.write_bytes(chunk)
            assert len(chunk) < 300000
            chunks.append({'path': part_name, 'bytes': len(chunk), 'sha256': digest(chunk)})
        rows.append({'object': name, 'original_source': original,
                     'original_sha256': digest(raw) if original else None,
                     'derived_from': list(derived_from), 'content_transform': transform,
                     'content_sha256': digest(raw), 'content_bytes': len(raw),
                     'redacted': transform == 'redacted', 'encoding': encoding,
                     'parts': chunks})

    def source(path, name=None):
        path = path.resolve()
        relative = path.relative_to(ROOT).as_posix()
        add(name or path.relative_to(HERE).as_posix(), path.read_bytes(), relative)

    flat = HERE / 'flat-interior-actual-v3'
    for name in ('report.json', 'gate.json', 'observer-retirement.json',
                 'rpc-0198-result.json'):
        source(flat / name, 'flat/' + name)
    for path in sorted(flat.glob('phase-*-native.json')):
        source(path, 'flat/' + path.name)
    image_names = [
        'report_opaque_top_base_shown_native.png',
        'report_opaque_top_candidate_shown_native.png',
        'report_opaque_grazing_base_shown_native.png',
        'report_opaque_grazing_candidate_shown_native.png',
        'report_default_top_base_shown_native.png',
        'report_default_top_candidate_shown_native.png',
    ]
    for name in image_names:
        source(flat / name, 'flat/images/' + name)
        source(flat / name.replace('.png', '.capture.json'), 'flat/images/' + name.replace('.png', '.capture.json'))
    for pose in ('top', 'grazing'):
        for mode in ('base', 'candidate'):
            for kind in ('mask', 'roi'):
                name = 'opaque_%s_%s_wire-%s.png' % (pose, mode, kind)
                source(flat / name, 'flat/pixel-checks/' + name)
    boundary = HERE / 'flat-boundary-actual-v3'
    for name in ('report.json', 'gate.json', 'rpc-0016-result.json',
                 'rpc-0018-result.json', 'rpc-0019-result.json', 'rpc-0020.py'):
        source(boundary / name, 'boundary/' + name)
    for name in ('stop.json', 'watcher-stop-v4.json', 'exact-exit.json', 'watch-binding.json'):
        source(HERE / 'launch-v3' / name, 'lifecycle/' + name)
    for name in ('boundary_frame_lower_bound_v3.py', 'boundary-frame-lower-bound-v3.json',
                 'actual-native-deltas-v3-flat.json', 'business-offline-v3.json',
                 'wire_business_regression_v3.py', 'v2-retire-size-evidence.json',
                 'frozen-trial-plan-v3.json', 'frozen-cold-lifecycle-plan-v4.json',
                 'source-binding-v2.json', 'sentinel-review-v3-root.json',
                 'offline-small-retirement-review-v3.json', 'small-retirement-v3.diff',
                 'trial_capture_v3.py', 'observer_client_v3.py', 'trial_payloads_v3.py',
                 'trial_fixtures_v1.py', 'native_receipts_v2.py',
                 'analyze_actual_native_v2.py', 'candidate_trace_v2.py'):
        source(HERE / name, 'inputs/' + name)
    for name in ('report.json',):
        source(HERE / 'flat-interior-actual-v2' / name, 'historical-v2/' + name)
    for name in ('stop.json', 'watcher-stop-v3.json'):
        source(HERE / 'launch-v2' / name, 'historical-v2/' + name)
    source(HERE.parent / 'root-wire-flat-v3-review/report.json', 'root-review/report.json')
    source(HERE.parent / 'root_review_wire_flat_v3.py', 'root-review/review.py')
    baseline = HERE / 'source-base/behavior_pack/modern_projection/projection/render_context.py'
    candidate = HERE / 'candidate-drop-direct-only/render_context.py'
    source(baseline, 'candidate/baseline-render_context.py')
    source(candidate, 'candidate/private-render_context.py')
    diff = ''.join(difflib.unified_diff(baseline.read_text('utf8').splitlines(True),
        candidate.read_text('utf8').splitlines(True), fromfile='baseline/render_context.py',
        tofile='private-candidate/render_context.py'))
    changed = []
    first = ast.parse(baseline.read_bytes()); second = ast.parse(candidate.read_bytes())
    original_defs = {node.name: ast.dump(node) for node in first.body if isinstance(node, ast.FunctionDef)}
    for node in second.body:
        if isinstance(node, ast.FunctionDef) and ast.dump(node) != original_defs[node.name]:
            changed.append(node.name)
    assert changed == ['_mark_floor_support', '_mark_palette_floor_support', '_hidden_neighbor']
    add('candidate/three-helpers.diff', diff.encode('utf8'), derived_from=[digest(baseline.read_bytes()), digest(candidate.read_bytes())], transform='diff')
    summary = {
        'schema': 'wire-r27-review-summary-v3',
        'production_changed': False, 'candidate_promoted': False, 'GPU_qualified': False,
        'manual_closures': 0,
        'flat': {'completed': True, 'restored': True, 'phase_count': 12, 'native_record_count': 72,
                 'root_original_images_reviewed': 6, 'original_images_in_bundle': 6,
                 'all_original_image_hashes_in_root_review': 24},
        'boundary': {'completed': False, 'restored': False, 'exported_phase_count': 0,
                     'image_count': 0, 'failed_rpc_number': 20, 'error': 'IPC JSON request timed out',
                     'actual_native_record_count_known': False, 'inferred_minimum_record_count': 21,
                     'minimum_IPC_JSON_plus_repr_bytes': 48340592},
        'lifecycle': {'ordinary_stop_returncode': 0, 'actual_game_exit': '0xC0000409',
                      'actual_MCDK_exit': '0x00000000', 'actual_watcher_exit': '0x00000001',
                      'genuinely_live_MC_at_cleanup': 0, 'forced_game_or_MCDK_stop': False,
                      'restarted_after_failure': False},
        'cpu_business': {'passed': True, 'positive_cases': 1024, 'negative_cases': 1288,
                         'mixed_cache_documents': 2, 'actual_native_paths_proved': False},
        'candidate': {'changed_helpers': changed, 'added_constant': '_DRY_WIRE',
                      'only_admitted_change': 'Directly lower copied dry concrete context neighbor under dry redstone wire; own targets and both logical layers retained'},
        'historical_v2_failure_retained': True,
        'acceptance_limits': ['Only flat GPU sentinel reviewed; other six fixtures unrun and boundary incomplete',
                              'No native stack attributes either game abnormal exit',
                              'CPU business expectations stay private runtime until promotion'],
    }
    add('summary.json', json.dumps(summary, ensure_ascii=False, indent=2).encode('utf8'), transform='derived summary')
    readme = '''# R27 红石线私有候选审查包

候选尚未晋升，生产代码未写入，人工关闭项为 0。新增 `_DRY_WIRE` 常量与三个 helper 的差异见 candidate/three-helpers.diff。

新 flat：12 阶段、72 条实际原生记录全部导出并恢复。主控已检查六张原始 PNG；本包保存这六张原图的原始字节分片，24 张完整原图的哈希在 root-review/report.json。

boundary：首次整阶段读取 RPC20 超时，阶段导出和截图均为 0，恢复未完成；其余扩展未测。boundary 下界分析由真实 Python 2 和部署 IPC 原函数执行，最少 21 条记录仅文档字段即使 IPC 下界达到 48,340,592 字节。此为源推导下界，实际完整记录数和响应包均未捕获。

同一实例 ordinary stop 返回 0，实际游戏退出 0xC0000409、MCDK 退出 0。专属 watcher 在精确身份核对后单独回收，退出 1。游戏异常退出没有被这份 IPC 容量证据归因。旧 v2 未恢复失败独立保留在 historical-v2。

CPU 私有业务回归：1024 正例、1288 反例、2 混合 cache 文档；不证明 GPU，也不纳入生产测试。所有证据都保留原始哈希，summary 与 diff 明确是派生内容。本包没有对原始证据做脱敏改写；凭据递归扫描为零发现，session/config 与完整项目源不打包。

manifest.json 描述每个对象、原始来源与原始 SHA256、存储编码与分片 SHA256。先按 parts 顺序拼接；encoding 为 gzip 时解压，所得字节必须等于 content_sha256/original_sha256。PNG 分片直接拼接，无重编码。每个存储文件小于 300,000 字节。verify_bundle.py 可独立在内存中核验全部分片与重建对象。
'''
    add('README.md', readme.encode('utf8'), transform='derived explanation')
    source(Path(__file__), 'tools/build_review_bundle_v3.py')
    source(HERE / 'verify_review_bundle_v3.py', 'verify_bundle.py')
    scan_report = {'passed': True, 'findings': [], 'known_secret_values_recorded': False,
                   'positive_controls': 3, 'negative_controls': 1, 'objects': scans.copy(),
                   'checks': ['raw exact credential bytes', 'credential patterns', 'nested JSON strings',
                              'JSON credential members', 'base64 members', 'escaped unicode/hex/quotes']}
    add('credential-scan.json', json.dumps(scan_report, indent=2).encode(), transform='derived scan report')
    manifest = {'schema': 'wire-r27-review-bundle-v3', 'objects': rows,
                'max_stored_file_bytes': max(part['bytes'] for row in rows for part in row['parts']),
                'candidate_promoted': False, 'GPU_qualified': False, 'manual_closures': 0}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
    assert (OUT / 'manifest.json').stat().st_size < 300000
    verified = 0
    for row in rows:
        stored = b''.join((OUT / part['path']).read_bytes() for part in row['parts'])
        raw = gzip.decompress(stored) if row['encoding'] == 'gzip' else stored
        assert len(raw) == row['content_bytes'] and digest(raw) == row['content_sha256']
        if row['original_source']:
            assert raw == (ROOT / row['original_source']).read_bytes()
        assert not credential_scan(raw, known)[0]
        verified += 1
    print(json.dumps({'bundle': str(OUT), 'verified_objects': verified,
                      'stored_files': len(list(OUT.rglob('*'))) - len([p for p in OUT.rglob('*') if p.is_dir()]),
                      'total_bytes': sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),
                      'manifest_sha256': digest((OUT / 'manifest.json').read_bytes()),
                      'credential_scan_passed': True, 'candidate_promoted': False}))


if __name__ == '__main__':
    main()
