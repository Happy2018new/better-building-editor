"""Bind host session/status reads to root-reviewed v5 Win32 retained reads."""
import hashlib
import importlib.util
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
V5=ROOT/'.runtime/round-20261022/water-anchor-watcher-v5'
WATCHER_SHA='804aab25fa70ab91c63cffc3eb5db170dbd5800e3c4450da5b52c5a897e49565'
READER_SHA='2ae4d46fc4fc63249b1b10d8cc6e7028009f4fa1941ea64f88452871a89eb28d'
_watcher=None


def approved():
    global _watcher
    for name,digest in (('watch_owned_disabled_skin_assert_r27_v5.py',WATCHER_SHA),
      ('windows_manifest_reader.py',READER_SHA)):
        assert hashlib.sha256((V5/name).read_bytes()).hexdigest()==digest,'Reviewed v5 host bytes changed'
    if _watcher is None:
        sys.path.insert(0,str(V5))
        spec=importlib.util.spec_from_file_location('_wire_root_reviewed_watcher_v5',V5/'watch_owned_disabled_skin_assert_r27_v5.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        _watcher=module
    return _watcher


def load_session(path,owner,live,events):
    watcher=approved()
    return watcher.bounded_manifest_read(lambda:watcher.native_load_session(path,owner,live),events,str(path))


def read_json(path,events):
    watcher=approved()
    return watcher.bounded_manifest_read(lambda:watcher.native_read_json(path),events,str(path))
