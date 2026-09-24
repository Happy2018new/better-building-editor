# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import mod.server.extraServerApi as serverApi
from .projection.model import AIR, Document, add, block
from .projection.world import WorldJob, coordinate
from .projection.transfer import Receiver, packets
from .projection.block_registry import canonical as registry_canonical, states as registry_states
from .projection.tool_items import SURVEY_WAND, TERMINAL, item_name, selection
import time

try:
    text_type = unicode
except NameError:
    text_type = str


def error_text(error):
    return text_type(error)

ServerSystem = serverApi.GetServerSystemCls()


class WorldAdapter(object):
    def __init__(self, player):
        self.player = player
        self.factory = serverApi.GetEngineCompFactory()
        self.level = serverApi.GetLevelId()
        self.dimension = self.factory.CreateDimension(player).GetEntityDimensionId()
        self.info = self.factory.CreateBlockInfo(self.level)
        self.validity = {}
        self.canonical_values = {}
        self.state_values = {}
        self.loading = {}

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
            self.canonical_values[value] = registry_canonical(value)
        return self.canonical_values[value]

    def read(self, pos):
        data = self.info.GetBlockNew(pos, self.dimension)
        if not data or not data.get('name') or data['name'] == 'minecraft:unknown':
            return None
        return block((data['name'], data.get('aux', 0)))

    def write(self, pos, value):
        value = self.canonical(value)
        name = value[0].encode('utf8')
        if value not in self.state_values:
            record = registry_states(value)
            self.state_values[value] = (None if record is None else dict(
                (key.encode('utf8'), item.encode('utf8') if isinstance(item,text_type) else item)
                for key,item in record.items()))
        record = self.state_values[value]
        # SetBlockNew can interpret modern aux as old species (quartz:1 becomes
        # chiseled quartz). Create the name's default, then apply exact states.
        # Custom blocks retain their own SDK aux convention. Zero is already
        # the default state, avoiding a second setter for common bulk fills.
        aux = value[1] if record is None else 0
        if not self.info.SetBlockNew(pos, {'name': name, 'aux': aux}, 0, self.dimension, True, False):
            # Native reports False for an unchanged default block as well.
            if self.read(pos) != (value[0], aux):
                return False
        if record and value[1] != 0:
            return self.factory.CreateBlockState(self.level).SetBlockStates(pos, record, self.dimension)
        return True

    def protected(self, pos, value):
        if value[0] in ('minecraft:bedrock', 'minecraft:barrier', 'minecraft:allow', 'minecraft:deny'):
            return True
        return self.info.GetBlockEntityData(self.dimension, pos) is not None

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


class HelloServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        ServerSystem.__init__(self, namespace, systemName)
        self.jobs = {}
        self.uploads = {}
        self.world_points = {}
        self.world_regions = {}
        self.tool_last_use = {}
        self.terminal_last_use = {}
        self.ListenForEvent('ModernProjection', 'HelloClientSystem', 'ProjectionRequest', self, self.request)
        self.ListenForEvent('ModernProjection', 'HelloClientSystem', 'BlockCatalogueRequest', self, self.block_catalogue)
        self.ListenForEvent('ModernProjection', 'HelloClientSystem', 'WorldToolRequest', self, self.world_tool_request)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'OnScriptTickServer', self, self.tick)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'DelServerPlayerEvent', self, self.leave)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'ServerItemUseOnEvent', self, self.tool_use_on)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'ServerItemTryUseEvent', self, self.tool_try_use)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'DimensionChangeFinishServerEvent', self, self.tool_dimension_changed)
        for event in ('StartDestroyBlockServerEvent', 'ServerPlayerTryDestroyBlockEvent'):
            self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), event, self, self.tool_prevent_break)

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
        if player not in serverApi.GetPlayerList() or self.held_tool(player) != SURVEY_WAND:
            return
        if args.get('action') == 'reset':
            self.world_points.pop(player, None)
            self.world_regions.pop(player, None)
            self.NotifyToClient(player, 'WorldToolPoint', {'clear': True})
        elif args.get('action') == 'point':
            try:
                pos = coordinate(args.get('pos'))
                foot = serverApi.GetEngineCompFactory().CreatePos(player).GetFootPos()
                if foot is None or sum((pos[i] + .5 - foot[i]) ** 2 for i in range(3)) > 144.:
                    raise ValueError('请在 12 格以内选取方块')
                dimension = serverApi.GetEngineCompFactory().CreateDimension(player).GetEntityDimensionId()
                self.tool_use_on(dict(zip(('x','y','z'),pos), entityId=player, dimensionId=dimension,
                                      itemDict={'newItemName': SURVEY_WAND}, face=args.get('face')))
            except (ValueError, TypeError, KeyError) as error:
                self.NotifyToClient(player, 'WorldToolPoint', {'error': error_text(error)})

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
        args['ret'] = True
        if name == TERMINAL:
            self.open_terminal(player)
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
                return
            previous = self.world_points.get(player)
            if previous and previous[1] == dimension and now - previous[2] < 600.:
                origin, size = selection(previous[0], pos)
                self.validate_target(adapter, origin, Document(size))
                self.world_points.pop(player, None)
                self.world_regions[player] = (dimension, origin, size)
                self.NotifyToClient(player, 'WorldToolPoint', {'index': 1, 'pos': pos,
                    'face': face, 'dimension': dimension, 'origin': origin, 'size': size})
            else:
                self.world_regions.pop(player, None)
                self.world_points[player] = (pos, dimension, now)
                self.NotifyToClient(player, 'WorldToolPoint', {'index': 0, 'pos': pos,
                    'face': face, 'dimension': dimension})
        except (ValueError, TypeError, KeyError) as error:
            self.world_points.pop(player, None)
            self.world_regions.pop(player, None)
            self.NotifyToClient(player, 'WorldToolPoint', {'error': error_text(error), 'clear': True})

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
        if args.get('action') == 'cancel':
            upload = self.uploads.get(player)
            if upload and upload[0] == request:
                self.uploads.pop(player, None)
            else:
                upload = None
            entry = self.jobs.get(player)
            if entry and entry[0] == request:
                if isinstance(entry[2], WorldJob):
                    entry[2].fail('操作已取消，正在恢复本次修改')
                else:
                    self.jobs.pop(player, None)
                    self.reply(player, request, done=True, error='世界读取已取消')
            elif upload:
                self.reply(player, upload[0], done=True, error='建筑传输已取消')
            return
        if args.get('action') == 'upload' or args.get('stream') is not None:
            try:
                if args.get('action') != 'upload':
                    if player in self.jobs or player in self.uploads or args.get('action') not in ('apply', 'check'):
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
                    self.validate_target(adapter, origin, Document(header.get('size', ())))
                    self.uploads[player] = (request, dict(args), Receiver(), time.time(), adapter)
                entry = self.uploads.get(player)
                if entry is None or entry[0] != request:
                    raise ValueError('建筑上传请求已失效')
                unused, initial, receiver, unused_time, adapter = entry
                if (adapter.factory.CreateDimension(player).GetEntityDimensionId() != adapter.dimension or
                        (initial['action'] == 'apply' and not adapter.allowed())):
                    raise ValueError('传输期间权限或维度已改变，请重试')
                packet = args.get('stream')
                result = receiver.feed(packet)
                self.uploads[player] = (request, initial, receiver, time.time(), adapter)
                self.reply(player, request, done=False, uploadAck=packet['seq'])
                if result is not None:
                    self.uploads.pop(player, None)
                    initial.pop('stream', None)
                    self.request(initial, result, adapter)
            except (ValueError, TypeError, KeyError) as error:
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
            if action == 'capture' and args.get('source') == 'world_item':
                region = self.world_regions.get(player)
                if region != (adapter.dimension, tuple(args.get('origin', ())), tuple(args.get('size', ()))):
                    raise ValueError('世界选区已改变，请重新选择两个角点')
            if action == 'apply' and not adapter.allowed():
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
                doc = Document(tuple(args.get('size', ()))) if action == 'capture' else transferred
                self.validate_target(adapter, origin, doc)
                if action == 'apply':
                    job = WorldJob(adapter, doc, origin, include_air=args.get('includeAir') is True)
                else:
                    job = self.read_job(player, request, action, adapter, doc, origin)
            self.jobs[player] = (request, action, job, adapter, 0)
        except (ValueError, TypeError, KeyError) as error:
            self.reply(player, request, done=True, error=error_text(error))

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
            if action == 'capture':
                if value != AIR:
                    doc.blocks[pos] = value
            elif value == adapter.canonical(doc.get(pos)):
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
                    if job.error:
                        self.reply(player, request, done=True, error=job.error)
                    else:
                        self.reply(player, request, done=True, message='已写入 %d 格' % len(job.journal))
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
                    phase = {'preflight':'检查目标', 'write':'写入方块', 'rollback':'恢复修改'}[job.phase]
                    self.reply(player, request, done=False, message='%s，已处理 %d 格' % (phase, max(0,job.cursor)))
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
            entry[2].fail('玩家已离开，恢复本次修改')
        else:
            self.jobs.pop(player, None)

    def Destroy(self):
        for entry in self.jobs.values():
            job = entry[2]
            if isinstance(job, WorldJob) and job.journal:
                job.fail('关闭世界，恢复未完成的写入')
                while not job.done:
                    job.step(512)
