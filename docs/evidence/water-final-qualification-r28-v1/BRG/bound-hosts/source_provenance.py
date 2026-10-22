"""Verify base ZIP plus declared add/change/delete overlay against live bytes."""
import hashlib
from pathlib import Path
import zipfile


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_source_provenance(binding):
    record = binding['source_provenance']
    assert record['kind'] == 'base_zip_plus_current_shared_overlay_v2'
    original = dict(record['base_source_sha256'], **record['base_auxiliary_sha256'])
    expected = dict(binding['source_sha256'], **binding['auxiliary_sha256'])
    additions = set(expected) - set(original)
    deletions = set(original) - set(expected)
    modifications = {name for name in set(expected) & set(original) if expected[name] != original[name]}
    delta_names = additions | modifications
    assert additions == set(record['added_files'])
    assert deletions == set(record['deleted_files'])
    assert modifications == set(record['changed_files'])
    base, overlay = Path(record['base']['path']), Path(record['overlay']['path'])
    assert digest(base.read_bytes()) == record['base']['sha256']
    assert digest(overlay.read_bytes()) == record['overlay']['sha256']
    project = Path(binding['project']).resolve()
    with zipfile.ZipFile(base) as old, zipfile.ZipFile(overlay) as delta:
        assert len(old.namelist()) == len(set(old.namelist())) == len(original)
        assert set(old.namelist()) == set(original)
        assert len(delta.namelist()) == len(set(delta.namelist())) == len(delta_names)
        assert set(delta.namelist()) == delta_names
        for name in sorted(original):
            assert digest(old.read(name)) == original[name], name
        for name in sorted(expected):
            raw = delta.read(name) if name in delta_names else old.read(name)
            assert digest(raw) == expected[name], name
            path = project / name
            assert path.resolve().is_relative_to(project) and path.read_bytes() == raw, name
        assert all(not (project / name).exists() for name in deletions)
    return {'passed': True, 'base_SHA_verified': True, 'overlay_SHA_verified': True,
            'base_files_compared': len(original), 'synthesized_files_compared': len(expected),
            'exact_changed_files': sorted(modifications), 'exact_added_files': sorted(additions),
            'exact_deleted_files': sorted(deletions), 'new_large_source_archive_created': False}
