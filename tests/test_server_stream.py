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
        self.entity_reads = []
        self.palette_reads = []
        self.state_writes = []
        self.factory = types.SimpleNamespace(
            CreateGame=lambda level: types.SimpleNamespace(GetPlayerGameType=lambda player: 1 if self.creative else 0),
            CreateDimension=lambda player: types.SimpleNamespace(GetEntityDimensionId=lambda: self.dimension),
            CreatePlayer=lambda player: types.SimpleNamespace(GetPlayerAbilities=lambda: self.abilities),
            CreatePos=lambda player: types.SimpleNamespace(GetFootPos=lambda: (0,64,0)),
            CreateBlockInfo=lambda level: types.SimpleNamespace(
                GetBlockNew=lambda pos, dim: dict(zip(('name','aux'),self.blocks.get(pos,AIR))),
                GetBlockBasicInfo=lambda name: {'name':name}, GetBlockEntityData=self.read_entity,
                GetLiquidBlock=lambda pos, dim: self.liquids.get(pos),
                SetSignBlockText=lambda pos, text, dim, side: True,
                SetBlockEntityData=self.set_actor, SetBlockNew=self.write,
                SetLiquidBlock=self.set_liquid),
            CreateBlockState=lambda level: types.SimpleNamespace(
                GetBlockAuxValueFromStates=lambda name, properties:
                    properties['direction'] + 8 * int(properties['head_piece_bit']) +
                    4 * int(properties['occupied_bit']),
                SetBlockStates=lambda pos, properties, dimension:
                    self.state_writes.append((pos, properties, dimension)) or True),
            CreateBlockEntity=lambda level: types.SimpleNamespace(
                SetSignTextStyle=lambda pos, dim, color, glow, side: True),
            CreateBlock=lambda level: types.SimpleNamespace(
                GetBlankBlockPalette=Palette,
                GetBlockPaletteBetweenPos=self.read_palette,
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

    def read_entity(self, dim, pos):
        self.entity_reads.append((dim, pos))
        return self.actors.get(pos)

    def read_palette(self, dim, low, high, eliminate):
        self.palette_reads.append((dim, low, high))
        size = tuple(high[i] - low[i] + 1 for i in range(3))
        doc = Document(size)
        for local in doc.points():
            pos = tuple(low[i] + local[i] for i in range(3))
            value = self.blocks.get(pos, AIR)
            if value != AIR:
                doc.blocks[local] = make_cell(value, nbt={} if pos in self.actors else None)
        return types.SimpleNamespace(SerializeBlockPalette=doc.palette_data)

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

    def set_liquid(self, pos, value, dimension):
        name = value['name'].decode('utf8')
        if name == 'minecraft:air':
            self.liquids.pop(pos, None)
        else:
            self.liquids[pos] = {'name': name, 'aux': value['aux']}
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
        replied = 0
        for unused in range(100):
            if not self.host.jobs: return
            self.host.tick()
            for player, request, data in self.replies[replied:]:
                if 'documentPacket' in data:
                    self.host.request({'__id__': player, 'request': request,
                                       'action': 'captureAck', 'sequence': data['documentPacket']['seq']})
            replied = len(self.replies)
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

    def test_server_side_capture_without_client_palette_is_rejected(self):
        self.host.world_regions['player'] = (0, (0,64,0), (1,1,1))
        self.host.request({'__id__':'player','request':7,'action':'capture',
                           'origin':(0,64,0),'size':(1,1,1)})
        self.assertIn('客户端 palette', self.replies[-1][2]['error'])
        self.assertFalse(self.host.jobs)
        self.assertFalse(self.writes)

    def test_capture_reads_registered_native_actors_without_uploading_client_blocks(self):
        self.host.world_regions['player'] = (0, (0,64,0), (1,1,1))
        self.host.request({'__id__':'player', 'request':31, 'action':'capture',
                           'clientCapture':True, 'origin':(0,64,0), 'size':(1,1,1)})
        self.assertTrue(self.host.selection_locked('player'))
        self.finish()
        self.assertFalse(self.host.jobs)
        self.assertFalse(self.host.uploads)
        self.assertEqual([], self.writes)
        self.assertEqual(0, self.allowed_checks)
        self.assertTrue(self.replies[-1][2]['done'])
        self.assertTrue(self.replies[-1][2]['clientCapture'])
        self.assertEqual([(0, (0,64,0), (0,64,0))], self.palette_reads)
        self.assertEqual([], self.entity_reads)

    def test_locked_selection_rejects_points_and_clear_silently_until_final_ack(self):
        self.host.world_regions['player'] = (0, (0,64,0), (1,1,1))
        self.blocks[(0,64,0)] = ('minecraft:purple_shulker_box', 0)
        self.actors[(0,64,0)] = {
            'id': {'__type__': 8, '__value__': 'ShulkerBox'},
            'Items': [{'Slot': {'__type__': 1, '__value__': 0}, 'tag': {'x': 999}}],
            'x': {'__type__': 3, '__value__': 0},
            'y': {'__type__': 3, '__value__': 64},
            'z': {'__type__': 3, '__value__': 0}}
        self.host.request({'__id__':'player', 'request':51, 'action':'capture',
                           'clientCapture':True, 'origin':(0,64,0), 'size':(1,1,1)})
        sent = []
        self.host.NotifyToClient = lambda player, event, payload: sent.append(payload)
        click = {'entityId':'player', 'itemDict':{'newItemName':'modern_projection:survey_wand'},
                 'dimensionId':0, 'x':3, 'y':64, 'z':0, 'face':4}
        self.host.tool_use_on(click)
        self.host.world_tool_request({'__id__':'player', 'action':'reset'})
        self.assertEqual([{'success':False, 'silent':True, 'createBounds':False}] * 2, sent)
        self.assertEqual((0, (0,64,0), (1,1,1)), self.host.world_regions['player'])
        self.assertFalse(click.get('ret', False))
        self.assertEqual([], self.entity_reads)
        self.finish()
        receiver = Receiver()
        for unused_player, request, response in self.replies:
            if 'documentPacket' in response:
                receiver.feed(response['documentPacket'])
        from modern_projection.projection.cell import actor_data
        from modern_projection.projection.visible_actor import entity_nbt
        entity = entity_nbt(actor_data(receiver.result.get((0,0,0))))
        self.assertEqual(0, entity['y']['__value__'])
        self.assertEqual(999, entity['Items'][0]['tag']['x'])
        self.assertEqual([(0, (0,64,0))], self.entity_reads)
        self.assertFalse(self.host.selection_locked('player'))
        self.host.world_tool_request({'__id__':'player', 'action':'reset'})
        self.assertTrue(sent[-1]['clear'])

    def test_registered_capture_recovers_wet_bed_nbt_across_palette_chunk_boundary(self):
        from modern_projection.projection.cell import AIR, actor_data, background, foreground
        from modern_projection.projection.visible_actor import entity_nbt
        self.host.world_regions['player'] = (0, (0, 64, 0), (18, 1, 1))
        foot, head = (15, 64, 0), (16, 64, 0)
        for pos, material in ((foot, ('minecraft:bed', 3)), (head, ('minecraft:bed', 11))):
            self.blocks[pos] = material
            self.liquids[pos] = {'name': 'minecraft:water', 'aux': 0}
            self.actors[pos] = {'id': {'__type__': 8, '__value__': 'Bed'},
                                'color': {'__type__': 1, '__value__': 7},
                                'x': {'__type__': 3, '__value__': pos[0]},
                                'y': {'__type__': 3, '__value__': pos[1]},
                                'z': {'__type__': 3, '__value__': pos[2]}}
        original_read = self.read_palette
        def omitted_palette(dim, low, high, eliminate):
            source = original_read(dim, low, high, eliminate).SerializeBlockPalette()
            if low[0] <= foot[0] <= high[0]:
                omitted = foot[0] - low[0]
                for key in ('common', 'actor'):
                    for entries in source[key].values():
                        if isinstance(entries, dict):
                            entries.pop(omitted, None)
                        elif omitted in entries:
                            entries.remove(omitted)
            return types.SimpleNamespace(SerializeBlockPalette=lambda: source)
        self.factory.CreateBlock = lambda level: types.SimpleNamespace(
            GetBlockPaletteBetweenPos=omitted_palette)
        self.host.request({'__id__': 'player', 'request': 54, 'action': 'capture',
                           'clientCapture': True, 'origin': (0, 64, 0), 'size': (18, 1, 1)})
        self.finish()
        self.assertTrue(self.replies[-1][2].get('clientCapture'))
        self.assertEqual([(0, foot), (0, head)], self.entity_reads)
        receiver = Receiver()
        for player, request, response in self.replies:
            if 'documentPacket' in response:
                receiver.feed(response['documentPacket'])
        for pos in ((15, 0, 0), (16, 0, 0)):
            value = receiver.result.get(pos)
            self.assertEqual(self.blocks[(pos[0], 64, 0)], foreground(value))
            self.assertEqual(('minecraft:water', 0), background(value))
            nbt = entity_nbt(actor_data(value))
            self.assertEqual(7, nbt['color']['__value__'])
            self.assertEqual(0, nbt['y']['__value__'])
        self.assertFalse(self.writes)
        self.assertFalse(self.host.selection_locked('player'))

    def test_capture_missing_ack_times_out_and_unlocks_selection(self):
        self.host.world_regions['player'] = (0, (0,64,0), (1,1,1))
        self.host.request({'__id__':'player', 'request':52, 'action':'capture',
                           'clientCapture':True, 'origin':(0,64,0), 'size':(1,1,1)})
        self.host.tick()
        self.host.tick()
        adapter = self.host.jobs['player'][3]
        self.assertEqual(0, adapter.capture_wait)
        self.host.request({'__id__':'player', 'request':52, 'action':'captureAck', 'sequence':1})
        self.assertEqual(0, adapter.capture_wait)
        adapter.capture_activity = 0.
        self.host.tick()
        self.assertFalse(self.host.selection_locked('player'))
        self.assertIn('超时', self.replies[-1][2]['error'])

    def test_capture_cancellation_releases_lock_without_clearing_registered_region(self):
        region = (0, (0,64,0), (1,1,1))
        self.host.world_regions['player'] = region
        self.host.request({'__id__':'player', 'request':53, 'action':'capture',
                           'clientCapture':True, 'origin':region[1], 'size':region[2]})
        self.host.request({'__id__':'player', 'request':53, 'action':'cancel'})
        self.assertFalse(self.host.selection_locked('player'))
        self.assertEqual(region, self.host.world_regions['player'])

    def test_client_palette_capture_rejects_unselected_or_mismatched_region(self):
        doc = Document((1,1,1), {(0,0,0):('minecraft:stone',0)})
        self.host.world_regions['player'] = (0, (4,64,0), (1,1,1))
        for packet in packets(doc):
            self.host.request({
                '__id__':'player', 'request':32,
                'action':'capture' if packet['seq'] == 0 else 'upload',
                'source':'world_item', 'clientCapture':True,
                'origin':(0,64,0), 'size':(1,1,1), 'stream':packet,
            })
        self.assertIn('重新选择', self.replies[-1][2]['error'])
        self.assertFalse(self.host.uploads)

        self.host.world_regions.pop('player')
        for packet in packets(doc):
            self.host.request({
                '__id__':'player', 'request':33,
                'action':'capture' if packet['seq'] == 0 else 'upload',
                'clientCapture':True, 'origin':(0,64,0),
                'size':(2,1,1), 'stream':packet,
            })
        self.assertIn('重新选择', self.replies[-1][2]['error'])
        self.assertFalse(self.host.uploads)

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
        self.assertFalse(first.get('ret', False))
        self.assertFalse(second.get('ret', False))
        self.assertTrue(sent[0][2]['success'])
        self.assertTrue(sent[1][2]['createBounds'])
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
                           'source':'world_item', 'clientCapture':True,
                           'origin':(1,64,0), 'size':(2,2,2)})
        self.assertFalse(self.host.jobs)
        self.assertIn('重新选择', self.replies[-1][2]['error'])
        self.host.request({'__id__':'player', 'request':22, 'action':'capture',
                           'source':'world_item', 'clientCapture':True,
                           'origin':(0,64,0), 'size':(2,2,2)})
        self.assertTrue(self.host.jobs)
        self.finish()
        self.assertTrue(self.replies[-1][2]['done'])
        self.assertFalse(self.writes)

    def test_remote_points_never_establish_a_selection_and_client_can_clear_without_wand(self):
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
        self.host.world_tool_request(request)
        self.assertFalse(sent)
        self.assertFalse(self.host.world_points)
        self.host.world_points['player'] = ((0,64,0), 0, 1.)
        carried['newItemName'] = 'minecraft:stick'
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

    def test_progress_read_keeps_liquid_background_without_server_actor_read(self):
        from modern_projection.projection.cell import background, actor_data
        front = {'name':'minecraft:oak_stairs', 'aux':0}
        self.blocks[(1,64,2)] = ('minecraft:oak_stairs',0)
        self.liquids[(1,64,2)] = {'name':'minecraft:water', 'aux':0}
        actor_reads = []
        self.factory.CreateBlockInfo = lambda level: types.SimpleNamespace(
            GetBlockNew=lambda pos, dim: front if pos == (1,64,2) else {'name':'minecraft:air','aux':0},
            GetLiquidBlock=lambda pos, dim: self.liquids.get(pos),
            GetBlockEntityData=lambda dim,pos: actor_reads.append(pos),
            GetBlockBasicInfo=lambda name: {'name':name}, SetBlockNew=self.write,
            SetBlockEntityData=self.set_actor)
        adapter = server.WorldAdapter('player')
        cell = adapter.read((1,64,2))
        self.assertEqual(('minecraft:water',0), background(cell))
        self.assertIsNone(actor_data(cell))
        self.assertEqual([], actor_reads)
        local = adapter.rebase(cell, (-1,-64,-2))
        self.assertEqual(('minecraft:oak_stairs',0), tuple(local))
        self.assertEqual(('minecraft:water',0), background(local))
        doc = Document((1,1,1), {(0,0,0): make_cell(
            ('minecraft:oak_stairs',0), ('minecraft:water',0),
            {'id':'Chest','Items':[{'Slot':0}]})})
        for unused in self.host.read_job('player', 77, 'check', adapter, doc, (1,64,2)):
            pass
        self.assertEqual(1, self.replies[-1][2]['progress']['correct'])
        self.assertEqual([], actor_reads)

    def test_standalone_fluid_is_not_duplicated_in_the_background(self):
        self.blocks[(0,64,0)] = ('minecraft:water',0)
        self.liquids[(0,64,0)] = {'name':'minecraft:water','aux':0}
        self.assertEqual(('minecraft:water',0), server.WorldAdapter('player').read((0,64,0)))

    def test_progress_checks_compare_native_layers_and_read_snow_background_without_entity_queries(self):
        from modern_projection.projection.cell import background, foreground, actor_data
        from modern_projection.projection.native_layers import native_cell
        water = ('minecraft:water', 0)
        grass = ('minecraft:short_grass', 0)
        fence = ('minecraft:oak_fence', 0)
        snow = ('minecraft:snow_layer', 2)
        cases = (make_cell(AIR, water), make_cell(AIR, grass),
                 make_cell(water, fence), make_cell(grass, snow))
        with patch('modern_projection.projection.native_layers.is_waterloggable', return_value=True):
            for logical in cases:
                with self.subTest(logical=logical):
                    native = native_cell(logical)
                    world_pos = (1, 64, 2)
                    self.blocks[world_pos] = foreground(native)
                    self.liquids[world_pos] = dict(zip(('name', 'aux'), background(native)))
                    data = Document((1, 1, 1), {(0, 0, 0): native}).palette_data()
                    data['actor'] = {'minecraft:snow_layer': {0: {'ignored': 'native actor'}}}
                    self.factory.CreateBlock = lambda level: types.SimpleNamespace(
                        GetBlockPaletteBetweenPos=lambda dim, low, high, eliminate:
                            types.SimpleNamespace(SerializeBlockPalette=lambda: data))
                    adapter = server.WorldAdapter('player')
                    result = adapter.read(world_pos)
                    self.assertEqual((foreground(native), background(native)),
                                     (foreground(result), background(result)))
                    self.assertIsNone(actor_data(result))
                    doc = Document((1, 1, 1), {(0, 0, 0): logical})
                    for unused in self.host.read_job('player', 81, 'check', adapter, doc, world_pos):
                        pass
                    self.assertEqual({'total': 1, 'correct': 1, 'missing': 0, 'wrong': 0},
                                     self.replies[-1][2]['progress'])
                    self.assertEqual(logical, doc.get((0, 0, 0)))
        self.assertEqual([], self.entity_reads)

    def test_world_write_uses_native_layer_order_without_mutating_logical_cells_or_render_ids(self):
        from modern_projection.projection.cell import foreground, background
        adapter = server.WorldAdapter('player')
        water = ('minecraft:water', 0)
        fence = ('minecraft:oak_fence', 0)
        grass = ('minecraft:short_grass', 0)
        cell = make_cell(water, fence)
        with patch('modern_projection.projection.native_layers.is_waterloggable', return_value=True):
            self.assertTrue(adapter.write((0,64,0), cell))
        data = self.palette_writes[-1][0]
        self.assertEqual({(b'minecraft:oak_fence',0): [0]}, data['common'])
        self.assertEqual({(b'minecraft:water',0): [0]}, data['extra'])
        self.assertEqual(water, foreground(cell))
        self.assertEqual(fence, background(cell))
        self.assertTrue(adapter.write((1,64,0), make_cell(grass, ('minecraft:snow_layer',2))))
        data = self.palette_writes[-1][0]
        self.assertEqual({(b'minecraft:snow_layer',0): [0]}, data['common'])
        self.assertTrue(data['states'][(b'minecraft:snow_layer',0)][b'covered_bit'])
        self.assertEqual({(b'minecraft:short_grass',0): [0]}, data['extra'])
        self.assertTrue(adapter.write((2,64,0), make_cell(back=water)))
        data = self.palette_writes[-1][0]
        self.assertEqual({(b'minecraft:water',0): [0]}, data['common'])
        self.assertEqual({(b'minecraft:air',0): [0]}, data['extra'])
        self.assertTrue(adapter.write((3,64,0), make_cell(('minecraft:oak_leaves',3), water)))
        self.assertEqual({(b'minecraft:oak_leaves',0): [0]}, self.palette_writes[-1][0]['common'])
        self.assertFalse(any(b'modern_projection:preview_' in key[0]
                             for data, unused_dim, unused_pos, unused_rot, unused_conflict
                             in self.palette_writes for key in data['common']))

    def test_native_bed_writes_use_one_head_with_exact_states_and_no_world_readback(self):
        from modern_projection.projection.block_registry import aux_values, states
        from modern_projection.projection.block_groups import group_partner
        adapter = server.WorldAdapter('player')
        adapter.info.GetBlockNew = lambda *args: self.fail('world writes do not read target blocks')
        adapter.info.GetLiquidBlock = lambda *args: self.fail('world writes do not read liquids')
        old_write = adapter.info.SetBlockNew
        def unchanged_head(pos, value, *unused):
            old_write(pos, value)
            return False
        adapter.info.SetBlockNew = unchanged_head
        for aux in aux_values('minecraft:bed'):
            with self.subTest(aux=aux):
                value = ('minecraft:bed', aux)
                properties = states(value)
                pos = (4, 64, 4)
                head = value
                if not properties['head_piece_bit']:
                    offset, head = group_partner(value)
                    pos = tuple(pos[i] + offset[i] for i in range(3))
                before = len(self.writes)
                self.assertTrue(adapter.write((4, 64, 4), make_cell(value, ('minecraft:water', 0))))
                self.assertEqual(before + 1, len(self.writes))
                self.assertEqual(pos, self.writes[-1])
                self.assertEqual((pos, states(head), 0), self.state_writes[-1])
                self.assertEqual({'name': 'minecraft:water', 'aux': 0}, self.liquids[(4, 64, 4)])
        self.assertEqual([], self.palette_writes)
        self.assertEqual([], self.entity_reads)
        adapter.blockstate_component.SetBlockStates = lambda *args: False
        self.assertFalse(adapter.write((4, 64, 4), ('minecraft:bed', 8)))

    def test_second_bed_half_does_not_recreate_and_reset_previous_head_entity_data(self):
        from modern_projection.projection.block_groups import group_partner
        adapter = server.WorldAdapter('player')
        foot = ('minecraft:bed', 0)
        offset, head = group_partner(foot)
        foot_pos = (4, 64, 4)
        head_pos = tuple(foot_pos[i] + offset[i] for i in range(3))
        actor = {'id': {'__type__': 8, '__value__': 'Bed'},
                 'color': {'__type__': 1, '__value__': 7}}
        self.assertTrue(adapter.write(head_pos, make_cell(head, nbt=actor)))
        self.assertTrue(adapter.write(foot_pos, make_cell(foot, nbt=actor)))
        self.assertEqual([head_pos], self.writes)
        self.assertEqual([head_pos, foot_pos], [record[1] for record in self.actor_writes])

    def test_visible_chest_actor_is_not_sent_to_server_nbt_setter(self):
        payload = {'chestIsLargeChest':True, 'chestMainSubChest':True,
                   'facingDirection':2, 'chestModelOffset':0.0}
        self.assertTrue(server.WorldAdapter('player').write(
            (0,64,0), make_cell(('minecraft:chest',2), nbt=payload)))
        self.assertEqual([], self.actor_writes)

    def test_visible_sign_text_and_styles_use_public_write_interfaces(self):
        adapter = server.WorldAdapter('player')
        texts, styles = [], []
        adapter.info.SetSignBlockText = lambda pos,text,dim,side: texts.append((text,side)) or True
        adapter.factory.CreateBlockEntity = lambda level: types.SimpleNamespace(
            SetSignTextStyle=lambda pos,dim,color,glow,side: styles.append((color,glow,side)) or True)
        payload = {'signRealText':'Front P0', 'signRealTextBack':'Back P0',
                   'signColor':-16777216, 'signColorBack':-65536,
                   'signGlowing':False, 'signGlowingBack':True}
        self.assertTrue(adapter.write((0,64,0), make_cell(('minecraft:standing_sign',0), nbt=payload)))
        self.assertEqual([(b'Front P0',0),(b'Back P0',1)], texts)
        self.assertEqual([((0.,0.,0.,1.),False,0),((1.,0.,0.,1.),True,1)], styles)
        self.assertEqual([], self.actor_writes)

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
