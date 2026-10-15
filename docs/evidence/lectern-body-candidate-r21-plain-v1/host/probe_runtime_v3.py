"""Use the normal JSON wire boundary when rebuilding the host document."""
import importlib.util
from pathlib import Path


SOURCE = Path(__file__).with_name('probe_runtime_v2.py')
SPEC = importlib.util.spec_from_file_location('lectern_runtime_v2', SOURCE)
WRAPPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WRAPPER)
HOST = WRAPPER.HOST
OLD = "Document.from_data(saved['document'])"
NEW = "Document.from_data(json.loads(json.dumps(saved['document'])))"
if HOST.LOAD_DOCUMENT.count(OLD) != 1:
    raise ValueError('The sealed host load template changed')
HOST.LOAD_DOCUMENT = HOST.LOAD_DOCUMENT.replace(OLD, NEW)
HOST.__file__ = __file__


if __name__ == '__main__':
    HOST.main()
