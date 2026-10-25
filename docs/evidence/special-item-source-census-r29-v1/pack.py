# -*- coding: utf-8 -*-
"""Archive existing census receipts only; never read installed assets or run tests."""
import gzip
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / '.runtime/special-item-census-r29-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')


def storage(raw):
    target = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0, compresslevel=9) as output:
        output.write(raw)
    return target.getvalue()


def write(name, raw):
    target = HERE / name
    assert not target.exists(), target
    target.write_bytes(raw)


assert {path.name for path in HERE.iterdir()} == {'pack.py'}
originals = {path.name: path.read_bytes() for path in sorted(SOURCE.iterdir()) if path.is_file()}
assert len(originals) == 23
delivery = json.loads(originals['delivery-index.json'])
aliases = []
for name, expected in delivery['files'].items():
    if name.startswith('fixture-root/'):
        raw = originals['special_item_capabilities_nemc_3.10.0.420447.json']
        assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256']
        aliases.append({'declared_path': name, 'raw_sha256': expected['sha256'], 'raw_bytes': expected['bytes'],
            'equivalent_archived_reference': 'special_item_capabilities_nemc_3.10.0.420447.json',
            'fixture_subtree_read_or_copied_by_packager': False,
            'binding_source': 'existing delivery-index and final-review; packaging validates equivalent top-level bytes'})
    else:
        raw = originals[name]
        assert len(raw) == expected['bytes'] and sha(raw) == expected['sha256'], name
assert len(aliases) == 1
assert len(originals['final-review.json']) == delivery['final_review']['bytes']
assert sha(originals['final-review.json']) == delivery['final_review']['sha256']
review = json.loads(originals['final-review.json'])
comparison = json.loads(originals['pack-scope-comparison-v2.json'])
original_provenance = json.loads(originals['resource-read-provenance.json'])
broader_provenance = json.loads(originals['broader-read-provenance.json'])
assert review['special_ids'] == 40 and len(review['names']) == 40
assert len(review['original_pack_scope']) == 3 and len(review['broader_pack_directories']) == 21
assert len(original_provenance['resource_reads']) == original_provenance['resource_read_count'] == 462
assert len(broader_provenance['resources']) == broader_provenance['files'] == 467
assert sum(row['bytes'] for row in original_provenance['resource_reads'].values()) == 2984554
assert sum(row['bytes'] for row in broader_provenance['resources'].values()) == 2995984
assert len(comparison['preliminary_type_only_deltas']) == 9
assert comparison['other_39_serialized_ID_rows_identical'] is True
assert comparison['changed_special_ids'] == [{'changed_fields': ['additional_source_assets'], 'name': 'minecraft:shield'}]
assert json.loads(originals['cli-check.json'])['exit_code'] == 0
assert json.loads(originals['fixture-result.json'])['tests_run'] == 1
assert originals['before.json'] == originals['after.json']

objects, references = {}, []
for name, raw in sorted(originals.items()):
    raw_sha = sha(raw)
    packed = storage(raw)
    assert gzip.decompress(packed) == raw and storage(raw) == packed
    if raw_sha not in objects:
        filename = raw_sha + '.gz'
        write(filename, packed)
        objects[raw_sha] = {'file': filename, 'raw_bytes': len(raw), 'stored_bytes': len(packed), 'stored_sha256': sha(packed)}
    references.append({'path': name, 'raw_sha256': raw_sha, 'raw_bytes': len(raw), 'object': objects[raw_sha]['file']})
index = {'schema': 1, 'scope': 'PRIVATE_OFFLINE_SOURCE_CENSUS_ONLY', 'logical_files': len(references),
    'source_directory': SOURCE.as_posix(), 'references': references, 'objects': objects,
    'declared_fixture_aliases': aliases,
    'raw_logical_bytes': sum(len(raw) for raw in originals.values()),
    'raw_unique_bytes': sum(row['raw_bytes'] for row in objects.values()),
    'stored_bytes': sum(row['stored_bytes'] for row in objects.values()),
    'gzip': {'filename': '', 'mtime': 0, 'compresslevel': 9},
    'bounded_candidate_ids': 40, 'original_packs': 3, 'broader_packs': 21,
    'actual_resource_references': {'original': 462, 'broader': 467},
    'original_test_runs_preserved_not_repeated': 1, 'original_check_exit_code': 0,
    'original_delivery_and_final_review_bound': True,
    'engine_resources_executable_fixture_tree_or_large_project_copied': False,
    'default_output_installed': False, 'existing_skip_receipts_rewritten': False,
    'production_qualified': False, 'MC_started': False, 'manual_issues_closed': 0}
