"""Retire only the completed private receipt after checks; never initialize."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value
from bootstrap_payload import readback_code


def main():
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    path = WORK / 'bootstrap-marker-retired-v1.json'
    assert not path.exists()
    os.environ.update(MCDEV_SESSION_FILE=launch['session_file'], MCDEV_OWNER=binding['owner'],
                      MCDEV_ALLOW_USER_FOREGROUND='0')
    with Client(timeout=10) as client:
        value = return_value(client.call('execute_code', {
            'code': readback_code(binding['bootstrap_receipt_marker'], retire=True),
            'is_client': True, 'direct_return': True}))
    receipt = json.loads(value) if isinstance(value, str) else value
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    assert receipt.get('marker_retired'), receipt
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
