# -*- coding: utf-8 -*-
"""Client SDK boundary: local library, previews, selection outline and ghost models."""
from __future__ import unicode_literals
import math
import sys
import mod.client.extraClientApi as clientApi
from .model import AIR, Document, Editor, add, bounds
from .world import coordinate


def native(value):
    return value.encode('utf8') if sys.version_info[0] == 2 and isinstance(value, type('')) else value


class ClientBridge(object):
    def __init__(self, system):
        self.system = system
        self.factory = clientApi.GetEngineCompFactory()
        self.level = clientApi.GetLevelId()
        self.player = clientApi.GetLocalPlayerId()
        self.session = None
        self.corners = [None, None]
        self.outline = []
        self.entity = None
        self.preparing_entity = None
        self.request_id = 0
        self.pending = None
        self.pending_data = None
        self.pending_state = None
        self.models = {}
        self.alive = True

    def later(self, delay, callback):
        def invoke():
            if self.alive:
                callback()
        return self.factory.CreateGame(self.level).AddTimer(delay, invoke)

    def load_library(self):
        return self.factory.CreateConfigClient(self.level).GetConfigData('modern_projection_library', True)

    def save_library(self, value):
        return self.factory.CreateConfigClient(self.level).SetConfigData('modern_projection_library', value, True)

    def player_origin(self):
        pos = self.factory.CreatePos(self.player).GetFootPos()
        if pos is None:
            return (0, 64, 0)
        return tuple(int(math.floor(v)) for v in pos)

    def use_player_origin(self):
        self.session.origin = self.player_origin()
        self.session.progress = None
        self.session.editor.message = '已将投影原点设为玩家脚下'
        self.session.emit()

    def geometry(self, document, visible=None):
        data = document.palette_data(visible)
        if not data['common']:
            return None
        fingerprint = (document.size, tuple(sorted((k, tuple(sorted(v))) for k, v in data['common'].items())))
        if fingerprint in self.models:
            return self.models[fingerprint]
        # Identical content reuses native geometry across undo and page changes.
        name = native('modern_projection_%d' % len(self.models))
        data['common'] = dict(((native(k[0]), k[1]), v) for k, v in data['common'].items())
        data = dict((native(k), v) for k, v in data.items())
        palette = self.factory.CreateBlock(self.level).GetBlankBlockPalette()
        if palette is None or not palette.DeserializeBlockPalette(data):
            raise ValueError('方块调色板生成失败')
        result = self.factory.CreateBlockGeometry(self.level).CombineBlockPaletteToGeometry(palette, name, 0)
        if result:
            self.models[fingerprint] = result
        return result

    def mark(self, index):
        pick = self.factory.CreateCamera(self.level).PickFacing()
        pos = tuple(int(pick[k]) for k in ('x', 'y', 'z')) if pick and pick.get('type') == 'Block' else self.player_origin()
        self.corners[index] = pos
        self.draw_bounds()
        self.session.editor.message = '已标记%s：%d, %d, %d' % tuple(['起点' if index == 0 else '终点'] + list(pos))
        self.factory.CreateTextNotifyClient(self.level).SetLeftCornerNotify(native(self.session.editor.message))
        self.session.emit()

    def draw_bounds(self):
        for shape in self.outline:
            shape.Remove()
        self.outline = []
        points = [p for p in self.corners if p is not None]
        if not points:
            return
        lo, hi = bounds(points)
        hi = tuple(v + 1. for v in hi)
        drawing = self.factory.CreateDrawing(self.level)
        for axis in range(3):
            other = [i for i in range(3) if i != axis]
            for a in (0, 1):
                for b in (0, 1):
                    start, end = list(lo), list(lo)
                    start[other[0]] = end[other[0]] = (lo, hi)[a][other[0]]
                    start[other[1]] = end[other[1]] = (lo, hi)[b][other[1]]
                    end[axis] = hi[axis]
                    shape = drawing.AddLineShape(tuple(start), tuple(end), (.28, .60, 1.))
                    if shape:
                        self.outline.append(shape)

    def request(self, action, data):
        if self.pending is not None:
            raise ValueError('请等待当前世界操作完成')
        self.request_id += 1
        self.pending = self.request_id
        self.pending_data = (action, data)
        self.pending_state = (id(self.session.editor), self.session.editor.revision, tuple(self.session.origin))
        data = dict(data, action=action, request=self.request_id)
        self.session.busy = True
        self.system.NotifyToServer('ProjectionRequest', data)
        self.session.emit()

    def capture(self):
        if None in self.corners:
            raise ValueError('先关闭工作台，用 F6 / F7 标记世界中的两点')
        lo, hi = bounds(self.corners)
        size = tuple(hi[i] - lo[i] + 1 for i in range(3))
        Document(size)
        self.request('capture', {'origin': lo, 'size': size})

    def check_progress(self):
        s = self.session
        self.request('check', {'origin': coordinate(s.origin), 'document': s.editor.document.to_data()})

    def apply_world(self):
        s = self.session
        self.request('apply', {'origin': coordinate(s.origin), 'document': s.editor.document.to_data(), 'includeAir': s.apply_air})

    def undo_world(self):
        self.request('undo', {})

    def receive(self, args):
        if args.get('request') != self.pending:
            return
        s = self.session
        if not args.get('done'):
            s.editor.message = args.get('message', '正在处理世界数据')
            if isinstance(s.editor.message, bytes):
                s.editor.message = s.editor.message.decode('utf8')
            s.emit()
            return
        action, sent = self.pending_data
        state = self.pending_state
        self.pending = self.pending_data = None
        s.busy = False
        if args.get('error'):
            s.editor.message = args['error']
        elif action in ('capture', 'check') and state != (id(s.editor), s.editor.revision, tuple(s.origin)):
            s.editor.message = '草稿或原点已改变，请重新读取或检查'
        elif action == 'capture':
            s.editor = Editor(Document.from_data(args['document']))
            s.name = s.editor.document.name
            s.origin = tuple(sent['origin'])
            s.canvas_x = s.canvas_z = 0
            s.progress = None
            s.editor.message = '已读取世界选区 · 方块实体内容不包含在草稿中'
            s.refresh_preview()
        elif action == 'check':
            s.progress = args['progress']
            s.editor.message = '建造进度已更新'
        else:
            s.editor.message = args.get('message', '操作完成')
        if isinstance(s.editor.message, bytes):
            s.editor.message = s.editor.message.decode('utf8')
        s.emit()

    def project(self):
        s = self.session
        origin = coordinate(s.origin)
        info = self.factory.CreateBlockInfo(self.level)

        def visible(pos):
            if pos[1] in s.editor.hidden_layers or (s.solo_layer and pos[1] != s.editor.layer):
                return False
            if s.projection_missing:
                actual = info.GetBlock(add(origin, pos))
                if actual is None:
                    raise ValueError('投影区域尚未加载，请靠近目标位置')
                return tuple(actual) != s.editor.document.get(pos)
            return True
        name = self.geometry(s.editor.document, visible)
        if not name:
            self.stop_projection()
            s.editor.message = '当前过滤条件下没有需要投影的方块'
            return
        entity = self.system.CreateClientEntityByTypeStr(native('modern_projection:anchor'), tuple(float(v) for v in origin), (0., 0.))
        if not entity:
            raise ValueError('无法创建投影，请靠近目标区域')
        if self.preparing_entity:
            self.system.DestroyClientEntity(self.preparing_entity)
        self.preparing_entity = entity
        opacity = s.opacity
        s.editor.message = '正在准备透明投影…'

        def attach():
            if self.preparing_entity != entity:
                return
            # A newly created client actor has no renderer until a later frame.
            # Attaching in its creation tick returns True but produces no model.
            render = self.factory.CreateActorRender(entity)
            success = (render.AddActorBlockGeometry(name) and render.EnableActorBlockGeometryTransparent(name, True)
                       and render.SetActorBlockGeometryTransparency(name, opacity))
            self.preparing_entity = None
            if success:
                if self.entity:
                    self.system.DestroyClientEntity(self.entity)
                self.entity = entity
                s.projection_active = True
                s.editor.message = '投影已生成 · 关闭工作台即可在世界中查看'
            else:
                self.system.DestroyClientEntity(entity)
                s.editor.message = '透明投影生成失败，原投影已保留'
            s.emit()
        self.later(.2, attach)

    def stop_projection(self):
        if self.preparing_entity:
            self.system.DestroyClientEntity(self.preparing_entity)
        self.preparing_entity = None
        if self.entity:
            self.system.DestroyClientEntity(self.entity)
        self.entity = None
        self.session.projection_active = False
        self.session.editor.message = '投影已关闭'

    def dimension_changed(self, unused):
        self.stop_projection()
        self.corners = [None, None]
        self.draw_bounds()
        self.session.progress = None
        self.session.emit()

    def destroy(self):
        self.alive = False
        self.stop_projection()
        self.corners = [None, None]
        self.draw_bounds()
