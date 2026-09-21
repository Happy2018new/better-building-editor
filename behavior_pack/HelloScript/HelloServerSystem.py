# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import mod.server.extraServerApi as serverApi
from .projection.model import AIR, Document, add, block
from .projection.world import WorldJob, coordinate
from .projection.transfer import Receiver, packets
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
        """Resolve legacy split IDs without placing temporary blocks in the world."""
        if value not in self.canonical_values:
            result = value
            if value != AIR:
                info = self.factory.CreateItem(self.level).GetItemInfoByBlockName(value[0].encode('utf8'), value[1])
                # Only upgrade the legacy identity, never replace a technical
                # block with its dropped item (lit lamps, crops, upper doors...).
                split_tree = value[0] in ('minecraft:log', 'minecraft:log2', 'minecraft:leaves', 'minecraft:leaves2')
                renamed = value[0] in ('minecraft:stonebrick', 'minecraft:grass')
                if info and (info.get('itemName') == value[0] or split_tree or renamed) and info.get('newItemName') != value[0]:
                    name = info.get('newItemName')
                    if name and self.info.GetBlockBasicInfo(name.encode('utf8')):
                        states = self.factory.CreateBlockState(self.level)
                        old_states = states.GetBlockStatesFromAuxValue(value[0].encode('utf8'), value[1])
                        # State lookup already splits legacy IDs and loses the
                        # old log-axis / leaf flags. Decode these known families.
                        if value[0] in ('minecraft:log', 'minecraft:log2'):
                            old_states = {'pillar_axis': ('y', 'x', 'z', 'y')[(value[1] >> 2) & 3]}
                        elif value[0] in ('minecraft:leaves', 'minecraft:leaves2'):
                            old_states = {'persistent_bit': bool(value[1] & 4), 'update_bit': bool(value[1] & 8)}
                        aux = states.GetBlockAuxValueFromStates(name.encode('utf8'), old_states) if old_states is not None else None
                        if aux is None or aux < 0:
                            raise ValueError('无法转换旧版方块状态，请重新选择该材质')
                        result = block((name, aux))
            self.canonical_values[value] = result
        return self.canonical_values[value]

    def read(self, pos):
        data = self.info.GetBlockNew(pos, self.dimension)
        if not data or not data.get('name') or data['name'] == 'minecraft:unknown':
            return None
        return block((data['name'], data.get('aux', 0)))

    def write(self, pos, value):
        name = value[0].encode('utf8')
        # Suppress explicit neighbor updates; native ticks can still change blocks.
        # GetBlockNew and state conversion return traditional aux. False here
        # reinterprets modern log axes as runtime indices and resets them to Y.
        return self.info.SetBlockNew(pos, {'name': name, 'aux': value[1]}, 0, self.dimension, True, False)

    def protected(self, pos, value):
        if value[0] in ('minecraft:bedrock', 'minecraft:barrier', 'minecraft:allow', 'minecraft:deny'):
            return True
        return self.info.GetBlockEntityData(self.dimension, pos) is not None

    def valid(self, value):
        if value[0] not in self.validity:
            data = self.info.GetBlockBasicInfo(value[0].encode('utf8'))
            self.validity[value[0]] = bool(data)
        return self.validity[value[0]]


class HelloServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        ServerSystem.__init__(self, namespace, systemName)
        self.jobs = {}
        self.undo_records = {}
        self.uploads = {}
        self.ListenForEvent('ModernProjection', 'HelloClientSystem', 'ProjectionRequest', self, self.request)
        self.ListenForEvent('ModernProjection', 'HelloClientSystem', 'BlockCatalogueRequest', self, self.block_catalogue)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'OnScriptTickServer', self, self.tick)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'DelServerPlayerEvent', self, self.leave)

    def reply(self, player, request, **data):
        data['request'] = request
        if data.get('done'):
            record = self.undo_records.get(player)
            data['canUndo'] = bool(record and record[1])
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
            if action not in ('capture', 'check', 'apply', 'undo'):
                raise ValueError('未知的世界操作')
            adapter = upload_adapter or WorldAdapter(player)
            if action in ('apply', 'undo') and not adapter.allowed():
                raise ValueError('世界写入需要创造模式、操作员和建造权限')
            if action == 'undo':
                record = self.undo_records.get(player)
                if not record:
                    raise ValueError('没有可以撤销的世界写入')
                if record[0] != adapter.dimension:
                    raise ValueError('请返回写入时的维度再撤销')
                job = WorldJob(adapter, None, (0, 0, 0), record[1])
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
                yield None
                batch = 0
                deadline = time.time() + .006
        if action == 'capture':
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
            if action in ('apply', 'undo'):
                job.step()
                if job.done:
                    if player not in serverApi.GetPlayerList():
                        self.jobs.pop(player, None)
                        self.undo_records.pop(player, None)
                        continue
                    if job.error:
                        if job.journal:
                            self.undo_records[player] = (adapter.dimension, job.journal)
                        self.reply(player, request, done=True, error=job.error)
                    else:
                        if action == 'apply':
                            self.undo_records[player] = (adapter.dimension, job.journal)
                        else:
                            self.undo_records.pop(player, None)
                        self.reply(player, request, done=True, message='已%s %d 格，跳过 %d 格' %
                                   ('撤销' if action == 'undo' else '写入', len(job.journal), job.skipped))
                    self.jobs.pop(player, None)
            else:
                try:
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
                else:
                    self.reply(player, request, done=False, message='正在读取世界，已处理 %d 批' % (ticks + 1))

    def leave(self, args):
        player = args.get('id')
        self.uploads.pop(player, None)
        entry = self.jobs.get(player)
        if entry and isinstance(entry[2], WorldJob):
            entry[2].fail('玩家已离开，恢复本次修改')
        else:
            self.jobs.pop(player, None)
        self.undo_records.pop(player, None)

    def Destroy(self):
        for entry in self.jobs.values():
            job = entry[2]
            if isinstance(job, WorldJob) and job.journal:
                job.fail('关闭世界，恢复未完成的写入')
                while not job.done:
                    job.step(512)
