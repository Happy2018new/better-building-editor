"""Measure nondefault native pot sherds and their client render fields.

Use a managed disposable world. The four distinct sherds are a Bedrock NBT
candidate until native readback and client replication both confirm them.
This captures data; visual face orientation is accepted separately.
"""
import argparse
import json
import time
from pathlib import Path

from verify_debug_blueprints import Client, write_json
from verify_native_entity_appearances import execute

SHERDS = ('minecraft:angler_pottery_sherd', 'minecraft:archer_pottery_sherd',
          'minecraft:arms_up_pottery_sherd', 'minecraft:blade_pottery_sherd')

SETUP = '''import json,math,sys
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry as registry
assert not hasattr(sys,'_native_pot_fields')
f=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
info=f.CreateBlockInfo(player)
dimension=f.CreateDimension(player).GetEntityDimensionId()
foot=f.CreatePos(player).GetFootPos()
target=(int(math.floor(foot[0]))+12,int(math.floor(foot[1]))+40,int(math.floor(foot[2]))+12)
support=(target[0],target[1]-1,target[2])
for pos in (target,support):
 before=info.GetBlockNew(pos,dimension)
 assert before and before.get('name')=='minecraft:air',(pos,before)
saved={'target':target,'support':support,'dimension':dimension,'player':player,
 'game_version':registry.source_version(),'palette_sha256':registry.fingerprint()}
sys._native_pot_fields=saved
assert info.SetBlockNew(support,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
_result=json.dumps(saved)
'''

WRITE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._native_pot_fields
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
aux,sherds=%r,%r
clear_result=info.SetBlockNew(saved['target'],{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
assert info.GetBlockNew(saved['target'],saved['dimension']).get('name')=='minecraft:air'
assert info.SetBlockNew(saved['target'],{'name':'minecraft:decorated_pot','aux':aux},0,saved['dimension'],True,False)
nbt=info.GetBlockEntityData(saved['dimension'],saved['target'])
assert nbt and nbt['id']['__value__']=='DecoratedPot',nbt
nbt['sherds']=[{'__type__':8,'__value__':name} for name in sherds]
accepted=info.SetBlockEntityData(saved['dimension'],saved['target'],nbt)
readback=info.GetBlockEntityData(saved['dimension'],saved['target'])
_result=json.dumps({'aux':aux,'requested':sherds,'accepted':accepted,'clear_result':clear_result,
 'block':info.GetBlockNew(saved['target'],saved['dimension']),'nbt':readback})
'''

READ = '''import json
import mod.client.extraClientApi as api
block=api.GetEngineCompFactory().CreateBlock(api.GetLevelId())
target,aux,sherds=%r,%r,%r
palette=block.GetBlockPaletteBetweenPos(target,target,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
actual=next(iter(data.get('common',{})),None)
actor=next(iter(data.get('actor',{}).get('minecraft:decorated_pot',{}).values()),None)
expected=list(sherds)
observed=[actor.get('decoratedPotShredNames'+str(index)) for index in range(4)] if actor else []
_result=json.dumps({'ready':actual==('minecraft:decorated_pot',aux) and observed==expected,
 'material':actual,'actor':actor,'observed':observed,'expected':expected})
'''

CLEANUP = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._native_pot_fields
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
results=[]
for pos in (saved['target'],saved['support']):
 results.append(info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False))
remaining=[pos for pos in (saved['target'],saved['support'])
 if info.GetBlockNew(pos,saved['dimension']).get('name')!='minecraft:air']
if not remaining:del sys._native_pot_fields
_result=json.dumps({'restored':not remaining,'remaining':remaining,'set_results':results})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = {'schema_version': 1, 'completed': False, 'rows': [],
              'scope': 'Native NBT sherd order and client field mapping; visual face mapping separate',
              'candidate_reference': 'dragonfly/server/block/decorated_pot.go:sherds'}
    with Client(timeout=30) as client:
        try:
            if execute(client, 'import sys\n_result=hasattr(sys,"_native_pot_fields")'):
                report['previous_cleanup'] = execute(client, CLEANUP)
                assert report['previous_cleanup']['restored'], report['previous_cleanup']
            report['setup'] = execute(client, SETUP)
            for aux in range(4):
                row = execute(client, WRITE % (aux, SHERDS))
                report['rows'].append(row)
                values = row['nbt'].get('sherds')
                assert row['accepted'] and values == [
                    {'__type__': 8, '__value__': name} for name in SHERDS], row
                deadline = time.monotonic() + 12
                while True:
                    row['client'] = execute(client, READ % (tuple(report['setup']['target']), aux, SHERDS), True)
                    if row['client']['ready']:
                        break
                    if time.monotonic() >= deadline:
                        raise AssertionError('Native pot replication did not match: %r' % row['client'])
                    time.sleep(.15)
                write_json(args.output, report)
            report['completed'] = True
        finally:
            if execute(client, 'import sys\n_result=hasattr(sys,"_native_pot_fields")'):
                report['cleanup'] = execute(client, CLEANUP)
            report['restored'] = report.get('cleanup', {}).get('restored', False)
            report['completed'] = report['completed'] and report['restored']
            if 'setup' in report:
                report['game_version'] = report['setup']['game_version']
                report['palette_sha256'] = report['setup']['palette_sha256']
            write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'rows': len(report['rows']), 'report': str(args.output.resolve())}))


if __name__ == '__main__':
    main()
