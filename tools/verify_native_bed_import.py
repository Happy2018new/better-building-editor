"""Verify bed import/request/packet/share paths in an owned disposable world.

No desktop input or persistent library writes. Selection registration and packet
acknowledgments are injected fixture controls, not real surveying-item clicks.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import time

from probe_native_bed_capture import prepare_code, SEED, CLEANUP
from probe_native_palette_actors import Client, ROOT, run, write_report
from _session import load_session


CAPTURE = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.projection.transfer import Receiver
probe=sys._bed_capture_probe
host=api.GetSystem('ModernProjection','ModernProjectionServerSystem')
player=probe['player']
assert not host.jobs and player not in host.uploads, 'Do not interrupt an active job'
saved_region=host.world_regions.get(player)
saved_reply=host.reply
receiver=Receiver()
responses=[]
packet_rows=[]
identity=2070000001
low,high=probe['low'],probe['high']
size=tuple(high[i]-low[i]+1 for i in range(3))
def receive(actual_player,request,**data):
 assert actual_player==player and request==identity
 responses.append(data)
 if 'documentPacket' in data:
  packet=data['documentPacket']
  packet_rows.append(packet)
  receiver.feed(packet)
  host.request({'__id__':player,'request':identity,'action':'captureAck','sequence':packet['seq']})
try:
 host.reply=receive
 host.world_regions[player]=(probe['adapter'].dimension,low,size)
 host.request({'__id__':player,'request':identity,'action':'capture','clientCapture':True,
               'origin':low,'size':size})
 assert host.selection_locked(player)
 for unused in range(100):
  host.tick()
  if not host.jobs:break
 assert not host.jobs and not host.selection_locked(player),responses
 assert responses[-1].get('clientCapture') is True and not responses[-1].get('error'),responses
 assert receiver.result is not None and len(receiver.result.blocks)==2,responses
 _result=json.dumps({'packets':packet_rows,'ticks':unused+1,'responses':responses,
                     'size':size,'low':low,'unlocked':True})
finally:
 host.jobs.pop(player,None)
 host.reply=saved_reply
 if saved_region is None:host.world_regions.pop(player,None)
 else:host.world_regions[player]=saved_region
'''

IMPORT = '''import json
import mod.client.extraClientApi as api
from modern_projection.projection.model import Document
from modern_projection.projection.cell import actor_data,background,foreground,freeze
from modern_projection.projection.world_capture import merge_palette,restore_omitted_palette_cells,merge_entity_document
from modern_projection.projection.visible_actor import entity_nbt
from modern_projection.projection.transfer import Receiver
from modern_projection.projection.sharing_codec import encode_steps,decode_steps
from modern_projection.projection.nbt_spatial import root_payload,scalar
data=json.loads(%r)
low=tuple(data['low'])
size=tuple(data['size'])
high=tuple(low[i]+size[i]-1 for i in range(3))
factory=api.GetEngineCompFactory()
palette=factory.CreateBlock(api.GetLevelId()).GetBlockPaletteBetweenPos(low,high,False)
assert palette is not None
doc=Document(size)
info=factory.CreateBlockInfo(api.GetLevelId())
source=palette.SerializeBlockPalette()
merge_palette(doc,source,(0,0,0),size,low)
restore_omitted_palette_cells(doc,source,(0,0,0),size,low,info.GetBlock)
receiver=Receiver()
for packet in data['packets']:receiver.feed(packet)
merge_entity_document(doc,receiver.result)
share=next(row['text'] for row in encode_steps(doc) if 'text' in row)
decoded=next(row['document'] for row in decode_steps(share) if 'document' in row)
assert decoded.to_data()==doc.to_data()
rows=[]
for pos,value in doc.blocks.items():
 nbt=entity_nbt(actor_data(value))
 root=root_payload(nbt)
 assert scalar(root,'color')==7,(pos,nbt)
 assert [scalar(root,axis) for axis in ('x','y','z')]==list(pos),(pos,nbt)
 rows.append({'pos':pos,'front':foreground(value),'back':background(value),'nbt':freeze(nbt)})
assert len(rows)==2,rows
_result=json.dumps({'rows':rows,'share_prefix':share[:4],'share_bytes':len(share),
                    'share_roundtrip':True,'source_palette':freeze(source)})
'''


def refresh(client):
    for name in ('native_palette_actor_data', 'native_palette_actor', 'world_capture'):
        path = ROOT / 'behavior_pack/modern_projection/projection' / (name + '.py')
        code = ('import base64\nimport modern_projection.projection.%s as module\n'
                'exec(compile(base64.b64decode(%r),%r,"exec"),module.__dict__)\n_result=True' %
                (name, base64.b64encode(path.read_bytes()).decode('ascii'), str(path)))
        run(client, code, True)
        run(client, code, False)
    path = ROOT / 'behavior_pack/modern_projection/server_system.py'
    code = ('import base64\nimport modern_projection.server_system as module\n'
            'exec(compile(base64.b64decode(%r),%r,"exec"),module.__dict__)\n'
            'import mod.server.extraServerApi as api\n'
            "host=api.GetSystem('ModernProjection','ModernProjectionServerSystem')\n"
            'type(host).capture_entities=module.ModernProjectionServerSystem.capture_entities.im_func\n_result=True' %
            (base64.b64encode(path.read_bytes()).decode('ascii'), str(path)))
    run(client, code, True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--height-offset', type=int, default=24)
    args = parser.parse_args()
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != ROOT:
        parser.error('The owned session belongs to another project')
    if not 12 <= args.height_offset <= 64:
        parser.error('Choose a bounded disposable region 12 to 64 blocks above the player')
    os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=args.owner,
                      MCDEV_MCP_URL=session['mcp_url'], MCDEV_GAME_PID=str(session['game_pid']))
    report = {'schema_version': 1, 'completed': False, 'restored': False, 'rows': [],
              'method': 'Production paired bed writes; real capture request and tick; injected selection/ack; MP4 roundtrip; v1',
              'scope': 'Data only, no real clicks, persistent library writes, or pixel acceptance',
              'session_file': session['session_file']}
    with Client(timeout=30) as client:
        refresh(client)
        try:
            report.update(run(client, prepare_code((6, args.height_offset, 6)), True))
            for index, case in enumerate(report['cases']):
                row = run(client, SEED % index, True)
                report['rows'].append(row)
                time.sleep(.35)
                capture = run(client, CAPTURE, True)
                imported = run(client, IMPORT % json.dumps(capture), False)
                row.update(capture=capture, imported=imported)
                wanted = [(entry['front'], entry['back']) for entry in row['observed']]
                actual = [(entry['front'], entry['back']) for entry in imported['rows']]
                assert sorted(actual) == sorted(wanted), (case, actual, wanted)
                write_report(args.output, report)
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            report['cleanup'] = run(client, CLEANUP, True)
            report['restored'] = report['cleanup']['restored']
            write_report(args.output, report)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'cases': len(report['rows']), 'output': str(args.output)}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
