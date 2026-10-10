"""Export a managed native probe's JSON result without truncating tool output."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--client', action='store_true')
args = parser.parse_args()
with Client(timeout=60) as client:
    result = return_value(client.call('execute_code', {
        'code': args.source.read_text(encoding='utf8'),
        'is_client': args.client, 'direct_return': True}))
if isinstance(result, str):
    result = json.loads(result)
args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf8')
print('Exported native JSON to %s' % args.output.resolve())
