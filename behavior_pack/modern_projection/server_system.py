# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import mod.server.extraServerApi as serverApi
from .projection.model import AIR, Document, add, block
from .projection.cell import actor_data, background, foreground, make_cell
from .projection.native_layers import native_cell
from .projection.world import WorldJob, coordinate
from .projection.error_text import error_text
from .projection.transfer import Receiver, packets
from .projection.block_registry import canonical as registry_canonical, states as registry_states
from .projection.nbt_spatial import rebase as rebase_actor
from .projection.visible_actor import compose_actor, entity_nbt, sign_sides
from .projection.native_entity_write import tile_rebuild_stages
from .projection.tool_items import SURVEY_WAND, TERMINAL, item_name, selection
import time

try:
    text_type = unicode
except NameError:
    text_type = str


ServerSystem = serverApi.GetServerSystemCls()


class WorldAdapter(object):
    def __init__(self, player):
        self.player = player
        self.factory = serverApi.GetEngineCompFactory()
        self.level = serverApi.GetLevelId()
        self.dimension = self.factory.CreateDimension(player).GetEntityDimensionId()
        self.info = self.factory.CreateBlockInfo(self.level)
        self.palette_block = self.factory.CreateBlock(self.level)
        self.validity = {}
        self.canonical_values = {}
        self.loading = {}
        self.sign_component = None
        self.blockstate_component = None
        self.native_aux_values = {}
        self.native_pairs_written = set()
        self.layer_info_component = None

    def ensure(self, pos):
        key = (pos[0] // 16, pos[2] // 16)
        state = self.loading.get(key)
        now = time.time()
        if state is not None:
            status, started = state
            if status is None:
                return False if now - started > 20. else None
            if now - started < 1.:
                return False
        self.loading[key] = (None, now)
        def ready(data):
            self.loading[key] = (data.get('code') == 1, time.time())
        start = (key[0] * 16, 0, key[1] * 16)
        end = (start[0] + 15, 1, start[2] + 15)
        if not self.factory.CreateChunkSource(self.level).DoTaskOnChunkAsync(self.dimension, start, end, ready):
            self.loading[key] = (False, now)
            return False
        return None

    def allowed(self):
        if self.player not in serverApi.GetPlayerList():
            return False
        abilities = self.factory.CreatePlayer(self.player).GetPlayerAbilities()
        return (self.factory.CreateGame(self.level).GetPlayerGameType(self.player) == 1 and
                self.factory.CreateDimension(self.player).GetEntityDimensionId() == self.dimension and
                isinstance(abilities, dict) and all(abilities.get(k) is True for k in ('op', 'build', 'mine')))

    def canonical(self, value):
        """Use the same authoritative state identity as the client renderer."""
        if value not in self.canonical_values:
            front = registry_canonical(foreground(value))
            back = registry_canonical(background(value))
            self.canonical_values[value] = make_cell(front, back, actor_data(value))
        return self.canonical_values[value]

    def rebase(self, value, offset):
        value = self.canonical(value)
        actor = actor_data(value)
        if actor is not None:
            actor = rebase_actor(actor, offset)
        return make_cell(foreground(value), background(value), actor)

    @staticmethod
    def _native_tree(value):
        if isinstance(value, text_type):
            return value.encode('utf8')
        if isinstance(value, list):
            return [WorldAdapter._native_tree(item) for item in value]
        if isinstance(value, tuple):
            return tuple(WorldAdapter._native_tree(item) for item in value)
        if isinstance(value, dict):
            return dict((WorldAdapter._native_tree(key), WorldAdapter._native_tree(item))
                        for key, item in value.items())
        return value

    def _palette_layer(self, value):
        value = registry_canonical(value)
        record = registry_states(value)
        key = (value[0].encode('utf8'), 0 if record is not None else value[1])
        if record is not None:
            record = dict((name.encode('utf8'), self._native_tree(item))
                          for name, item in record.items())
        return key, record

    def read(self, pos):
        data = self.info.GetBlockNew(pos, self.dimension)
        if not data or not data.get('name') or data['name'] == 'minecraft:unknown':
            return None
        front = block((data['name'], data.get('aux', 0)))
        if front[0] == 'minecraft:snow_layer':
            from .projection.world_capture import merge_palette
            palette = self.palette_block.GetBlockPaletteBetweenPos(self.dimension, pos, pos, False)
            if palette is None:
                return None
            source = dict(palette.SerializeBlockPalette())
            source['actor'] = {}
            cell = Document((1, 1, 1))
            merge_palette(cell, source, (0, 0, 0), (1, 1, 1), pos)
            return cell.get((0, 0, 0))
        liquid = self.info.GetLiquidBlock(pos, self.dimension)
        back = AIR
        if liquid and liquid.get('name') and liquid['name'] != 'minecraft:air':
            back = block((liquid['name'], liquid.get('aux', 0)))
            if back == front:
                back = AIR
        return make_cell(front, back)

    def validate_write(self, document, pos, value):
        front = foreground(native_cell(self.canonical(value)))
        properties = registry_states(front)
        if properties is None or 'head_piece_bit' not in properties:
            return
        from .projection.block_groups import paired_position

        def get_block(local):
            if document.contains(local):
                return foreground(native_cell(self.canonical(document.get(local))))

        # Native bed placement creates its other half. Only permit a pair
        # already present in this frozen document, including promoted layers.
        paired_position(get_block, pos)

    def write(self, pos, value, origin=(0, 0, 0)):
        value = native_cell(self.canonical(value))
        front, back = foreground(value), background(value)
        common_key, common_states = self._palette_layer(front)
        extra, extra_states = {}, {}
        states = {} if common_states is None else {common_key: common_states}
        extra_key, record = self._palette_layer(back)
        extra[extra_key] = [0]
        if record is not None:
            extra_states[extra_key] = record
        data = {
            'volume': (1, 1, 1),
            'common': {common_key: [0]},
            'states': states,
            'extra': extra,
            'extraStates': extra_states,
            'actor': {},
            'void': False,
            'eliminateAir': False,
        }
        raw_actor = actor_data(value)
        nbt = entity_nbt(raw_actor)
        rebuild_stages = tile_rebuild_stages(front, back, nbt)
        properties = registry_states(front)
        if properties is not None and 'head_piece_bit' in properties:
            if not self._write_head_first_pair(pos, front, back, properties):
                return False
        else:
            palette = self.palette_block.GetBlankBlockPalette()
            if palette is None or not palette.DeserializeBlockPalette(data):
                return False
            # Rebuild the observed tile while preserving wet layers for client
            # replication, then apply the final palette and typed NBT together.
            for name, aux in rebuild_stages:
                self.info.SetBlockNew(pos, {'name': name.encode('utf8'), 'aux': aux},
                                      0, self.dimension, True, False)
            if not self.palette_block.SetBlockByBlockPalette(
                    palette, self.dimension, pos, 0, 0):
                return False
        if nbt is not None:
            world_actor = rebase_actor(nbt, origin)
            return self.info.SetBlockEntityData(
                self.dimension, pos, self._native_tree(world_actor))
        result = True
        for side, text, color, glow in sign_sides(raw_actor):
            result = bool(self.info.SetSignBlockText(
                pos, self._native_tree(text), self.dimension, side)) and result
            if color is not None and glow is not None:
                if self.sign_component is None:
                    self.sign_component = self.factory.CreateBlockEntity(self.level)
                result = bool(self.sign_component.SetSignTextStyle(
                    pos, self.dimension, color, glow, side)) and result
        return result

    def _write_head_first_pair(self, pos, front, back, properties):
        from .projection.block_groups import group_partner
        head_pos, head = pos, front
        if not properties['head_piece_bit']:
            offset, head = group_partner(front)
            head_pos = tuple(pos[i] + offset[i] for i in range(3))
            properties = registry_states(head)
        if self.blockstate_component is None:
            self.blockstate_component = self.factory.CreateBlockState(self.level)
        if head not in self.native_aux_values:
            aux = self.blockstate_component.GetBlockAuxValueFromStates(
                head[0].encode('utf8'), properties)
            if aux is None or aux < 0:
                return False
            self.native_aux_values[head] = aux
        # Native bed placement creates its reciprocal foot. Replacing an
        # already equal head reports False, so use the state setter's result.
        identity = (head_pos, head)
        if identity not in self.native_pairs_written:
            self.info.SetBlockNew(head_pos, {
                'name': head[0].encode('utf8'), 'aux': self.native_aux_values[head]},
                0, self.dimension, True, False)
        if not self.blockstate_component.SetBlockStates(head_pos, properties, self.dimension):
            return False
        self.native_pairs_written.add(identity)
        liquid = {'name': back[0].encode('utf8'), 'aux': back[1]}
        if self.layer_info_component is None:
            self.layer_info_component = self.factory.CreateBlockInfo(self.player)
        result = self.layer_info_component.SetLiquidBlock(pos, liquid, self.dimension)
        return back == AIR or result is not False

    def valid(self, value):
        try:
            registry_canonical(value)
            if value[0].startswith('minecraft:'):
                return True
        except (ValueError, TypeError):
            return False
        if value[0] not in self.validity:
            data = self.info.GetBlockBasicInfo(value[0].encode('utf8'))
            self.validity[value[0]] = bool(data)
        return self.validity[value[0]]


class ModernProjectionServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        ServerSystem.__init__(self, namespace, systemName)
        self.jobs = {}
        self.uploads = {}
        self.world_points = {}
        self.world_regions = {}
        self.tool_last_use = {}
        self.terminal_last_use = {}
        self.aura_tick = 0
        self.ListenForEvent('ModernProjection', 'ModernProjectionClientSystem', 'ProjectionRequest', self, self.request)
        self.ListenForEvent('ModernProjection', 'ModernProjectionClientSystem', 'BlockCatalogueRequest', self, self.block_catalogue)
        self.ListenForEvent('ModernProjection', 'ModernProjectionClientSystem', 'WorldToolRequest', self, self.world_tool_request)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'OnScriptTickServer', self, self.tick)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'DelServerPlayerEvent', self, self.leave)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'ServerItemUseOnEvent', self, self.tool_use_on)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'ServerBlockUseEvent', self, self.tool_block_use)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'ServerItemTryUseEvent', self, self.tool_try_use)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'DimensionChangeFinishServerEvent', self, self.tool_dimension_changed)
        for event in ('StartDestroyBlockServerEvent', 'ServerPlayerTryDestroyBlockEvent'):
            self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), event, self, self.tool_prevent_break)
        factory = serverApi.GetEngineCompFactory()
        self.block_use_listener = factory.CreateBlockUseEventWhiteList(serverApi.GetLevelId())
        self.block_use_names = factory.CreateBlockInfo(serverApi.GetLevelId()).GetLoadBlocks()
        for name in self.block_use_names:
            self.block_use_listener.AddBlockItemListenForUseEvent(name)

    def held_tool(self, player):
        item = serverApi.GetEngineCompFactory().CreateItem(player).GetPlayerItem(
            serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0)
        return item_name(item)

    def tool_dimension_changed(self, args):
        player = args.get('playerId')
        self.world_points.pop(player, None)
        self.world_regions.pop(player, None)

    def tool_prevent_break(self, args):
        player = args.get('playerId')
        if player in serverApi.GetPlayerList() and self.held_tool(player) in (SURVEY_WAND, TERMINAL):
            args['cancel'] = True

    def world_tool_request(self, args):
        # HUD requests are untrusted. The sender is supplied by the engine.
        if not isinstance(args, dict):
            return
        player = args.get('__id__')
        if player not in serverApi.GetPlayerList():
            return
        if args.get('action') == 'reset':
            if self.selection_locked(player):
                self.NotifyToClient(player, 'WorldToolPoint', {
                    'success': False, 'silent': True, 'createBounds': False})
                return
            self.world_points.pop(player, None)
            self.world_regions.pop(player, None)
            self.NotifyToClient(player, 'WorldToolPoint', {
                'success': True, 'clear': True, 'createBounds': False})
        # Coordinates from a client packet can never establish a selection.

    def selection_locked(self, player):
        entry = self.jobs.get(player)
        upload = self.uploads.get(player)
        return bool((entry and entry[1] == 'capture') or
                    (upload and upload[1].get('action') == 'capture'))

    def validate_capture(self, adapter, args):
        region = self.world_regions.get(adapter.player)
        if region != (adapter.dimension, tuple(args.get('origin', ())), tuple(args.get('size', ()))):
            raise ValueError('世界选区已改变，请重新选择两个角点')
        if args.get('clientCapture') is not True:
            raise ValueError('世界选区必须通过客户端 palette 读取')

    def tool_block_use(self, args):
        event = dict(args, entityId=args.get('playerId'))
        self.tool_use_on(event)

    def tool_try_use(self, args):
        if item_name(args.get('itemDict')) != TERMINAL:
            return
        player = args.get('playerId')
        if player in serverApi.GetPlayerList():
            args['cancel'] = True
            self.open_terminal(player)

    def open_terminal(self, player):
        now = time.time()
        if now - self.terminal_last_use.get(player, 0.) < .3:
            return
        self.terminal_last_use[player] = now
        self.NotifyToClient(player, 'OpenProjectionUi', {})

    def tool_use_on(self, args):
        name = item_name(args.get('itemDict'))
        player = args.get('entityId')
        if name not in (SURVEY_WAND, TERMINAL) or player not in serverApi.GetPlayerList():
            return
        if name == TERMINAL:
            args['ret'] = True
            self.open_terminal(player)
            return
        if self.selection_locked(player):
            self.NotifyToClient(player, 'WorldToolPoint', {
                'success': False, 'silent': True, 'createBounds': False})
            return
        try:
            adapter = WorldAdapter(player)
            dimension = args.get('dimensionId')
            if dimension != adapter.dimension:
                raise ValueError('维度已改变，请重新选取')
            pos = tuple(args[axis] for axis in ('x', 'y', 'z'))
            if any(type(value) is not int for value in pos):
                raise ValueError('选点坐标无效')
            face = args.get('face')
            if type(face) is not int or not 0 <= face <= 5:
                face = None
            now = time.time()
            last = self.tool_last_use.get(player)
            self.tool_last_use[player] = now
            if last is not None and now - last < .2:
                self.NotifyToClient(player, 'WorldToolPoint', {
                    'success': False, 'silent': True, 'createBounds': False})
                return
            previous = self.world_points.get(player)
            if previous and previous[1] == dimension and now - previous[2] < 600.:
                origin, size = selection(previous[0], pos)
                self.validate_target(adapter, origin, Document(size))
                self.world_points.pop(player, None)
                self.world_regions[player] = (dimension, origin, size)
                self.NotifyToClient(player, 'WorldToolPoint', {'success': True, 'createBounds': True,
                    'first': previous[0], 'index': 1, 'pos': pos,
                    'face': face, 'dimension': dimension, 'origin': origin, 'size': size})
            else:
                self.world_regions.pop(player, None)
                self.world_points[player] = (pos, dimension, now)
                self.NotifyToClient(player, 'WorldToolPoint', {'success': True, 'createBounds': True,
                    'index': 0, 'pos': pos,
                    'face': face, 'dimension': dimension})
        except (ValueError, TypeError, KeyError) as error:
            self.world_points.pop(player, None)
            self.world_regions.pop(player, None)
            self.NotifyToClient(player, 'WorldToolPoint', {'success': False,
                'error': error_text(error), 'clear': True, 'createBounds': False})

    def reply(self, player, request, **data):
        data['request'] = request
        self.NotifyToClient(player, 'ProjectionResponse', data)

    def block_catalogue(self, args):
        player = args.get('__id__')
        if player:
            names = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId()).GetLoadBlocks()
            # Read-only catalogue, independent of capture/write jobs.
            self.NotifyToClient(player, 'BlockCatalogueResponse', {'names': sorted(names)})

    def request(self, args, transferred=None, upload_adapter=None):
        # Use engine-injected identity, never a client-selected player id.
        if not isinstance(args, dict):
            return
        player, request = args.get('__id__'), args.get('request')
        if not player or player not in serverApi.GetPlayerList() or type(request) is not int or not 0 < request <= 2147483647:
            return
        if args.get('action') == 'captureAck':
            entry = self.jobs.get(player)
            if (entry and entry[0] == request and entry[1] == 'capture' and
                    type(args.get('sequence')) is int and
                    args['sequence'] == getattr(entry[3], 'capture_wait', None)):
                entry[3].capture_wait = None
                entry[3].capture_activity = time.time()
            return
        if args.get('action') == 'cancel':
            upload = self.uploads.get(player)
            if upload and upload[0] == request:
                self.uploads.pop(player, None)
            else:
                upload = None
            entry = self.jobs.get(player)
            if entry and entry[0] == request:
                if isinstance(entry[2], WorldJob):
                    job = entry[2]
                    job.cancel()
                    self.jobs.pop(player, None)
                    self.reply(player, request, done=True, error=job.error,
                               progress={'total': job.total, 'processed': job.cursor,
                                         'written': job.written, 'failed': job.failed})
                else:
                    self.jobs.pop(player, None)
                    self.reply(player, request, done=True, error='世界读取已取消')
            elif upload:
                self.reply(player, upload[0], done=True, error='建筑传输已取消')
            return
        active = self.jobs.get(player)
        if active and active[0] == request:
            return
        if args.get('action') == 'upload' or args.get('stream') is not None:
            try:
                entry = self.uploads.get(player)
                packet = args.get('stream')
                if (entry and entry[0] == request and isinstance(packet, dict) and
                        type(packet.get('seq')) is int and 0 <= packet['seq'] < entry[2].sequence):
                    self.reply(player, request, done=False, uploadAck=packet['seq'])
                    return
                if args.get('action') != 'upload':
                    if player in self.jobs or player in self.uploads or args.get('action') not in ('apply', 'check', 'capture'):
                        raise ValueError('已有世界操作正在进行')
                    adapter = WorldAdapter(player)
                    if args['action'] == 'apply' and not adapter.allowed():
                        raise ValueError('世界写入需要创造模式、操作员和建造权限')
                    # Validate dimensions, destination and authorization before
                    # allocating/decompressing the rest of a client's upload.
                    origin = coordinate(args.get('origin'))
                    header = args.get('stream')
                    if not isinstance(header, dict) or header.get('kind') != 'begin':
                        raise ValueError('缺少建筑传输头')
                    document = Document(header.get('size', ()))
                    if args['action'] == 'capture':
                        self.validate_capture(adapter, args)
                        if tuple(args.get('size', ())) != document.size:
                            raise ValueError('客户端世界读取尺寸不匹配')
                    self.validate_target(adapter, origin, document)
                    self.uploads[player] = (request, dict(args), Receiver(), time.time(), adapter)
                entry = self.uploads.get(player)
                if entry is None or entry[0] != request:
                    raise ValueError('建筑上传请求已失效')
                unused, initial, receiver, unused_time, adapter = entry
                if adapter.factory.CreateDimension(player).GetEntityDimensionId() != adapter.dimension:
                    raise ValueError('传输期间维度已改变，请重试')
                packet = args.get('stream')
                result = receiver.feed(packet)
                self.uploads[player] = (request, initial, receiver, time.time(), adapter)
                self.reply(player, request, done=False, uploadAck=packet['seq'])
                if result is not None:
                    self.uploads.pop(player, None)
                    initial.pop('stream', None)
                    self.request(initial, result, adapter)
            except (ValueError, TypeError, KeyError, RuntimeError) as error:
                entry = self.uploads.get(player)
                if entry and entry[0] == request:
                    self.uploads.pop(player, None)
                self.reply(player, request, done=True, error=error_text(error))
            return
        if player in self.jobs or player in self.uploads:
            self.reply(player, request, done=True, error='已有世界操作正在进行')
            return
        try:
            action = args.get('action')
            if action not in ('capture', 'check', 'apply', 'resolve'):
                raise ValueError('未知的世界操作')
            adapter = upload_adapter or WorldAdapter(player)
            if action == 'capture' and upload_adapter is None:
                self.validate_capture(adapter, args)
            if action == 'apply' and upload_adapter is None and not adapter.allowed():
                raise ValueError('世界写入需要创造模式、操作员和建造权限')
            if action == 'resolve':
                values = args.get('palette')
                if not isinstance(values, list) or not 1 <= len(values) <= 64:
                    raise ValueError('投影材质数量无效')
                job = self.resolve_palette(player, request, adapter, [block(value) for value in values])
            else:
                origin = coordinate(args.get('origin'))
                if action != 'capture' and transferred is None:
                    raise ValueError('请使用完整的建筑分包传输')
                if action == 'capture' and args.get('clientCapture') is True:
                    declared_size = tuple(args.get('size', ()))
                    if transferred is not None and declared_size != transferred.size:
                        raise ValueError('客户端世界读取尺寸不匹配')
                    doc = Document(declared_size)
                else:
                    doc = Document(tuple(args.get('size', ()))) if action == 'capture' else transferred
                if action != 'capture' or upload_adapter is None:
                    self.validate_target(adapter, origin, doc)
                if action == 'capture' and args.get('clientCapture') is True:
                    job = self.capture_entities(player, request, adapter, doc, origin)
                elif action == 'apply':
                    job = WorldJob(adapter, doc, origin, include_air=args.get('includeAir') is True)
                else:
                    job = self.read_job(player, request, action, adapter, doc, origin)
            self.jobs[player] = (request, action, job, adapter, 0)
        except (ValueError, TypeError, KeyError) as error:
            self.reply(player, request, done=True, error=error_text(error))

    def capture_entities(self, player, request, adapter, document, origin):
        from .projection.world_capture import native_actor_cells
        adapter.read_processed, adapter.read_total = 0, document.volume
        adapter.capture_wait = None
        adapter.capture_activity = time.time()
        for y in range(0, document.size[1], 16):
            for x in range(0, document.size[0], 16):
                for z in range(0, document.size[2], 16):
                    local = (x, y, z)
                    size = tuple(min(16, document.size[i] - local[i]) for i in range(3))
                    low = add(origin, local)
                    high = tuple(low[i] + size[i] - 1 for i in range(3))
                    palette = adapter.palette_block.GetBlockPaletteBetweenPos(
                        adapter.dimension, low, high, False)
                    if palette is None:
                        raise ValueError('服务端选区未加载，请靠近后重新读取')
                    for pos, material in native_actor_cells(
                            palette.SerializeBlockPalette(), local, size,
                            lambda pos: adapter.read(add(origin, pos))):
                        nbt = adapter.info.GetBlockEntityData(adapter.dimension, add(origin, pos))
                        if nbt is not None:
                            actual = adapter.read(add(origin, pos))
                            if actual is None:
                                raise ValueError('服务端方块实体未加载，请靠近后重新读取')
                            nbt = rebase_actor(nbt, tuple(-value for value in origin))
                            document.blocks[pos] = make_cell(
                                material, background(actual), compose_actor(None, nbt))
                    adapter.read_processed += size[0] * size[1] * size[2]
                    yield None
        for packet in packets(document):
            adapter.capture_wait = packet['seq']
            adapter.capture_activity = time.time()
            self.reply(player, request, done=False, documentPacket=packet)
            while adapter.capture_wait is not None:
                if time.time() - adapter.capture_activity > 30.:
                    raise ValueError('方块实体传输超时，请重新导入')
                yield None
        self.reply(player, request, done=True, streamed=True, clientCapture=True)

    def resolve_palette(self, player, request, adapter, values):
        # Read-only identity/state conversion. No world cells or actors are
        # written, and survival players can use it for their local projection.
        resolved = []
        deadline = time.time() + .006
        for value in values:
            resolved.append(list(adapter.canonical(value)))
            if time.time() >= deadline:
                yield None
                deadline = time.time() + .006
        self.reply(player, request, done=True, palette=resolved)

    def validate_target(self, adapter, origin, doc):
        if origin[1] < (-64 if adapter.dimension == 0 else 0) or origin[1] + doc.size[1] > (320 if adapter.dimension == 0 else 256):
            raise ValueError('选区超出维度建造高度')
        if any(abs(origin[i] + doc.size[i] - 1) > 30000000 for i in (0, 2)):
            raise ValueError('目标范围超出世界边界')
        foot = adapter.factory.CreatePos(adapter.player).GetFootPos()
        if foot is None or any(max(origin[i] - foot[i], foot[i] - (origin[i] + doc.size[i] - 1)) > 128 for i in range(3)):
            raise ValueError('请移动到目标区域附近（128 格以内）')

    def read_job(self, player, request, action, adapter, doc, origin):
        stats = {'total': len(doc.blocks), 'correct': 0, 'missing': 0, 'wrong': 0}
        adapter.read_processed = 0
        adapter.read_total = doc.volume if action == 'capture' else len(doc.blocks)
        points = doc.points() if action == 'capture' else iter(doc.blocks)
        deadline = time.time() + .006
        batch = 0
        previous_chunk = None
        for index, pos in enumerate(points):
            if action == 'capture':
                key = tuple(v >> 4 for v in pos)
                if previous_chunk is not None and key != previous_chunk:
                    doc.blocks.compact(previous_chunk)
                previous_chunk = key
            value = adapter.read(add(origin, pos))
            while value is None and adapter.ensure(add(origin, pos)) is None:
                yield None
                value = adapter.read(add(origin, pos))
                deadline = time.time() + .006
            if value is None:
                self.reply(player, request, done=True, error='区域尚未加载，请靠近后重试')
                return
            value = adapter.rebase(value, tuple(-v for v in origin))
            if action == 'capture':
                if value != AIR:
                    doc.blocks[pos] = value
            else:
                expected = native_cell(adapter.canonical(doc.get(pos)))
                if (foreground(value), background(value)) == (
                        foreground(expected), background(expected)):
                    stats['correct'] += 1
                elif value == AIR:
                    stats['missing'] += 1
                else:
                    stats['wrong'] += 1
            batch += 1
            if batch >= 2048 or time.time() >= deadline:
                adapter.read_processed = index + 1
                yield None
                batch = 0
                deadline = time.time() + .006
        if action == 'capture':
            adapter.read_processed = adapter.read_total
            if previous_chunk is not None:
                doc.blocks.compact(previous_chunk)
            doc.name = '世界选区'
            for packet in packets(doc):
                self.reply(player, request, done=False, documentPacket=packet)
                yield None
            self.reply(player, request, done=True, streamed=True)
        else:
            self.reply(player, request, done=True, progress=stats)

    def tick(self, unused=None):
        self.aura_tick += 1
        if self.aura_tick % 15 == 0:
            players = serverApi.GetPlayerList()
            carried = dict((player, name) for player in players
                           for name in (self.held_tool(player),)
                           if name in (SURVEY_WAND, TERMINAL))
            self.BroadcastToAllClient('StaffAuraState', {'carried': carried})
        for player, entry in list(self.uploads.items()):
            if time.time() - entry[3] > 60.:
                self.uploads.pop(player, None)
                self.reply(player, entry[0], done=True, error='建筑传输超时，请重试')
        for player, entry in list(self.jobs.items()):
            request, action, job, adapter, ticks = entry
            self.jobs[player] = (request, action, job, adapter, ticks + 1)
            if action == 'apply':
                job.step()
                if job.done:
                    if player not in serverApi.GetPlayerList():
                        self.jobs.pop(player, None)
                        continue
                    progress = {'total': job.total, 'processed': job.cursor,
                                'written': job.written, 'failed': job.failed}
                    if job.error:
                        self.reply(player, request, done=True, error=job.error,
                                   progress=progress)
                    else:
                        self.reply(player, request, done=True,
                                   message='已写入 %d 格' % job.written,
                                   progress=progress)
                    self.jobs.pop(player, None)
            else:
                try:
                    if adapter is not None and (player not in serverApi.GetPlayerList() or
                            adapter.factory.CreateDimension(player).GetEntityDimensionId() != adapter.dimension):
                        raise ValueError('玩家已离开或维度已改变，已取消世界读取')
                    next(job)
                except StopIteration:
                    self.jobs.pop(player, None)
                except (ValueError, TypeError, KeyError, RuntimeError) as error:
                    self.jobs.pop(player, None)
                    self.reply(player, request, done=True, error=error_text(error))
            if ticks % 10 == 0 and player in self.jobs:
                if isinstance(job, WorldJob):
                    self.reply(player, request, done=False,
                               message='写入方块，已处理 %d/%d 格' % (job.cursor, job.total),
                               progress={'total': job.total, 'processed': job.cursor,
                                         'written': job.written, 'failed': job.failed})
                elif action != 'resolve':
                    total = getattr(adapter, 'read_total', 0)
                    count = getattr(adapter, 'read_processed', 0)
                    message = ('正在传输选区数据' if count == total else
                               '正在读取世界 %d%%' % (100 * count // max(1, total)))
                    self.reply(player, request, done=False, message=message)

    def leave(self, args):
        player = args.get('id')
        self.world_points.pop(player, None)
        self.world_regions.pop(player, None)
        self.tool_last_use.pop(player, None)
        self.terminal_last_use.pop(player, None)
        self.uploads.pop(player, None)
        entry = self.jobs.get(player)
        if entry and isinstance(entry[2], WorldJob):
            entry[2].cancel('玩家已离开')
        self.jobs.pop(player, None)

    def Destroy(self):
        for entry in self.jobs.values():
            job = entry[2]
            if isinstance(job, WorldJob):
                job.cancel('世界操作已关闭')
        for name in getattr(self, 'block_use_names', ()):
            self.block_use_listener.RemoveBlockItemListenForUseEvent(name)
        self.UnListenAllEvents()
