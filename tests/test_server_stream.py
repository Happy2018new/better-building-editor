"""Server stream lifecycle and read failures without a running game."""
import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack'))
for name in ('mod', 'mod.server', 'mod.server.extraServerApi'):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules['mod.server.extraServerApi'].GetServerSystemCls = lambda: object
from modern_projection import server_system as server
from modern_projection.projection.model import Document, AIR
from modern_projection.projection.transfer import packets, Receiver
from modern_projection.projection.cell import make_cell


class Palette(object):
    def DeserializeBlockPalette(self, data):
        self.data = data
        return True


class ServerStreamTests(unittest.TestCase):
    def setUp(self):
        self.host = object.__new__(server.ModernProjectionServerSystem)
        self.host.jobs = {}
        self.host.uploads = {}
        self.host.tool_last_use = {}
        self.host.terminal_last_use = {}
        self.host.aura_tick = 0
        self.aura_states = []
        self.host.BroadcastToAllClient = lambda event, value: self.aura_states.append((event, value))
        self.host.world_regions = {}
        self.host.world_points = {}
        self.replies = []
        self.host.reply = lambda player, request, **data: self.replies.append((player, request, data))
        self.creative = True
        self.dimension = 0
        self.abilities = dict(op=True, build=True, mine=True)
        self.blocks = {}
        self.writes = []
        self.palette_writes = []
        self.actor_writes = []
        self.allowed_checks = 0
        self.liquids = {}
        self.actors = {}
        self.factory = types.SimpleNamespace(
            CreateGame=lambda level: types.SimpleNamespace(GetPlayerGameType=lambda player: 1 if self.creative else 0),
            CreateDimension=lambda player: types.SimpleNamespace(GetEntityDimensionId=lambda: self.dimension),
            CreatePlayer=lambda player: types.SimpleNamespace(GetPlayerAbilities=lambda: self.abilities),
            CreatePos=lambda player: types.SimpleNamespace(GetFootPos=lambda: (0,64,0)),
            CreateBlockInfo=lambda level: types.SimpleNamespace(
                GetBlockNew=lambda pos, dim: dict(zip(('name','aux'),self.blocks.get(pos,AIR))),
                GetBlockBasicInfo=lambda name: {'name':name}, GetBlockEntityData=lambda dim,pos: None,
                GetLiquidBlock=lambda pos, dim: self.liquids.get(pos),
                SetBlockEntityData=self.set_actor, SetBlockNew=self.write),
            CreateBlock=lambda level: types.SimpleNamespace(
                GetBlankBlockPalette=Palette,
                SetBlockByBlockPalette=self.write_palette),
            CreateItem=lambda level: types.SimpleNamespace(GetItemInfoByBlockName=lambda n,a: {},
                GetPlayerItem=lambda kind,slot: {'newItemName':'minecraft:stick'}))
        for name,value in [('GetPlayerList',lambda:['real_player','player']), ('GetLevelId',lambda:'level'),
                           ('GetEngineCompFactory',lambda:self.factory),
                           ('GetMinecraftEnum',lambda:types.SimpleNamespace(
                               ItemPosType=types.SimpleNamespace(CARRIED=1)))]:
            p = patch.object(server.serverApi,name,value,create=True)
            p.start(); self.addCleanup(p.stop)
        original_allowed = server.WorldAdapter.allowed
        def count_allowed(adapter):
            self.allowed_checks += 1
            return original_allowed(adapter)
        p = patch.object(server.WorldAdapter, 'allowed', count_allowed)
        p.start(); self.addCleanup(p.stop)

    def write(self, pos, data, *unused):
        self.blocks[pos]=(data['name'].decode('utf8'),data['aux'])
        self.writes.append(pos)
        return True

    def write_palette(self, palette, dimension, pos, rotation, conflict):
        self.palette_writes.append((palette.data, dimension, pos, rotation, conflict))
        (name, aux), unused_positions = next(iter(palette.data['common'].items()))
        if isinstance(name, bytes):
            name = name.decode('utf8')
        self.blocks[pos] = (name, aux)
        self.writes.append(pos)
        return True

    def set_actor(self, dimension, pos, actor):
        self.actor_writes.append((dimension, pos, actor))
        return True

    def test_staff_state_snapshot_uses_server_equipment(self):
        self.factory.CreateItem=lambda player:types.SimpleNamespace(
            GetPlayerItem=lambda kind,slot:{'newItemName':
                'modern_projection:terminal' if player=='real_player' else 'minecraft:stick'})
        for unused in range(15):self.host.tick()
        self.assertEqual([('StaffAuraState',{'carried':{'real_player':'modern_projection:terminal'}})],
                         self.aura_states)

    def send(self, action='apply', doc=None, identity=1):
        for packet in packets(doc or Document((2,1,1),{(0,0,0):('minecraft:stone',0)})):
            self.host.request({'__id__':'player','request':identity,'action':action if packet['seq']==0 else 'upload',
                               'origin':(0,64,0),'stream':packet})

    def finish(self):
        for unused in range(100):
            if not self.host.jobs: return
            self.host.tick()
        self.fail('world job did not finish')

    def test_upload_cancellation_and_timeout_release_state(self):
        first = next(packets(Document((64, 100, 64))))
        self.host.request({'__id__': 'real_player', 'player': 'forged', 'request': 12, 'action': 'check', 'origin':(0,0,0), 'stream': first})
        self.assertIn('real_player', self.host.uploads)
        self.assertNotIn('forged', self.host.uploads)
        self.assertEqual(0, self.replies[-1][2]['uploadAck'])
        self.host.request({'__id__': 'real_player', 'request': 12, 'action': 'cancel'})
        self.assertEqual({}, self.host.uploads)
        self.assertTrue(self.replies[-1][2]['done'])
        self.host.request({'__id__': 'real_player', 'request': 13, 'action': 'check', 'origin':(0,0,0), 'stream': first})
        entry = self.host.uploads['real_player']
        self.host.uploads['real_player'] = entry[:3] + (0.,) + entry[4:]
        self.host.tick()
        self.assertEqual({}, self.host.uploads)
        self.assertIn('超时', self.replies[-1][2]['error'])

    def test_bad_packet_releases_upload_and_anonymous_requests_ignored(self):
        self.host.request({'request': 1, 'action': 'check', 'stream': {}})
        self.assertEqual([], self.replies)
        self.host.request({'__id__': 'player', 'request': 1, 'action': 'check', 'stream': {}})
        self.assertEqual({}, self.host.uploads)
        self.assertTrue(self.replies[-1][2]['done'])

    def test_capture_yields_packets_then_publishes_one_complete_document(self):
        stone = ('minecraft:stone', 0)
        adapter = types.SimpleNamespace(
            read=lambda p: stone if p == (0, 0, 0) else AIR,
            rebase=lambda value, offset: value)
        doc = Document((17, 16, 16))
        for unused in self.host.read_job('player', 7, 'capture', adapter, doc, (0, 0, 0)):
            pass
        receiver = Receiver()
        for unused_player, unused_request, data in self.replies:
            if 'documentPacket' in data:
                receiver.feed(data['documentPacket'])
        self.assertTrue(self.replies[-1][2]['streamed'])
        self.assertEqual(stone, receiver.result.get((0, 0, 0)))
        self.assertEqual(1, len(receiver.result.blocks))

    def test_survey_wand_marks_two_authorized_corners_without_world_writes(self):
        self.host.world_points = {}
        sent = []
        self.host.NotifyToClient = lambda player, event, payload: sent.append((player,event,payload))
        first = {'entityId':'player', 'itemDict':{'newItemName':'modern_projection:survey_wand'},
                 'dimensionId':0, 'x':0, 'y':64, 'z':0, 'face':4}
        second = dict(first, x=3, y=66, z=2, face=1)
        with patch.object(server.time, 'time', side_effect=(10., 11.)):
            self.host.tool_use_on(first)
            self.host.tool_use_on(second)
        self.assertTrue(first['ret'])
        self.assertTrue(second['ret'])
        self.assertEqual((0,64,0), sent[1][2]['origin'])
        self.assertEqual((4,3,3), sent[1][2]['size'])
        self.assertEqual(4, sent[0][2]['face'])
        self.assertEqual(1, sent[1][2]['face'])
        self.assertFalse(self.host.world_points)
        self.assertEqual((0,(0,64,0),(4,3,3)), self.host.world_regions['player'])
        self.assertFalse(self.writes)

    def test_world_tool_capture_cannot_forge_an_unselected_region(self):
        self.host.world_regions['player'] = (0, (0,64,0), (2,2,2))
        self.host.request({'__id__':'player', 'request':21, 'action':'capture',
                           'source':'world_item', 'origin':(1,64,0), 'size':(2,2,2)})
        self.assertFalse(self.host.jobs)
        self.assertIn('重新选择', self.replies[-1][2]['error'])
        self.host.request({'__id__':'player', 'request':22, 'action':'capture',
                           'source':'world_item', 'origin':(0,64,0), 'size':(2,2,2)})
        self.assertIn('player', self.host.jobs)
        self.finish()
        self.assertFalse(self.writes)

    def test_world_tool_hud_requests_require_holding_wand_and_nearby_target(self):
        original = self.factory.CreateItem
        carried = {'newItemName':'minecraft:stick'}
        self.factory.CreateItem = lambda player: types.SimpleNamespace(
            GetPlayerItem=lambda kind, slot: carried)
        p = patch.object(server.serverApi, 'GetMinecraftEnum',
                         lambda: types.SimpleNamespace(ItemPosType=types.SimpleNamespace(CARRIED=0)), create=True)
        p.start();self.addCleanup(p.stop)
        self.addCleanup(lambda: setattr(self.factory, 'CreateItem', original))
        sent = []
        self.host.NotifyToClient = lambda player, event, payload: sent.append(payload)
        request = {'__id__':'player', 'action':'point', 'pos':(0,64,0), 'face':5}
        self.host.world_tool_request(request)
        self.assertFalse(sent)
        carried['newItemName']='modern_projection:survey_wand'
        self.host.world_tool_request(dict(request, pos=(50,64,0)))
        self.assertIn('12 格', sent[-1]['error'])
        self.host.world_tool_request(request)
        self.assertEqual(0, sent[-1]['index'])
        self.assertEqual(5, sent[-1]['face'])
        self.host.world_tool_request({'__id__':'player','action':'reset'})
        self.assertTrue(sent[-1]['clear'])
        self.assertFalse(self.host.world_points)

    def test_survey_wand_rejects_oversize_and_wrong_dimension(self):
        self.host.world_points = {}
        sent = []
        self.host.NotifyToClient = lambda player, event, payload: sent.append(payload)
        point = {'entityId':'player', 'itemDict':{'newItemName':'modern_projection:survey_wand'},
                 'dimensionId':0, 'x':0, 'y':64, 'z':0}
        with patch.object(server.time, 'time', side_effect=(10., 11.)):
            self.host.tool_use_on(dict(point))
            self.host.tool_use_on(dict(point, x=64))
        self.assertIn('64', sent[-1]['error'])
        self.assertFalse(self.host.world_points)
        self.host.tool_use_on(dict(point, dimensionId=1))
        self.assertIn('维度', sent[-1]['error'])

    def test_terminal_item_use_requests_only_own_clients_ui(self):
        sent = []
        self.host.NotifyToClient = lambda player, event, payload: sent.append((player,event))
        args = {'playerId':'player', 'itemDict':{'newItemName':'modern_projection:terminal'}}
        self.host.tool_try_use(args)
        self.assertTrue(args['cancel'])
        self.assertEqual([('player','OpenProjectionUi')], sent)
        self.host.tool_try_use({'playerId':'player', 'itemDict':{'newItemName':'minecraft:stick'}})
        self.assertEqual(1, len(sent))

    def test_read_exception_finishes_job_with_error(self):
        def broken():
            raise ValueError('test read error')
            yield None
        self.host.jobs['player'] = (8, 'capture', broken(), None, 0)
        self.host.tick()
        self.assertEqual({}, self.host.jobs)
        self.assertEqual('test read error', self.replies[-1][2]['error'])

    def test_server_authorizes_creative_operator_build_and_mine_before_upload(self):
        first=next(packets(Document((1,1,1), {(0,0,0):('minecraft:stone',0)})))
        args={'__id__':'player','request':1,'action':'apply','origin':(0,64,0),'stream':first,
              'isCreative':True,'isOperator':True,'player':'real_player'}
        for missing in ('op','build','mine'):
            self.abilities[missing]=False
            self.host.request(args)
            self.assertFalse(self.host.uploads)
            self.assertTrue(self.replies[-1][2]['error'])
            self.abilities[missing]=True
        self.creative=False
        self.host.request(args)
        self.assertFalse(self.host.uploads)
        self.assertFalse(self.writes)

    def test_streamed_apply_and_removed_undo_cannot_modify_world(self):
        self.send();self.finish()
        self.assertEqual(('minecraft:stone',0),self.blocks[(0,64,0)])
        self.host.request({'__id__':'player','request':2,'action':'undo','player':'real_player'})
        self.finish()
        self.assertEqual(('minecraft:stone',0),self.blocks[(0,64,0)])
        self.assertIn('未知',self.replies[-1][2]['error'])

    def test_cancel_running_apply_keeps_written_prefix_and_stops_future_cells(self):
        doc = Document((3,1,1), {(i,0,0):('minecraft:stone',0) for i in range(3)})
        self.send(doc=doc)
        job = self.host.jobs['player'][2]
        original_step = job.step
        job.step = lambda budget=2048: original_step(1)
        self.host.tick()
        self.assertEqual([(0,64,0)], self.writes)
        self.host.request({'__id__':'player','request':1,'action':'cancel'})
        self.host.tick()
        self.assertEqual([(0,64,0)], self.writes)
        self.assertNotIn('player', self.host.jobs)
        self.assertEqual({'total':3,'processed':1,'written':1,'failed':0},
                         self.replies[-1][2]['progress'])

    def test_permission_is_checked_once_at_upload_start(self):
        stream=list(packets(Document((1,1,1), {(0,0,0):('minecraft:stone',0)})))
        self.host.request({'__id__':'player','request':1,'action':'apply','origin':(0,64,0),'stream':stream[0]})
        self.assertEqual(1, self.allowed_checks)
        self.abilities['op']=False
        for packet in stream[1:]:
            self.host.request({'__id__':'player','request':1,'action':'upload','stream':packet})
        self.assertFalse(self.host.uploads)
        self.finish()
        self.assertEqual(1, self.allowed_checks)
        self.assertEqual([(0,64,0)], self.writes)

        self.abilities['build']=False
        self.host.request({'__id__':'player','request':2,'action':'apply','origin':(0,64,0),'stream':stream[0]})
        self.assertFalse(self.host.uploads)
        self.assertEqual(2, self.allowed_checks)
        self.assertEqual(1, len(self.writes))

    def test_wrong_request_cannot_cancel_or_evict_another_upload(self):
        first=next(packets(Document((1,1,1))))
        self.host.request({'__id__':'player','request':1,'action':'check','origin':(0,64,0),'stream':first})
        self.host.request({'__id__':'player','request':2,'action':'cancel'})
        self.assertIn('player',self.host.uploads)
        self.host.request({'__id__':'player','request':2,'action':'upload','stream':{}})
        self.assertIn('player',self.host.uploads)
        self.host.request({'__id__':'player','request':1,'action':'upload','stream':{'seq':99,'kind':'end'}})
        self.assertFalse(self.host.uploads)
        self.assertFalse(self.writes)

    def test_target_bounds_dimension_and_complete_stream_are_required(self):
        first=next(packets(Document((1,1,1))))
        for origin in ((0,320,0),(1000,64,0)):
            self.host.request({'__id__':'player','request':1,'action':'apply','origin':origin,'stream':first})
            self.assertFalse(self.host.uploads)
        self.host.request({'__id__':'player','request':1,'action':'apply','origin':(0,64,0),'stream':first})
        self.dimension=1
        self.host.request({'__id__':'player','request':1,'action':'upload','stream':{'seq':1,'kind':'end'}})
        self.assertFalse(self.host.uploads)
        self.host.request({'__id__':'player','request':2,'action':'apply','origin':(0,64,0),'document':Document().to_data()})
        self.assertFalse(self.host.jobs)
        self.assertFalse(self.writes)

    def test_disconnected_identity_ignored(self):
        self.host.request({'__id__':'forged','request':1,'action':'undo'})
        self.assertFalse(self.replies)

    def test_projection_palette_lookup_is_bounded_read_only_and_available_in_survival(self):
        self.creative=False
        self.host.request({'__id__':'player','request':1,'action':'resolve','palette':[['minecraft:stone',0]]})
        self.finish()
        self.assertEqual([['minecraft:stone',0]],self.replies[-1][2]['palette'])
        self.assertFalse(self.writes)
        self.host.request({'__id__':'player','request':2,'action':'resolve','palette':[['minecraft:stone',0]]*65})
        self.assertFalse(self.host.jobs)
        self.assertTrue(self.replies[-1][2]['error'])

    def test_legacy_ids_preserve_axis_and_palette_complete_layers(self):
        aliases = {'log': ('log','spruce_log'), 'log2': ('log2','acacia_log'),
                   'leaves': ('oak_leaves','oak_leaves'), 'planks': ('planks','birch_planks'),
                   'grass': ('grass_block','grass_block'), 'stonebrick': ('stone_bricks','stone_bricks'),
                   'lit_redstone_lamp': ('redstone_lamp','redstone_lamp')}
        def item(name, aux):
            name = name.decode('utf8').split(':')[1]
            old,new = aliases.get(name,(name,name))
            if name == 'log' and aux == 13: old = new = 'spruce_wood'
            return dict(itemName='minecraft:'+old,newItemName='minecraft:'+new)
        def aux(name, states):
            if 'pillar_axis' in states: return {'y':0,'x':1,'z':2}[states['pillar_axis']]
            return int(states.get('persistent_bit',False)) + 2*int(states.get('update_bit',False))
        self.factory.CreateItem = lambda level: types.SimpleNamespace(GetItemInfoByBlockName=item)
        self.factory.CreateBlockState = lambda level: types.SimpleNamespace(
            GetBlockStatesFromAuxValue=lambda name,aux: {}, GetBlockAuxValueFromStates=aux)
        adapter = server.WorldAdapter('player')
        for old,data,new,result in [('log',5,'spruce_log',1),('log',9,'spruce_log',2),
                                    ('log',13,'spruce_wood',0),('log2',4,'acacia_log',1),
                                    ('leaves',12,'oak_leaves',3),('planks',2,'birch_planks',0),
                                    ('grass',0,'grass_block',0),('stonebrick',0,'stone_bricks',0),
                                    ('oak_stairs',2,'oak_stairs',2),('lit_redstone_lamp',0,'lit_redstone_lamp',0)]:
            self.assertEqual(('minecraft:'+new,result),adapter.canonical(('minecraft:'+old,data)))
        adapter.write((0,64,0),('minecraft:spruce_log',1))
        data = self.palette_writes[-1][0]
        self.assertEqual((1,1,1),data['volume'])
        self.assertEqual({(b'minecraft:spruce_log',0):[0]},data['common'])
        self.assertEqual({(b'minecraft:spruce_log',0):{b'pillar_axis':b'x'}},data['states'])
        adapter.write((0,64,0),make_cell(('minecraft:oak_stairs',0),('minecraft:water',0)))
        data = self.palette_writes[-1][0]
        self.assertEqual({(b'minecraft:water',0):[0]},data['extra'])
        self.assertIn((b'minecraft:oak_stairs',0),data['states'])
        self.assertFalse(data['eliminateAir'])

    def test_capture_reads_liquid_background_and_typed_actor_data(self):
        from modern_projection.projection.cell import background, actor_data
        front = {'name':'minecraft:oak_stairs', 'aux':0}
        self.blocks[(1,64,2)] = ('minecraft:oak_stairs',0)
        self.liquids[(1,64,2)] = {'name':'minecraft:water', 'aux':0}
        typed_actor = {'x': {'__type__':3, '__value__':1},
                       'y': {'__type__':3, '__value__':64},
                       'z': {'__type__':3, '__value__':2},
                       b'pairx': {'__type__':3, '__value__':9},
                       b'pairz': {'__type__':3, '__value__':10}}
        self.actors[(1,64,2)] = typed_actor
        self.factory.CreateBlockInfo = lambda level: types.SimpleNamespace(
            GetBlockNew=lambda pos, dim: front if pos == (1,64,2) else {'name':'minecraft:air','aux':0},
            GetLiquidBlock=lambda pos, dim: self.liquids.get(pos),
            GetBlockEntityData=lambda dim,pos: self.actors.get(pos),
            GetBlockBasicInfo=lambda name: {'name':name}, SetBlockNew=self.write,
            SetBlockEntityData=self.set_actor)
        adapter = server.WorldAdapter('player')
        cell = adapter.read((1,64,2))
        self.assertEqual(('minecraft:water',0), background(cell))
        self.assertEqual(typed_actor, actor_data(cell))
        local = adapter.rebase(cell, (-1,-64,-2))
        self.assertEqual(0, actor_data(local)['x']['__value__'])
        self.assertEqual(0, actor_data(local)['y']['__value__'])
        self.assertEqual(0, actor_data(local)['z']['__value__'])
        self.assertEqual(8, actor_data(local)[b'pairx']['__value__'])
        self.assertEqual(8, actor_data(local)[b'pairz']['__value__'])

    def test_actor_nbt_is_written_after_palette_with_rebased_coordinates(self):
        actor = {'id': {'__type__':8, '__value__':'Chest'},
                 'x': {'__type__':3, '__value__':0},
                 'y': {'__type__':3, '__value__':0},
                 'z': {'__type__':3, '__value__':0}}
        adapter = server.WorldAdapter('player')
        cell = make_cell(('minecraft:chest',0), AIR, actor)
        self.assertTrue(adapter.write((8,70,9), cell, (8,70,9)))
        self.assertEqual((0,(8,70,9)), self.actor_writes[-1][:2])
        actor = self.actor_writes[-1][2]
        self.assertEqual(b'Chest', actor[b'id'][b'__value__'])
        self.assertEqual(8, actor[b'x'][b'__value__'])
        self.assertEqual(70, actor[b'y'][b'__value__'])
        self.assertEqual(9, actor[b'z'][b'__value__'])

    def test_apply_writes_palette_without_reading_target_cells(self):
        pos = (0,64,0)
        self.blocks[pos] = ('minecraft:grass',0)
        reads = []
        def read(pos, dim):
            reads.append(pos)
            name, aux = self.blocks.get(pos, AIR)
            return {'name':name,'aux':aux}
        self.factory.CreateBlockInfo = lambda level: types.SimpleNamespace(
            GetBlockNew=read, GetBlockBasicInfo=lambda name: {'name':name},
            GetBlockEntityData=lambda dim,pos: None, SetBlockNew=self.write)
        self.send(doc=Document((1,1,1), {(0,0,0):('minecraft:stone',0)}))
        self.finish()
        self.assertFalse(self.replies[-1][2].get('error'))
        self.assertEqual(('minecraft:stone',0), self.blocks[pos])
        self.assertEqual([pos], self.writes)
        self.assertEqual([], reads)


if __name__ == '__main__':
    unittest.main()
