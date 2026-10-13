"""Owned, one-shot offline verification; never import any game/runtime module."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('D:/bbe-r13-liquid/docs/evidence')
NAMES = ('liquid-native-write-r13-v2', 'liquid-native-write-r13-v2-source-closure',
         'liquid-native-write-r13-v2-source-closure-extra')
OUT = ROOT / '.runtime/liquid-v2-cold-verification-v2'
OUT.mkdir(exist_ok=False)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(cold, name, expect_ok):
    output = cold / (name + '.json')
    command = [sys.executable, '-I', '-X', 'utf8', str(cold / 'replay.py'),
               '--archive', str(cold / NAMES[0]), '--closure', 'archive-index.json',
               '--source-archive', str(cold / NAMES[1]),
               '--source-archive', str(cold / NAMES[2]), '--output', str(output)]
    result = subprocess.run(command, cwd=cold, capture_output=True, timeout=60,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    (OUT / (name + '.stdout.txt')).write_bytes(result.stdout)
    (OUT / (name + '.stderr.txt')).write_bytes(result.stderr)
    row = {'returncode': result.returncode, 'output_written': output.exists(),
           'command': command, 'cwd': str(cold), 'expected_success': expect_ok}
    if expect_ok:
        assert result.returncode == 0 and output.is_file(), result.stderr.decode('utf8')
        shutil.copyfile(output, OUT / 'cold-replay.json')
        report = json.loads(output.read_bytes())
        assert report['reproduced'] is True
        assert report['recomputed']['status'] == 'FAIL'
        assert not report['recomputed']['production_qualified']
        assert len(report['imported_source_sha256']) == 46
        assert report['new_launches'] == 0 and report['sdk_or_network_calls'] == 0
        row['report_sha256'] = digest(output)
        row['imported_sources'] = len(report['imported_source_sha256'])
    else:
        assert result.returncode != 0 and not output.exists()
        assert b'Archived original bytes changed:' in result.stderr
        row['refusal'] = 'Exact-byte index mismatch before source scoring; no output created'
    return row


with tempfile.TemporaryDirectory(prefix='bbe-cold-liquid-r13-') as directory:
    cold = Path(directory)
    shutil.copyfile(ROOT / 'tools/replay_liquid_native_archive.py', cold / 'replay.py')
    for name in NAMES:
        shutil.copytree(SOURCE / name, cold / name)
    assert sorted(path.name for path in cold.iterdir()) == sorted(list(NAMES) + ['replay.py'])
    checks = {'schema': 1, 'scope': 'Offline cold relocation plus exact-byte tamper refusal',
              'cold_root': str(cold), 'new_game_launches': 0, 'sdk_or_network_calls': 0,
              'initial_contents': sorted(path.name for path in cold.iterdir()),
              'source_indexes': {name: digest(cold / name / 'archive-index.json') for name in NAMES},
              'helper_sha256': digest(cold / 'replay.py'), 'checks': []}
    checks['checks'].append(execute(cold, 'cold-original', True))
    source = cold / NAMES[1] / 'sources/tools/analyze_liquid_sides.py'
    raw = source.read_bytes()
    assert b'\r\n' in raw
    source.write_bytes(raw.replace(b'\r\n', b'\n'))
    checks['checks'].append(execute(cold, 'changed-newlines', False))
    source.write_bytes(raw)
    image = cold / NAMES[0] / 'original-priority_native_palette_h_vnw.png'
    if not image.is_file():
        names = [path for path in (cold / NAMES[0]).glob('*.png')
                 if 'native_palette_h_vnw' in path.name]
        assert len(names) == 1
        image = names[0]
    raw = image.read_bytes()
    image.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    checks['checks'].append(execute(cold, 'changed-capture-byte', False))
    image.write_bytes(raw)
    for name in NAMES:
        assert checks['source_indexes'][name] == digest(cold / name / 'archive-index.json')
    checks['all_checks_passed'] = True
    (OUT / 'verification.json').write_text(json.dumps(checks, indent=2) + '\n', encoding='ascii')
print(json.dumps({'passed': True, 'evidence': str(OUT), 'checks': len(checks['checks'])}))
