"""Supply the frozen private session modules to the unchanged v2 analyzer wrapper."""
import hashlib
import importlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / '.runtime/round-20261022/water-merged-fullA-v2'
BINDING = HOST / 'final-source-binding-v1.json'
binding = json.loads(BINDING.read_bytes())
project = Path(binding['project'])
scripts = project / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(scripts))
modules = []
for name in ('_session', '_window'):
    module = importlib.import_module(name)
    path = Path(module.__file__).resolve()
    relative = path.relative_to(project).as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.parent == scripts.resolve()
    assert digest == binding['source_sha256'][relative]
    modules.append({'name': name, 'path': str(path), 'sha256': digest})
wrapper = ROOT / '.runtime/round-20261022/water-merged-fullA-analysis-v2/run_analysis.py'
assert hashlib.sha256(wrapper.read_bytes()).hexdigest() == '54f3cba4b255991fd66d3b41f91f769dca365d82bd7472f3e4468d8d64a88425'
receipt = ROOT / '.runtime/round-20261022/root-water-strict-session-binding-v1.json'
assert not receipt.exists()
receipt.write_text(json.dumps({'schema': 1, 'frozen_private_modules': modules,
    'binding_sha256': hashlib.sha256(BINDING.read_bytes()).hexdigest(),
    'wrapper_sha256': hashlib.sha256(wrapper.read_bytes()).hexdigest(),
    'host_launcher_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'previous_attempt': {'output_directory': '.runtime/round-20261022/root-water-fullA-v2-strict-analysis-v1',
        'exit_code': 1, 'phase': 'import capture_native_burst before any flow analysis',
        'exception_type': 'ModuleNotFoundError', 'message': "No module named '_session'",
        'product_or_analyzer_modified': False},
    'MC_started': False, 'RPC_dispatched': False,
    'private_product_and_analyzer_bytes_modified': False}, indent=2) + '\n', encoding='utf8')
runpy.run_path(str(wrapper), run_name='__main__')
