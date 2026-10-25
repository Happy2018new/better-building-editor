# -*- coding: utf-8 -*-
"""Freeze the 17 existing small layout originals; never import the product."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / '.runtime/lib-layout-callers-r29-v1'
CUTOVER = ROOT / 'docs/verification/LIBRARY_CUTOVER_R29.md'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8')


def compressed(raw):
    target = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', compresslevel=9, fileobj=target, mtime=0) as output:
        output.write(raw)
    return target.getvalue()


def write(name, raw):
    target = HERE / name
    assert not target.exists(), target
    target.write_bytes(raw)


assert {path.name for path in HERE.iterdir()} == {'pack.py'}
originals = {path.name: path.read_bytes() for path in sorted(SOURCE.iterdir()) if path.is_file()}
assert len(originals) == 17 and len(list(SOURCE.iterdir())) == 17
for index_name in ('archive-index.json', 'archive-index-v2.json'):
    for row in json.loads(originals[index_name])['files']:
        raw = originals[row['path']]
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
summary = json.loads(originals['summary-v2.json'])
assert summary['passed'] and summary['four_way_complete_outputs_equal']
assert summary['case_count_per_mode_per_interpreter'] == 33
assert summary['actual_vendor_calls_per_candidate_interpreter']['context_position'] == 18
for name, row in summary['final_receipts'].items():
    assert sha(originals[name]) == row['sha256'] and len(originals[name]) == row['bytes']
    assert json.loads(originals[name])['driver']['sha256'] == sha(originals['verify.py'])
assert summary['import_scope_metadata_correction']['sha256'] == sha(originals['import-scope-correction.json'])

objects, references = {}, []
for name, raw in sorted(originals.items()):
    raw_sha = sha(raw)
    storage = compressed(raw)
    assert storage == compressed(raw) and gzip.decompress(storage) == raw
    if raw_sha not in objects:
        filename = raw_sha + '.gz'
        write(filename, storage)
        objects[raw_sha] = {'file': filename, 'raw_bytes': len(raw),
                            'stored_bytes': len(storage), 'stored_sha256': sha(storage)}
    references.append({'path': name, 'raw_sha256': raw_sha, 'raw_bytes': len(raw),
                       'object': objects[raw_sha]['file']})

index = {'schema': 1, 'description': 'Final fixed-source actual layout caller CPU controls and preserved preparation history',
    'source_commit': summary['fixed_candidate_source_commit'], 'source_directory': SOURCE.as_posix(),
    'logical_files': len(references), 'objects': objects, 'references': references,
    'raw_logical_bytes': sum(len(raw) for raw in originals.values()),
    'raw_unique_bytes': sum(row['raw_bytes'] for row in objects.values()),
    'stored_bytes': sum(row['stored_bytes'] for row in objects.values()),
    'gzip': {'filename': '', 'mtime': 0, 'compression_level': 9},
    'authoritative_summary': 'summary-v2.json', 'raw_receipt_scope_erratum': 'import-scope-correction.json',
    'case_count_per_mode_per_interpreter': 33, 'normal_cases': 22, 'rejection_cases': 11,
    'four_way_complete_outputs_equal': True, 'candidate_context_position_profiled_calls_per_interpreter': 18,
    'other_eight_layout_functions_profiled_calls': 0, 'project_copied': False,
    'MC_started': False, 'native_qualification_granted': False, 'manual_issues_closed': 0}
write('index.json', encode(index))
readme = '''# R29：固定源布局 caller 的最小双解释器验证

绑定 `{commit}` 的固定私有候选。真实 Python 2.7.13／3.13.13 分别执行宿主与候选，四路各 **33 条：22 正常＋11 拒绝**，完整输出完全一致。候选每个解释器在受测入口记录 vendor **context_position 18 次**，唯一现场为 render_context.py:257 的 prepare_context_palette。其余 8 个布局函数实际计数为 0；9 个 adapter 导出仅核对了 vendor 同一函数对象，不能称 9 函数都经过 caller。

四个实际 caller 分别验证：geometry_palette 的雪／蕨叠加带与高度常量；render_context 的完整调色板函数调用、Document builder 与局部分块常量编码；preview_depth 的真实函数内布局常量导入及深度／裁剪编码；spawner_marker 的最大高度和分离叠加带。包含高度 127／128 及 129 拒绝、X=15／16 分块边界、可见层、越界目标与负世界 render_origin。负世界原点不等于负逻辑调色板位置；当前空的位置敏感植物 profile 不证明随机偏移行为。刷怪笼仅使用显式候选 profile。

权威摘要为 summary-v2.json，四份 final-* 回执包含完整输出、真实模块路径／SHA、实际函数身份、profile 计数和执行行。候选每个解释器实际载入 60 个模块、宿主 57 个；只读源码 loader 在 compile 前验证冻结 SHA，不读取已有 pyc。732 文件候选全树前后保护通过。sys.setprofile 对生成器的 call 事件包含恢复执行；两次真实上下文准备只作输出参照，未纳入受测入口的 18 次计数。没有 SDK 导入或 stub，没有 MC／RPC／GPU 或世界访问。

preparation-history.json 保留主源 Py2 旧字节码被严格守卫拒绝、可见层 fixture 和私有 loader 准备错误；旧缓存未删除或更改。早期成功回执与对应驱动也保留。原始回执的 module_level_import_before_profile 曾用行号启发式误标 preview_depth，import-scope-correction.json 以 AST 确认其为函数内导入；原始回执、计数和输出均未改写，不为元数据勘误重跑控制。

[index.json](index.json) 保存全部 {logical} 份小原件（含原 archive-index 和 archive-index-v2），映射为 {objects} 个确定性 gzip 对象。逻辑原文 {raw_bytes:,}B，存储 {stored_bytes:,}B，最大对象 {maximum:,}B；不复制 project。对象文件名为 raw SHA，索引列出 raw 与 storage SHA／长度；filename 为空、mtime=0、level=9。按 references.path 恢复原名，核对 raw SHA。两份原索引、四份最终回执／驱动绑定和摘要勘误绑定已再次校验。pack.py 仅封装／核验字节，不重复 33 条、既有 115 条或 66,249 网格。

局部凭据扫描及新进程解压／重压校验见 [verification.json](verification.json)。扫描覆盖原件、JSON 解码字符串、新目录元数据和[切换前检查](../../verification/LIBRARY_CUTOVER_R29.md)。这是指定 CPU caller 缺口的证据；其余 8 函数的旧网格是历史对等控制，当前完整组合全量另见[独立证据](../library-full-current-r29-v1/README.md)。最终发布包冻结、冷启动与编辑器／完整投影／缺失投影的原生资格仍待，人工关闭 0。
'''.format(commit=index['source_commit'], logical=len(references), objects=len(objects),
           raw_bytes=index['raw_logical_bytes'], stored_bytes=index['stored_bytes'],
           maximum=max(row['stored_bytes'] for row in objects.values()))
write('README.md', readme.encode('utf-8'))

patterns = {'api_token': re.compile(r'\bsk-[A-Za-z0-9_-]{20,}'),
            'github_token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,})'),
            'bearer_token': re.compile(r'(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}'),
            'private_key': re.compile(r'-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----')}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(key)
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


scan_inputs = dict(originals)
for path in HERE.iterdir():
    if path.is_file() and path.suffix != '.gz':
        scan_inputs['package/' + path.name] = path.read_bytes()
scan_inputs['document/LIBRARY_CUTOVER_R29.md'] = CUTOVER.read_bytes()
scan_rows, hits = [], []
for name, raw in sorted(scan_inputs.items()):
    text = raw.decode('utf-8', 'replace')
    values = [text]
    try:
        values.extend(strings(json.loads(raw)))
    except (ValueError, UnicodeError):
        pass
    for kind, expression in patterns.items():
        if any(expression.search(value) for value in values):
            hits.append({'input': name, 'kind': kind})
    scan_rows.append({'input': name, 'bytes': len(raw), 'sha256': sha(raw)})
assert not hits, hits
write('credential-scan.json', encode({'passed': True, 'scope': '17 originals, decoded JSON strings, package metadata and changed cutover document only',
    'patterns': sorted(patterns), 'inputs': scan_rows, 'matches': 0, 'system_or_other_conversation_scan': False}))
for name, raw in originals.items():
    assert (SOURCE / name).read_bytes() == raw
assert {path.name for path in SOURCE.iterdir()} == set(originals)
print(json.dumps({'passed': True, 'logical_files': len(references), 'objects': len(objects),
    'raw_bytes': index['raw_logical_bytes'], 'stored_bytes': index['stored_bytes'],
    'largest_object': max(row['stored_bytes'] for row in objects.values()), 'credential_matches': 0}, sort_keys=True))
