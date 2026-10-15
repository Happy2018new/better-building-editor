"""Bind one helper-only amendment while retaining the original v5 bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
CONTROL = Path(__file__).resolve().parent
ORIGINAL = ROOT/'.runtime/shelf-render-palette-r21-v5'
HELPER = 'tools/shelf_render_palette_candidate_r21.py'
sys.path.insert(0, str(ROOT/'tools'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preserve', 'freeze'))
    args = parser.parse_args()
    original = json.loads((ORIGINAL/'frozen.json').read_bytes())
    archived = CONTROL/'original_shelf_render_palette_candidate_r21.py'
    expected = original['host_sources'][HELPER]
    if args.action == 'preserve':
        if sha(ROOT/HELPER) != expected:
            raise ValueError('The original helper must still match the old frozen bytes')
        if archived.exists():
            raise ValueError('The original helper archive already exists')
        shutil.copyfile(ROOT/HELPER, archived)
        print(json.dumps({'preserved_sha256': sha(archived)}))
        return
    if sha(archived) != expected or (CONTROL/'frozen.json').exists():
        raise ValueError('Use the original archived helper and a fresh amendment freeze')
    from prepare_shelf_render_palette_r21 import hosts, verify
    current = hosts()
    changed = [name for name in current if current[name] != original['host_sources'][name]]
    if changed != [HELPER]:
        raise ValueError('Only the intended helper may differ: '+repr(changed))
    original['host_sources'] = current
    original['amendment'] = {
        'original_freeze': str(ORIGINAL/'frozen.json'), 'original_freeze_sha256': sha(ORIGINAL/'frozen.json'),
        'original_helper': str(archived), 'original_helper_sha256': sha(archived),
        'new_helper_sha256': current[HELPER],
        'preparer_sha256': sha(Path(__file__)),
        'scope': 'One explicit-state guard in the existing helper. Clone/resources and three-image plan unchanged.'}
    shutil.copyfile(ORIGINAL/'run.py', CONTROL/'run.py')
    original['amendment']['runner_matches_original'] = sha(CONTROL/'run.py') == sha(ORIGINAL/'run.py')
    (CONTROL/'frozen.json').write_text(json.dumps(original, indent=2)+'\n', encoding='ascii', newline='\n')
    verify(CONTROL/'frozen.json')
    print(json.dumps({'prepared': True, 'changed_hosts': changed,
                      'freeze_sha256': sha(CONTROL/'frozen.json'), 'files_sha256': original['files_sha256']}))


if __name__ == '__main__':
    main()
