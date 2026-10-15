"""Export the bounded native water item-use probe without holding game threads."""
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
    parser.add_argument('--profile', choices=('smoke', 'extinguish_states', 'flow_spread',
                                             'source_stability_states'), default='smoke')
    args = parser.parse_args()
    with Client(timeout=45) as client:
        def run(code):
            value = return_value(client.call('execute_code', {
                'code': code, 'is_client': False, 'direct_return': True}))
            return json.loads(value) if isinstance(value, str) else value
        run("import sys\nsys._p0_water_profile_mode=%r\n" % args.profile +
            (ROOT / 'tools/probe_water_interactions.py').read_text(encoding='utf8'))
        deadline = time.monotonic() + 300
        args.output.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = args.output.with_name(args.output.stem + '-partial.json')
        while time.monotonic() < deadline:
            progress = run("import sys,json\ns=sys._p0_water_interactions\n"
                           "_result=json.dumps(s)")
            checkpoint.write_text(json.dumps(progress, indent=2, sort_keys=True) + '\n', encoding='utf8')
            if progress['done']:
                break
            time.sleep(.5)
        else:
            raise AssertionError('Water item-use probe exceeded deadline: %r' % progress)
        length = run("import sys,json\nsys._p0_water_interaction_export=json.dumps(sys._p0_water_interactions,sort_keys=True)\n"
                     "_result=len(sys._p0_water_interaction_export)")
        pieces = [run("import sys,json\n_result=json.dumps(sys._p0_water_interaction_export[%d:%d])" %
                      (offset, offset + 49152)) for offset in range(0, length, 49152)]
        data = json.loads(''.join(pieces))
        run("import sys\ndel sys._p0_water_interaction_export\n_result=True")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf8')
    print(json.dumps({'output': str(args.output.resolve()), 'rows': len(data['rows']),
                      'failure': data['failure']}))
    if data['failure']:
        raise AssertionError(data['failure'])
    if not data.get('restored') or data.get('cleanup_residue') or data.get('cleanup_failure'):
        raise AssertionError('Water probe cleanup did not restore the owned fixture')


if __name__ == '__main__':
    main()
