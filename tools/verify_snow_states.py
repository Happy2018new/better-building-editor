"""Export bounded snow-state observations with interruption checkpoints."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with Client(timeout=30) as client:
        def run(code):
            value = return_value(client.call('execute_code', {
                'code': code, 'is_client': False, 'direct_return': True}))
            return json.loads(value) if isinstance(value, str) else value
        run((ROOT / 'tools/probe_snow_states.py').read_text(encoding='utf8'))
        deadline = time.monotonic() + 180
        checkpoint = args.output.with_name(args.output.stem + '-partial.json')
        while time.monotonic() < deadline:
            data = run('import sys,json\n_result=json.dumps(sys._p0_snow_states)')
            checkpoint.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf8')
            if data['done']:
                break
            time.sleep(.5)
        else:
            raise AssertionError('Snow state probe exceeded deadline: %r' % data)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf8')
    print(json.dumps({'rows': len(data['rows']), 'failure': data['failure'], 'restored': data.get('restored')}))
    if data['failure'] or not data.get('restored') or data.get('cleanup_failure'):
        raise AssertionError('Snow state probe did not finish and restore its fixture')
    failed = []
    for row in data['rows']:
        expected = {'covered_bit': True, 'height': row['height'] - 1}
        after = row['delayed']
        if (not row['set_snow'] or after['front'][0] != 'minecraft:snow_layer'
                or after['states'] != expected or after['back'] != [row['name'], row['aux']]
                or after['back_states'] != row['dry']['states']):
            failed.append((row['name'], row['aux'], row['height']))
    if failed:
        raise AssertionError('Native snow state readbacks differ: %r' % failed)


if __name__ == '__main__':
    main()
