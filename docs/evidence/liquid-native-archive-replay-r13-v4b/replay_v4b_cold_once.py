import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('D:/bbe-r13-liquid/docs/evidence/liquid-native-write-r13-v4b')
OUT = ROOT / '.runtime/liquid-v4b-cold-replay-v2'
OUT.mkdir(exist_ok=False)
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

with tempfile.TemporaryDirectory(prefix='bbe-v4b-cold-') as directory:
    cold = Path(directory)
    archive = cold / 'archive'
    shutil.copytree(SOURCE, archive)
    shutil.copyfile(ROOT / 'tools/replay_liquid_native_archive.py', cold / 'replay.py')
    index = json.loads((archive / 'archive-index.json').read_bytes())
    rows = [row for row in index['files'] if 'project_relative_path' in row]
    assert len(rows) == 117 and all(row['project_relative_path'].endswith('.py') for row in rows)
    supplement = cold / 'source-closure'
    supplement.mkdir()
    sources = []
    for row in rows:
        derived = dict(row)
        derived['original_path'] = str(PureWindowsPath(index['frozen_project']) / row['project_relative_path'])
        derived['frozen_original_path'] = row['original_path']
        target = supplement / row['archive_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive / row['archive_path'], target)
        assert digest(target) == row['sha256']
        sources.append(derived)
    closure = {'schema': 1, 'analyzer': 'tools/analyze_liquid_native_write.py', 'files': sources,
               'derived_from_index_sha256': digest(archive/'archive-index.json'),
               'derived_alias_rule': 'frozen_project + project_relative_path; exact original and frozen SHA unchanged'}
    (supplement / 'archive-index.json').write_text(json.dumps(closure, indent=2) + '\n', encoding='ascii')
    assert digest(archive / 'archive-index.json') == digest(SOURCE / 'archive-index.json')
    command = [sys.executable, '-I', '-X', 'utf8', str(cold / 'replay.py'),
               '--archive', str(archive), '--source-archive', str(supplement),
               '--closure', 'archive-index.json', '--expected', 'native-write-analysis.json',
               '--output', str(cold / 'replay.json')]
    result = subprocess.run(command, cwd=cold, capture_output=True, timeout=60,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT / 'stdout.txt').write_bytes(result.stdout)
    (OUT / 'stderr.txt').write_bytes(result.stderr)
    assert result.returncode == 0, result.stderr.decode('utf8')
    report = json.loads((cold / 'replay.json').read_bytes())
    assert report['reproduced'] is True and report['recomputed']['status'] == 'OBSERVED'
    assert report['recomputed']['native_visibility_observed'] is True
    assert all(report['recomputed'][name] is False for name in
               ('side_uv_qualified','transparency_qualified','animation_qualified','production_qualified'))
    assert digest(archive / 'archive-index.json') == digest(SOURCE / 'archive-index.json')
    shutil.copyfile(cold / 'replay.json', OUT / 'replay.json')
    shutil.copyfile(supplement / 'archive-index.json', OUT / 'derived-closure.json')
    metadata = {'schema': 1, 'scope': 'Existing V4b read-only cold replay; derived closure from indexed source rows',
                'archive_index_sha256': digest(SOURCE/'archive-index.json'),
                'archive_records': len(index['files']), 'source_records': len(rows),
                'imported_sources': len(report['imported_source_sha256']),
                'helper_sha256': digest(cold/'replay.py'), 'replay_sha256': digest(cold/'replay.json'),
                'derived_closure_sha256': digest(supplement/'archive-index.json'),
                'original_input_sha256': report['original_input_sha256'],
                'original_result_sha256': report['original_result_sha256'],
                'new_game_launches': 0, 'sdk_or_network_calls': 0,
                'original_index_unchanged': True, 'result': report['recomputed']['status']}
    (OUT/'verification.json').write_text(json.dumps(metadata, indent=2)+'\n',encoding='ascii')
print(json.dumps(metadata))
