"""Bind host session/status reads to private v10 status mutex; session reads keep unchanged native semantics."""
import hashlib
import importlib.util
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
STATUS_HOST=ROOT/'.runtime/round-20261022/wire-atomic-watcher-v10'
WATCHER_SHA='befb2e6c4784801d2b04c6c4af527c8789ac1ea08e933f21dd0bd94c6bbb8ad2'
STATUS_IO_SHA='69f9c17426c32e1bf1e42bed2f77e0097805462116812e50e7fe32e9c4592e42'
READER_SHA='2ae4d46fc4fc63249b1b10d8cc6e7028009f4fa1941ea64f88452871a89eb28d'
_watcher=None
_status_io=None


def approved():
    global _watcher,_status_io
    for name,digest in (('watch_owned_disabled_skin_assert_r27_v10.py',WATCHER_SHA),
      ('status_io.py',STATUS_IO_SHA),
      ('windows_manifest_reader.py',READER_SHA)):
        assert hashlib.sha256((STATUS_HOST/name).read_bytes()).hexdigest()==digest,'Private status host bytes changed'
    if _watcher is None:
        sys.path.insert(0,str(STATUS_HOST))
        spec=importlib.util.spec_from_file_location('_wire_private_status_watcher_v10',STATUS_HOST/'watch_owned_disabled_skin_assert_r27_v10.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        status_module=sys.modules[module.publish_status.__module__]
        assert Path(status_module.__file__).resolve()==(STATUS_HOST/'status_io.py').resolve(),'Different status_io module already imported'
        assert hashlib.sha256(Path(status_module.__file__).read_bytes()).hexdigest()==STATUS_IO_SHA
        _status_io=status_module
        _watcher=module
    return _watcher


def load_session(path,owner,live,events):
    watcher=approved()
    return watcher.bounded_manifest_read(lambda:watcher.native_load_session(path,owner,live),events,str(path))


def read_json(path,events):
    watcher=approved()
    return watcher.bounded_manifest_read(lambda:watcher.native_read_json(path),events,str(path))


def read_status_json(path,events):
    approved()
    return _status_io.read_status_json(path,events)
