"""Record exact-version engine item/icon resolution without changing game state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value
from _session import load_session


def run(session_file, owner, output, basic_only=False):
    session = load_session(session_file, owner)
    os.environ.update(MCDEV_SESSION_FILE=str(session_file), MCDEV_OWNER=owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'owner': owner, 'session_id': session['id'],
              'engine_version': Path(session['game_executable']).parent.name,
              'method': ('GetLoadItems(True), GetItemBasicInfo(identifier,0)' if basic_only else
                         'GetLoadItems(True), GetItemTexture(identifier:aux)'),
              'world_modified': False, 'requests': [], 'rows': []}
    path = output / 'catalog.json'
    def save():
        path.write_text(json.dumps(report, ensure_ascii=True, indent=2)+'\n', encoding='ascii')
    def execute(client, code, server=False):
        result = client.call('execute_code', {'code': code, 'is_client': not server,
                                              'direct_return': True})
        if result.get('isError'):
            raise RuntimeError(result)
        return return_value(result)
    with Client(timeout=30) as client:
        names = execute(client, 'import mod.server.extraServerApi as api\n'
                        'items=api.GetEngineCompFactory().CreateItem(api.GetLevelId())\n'
                        '_result=items.GetLoadItems(True)\n', True)
        report['loaded_ids'] = sorted(names)
        save()
        probes = [(name, aux) for name in sorted(names) if name.startswith('minecraft:')
                  for aux in (range(1) if basic_only else range(48 if name in
                      ('minecraft:potion', 'minecraft:splash_potion', 'minecraft:lingering_potion',
                       'minecraft:arrow') else 16))]
        for start in range(0, len(probes), 128):
            before = time.monotonic()
            expression = ('items.GetItemBasicInfo(name,aux)' if basic_only else
                          'items.GetItemTexture(name+":"+str(aux))')
            rows = execute(client, 'import mod.client.extraClientApi as api\n'
                           'items=api.GetEngineCompFactory().CreateItem(api.GetLevelId())\n'
                           'probes='+repr(probes[start:start+128])+'\n'
                           '_result=[{"name":name,"aux":aux,"value":'+expression+'}'
                           ' for name,aux in probes]\n')
            report['rows'].extend(rows)
            report['requests'].append({'start': start, 'count': len(rows),
                                       'seconds': time.monotonic()-before})
            save()
        report['completed'] = True
        report['row_count'] = len(report['rows'])
        save()
    print(json.dumps({'output': str(path), 'loaded_ids': len(names),
                      'rows': len(report['rows']), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--basic-only', action='store_true')
    args = parser.parse_args()
    run(args.session, args.owner, args.output, args.basic_only)
