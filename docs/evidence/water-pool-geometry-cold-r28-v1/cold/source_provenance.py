"""Verify a reused base ZIP plus a small exact overlay against all live files."""
import hashlib
import json
from pathlib import Path
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_source_provenance(binding):
    provenance = binding['source_provenance']
    assert provenance['kind'] == 'base_zip_plus_exact_overlay_v1'
    base = Path(provenance['base']['path'])
    overlay = Path(provenance['overlay']['path'])
    assert sha(base.read_bytes()) == provenance['base']['sha256']
    assert sha(overlay.read_bytes()) == provenance['overlay']['sha256']
    original = dict(provenance['base_source_sha256'], **provenance['base_auxiliary_sha256'])
    expected = dict(binding['source_sha256'], **binding['auxiliary_sha256'])
    changed = provenance['changed_files']
    project = Path(binding['project']).resolve()
    assert set(expected) == set(original) and len(changed) == 2
    assert set(changed) == {name for name in expected if expected[name] != original[name]}
    with zipfile.ZipFile(base) as old, zipfile.ZipFile(overlay) as delta:
        assert len(old.namelist()) == len(set(old.namelist())) == len(original)
        assert set(old.namelist()) == set(original)
        assert len(delta.namelist()) == len(set(delta.namelist())) == len(changed)
        assert set(delta.namelist()) == set(changed)
        for name in sorted(expected):
            raw = old.read(name)
            assert sha(raw) == original[name], name
            if name in changed:
                assert changed[name]['before_sha256'] == original[name]
                raw = delta.read(name)
                assert changed[name]['after_sha256'] == expected[name]
            assert sha(raw) == expected[name], name
            live = project / name
            assert live.resolve().is_relative_to(project) and live.read_bytes() == raw, name
    return {'passed': True, 'base_SHA_verified': True, 'overlay_SHA_verified': True,
            'base_files_compared': len(original), 'synthesized_files_compared': len(expected),
            'exact_changed_files': sorted(changed), 'new_large_source_archive_created': False}
