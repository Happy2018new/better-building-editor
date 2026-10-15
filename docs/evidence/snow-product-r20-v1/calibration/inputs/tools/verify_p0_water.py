"""Start and export actual native placement evidence in the owned test world."""
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
    parser.add_argument('--read-existing', action='store_true')
    args = parser.parse_args()
    with Client(timeout=45) as client:
        def run(code):
            value = return_value(client.call('execute_code', {
                'code': code, 'is_client': False, 'direct_return': True}))
            return json.loads(value) if isinstance(value, str) else value
        if not args.read_existing:
            run((ROOT / 'tools/dump_waterloggable_blocks.py').read_text(encoding='utf8'))
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            progress = run("import sys,json\ns=sys._p0_native_probe\n"
                           "_result=json.dumps({k:s.get(k) for k in "
                           "('done','tested_states','verified_states','failure')})")
            if progress['done']:
                break
            time.sleep(.5)
        else:
            raise AssertionError('Native probe exceeded the deadline: %r' % progress)
        summary = run("import sys,json\ns=sys._p0_native_probe\n"
                      "_result=json.dumps({k:s.get(k) for k in "
                      "('schema','game_version','palette_sha256','method','blocks',"
                      "'tested_states','total_states','verified_states','failure',"
                      "'cleanup_failure','elapsed_seconds','states_per_subchunk')})")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        summary_path = args.output.with_name(args.output.stem + '-summary.json')
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf8')
        print(json.dumps({'summary': str(summary_path.resolve()),
                          'states': summary['tested_states'], 'verified': summary['verified_states'],
                          'failure': summary['failure']}), flush=True)
        run((ROOT / 'tools/p0_water_probe_evidence.py').read_text(encoding='utf8') +
            "\nsys._p0_water_export_text=_result\n_result=len(sys._p0_water_export_text)")
        length = run("import sys\n_result=len(sys._p0_water_export_text)")
        pieces = []
        for offset in range(0, length, 49152):
            pieces.append(run("import sys,json\n_result=json.dumps(sys._p0_water_export_text[%d:%d])" %
                              (offset, offset + 49152)))
        result = json.loads(''.join(pieces))
        run("import sys\ndel sys._p0_water_export_text\n_result=True")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf8')
    print(json.dumps({'output': str(args.output.resolve()), 'states': result['tested_states'],
                      'verified': result['verified_states'], 'failure': result['failure'],
                      'mismatches': len(result['state_mismatches']),
                      'entity_blocks': len(result.get('block_entities', {}))}))
    if result['failure'] or result.get('cleanup_failure'):
        raise AssertionError('Native probe evidence was saved but is not accepted')


if __name__ == '__main__':
    main()
