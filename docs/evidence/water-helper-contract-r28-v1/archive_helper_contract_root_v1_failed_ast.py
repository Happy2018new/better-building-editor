"""Review the one-entry private contract patch and preserve the exact offline kit."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.runtime/round-20261023/water-owner-helper-contract-v1'
OUT = ROOT / 'docs/evidence/water-helper-contract-r28-v1'


def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(path.read_bytes())


index = read(SOURCE / 'index.json')
assert sha((SOURCE / 'index.json').read_bytes()) == 'b4fb8ed6f4aa08383b9f1c48194ac7c6ba63082da34e91cd2741a50b00462405'
old_root, new_root = [SOURCE / 'projects' / name for name in ('baseline39', 'candidate40')]
generator = Path('tools/generate_liquid_product_owner_contract.py')
before = ast.parse((old_root / generator).read_bytes())
after = ast.parse((new_root / generator).read_bytes())


def sources_node(tree):
    rows = [node for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'SOURCES' for target in node.targets)]
    assert len(rows) == 1
    return rows[0]


old_sources = ast.literal_eval(sources_node(before).value)
new_sources = ast.literal_eval(sources_node(after).value)
assert len(old_sources) == 39 and len(new_sources) == len(set(new_sources)) == 40
assert tuple(name for name in new_sources if name != 'scene_owner') == tuple(old_sources)
restored = copy.deepcopy(after)
sources_node(restored).value = copy.deepcopy(sources_node(before).value)
assert ast.dump(restored) == ast.dump(before)
contract_path = Path('tools/data/liquid_product_owner_contract_v1.json')
old_contract, new_contract = [read(project / contract_path) for project in (old_root, new_root)]
helper = 'behavior_pack/modern_projection/projection/scene_owner.py'
assert set(new_contract['source_sha256']) - set(old_contract['source_sha256']) == {helper}
assert all(new_contract['source_sha256'][name] == digest for name, digest in old_contract['source_sha256'].items())
for relative, digest in new_contract['source_sha256'].items():
    assert sha((new_root / relative).read_bytes().replace(b'\r\n', b'\n')) == digest, relative
assert sha((new_root / generator).read_bytes().replace(b'\r\n', b'\n')) == new_contract['generator_sha256']
assert old_contract['schema_version'] == new_contract['schema_version'] == 1
assert not OUT.exists()
OUT.mkdir()
for row in index['files']:
    source = (SOURCE / row['path']).resolve()
    assert source.is_relative_to(SOURCE.resolve())
    data = source.read_bytes()
    assert sha(data) == row['sha256'] and len(data) == row['bytes']
    target = OUT / row['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
shutil.copyfile(SOURCE / 'index.json', OUT / 'index.json')
shutil.copyfile(__file__, OUT / 'archive_helper_contract_root_v1.py')
receipt = {
    'completed': True, 'original_agent_index_sha256': sha((SOURCE / 'index.json').read_bytes()),
    'exact_original_files': len(index['files']), 'whole_generator_AST_only_one_source_added': True,
    'explicit_sources': 40, 'all_39_previous_hashes_unchanged': True,
    'all_40_actual_candidate_sources_and_generator_independently_hashed': True,
    'root_actual_positive_CLI_replays': [
        {'script': 'candidate40/tools/generate_liquid_product_owner_contract.py', 'args': ['--check'], 'returncode': 0},
        {'script': 'candidate40/tools/check_liquid_product_owner_contract.py', 'args': ['--check'], 'returncode': 0},
    ],
    'candidate_contract_sha256': sha((new_root / contract_path).read_bytes()),
    'merged': False, 'qualifier_called': False, 'new_water_gates_awarded': 0,
    'MC_started': False, 'manual_issues_closed': 0,
    'independent_portal_and_book_source_lists_still_require_helper': True,
}
(OUT / 'root-review.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf8')
(OUT / 'ROOT_REVIEW.md').write_text('''# Root复核边界\n\n这是下一窗口的私有工具准备。原112项文件和代理索引保持原字节；root独立核整个生成器AST仅多一项SOURCES，旧39项指纹一致，新40项源码及生成器实际hash全部匹配，并实际复跑candidate40生成器与checker的只读--check。14项正／负CLI控制按原回执保留。没有调用qualifier、修改主仓或授新水门。\n\n原脚本保留.runtime及私有项目布局假设；复跑前先恢复原位置，不能在此归档目录盲目执行准备脚本。最大单文件约289KB，无大源码ZIP。portal和book还须各自加helper，历史archive／report未捕获helper，应明确拒绝转授。详细命令与原始边界见README.md。\n''', encoding='utf8')
entries = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        data = path.read_bytes()
        entries.append({'path': path.relative_to(OUT).as_posix(), 'bytes': len(data), 'sha256': sha(data)})
(OUT / 'root-index.json').write_text(json.dumps({'entries': entries, 'merged': False}, indent=2, sort_keys=True) + '\n', encoding='utf8')
print(json.dumps({'completed': True, 'archive_files': len(entries) + 1,
                  'bytes_without_root_index': sum(row['bytes'] for row in entries),
                  'max_file_bytes': max(row['bytes'] for row in entries)}))
