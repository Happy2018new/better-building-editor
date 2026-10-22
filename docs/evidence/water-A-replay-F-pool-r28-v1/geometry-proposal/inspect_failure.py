"""Read-only compact geometry diagnosis of the preserved F-editor failure."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
SOURCE = ROOT / '.runtime/round-20261023/water-formal-f-editor-v2/product-v2-f-editor-v1.json'


def main():
    report = json.loads(SOURCE.read_bytes())
    prefix = 'RuntimeError: Scene liquid failure: '
    assert report['error'].startswith(prefix)
    state = ast.literal_eval(report['error'][len(prefix):])
    output = WORK / 'actual-failure-state-v1.json'
    assert not output.exists()
    output.write_text(json.dumps(state, indent=2, sort_keys=True) + '\n', encoding='ascii')
    compact = {key: value for key, value in state.items()
               if any(word in key.lower() for word in ('scene', 'viewport', 'screen', 'clip', 'gui', 'camera'))}
    compact['source'] = {'path': str(SOURCE.relative_to(ROOT)),
                         'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    compact['native_water_controls'] = state['native_water_controls']
    compact['liquid'] = state['liquid']
    compact['restored'] = report['restored']
    compact['completed'] = report['completed']
    compact['captures'] = len(report['captures'])
    compact['actual_failure_state_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    (WORK / 'actual-geometry-v1.json').write_text(json.dumps(compact, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({key: value for key, value in compact.items() if key != 'native_water_controls'}, indent=2))


if __name__ == '__main__':
    main()
