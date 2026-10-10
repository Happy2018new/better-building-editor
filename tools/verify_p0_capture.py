"""Native NBT capture, authoritative selection lock and omitted-part regression."""
import argparse
import base64
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value

SERVER = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
f=api.GetEngineCompFactory()
p=api.GetPlayerList()[0]
s=api.GetSystem('ModernProjection','ModernProjectionServerSystem')
a=WorldAdapter(p)
'''
CLIENT = '''import json,sys
import mod.client.extraClientApi as api
s=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
b=s.bridge
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    evidence = {'schema': 1, 'checks': []}
    with Client(timeout=30) as client:
        def run(code, side=False):
            value = return_value(client.call('execute_code', {
                'code': (CLIENT if side else SERVER) + code,
                'is_client': side, 'direct_return': True}))
            return json.loads(value) if isinstance(value, str) else value

        run("if hasattr(sys,'_p0_saved_notify'):s.NotifyToServer=sys._p0_saved_notify\n_result=True", True)

        for module in ('nbt_spatial', 'block_groups', 'world_capture', 'transfer'):
            path = ROOT / 'behavior_pack/modern_projection/projection' / (module + '.py')
            code = ('import base64\nimport modern_projection.projection.%s as refreshed\n'
                    'exec(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                    '_result=True' % (module, base64.b64encode(path.read_bytes()).decode('ascii'), str(path)))
            run(code)
            run(code, True)
        path = ROOT / 'behavior_pack/modern_projection/projection/bridge.py'
        run('import base64\nimport modern_projection.projection.bridge as refreshed\n'
            'exec(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
            'type(b).capture_region=refreshed.ClientBridge.capture_region.im_func\n_result=True' %
            (base64.b64encode(path.read_bytes()).decode('ascii'), str(path)), True)
        setup = run('''positions=sys._p0_acceptance_positions
box=positions[1]
assert a.info.SetBlockNew(box,{'name':'minecraft:air','aux':0},0,a.dimension,True,False)
assert a.info.SetBlockNew(box,{'name':'minecraft:purple_shulker_box','aux':0},0,a.dimension,True,False)
item=f.CreateItem(p)
assert item.SpawnItemToContainer({'itemName':'minecraft:diamond','count':7,'auxValue':0},0,box,a.dimension)
item.SpawnItemToContainer({'itemName':'minecraft:apple','count':3,'auxValue':0},0,positions[8],a.dimension)
f.CreateTime(api.GetLevelId()).SetTimeOfDay(6000)
_result=json.dumps({'region':s.world_regions[p],'shulker':box,'chest':positions[8],
 'shulker_nbt':a.info.GetBlockEntityData(a.dimension,box),
 'chest_nbt':a.info.GetBlockEntityData(a.dimension,positions[8])})''')
        evidence['fixture'] = setup
        time.sleep(.3)
        run('''assert None not in b.corners,repr(b.corners)
if hasattr(sys,'_p0_saved_notify'):s.NotifyToServer=sys._p0_saved_notify
sys._p0_saved_notify=s.NotifyToServer
sys._p0_held_acks=[]
sys._p0_capture_corners=list(b.corners)
def hold_ack(event,data):
 if event=='ProjectionRequest' and data.get('action')=='captureAck':
  sys._p0_held_acks.append((event,data))
 else:
  sys._p0_saved_notify(event,data)
s.NotifyToServer=hold_ack
b.capture()
_result=True''', True)
        try:
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                progress = run('''_result=json.dumps({'held':len(sys._p0_held_acks),
 'pending':b.pending,'message':b.session.editor.message})''', True)
                if progress['held']:
                    break
                time.sleep(.1)
            else:
                raise AssertionError('Native capture never reached a held packet: %r' % progress)
            before = run('''_result=json.dumps({'locked':s.selection_locked(p),
 'region':s.world_regions.get(p),'point':s.world_points.get(p)})''')
            assert before['locked'], before
            run('''s.world_tool_request({'__id__':p,'action':'reset'})
f.CreateBlockInfo(p).PlayerUseItemToPos(sys._p0_acceptance_positions[0],
 api.GetMinecraftEnum().ItemPosType.CARRIED,0,1)
_result=True''')
            time.sleep(.2)
            after = run('''_result=json.dumps({'locked':s.selection_locked(p),
 'region':s.world_regions.get(p),'point':s.world_points.get(p)})''')
            assert before == after, (before, after)
            visible = run('''_result=json.dumps({'before':sys._p0_capture_corners,
 'after':b.corners,'message':b.session.editor.message})''', True)
            assert visible['before'] == visible['after'], visible
            evidence.update(lock=after, visible=visible)
        finally:
            run('''s.NotifyToServer=sys._p0_saved_notify
held=sys._p0_held_acks
sys._p0_held_acks=[]
for event,data in held:s.NotifyToServer(event,data)
_result=True''', True)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            status = run('''_result=json.dumps({'pending':b.pending,'busy':b.session.busy,
 'message':b.session.editor.message})''', True)
            if status['pending'] is None:
                break
            time.sleep(.1)
        assert status['pending'] is None, status
        assert not run('_result=s.selection_locked(p)'), 'Capture lock was not released'
        document = run('''from modern_projection.projection.cell import foreground,background,actor_data
from modern_projection.projection.visible_actor import entity_nbt
doc=b.session.editor.document
rows=[]
for pos,value in doc.blocks.items():
 nbt=entity_nbt(actor_data(value))
 if nbt is not None:rows.append({'pos':pos,'front':foreground(value),'nbt':nbt})
_result=json.dumps({'size':doc.size,'count':len(doc.blocks),'actors':rows,
 'door_lower':foreground(doc.get((18,0,0))),
 'door_upper':foreground(doc.get((18,1,0))),
 'fence':foreground(doc.get((0,0,0))), 'water':background(doc.get((0,0,0)))})''', True)
        assert document['door_upper'] == ['minecraft:wooden_door', 9], document
        assert document['water'][0] == 'minecraft:water', document
        by_name = {row['front'][0]: row for row in document['actors']}
        assert by_name['minecraft:purple_shulker_box']['nbt']['Items'], document
        assert any(row['front'][0] == 'minecraft:chest' and row['nbt'].get('Items')
                   for row in document['actors']), document
        evidence.update(document=document, status=status)
        run('''s.tool_reset()
_result=True''', True)
        time.sleep(.1)
        assert run('_result=s.world_regions.get(p)') is None, 'Selection clear was not accepted'
        evidence['checks'] = ['server selection lock', 'silent reset and use rejection',
                              'visible corners unchanged', 'ack releases lock',
                              'shulker inventory captured', 'chest inventory captured',
                              'actual omitted door half restored', 'background water preserved',
                              'selection clear accepted after transfer']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n', encoding='utf8')
    print(json.dumps({'evidence': str(args.output.resolve()), 'checks': evidence['checks']}))


if __name__ == '__main__':
    main()