write('index.json', encode(index))
readme = '''# R29：特殊物品来源的有限候选普查

本包保存既有只读调查的 23 份顶层原件，包括 delivery-index、final-review、生成／check／单测试回执、资源读取 provenance、版本调查和前后守卫。此次只封装字节，不重新生成 census、不重跑测试或 check、不读取引擎资源本体或 exe，也不复制 fixture-root、运行工程或 326MB 私有工程。默认 tools/data census 仍缺失，原全量／skip 记录保持原结论。

这份候选范围是 **40 个 ID**，受现有来源分类器与 catalog 限定，不能当作全部特殊物品的穷举或生产支持。9 类计数为：弩 1、空地图 1、填充地图 1、挽具 16、不确定手持模型 3、旗帜物品 1、图案盾牌 1、头颅方块物品 8、特殊武器模型 8。catalog 的 1907 个已加载 ID 中，427 个 ID／6098 个 aux 组合是平面候选，仍非生产资格；1532 个有拒绝记录的 ID 中有 52 个同时存在平面候选组合，不能把至少一个被拒探针扩张成整个 ID 不支持。

原工具只查 vanilla／vanilla_base／vanilla_netease **3 个包**。私有进程将包范围临时扩展到安装目录中全部 **21 个包**后恢复模块常量；原始输出没有替换。实际读取 provenance 为 **462 文件／2,984,554B** 和 **467 文件／2,995,984B**。这两个数是本调查实读资源引用数，既不是 40 个 ID 的数量，也不是全部安装资源的总数；较宽 report 中 121 条关联资产记录另有自身口径。

较宽定义扫描多出 chemistry 的 3 份 JSON（4,015B），对这 40 个 ID 没有找到新的几何或纹理。按两边已序列化 JSON 对比，39 个 ID 行完全一致，只有 shield 的 additional_source_assets 真正新增 chemistry/materials/entity.material 和 vanilla_login/materials/entity.material 两条引用；未找到新的图案材质定义。多包同相对材质路径存在不同 SHA，没有推断引擎实际包优先级。早期 pack-scope-comparison.json 的 9 个表面变化来自内存 tuple 与 JSON list 的类型差异，pack-scope-comparison-v2.json 明确纠正并保留旧报告，不把假差异当新增适配工作。

安装路径名为 3.10.0.420447；21 份 pack manifest、exe 版本记录及 SHA 只作为来源材料。Minecraft.Windows.exe 的 FileVersion／ProductVersion 为 1.21.130.0，其与网易发行版 3.10.0.420447 的映射 **未独立证实**。目录名与 manifest 不能提升为该映射的独立证明，也没有据此判定安装错误。

既有工具曾用明确私有输出成功生成完整 JSON，随后原 CLI --check exit0。既有真实 InstalledSourceTests.test_checked_in_census_preserves_known_overlap_and_scope 仅执行 **1 条、通过 1 条**：测试模块 ROOT 在内存中指向完整未修改的私有 fixture，原测试源码没有改。私有 fixture 与顶层生成 JSON 的 SHA 相同；本封装只归档顶层等价字节，在 index 的 declared_fixture_aliases 引用原 delivery 绑定，不读取或复制 fixture-root 树。这证明工具和该条断言在这些私有输入下可工作，不能替代默认路径的缺失、将旧全量 census skip 改成通过或推定整个 suite／精确版本来源／原生渲染都已合格。未发现默认文件过去已生成的跟踪记录，也没有编造其历史缺失原因。

旗帜在 3 包与 21 包下均未找到 attachable 来源；**不能由无 attachable 推断旗帜不能接入**，也没有把立地旗帜方块姿态直接当作旗帜物品／展示框姿态。盾牌有 1 个 attachable、atlas.shield 动态图集引用和 44 个图案 PNG 来源；这些存在性证据不证明编辑器可直接使用。盾牌图案着色合成、动态 atlas 绑定、真实 item userdata、物品展示框模型与 pose、编辑器／世界渲染、包优先级及新原生资格都仍待验证。没有因找到资源就宣告旗帜或图案盾牌支持完成，production_qualified=false，人工关闭 0。

[index.json](index.json) 将 {logical} 个逻辑原件按 raw SHA 去重为 {objects} 个确定性 gzip 对象，逻辑原文 {raw:,}B、去重原文 {unique:,}B、存储 {stored:,}B，最大对象 {maximum:,}B。filename 为空、mtime=0、level=9；每条 reference 记录原名／raw SHA／长度，objects 记录 storage SHA／长度。解压后按 references.path 恢复原名并核 raw SHA。delivery-index 中未复制的 fixture 别名独立列出，不冒充本封装重新读取了 fixture 或引擎资源。

[verification.json](verification.json)由独立新进程逐项核 raw／storage SHA、长度、确定性重压、解压回读、原件不变与相对链接；局部凭据扫描覆盖原文、JSON 解码字符串与本目录元数据，未扫描整个历史 runtime 或其他会话。pack.py／verify.py 只封装与检查材料，不导入产品、不运行已有测试。完整私有组合全量及历史补验的边界见[独立证据](../library-full-current-r29-v1/README.md)；本包不会改写它们。
'''.format(logical=len(references), objects=len(objects), raw=index['raw_logical_bytes'], unique=index['raw_unique_bytes'],
           stored=index['stored_bytes'], maximum=max(row['stored_bytes'] for row in objects.values()))
write('README.md', readme.encode('utf-8'))
assert {path.name for path in SOURCE.iterdir() if path.is_file()} == set(originals)
assert all((SOURCE / name).read_bytes() == raw for name, raw in originals.items())
print(json.dumps({'passed': True, 'logical_files': len(references), 'objects': len(objects),
    'raw_bytes': index['raw_logical_bytes'], 'stored_bytes': index['stored_bytes'],
    'largest_object': max(row['stored_bytes'] for row in objects.values())}, sort_keys=True))
