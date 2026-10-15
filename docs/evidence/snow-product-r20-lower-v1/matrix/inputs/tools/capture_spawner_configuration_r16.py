"""Capture native spawner configuration after spawn-egg use in an owned world.

Only the disposable fixture is written. Original block/NBT data is restored
and checked even when a native interaction fails; failure remains in the report.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session
from mcdk import Client, return_value

SETUP = '''import json,math
import mod.server.extraServerApi as api
assert api.GetMinecraftVersion()=='1.21.130.0'
assert not hasattr(api,'_spawner_r16'), 'Restore the previous fixture first'
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
assert dimension==0
info=factory.CreateBlockInfo(player)
foot=factory.CreatePos(player).GetFootPos()
origin=(int(math.floor(foot[0]))-6,int(math.floor(foot[1]))+2,int(math.floor(foot[2]))+6)
rows=[]
for name in ('mob_spawner','trial_spawner'):
 for egg in (None,'pig_spawn_egg','zombie_spawn_egg'):
  index=len(rows)
  rows.append({'id':name+'_'+(egg or 'empty'),'name':'minecraft:'+name,
   'egg':egg,'pos':(origin[0]+index*2,origin[1],origin[2])})
positions=[]
for row in rows:
 positions.extend((row['pos'],(row['pos'][0],row['pos'][1]-1,row['pos'][2])))
journal=[]
for pos in positions:
 block=info.GetBlockNew(pos,dimension)
 assert isinstance(block,dict) and block.get('name'),('Unloaded fixture',pos)
 journal.append({'pos':pos,'block':block,'nbt':info.GetBlockEntityData(dimension,pos)})
saved={'rows':rows,'journal':journal,'player':player,'dimension':dimension}
api._spawner_r16=saved
for row in rows:
 pos=row['pos']
 assert info.SetBlockNew((pos[0],pos[1]-1,pos[2]),{'name':'minecraft:stone','aux':0},0,dimension,True,False)
 row['placed']=info.SetBlockNew(pos,{'name':row['name'],'aux':0},0,dimension,True,False)
 row['before']=info.GetBlockEntityData(dimension,pos)
 if row['egg']:
  item={'newItemName':'minecraft:'+row['egg'],'newAuxValue':0,'count':1}
  row['used']=factory.CreateGame(api.GetLevelId()).UseItemToPos(item,dimension,pos,1)
 row['after_immediate']=info.GetBlockEntityData(dimension,pos)
 row['block']=info.GetBlockNew(pos,dimension)
 row['states']=factory.CreateBlockState(api.GetLevelId()).GetBlockStates(pos,dimension)
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'rows':rows,'origin':origin,'journal_count':len(journal)})
'''

READ = '''import json
import mod.server.extraServerApi as api
saved=api._spawner_r16
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
_result=json.dumps({'rows':[dict(row,after_delayed=info.GetBlockEntityData(saved['dimension'],tuple(row['pos'])))
 for row in saved['rows']]})
'''

RESTORE = '''import mod.server.extraServerApi as api
saved=getattr(api,'_spawner_r16',None)
assert saved is not None
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
rows=[]
for entry in reversed(saved['journal']):
 pos=tuple(entry['pos'])
 changed=info.SetBlockNew(pos,entry['block'],0,saved['dimension'],True,False)
 nbt_result=info.SetBlockEntityData(saved['dimension'],pos,entry['nbt']) if entry['nbt'] is not None else None
 actual=info.GetBlockNew(pos,saved['dimension'])
 actual_nbt=info.GetBlockEntityData(saved['dimension'],pos)
 rows.append({'pos':pos,'changed':changed,'nbt_result':nbt_result,
  'block_restored':actual==entry['block'],'nbt_restored':actual_nbt==entry['nbt'],
  'actual':actual,'expected':entry['block']})
ok=all(row['block_restored'] and row['nbt_restored'] for row in rows)
if ok:del api._spawner_r16
_result={'restored':ok,'rows':rows}
'''


def execute(client, source, output, name):
    (output / (name + '.py')).write_text(source, encoding='ascii')
    result = client.call('execute_code', {'code': source, 'is_client': False,
                                          'direct_return': True})
    (output / (name + '-receipt.json')).write_text(
        json.dumps(result, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    if result.get('isError'):
        raise RuntimeError(result)
    value = return_value(result)
    return json.loads(value) if isinstance(value, str) else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--restore-only', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ.update(MCDEV_SESSION_FILE=str(args.session), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    session = load_session(args.session, args.owner, live=True)
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
              'engine_version': '3.10.0.420447', 'owner': args.owner,
              'project': session['project'], 'game_pid': session['game_pid'],
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'pixel_acceptance': False, 'completed': False}
    try:
        with Client(timeout=45) as client:
            if args.restore_only:
                report['restore'] = execute(client, RESTORE, args.output, 'restore')
            else:
                attempted = False
                try:
                    attempted = True
                    report['setup'] = execute(client, SETUP, args.output, 'setup')
                    time.sleep(2)
                    report['read'] = execute(client, READ, args.output, 'read')
                    report['completed'] = True
                finally:
                    if attempted:
                        report['restore'] = execute(client, RESTORE, args.output, 'restore')
            if report['restore']['restored'] is not True:
                raise RuntimeError('Spawner fixture restoration did not match original blocks/NBT')
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        (args.output / 'result.json').write_text(
            json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'completed': report['completed'],
                      'restored': report['restore']['restored'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
