"""Prepare an independent short-title source and cold clone, without game calls."""
import hashlib
import json
from pathlib import Path
import shutil
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from freeze_intrinsic_glint_project_r21 import fingerprint, freeze


BASE = ROOT / '.runtime/projects/root-signed-book-r21-v1'
BASE_MANIFEST = ROOT / '.runtime/signed-book-r21/source-manifest.json'
BASE_MANIFEST_SHA256 = 'cc57450722012534f51238d4442a96021ea26bd447066f1a0f6bef953f342d25'
SOURCE = ROOT / '.runtime/projects/book-r20-native-oracle-short-source-v2'
CLONE = ROOT / '.runtime/projects/book-r20-native-oracle-short-v2'
OUTPUT = HERE / 'native-oracle-short-v2'
LOOT = 'behavior_pack/loot_tables/modern_projection/r21_signed_book.json'
EXPECTED = {'function': 'set_book_contents', 'title': 'R21 Book A',
            'author': 'R21 Native Loot',
            'pages': ['First authored control.', 'Second authored control.']}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_project(source, destination):
    destination.mkdir(parents=True)
    shutil.copy2(source / '.mcdev.json', destination / '.mcdev.json')
    for folder in ('behavior_pack', 'resource_pack'):
        shutil.copytree(source / folder, destination / folder)


def prepare():
    assert sha(BASE_MANIFEST) == BASE_MANIFEST_SHA256
    baseline = json.loads(BASE_MANIFEST.read_bytes())
    assert fingerprint(BASE) == baseline['files']
    assert not SOURCE.exists() and not CLONE.exists() and not OUTPUT.exists()
    copy_project(BASE, SOURCE)
    path = SOURCE / LOOT
    original = json.loads(path.read_bytes())
    changed = json.loads(path.read_bytes())
    request = changed['pools'][0]['entries'][0]['functions'][0]
    assert request == dict(EXPECTED, title='R21 Native Authored Book A')
    request['title'] = EXPECTED['title']
    assert request == EXPECTED
    restored = json.loads(json.dumps(changed))
    restored['pools'][0]['entries'][0]['functions'][0]['title'] = 'R21 Native Authored Book A'
    assert restored == original
    path.write_text(json.dumps(changed, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    copy_project(SOURCE, CLONE)
    result = freeze(SOURCE, CLONE, OUTPUT / 'source-manifest.json')
    before = {row['path']: row for row in baseline['files']}
    after = {row['path']: row for row in result['files']}
    changed_files = [name for name in sorted(set(before) | set(after))
                     if before.get(name) != after.get(name)]
    assert changed_files == [LOOT]
    assert fingerprint(BASE) == baseline['files']
    receipt = {'schema': 1, 'base_project': str(BASE), 'source': str(SOURCE),
               'clone': str(CLONE), 'base_manifest_sha256': BASE_MANIFEST_SHA256,
               'manifest_sha256': sha(OUTPUT / 'source-manifest.json'),
               'source_digest': result['files_sha256'], 'file_count': result['file_count'],
               'changed_files': changed_files, 'only_semantic_change': 'Authored A title request',
               'expected_request': EXPECTED, 'base_source_unchanged': True,
               'game_calls': 0, 'game_launched': False, 'production_qualified': False}
    with (OUTPUT / 'prepare.json').open('x', encoding='ascii') as handle:
        handle.write(json.dumps(receipt, ensure_ascii=True, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    print(json.dumps(prepare(), ensure_ascii=True))
