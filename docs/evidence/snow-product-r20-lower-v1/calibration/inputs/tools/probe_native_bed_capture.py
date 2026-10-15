"""Record paired-bed palette omissions in an owned disposable native world.

This data-only probe does not activate a window or send desktop input. It
compares exact and support-padded bounds, ordinary block reads, and entity
discovery; successful writes are not a rendering acceptance claim.
"""
import argparse
import json
import os
import time

from probe_native_palette_actors import Client, read_palette, run, write_report
from _session import load_session


PREPARE_TEMPLATE = '''import json,sys,math
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection import block_registry as registry
from modern_projection.projection.cell import AIR
assert not hasattr(sys,'_bed_capture_probe')
player=api.GetPlayerList()[0]
adapter=WorldAdapter(player)
foot=adapter.factory.CreatePos(player).GetFootPos()
origin=tuple(int(math.floor(foot[i]))+%r[i] for i in range(3))
region=tuple((origin[0]+x,origin[1]+y,origin[2]+z)
             for x in range(-2,3) for y in (-1,0,1) for z in range(-2,3))
for pos in region:assert adapter.read(pos)==AIR,(pos,adapter.read(pos))
cases=[{'aux':aux,'wet':wet,'color':7} for aux in registry.aux_values('minecraft:bed')
       for wet in (False,True)]
sys._bed_capture_probe={'player':player,'origin':origin,'region':region,'cases':cases}
_result=json.dumps({'game_version':registry.source_version(),'palette_sha256':registry.fingerprint(),
 'origin':origin,'cases':cases})
'''


def prepare_code(offset=(6, 12, 6)):
    return PREPARE_TEMPLATE % (offset,)


PREPARE = prepare_code()

SEED = '''import json,sys
from modern_projection.server_system import WorldAdapter
from modern_projection.projection import block_registry as registry,block_groups,entity_defaults
from modern_projection.projection.cell import AIR,make_cell,foreground,background
from modern_projection.projection.nbt_spatial import root_payload,set_scalar
from modern_projection.projection.visible_actor import compose_actor
probe=sys._bed_capture_probe
adapter=WorldAdapter(probe['player'])
for unused in range(2):
 for pos in probe['region']:
  if adapter.read(pos)!=AIR:assert adapter.write(pos,AIR),(pos,'clear')
origin=probe['origin']
for pos in probe['region']:
 if pos[1]==origin[1]-1:assert adapter.write(pos,('minecraft:stone',0))
case=probe['cases'][%d]
value=('minecraft:bed',case['aux'])
delta,partner=block_groups.group_partner(value)
pair=[(origin,value),(tuple(origin[i]+delta[i] for i in range(3)),partner)]
pair.sort(key=lambda row:not registry.states(row[1])['head_piece_bit'])
adapter=WorldAdapter(probe['player'])
observed=[]
for pos,material in pair:
 nbt=entity_defaults.nbt('minecraft:bed',pos)
 assert nbt is not None
 set_scalar(root_payload(nbt),'color',case['color'])
 cell=make_cell(material,('minecraft:water',0) if case['wet'] else AIR,compose_actor(None,nbt))
 assert adapter.write(pos,cell),(case,pos,cell)
 actual=adapter.read(pos)
 assert foreground(actual)==material and background(actual)==background(cell),(case,pos,actual,cell)
 observed.append({'pos':pos,'front':foreground(actual),'back':background(actual)})
low=tuple(min(pos[i] for pos,material in pair) for i in range(3))
high=tuple(max(pos[i] for pos,material in pair) for i in range(3))
padded_low=(low[0]-1,low[1]-1,low[2]-1)
padded_high=(high[0]+1,high[1]+1,high[2]+1)
probe.update(adapter=adapter,pair=pair,low=low,high=high,padded_low=padded_low,padded_high=padded_high)
_result=json.dumps({'case':case,'observed':observed,'low':low,'high':high,
 'padded_low':padded_low,'padded_high':padded_high})
'''

