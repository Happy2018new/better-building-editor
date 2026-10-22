"""Prepare an unadmitted portal anchor candidate from exact b70 Git blobs."""
import difflib
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COMMIT = 'b70ce7bf13ad6a4472f2b089ac812c162b174861'
PREFIX = 'behavior_pack/modern_projection/projection/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')


def git_blob(relative):
    return subprocess.check_output(['git', 'show', COMMIT + ':' + relative], cwd=ROOT)


def main():
    assert not (HERE / 'provenance.json').exists(), 'Never replace a complete candidate'
    contract = json.loads((ROOT / 'tools/data/liquid_product_owner_contract_v1.json').read_bytes())
    protected = set(contract['source_sha256']) | {
        PREFIX + 'portal_profile.py',
        PREFIX + 'liquid_product_owner_data.py',
        PREFIX + 'liquid_product_qualification_data.py',
        'tools/data/liquid_product_owner_contract_v1.json',
        'tools/data/liquid_product_resource_contract_v1.json',
        'tools/data/portal_resource_contract_nemc310_v1.json',
    }
    boundary = {
        'files': {name: digest((ROOT / name).read_bytes()) for name in sorted(protected)},
        'scope': 'Read-only byte guard; includes all 39 current water implementation entries and metadata',
    }
    boundary_path = HERE / 'workspace-boundary-before.json'
    if boundary_path.exists():
        assert json.loads(boundary_path.read_bytes()) == boundary
    else:
        write_json(boundary_path, boundary)

    patches = []
    rows = []
    for name in ('portal_profile.py', 'scene.py'):
        relative = PREFIX + name
        raw = git_blob(relative)
        before = HERE / 'baseline' / relative
        after = HERE / 'candidate' / relative
        before.parent.mkdir(parents=True, exist_ok=True)
        after.parent.mkdir(parents=True, exist_ok=True)
        if before.exists():
            assert before.read_bytes() == raw
        else:
            before.write_bytes(raw)
        if name == 'portal_profile.py':
            old = b'        return 0., min(size) / 4.\n'
            new = old + b'''\n    @staticmethod
    def ui_offset_for_gui(size, gui):
        """Compensate the native skeleton anchor at the actual GUI scale."""
        if (isinstance(gui, bool) or not isinstance(gui, integer_types + (float,))
                or not 1. <= gui < float('inf') or gui != round(gui)):
            raise ValueError('Portal preview needs a positive integer native GUI scale')
        return 0., min(size) / float(gui)
'''
        else:
            old = b'                offset = portal_profile.ui_offset(view.size)\n'
            new = b'''                gui_offset = getattr(portal_profile, 'ui_offset_for_gui', None)
                offset = (gui_offset(view.size, Theme.native_gui_scale) if gui_offset is not None
                          else portal_profile.ui_offset(view.size))
'''
        if b'\r\n' in raw:
            old = old.replace(b'\n', b'\r\n')
            new = new.replace(b'\n', b'\r\n')
        assert raw.count(old) == 1, name
        changed = raw.replace(old, new, 1)
        assert changed.replace(new, old, 1) == raw
        after.write_bytes(changed)
        patches.extend(difflib.unified_diff(raw.decode('utf8').splitlines(True),
                                          changed.decode('utf8').splitlines(True),
                                          fromfile='a/' + relative, tofile='b/' + relative))
        oid = subprocess.check_output(['git', 'rev-parse', COMMIT + ':' + relative], cwd=ROOT, text=True).strip()
        rows.append({'path': relative, 'base_git_blob': oid, 'base_sha256': digest(raw),
                     'candidate_sha256': digest(changed), 'base_bytes': len(raw), 'candidate_bytes': len(changed)})
    (HERE / 'candidate.patch').write_text(''.join(patches), encoding='utf8', newline='\n')
    support = HERE / 'support'
    support.mkdir()
    cell = git_blob(PREFIX + 'cell.py')
    (support / 'cell.py').write_bytes(cell)
    write_json(HERE / 'provenance.json', {
        'source_commit': COMMIT, 'files': rows,
        'cell_source_path': PREFIX + 'cell.py', 'cell_sha256': digest(cell),
        'patch_sha256': digest((HERE / 'candidate.patch').read_bytes()),
        'production_modified': False, 'metadata_modified': False, 'water39_contract_modified': False,
        'merge_authorized': False, 'MC_started': False, 'qualification_awarded': False,
        'candidate_cold_tested': False,
        'V4_scope': 'Actual V4 only tested a temporary instance ui_offset override; it did not execute this candidate',
    })
    print(json.dumps({'prepared': True, 'source_commit': COMMIT, 'candidate_files': len(rows),
                      'protected_workspace_files': len(protected), 'patch_sha256': digest((HERE / 'candidate.patch').read_bytes()),
                      'production_modified': False, 'MC_started': False, 'candidate_cold_tested': False}))


if __name__ == '__main__':
    main()
