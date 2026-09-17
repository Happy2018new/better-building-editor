# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import mod.server.extraServerApi as serverApi
from .projection.model import AIR, Document, add, block
from .projection.world import WorldJob, coordinate

ServerSystem = serverApi.GetServerSystemCls()


class WorldAdapter(object):
    def __init__(self, player):
        self.player = player
        self.factory = serverApi.GetEngineCompFactory()
        self.level = serverApi.GetLevelId()
        self.dimension = self.factory.CreateDimension(player).GetEntityDimensionId()
        self.info = self.factory.CreateBlockInfo(self.level)
        self.validity = {}

    def allowed(self):
        return (self.factory.CreateGame(self.level).GetPlayerGameType(self.player) == 1 and
                self.factory.CreateDimension(self.player).GetEntityDimensionId() == self.dimension)

    def read(self, pos):
        data = self.info.GetBlockNew(pos, self.dimension)
        if not data or not data.get('name') or data['name'] == 'minecraft:unknown':
            return None
        return block((data['name'], data.get('aux', 0)))

    def write(self, pos, value):
        name = value[0].encode('utf8')
        # Suppress neighbor updates so a batch cannot cascade outside its cuboid.
        return self.info.SetBlockNew(pos, {'name': name, 'aux': value[1]}, 0, self.dimension, False, False)

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
        self.ListenForEvent('ModernProjection', 'HelloClientSystem', 'ProjectionRequest', self, self.request)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'OnScriptTickServer', self, self.tick)
        self.ListenForEvent(serverApi.GetEngineNamespace(), serverApi.GetEngineSystemName(), 'DelServerPlayerEvent', self, self.leave)

    def reply(self, player, request, **data):
        data['request'] = request
        self.NotifyToClient(player, 'ProjectionResponse', data)

    def request(self, args):
        # Use engine-injected identity, never a client-selected player id.
        player, request = args.get('__id__'), args.get('request')
        if not player:
            return
        if player in self.jobs:
            self.reply(player, request, done=True, error='已有世界操作正在进行')
            return
        try:
            action = args.get('action')
            if action not in ('capture', 'check', 'apply', 'undo'):
                raise ValueError('未知的世界操作')
            adapter = WorldAdapter(player)
            if action == 'undo':
                record = self.undo_records.get(player)
                if not record:
                    raise ValueError('没有可以撤销的世界写入')
                if record[0] != adapter.dimension:
                    raise ValueError('请返回写入时的维度再撤销')
                job = WorldJob(adapter, None, (0, 0, 0), record[1])
            else:
                origin = coordinate(args.get('origin'))
                doc = Document(tuple(args.get('size', ()))) if action == 'capture' else Document.from_data(args.get('document'))
                if origin[1] < -64 or origin[1] + doc.size[1] > (320 if adapter.dimension == 0 else 256):
                    raise ValueError('选区超出维度建造高度')
                foot = adapter.factory.CreatePos(player).GetFootPos()
                if foot is None or any(abs(origin[i] - foot[i]) > 128 for i in range(3)):
                    raise ValueError('请移动到目标区域附近（128 格以内）')
                if action == 'apply':
                    if not adapter.allowed():
                        raise ValueError('仅创造模式可写入世界；生存模式请使用投影')
                    job = WorldJob(adapter, doc, origin, include_air=args.get('includeAir') is True)
                else:
                    job = self.read_job(player, request, action, adapter, doc, origin)
            self.jobs[player] = (request, action, job, adapter, 0)
        except (ValueError, TypeError, KeyError) as error:
            self.reply(player, request, done=True, error=str(error))

    def read_job(self, player, request, action, adapter, doc, origin):
        stats = {'total': len(doc.blocks), 'correct': 0, 'missing': 0, 'wrong': 0}
        points = doc.points() if action == 'capture' else sorted(doc.blocks)
        for index, pos in enumerate(points):
            value = adapter.read(add(origin, pos))
            if value is None:
                self.reply(player, request, done=True, error='区域尚未加载，请靠近后重试')
                return
            if action == 'capture':
                if value != AIR:
                    doc.blocks[pos] = value
            elif value == doc.get(pos):
                stats['correct'] += 1
            elif value == AIR:
                stats['missing'] += 1
            else:
                stats['wrong'] += 1
            if index % 128 == 127:
                yield None
        if action == 'capture':
            doc.name = '世界选区'
            self.reply(player, request, done=True, document=doc.to_data())
        else:
            self.reply(player, request, done=True, progress=stats)

    def tick(self, unused=None):
        for player, entry in list(self.jobs.items()):
            request, action, job, adapter, ticks = entry
            self.jobs[player] = (request, action, job, adapter, ticks + 1)
            if action in ('apply', 'undo'):
                job.step()
                if job.done:
                    if job.error:
                        if job.journal:
                            self.undo_records[player] = (adapter.dimension, job.journal)
                        self.reply(player, request, done=True, error=job.error)
                    else:
                        if action == 'apply':
                            self.undo_records[player] = (adapter.dimension, job.journal)
                        else:
                            self.undo_records.pop(player, None)
                        self.reply(player, request, done=True, message='已%s %d 格 · 跳过 %d 格' %
                                   ('撤销' if action == 'undo' else '写入', len(job.journal), job.skipped))
                    self.jobs.pop(player, None)
            else:
                try:
                    next(job)
                except StopIteration:
                    self.jobs.pop(player, None)
            if ticks % 20 == 0 and player in self.jobs:
                self.reply(player, request, done=False, message='正在%s · 已处理 %d 批' %
                           ('检查 / 写入' if action in ('apply', 'undo') else '读取世界', ticks + 1))

    def leave(self, args):
        player = args.get('id')
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
