"""Exact final commit/runtime/host/config binding, with no game mutation."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
def verify():
    manifest=json.loads((HERE/'source-manifest.json').read_bytes())
    project=Path(manifest['project'])
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    actual={path.relative_to(project).as_posix():sha(path)
            for folder in ('behavior_pack','resource_pack') for path in (project/folder).rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.pyo')}
    assert actual==manifest['files']
    assert all(sha(project/path)==digest for path,digest in manifest['host_files'].items())
    assert all(sha(HERE/path)==digest for path,digest in manifest['evidence_hosts'].items())
    assert all(sha(Path(path))==digest for path,digest in manifest['diagnostic_host_assets'].items())
    assert sha(project/'.mcdev.json')==manifest['mcdev_sha256']
    return manifest
if __name__=='__main__':
    manifest=verify();print(json.dumps({'source_commit':manifest['source_commit'],'source_unchanged':True}))