SERVER_READ = '''import json,sys
from modern_projection.projection.cell import freeze
from modern_projection.projection.world_capture import native_actor_cells
from modern_projection.projection.nbt_spatial import root_payload,scalar
probe=sys._bed_capture_probe
adapter=probe['adapter']
palettes={}
for label,low,high in (('exact',probe['low'],probe['high']),
                       ('padded',probe['padded_low'],probe['padded_high'])):
 palette=adapter.palette_block.GetBlockPaletteBetweenPos(adapter.dimension,low,high,False)
 source=None if palette is None else palette.SerializeBlockPalette()
 located=[]
 error=None
 if source is not None:
  try:
   located=list(native_actor_cells(source,(0,0,0),tuple(high[i]-low[i]+1 for i in range(3))))
  except ValueError as failure:error=str(failure)
 palettes[label]={'palette':freeze(source),'entity_cells':located,'discovery_error':error}
actors=[]
for pos,material in probe['pair']:
 nbt=adapter.info.GetBlockEntityData(adapter.dimension,pos)
 root=root_payload(nbt)
 actors.append({'pos':pos,'nbt':freeze(nbt),'id':scalar(root,'id'),
  'color':scalar(root,'color'),'coordinates':[scalar(root,axis) for axis in ('x','y','z')]})
_result=json.dumps({'palettes':palettes,'actors':actors})
'''

CLIENT_READ = '''import json
import mod.client.extraClientApi as api
from modern_projection.projection.cell import freeze
factory=api.GetEngineCompFactory()
block=factory.CreateBlock(api.GetLevelId())
info=factory.CreateBlockInfo(api.GetLevelId())
observed=json.loads(%r)
palettes={}
for label,low,high in (('exact',%r,%r),('padded',%r,%r)):
 palette=block.GetBlockPaletteBetweenPos(low,high,False)
 palettes[label]=None if palette is None else freeze(palette.SerializeBlockPalette())
actual=[{'pos':row['pos'],'front':info.GetBlock(tuple(row['pos']))} for row in observed]
_result=json.dumps({'palettes':palettes,'observed':actual})
'''

CLEANUP = '''import json,sys
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR
probe=getattr(sys,'_bed_capture_probe',None)
residue=[]
if probe is not None:
 adapter=WorldAdapter(probe['player'])
 for unused in range(2):
  for pos in probe['region']:
   if adapter.read(pos)!=AIR:adapter.write(pos,AIR)
 residue=[pos for pos in probe['region'] if adapter.read(pos)!=AIR]
 if not residue:del sys._bed_capture_probe
_result=json.dumps({'restored':not residue,'residue':residue})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    args = parser.parse_args()
    session = load_session(args.session, args.owner, live=True)
    os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=args.owner,
                      MCDEV_MCP_URL=session['mcp_url'], MCDEV_GAME_PID=str(session['game_pid']))
    from pathlib import Path
    output = Path(args.output)
    report = {'schema_version': 1, 'completed': False, 'restored': False, 'rows': [],
              'method': 'Complete production-written bed pair, exact/padded native palettes, typed color; v1',
              'scope': 'Data only; no pixel or player-item acceptance',
              'session_file': session['session_file']}
    with Client(timeout=30) as client:
        try:
            report.update(run(client, PREPARE, True))
            for index, case in enumerate(report['cases']):
                row = run(client, SEED % index, True)
                report['rows'].append(row)
                time.sleep(.35)
                row['server'] = read_palette(client, SERVER_READ, True)
                row['client'] = read_palette(client, CLIENT_READ % (
                    json.dumps(row['observed']), tuple(row['low']), tuple(row['high']),
                    tuple(row['padded_low']), tuple(row['padded_high'])))
                write_report(output, report)
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            report['cleanup'] = run(client, CLEANUP, True)
            report['restored'] = report['cleanup']['restored']
            write_report(output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'cases': len(report['rows']), 'output': str(output)}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
