# -*- coding: utf-8 -*-
"""Client SDK boundary: local library, previews, selection outline and ghost models."""
from __future__ import unicode_literals
import math
import sys
import zlib
import json
import time
import mod.client.extraClientApi as clientApi
from .model import AIR, Document, Editor, add, bounds
from .world import coordinate
from .transfer import Receiver, packets
from .model import SMALL_VOLUME


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
        self.upload = None
        self.upload_sequence = None
        self.download = None
        self.projection_serial = 0
        self.projection_entities = {}
        self.frame_pumps = 0
        self.frame_work = []

    def later(self, delay, callback):
        def invoke():
            if self.alive:
                callback()
        return self.factory.CreateGame(self.level).AddTimer(delay, invoke)

    def next_frame(self, callback):
        if self.frame_pumps:
            self.frame_work.append(callback)
        else:
            self.later(0., callback)

    def pump_frame(self):
        pending, self.frame_work = self.frame_work, []
        for callback in pending:
            if self.alive:
                callback()

    def attach_frame_pump(self):
        self.frame_pumps += 1
        def detach():
            self.frame_pumps -= 1
            if not self.frame_pumps:
                pending, self.frame_work = self.frame_work, []
                for callback in pending:
                    self.later(0., callback)
        return detach

    def load_library(self):
        return self.factory.CreateConfigClient(self.level).GetConfigData('modern_projection_library', True)

    def load_preferences(self):
        return self.factory.CreateConfigClient(self.level).GetConfigData('modern_projection_preferences', True)

    def save_preferences(self, value):
        return self.factory.CreateConfigClient(self.level).SetConfigData('modern_projection_preferences', value, True)

    def request_catalogue(self):
        self.system.NotifyToServer('BlockCatalogueRequest', {})
        def timeout():
            if self.session.catalogue_loading and not getattr(self, 'catalogue_work', None):
                self.session.catalogue_loading = False
                self.session.emit('block_catalogue')
        self.later(10., timeout)

    def receive_catalogue(self, args):
        from .materials import VARIANTS, entry, clean_name, inventory_info, unique_inventory
        names = args.get('names', [])
        if not isinstance(names, list):
            return
        queue = [(clean_name(name), aux) for name in names
                 for aux in range(VARIANTS.get(clean_name(name).split(':')[-1], 1))]
        queue.extend(item['value'] for item in self.session.block_catalogue)
        self.catalogue_work = queue
        comp = self.factory.CreateItem(self.level)
        found = dict((item['value'], item) for item in self.session.block_catalogue)
        def advance():
            if self.catalogue_work is not queue:
                return
            deadline = time.time()+.003
            for unused in range(16):
                if not queue:
                    self.session.block_catalogue = unique_inventory(found.values(), self.session.palette)
                    self.session.catalogue_loading = False
                    self.session.catalogue_ready = True
                    self.catalogue_work = None
                    self.session.emit('block_catalogue')
                    return
                name, aux = queue.pop()
                info = comp.GetItemBasicInfo(native(name), aux)
                # Internal blocks with no inventory item are not useful in the picker.
                if inventory_info(info):
                    found[(name, aux)] = entry(name, aux, info['itemName'], info.get('itemCategory'))
                if time.time() >= deadline:
                    break
            self.next_frame(advance)
        self.next_frame(advance)

    def save_library(self, value):
        return self.factory.CreateConfigClient(self.level).SetConfigData('modern_projection_library', value, True)

    def load_archive_page(self, identity, part):
        key = native('modern_projection_building_%d_%d' % (identity, part))
        return self.factory.CreateConfigClient(self.level).GetConfigData(key, True)

    def save_archive_page(self, identity, part, value):
        key = native('modern_projection_building_%d_%d' % (identity, part))
        return self.factory.CreateConfigClient(self.level).SetConfigData(key, value, True)

    def clear_archive(self, identity, parts):
        def clear(part=0):
            if part < parts:
                self.save_archive_page(identity, part, {})
                self.later(0., lambda: clear(part + 1))
        self.later(0., clear)

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

    def geometry(self, document, visible=None, name=None):
        data = document.palette_data(visible)
        if not data['common']:
            return None
        # The embedded Python omits hashlib.sha256. An exact compressed key
        # avoids collisions and retains no second Python list of voxel indices.
        fingerprint = None if name is not None else zlib.compress(repr((document.size, sorted(data['common'].items()))).encode('utf8'), 1)
        if fingerprint is not None and fingerprint in self.models:
            return self.models[fingerprint]
        # Identical content reuses native geometry across undo and page changes.
        name = native(name or 'modern_projection_%d' % len(self.models))
        data['common'] = dict(((native(k[0]), k[1]), v) for k, v in data['common'].items())
        data = dict((native(k), v) for k, v in data.items())
        palette = self.factory.CreateBlock(self.level).GetBlankBlockPalette()
        if palette is None or not palette.DeserializeBlockPalette(data):
            raise ValueError('方块调色板生成失败')
        result = self.factory.CreateBlockGeometry(self.level).CombineBlockPaletteToGeometry(palette, name, 0)
        if result and fingerprint is not None:
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
        if self.session.edit_job is not None or self.session.io_job is not None:
            raise ValueError('请等待编辑任务完成')
        if self.pending is not None:
            raise ValueError('请等待当前世界操作完成')
        self.request_id += 1
        self.pending = self.request_id
        self.pending_data = (action, data)
        self.pending_state = (id(self.session.editor), self.session.editor.revision, tuple(self.session.origin))
        data = dict(data, action=action, request=self.request_id)
        self.session.busy = True
        self.download = Receiver() if action == 'capture' else None
        document = data.get('document')
        if isinstance(document, Document):
            data.pop('document')
            snapshot = Document(document.size, name=document.name)
            snapshot.blocks = document.blocks.copy()
            self.upload = packets(snapshot)
            packet = next(self.upload)
            self.upload_sequence = packet['seq']
            data['stream'] = packet
        self.system.NotifyToServer('ProjectionRequest', data)
        self.session.emit()

    def capture(self):
        if None in self.corners:
            raise ValueError('尚未设置世界选区，无法读取')
        lo, hi = bounds(self.corners)
        size = tuple(hi[i] - lo[i] + 1 for i in range(3))
        Document(size)
        self.request('capture', {'origin': lo, 'size': size})

    def check_progress(self):
        s = self.session
        self.request('check', {'origin': coordinate(s.origin), 'document': s.editor.document})

    def apply_world(self):
        s = self.session
        self.request('apply', {'origin': coordinate(s.origin), 'document': s.editor.document, 'includeAir': s.apply_air})

    def undo_world(self):
        self.request('undo', {})

    def cancel_world(self):
        if self.pending is not None:
            self.upload = None
            self.system.NotifyToServer('ProjectionRequest', {'request': self.pending, 'action': 'cancel'})

    def receive(self, args):
        if args.get('request') != self.pending:
            return
        s = self.session
        if not args.get('done'):
            if 'uploadAck' in args:
                if self.upload is not None and args['uploadAck'] == self.upload_sequence:
                    request = self.pending
                    def send_next():
                        if self.pending != request or self.upload is None:
                            return
                        try:
                            packet = next(self.upload)
                        except StopIteration:
                            self.upload = None
                            return
                        self.upload_sequence = packet['seq']
                        self.system.NotifyToServer('ProjectionRequest', {'request': request, 'action': 'upload', 'stream': packet})
                    self.later(0., send_next)
                return
            if 'documentPacket' in args:
                try:
                    self.download.feed(args['documentPacket'])
                except (ValueError, TypeError, KeyError) as error:
                    self.cancel_world()
                    s.editor.message = str(error)
                    self.pending = self.pending_data = self.pending_state = None
                    self.download = None
                    s.busy = False
                    s.emit()
                return
            s.editor.message = args.get('message', '正在处理世界数据')
            if isinstance(s.editor.message, bytes):
                s.editor.message = s.editor.message.decode('utf8')
            s.emit()
            return
        action, sent = self.pending_data
        state = self.pending_state
        self.pending = self.pending_data = self.pending_state = None
        self.upload = None
        s.busy = False
        if args.get('error'):
            s.editor.message = args['error']
        elif action in ('capture', 'check') and state != (id(s.editor), s.editor.revision, tuple(s.origin)):
            s.editor.message = '草稿或原点已改变，请重新读取或检查'
        elif action == 'capture':
            document = self.download.result if args.get('streamed') and self.download else Document.from_data(args['document'])
            if document is None:
                s.editor.message = '建筑传输不完整，请重新读取'
                s.emit()
                return
            s.editor = Editor(document)
            s.focused = s.box_anchor = None
            s.name = s.editor.document.name
            s.origin = tuple(sent['origin'])
            s.canvas_x = s.canvas_z = 0
            s.progress = None
            s.reset_camera(False)
            s.editor.message = '已读取世界选区，方块实体内容不包含在草稿中'
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
        if s.editor.document.volume > SMALL_VOLUME:
            return self.project_large(origin)
        if self.projection_entities:
            self.stop_projection()
        info = self.factory.CreateBlockInfo(self.level)

        def visible(pos):
            if not s.visible_layer(pos[1]):
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
                s.editor.message = '投影已生成，关闭工作台即可在世界中查看'
            else:
                self.system.DestroyClientEntity(entity)
                s.editor.message = '透明投影生成失败，原投影已保留'
            s.emit()
        self.later(.2, attach)

    def stop_projection(self):
        self.projection_serial += 1
        for entity in self.projection_entities.values():
            self.system.DestroyClientEntity(entity)
        self.projection_entities = {}
        if self.preparing_entity:
            self.system.DestroyClientEntity(self.preparing_entity)
        self.preparing_entity = None
        if self.entity:
            self.system.DestroyClientEntity(self.entity)
        self.entity = None
        self.session.projection_active = False
        self.session.editor.message = '投影已关闭'

    def project_large(self, origin):
        """Stream exact nearby 16-cubed ghosts as the builder moves around."""
        self.stop_projection()
        self.projection_serial += 1
        serial = self.projection_serial
        s = self.session
        document = Document(s.editor.document.size)
        document.blocks = s.editor.document.blocks.copy()
        hidden, solo, layer = s.preview_hidden(), s.solo_layer, s.editor.layer
        opacity, missing = s.opacity, s.projection_missing
        s.projection_active = True
        s.editor.message = '投影已开启，随玩家位置加载附近方块'
        info = self.factory.CreateBlockInfo(self.level)
        preparing = set()
        empty = set()

        def active():
            return self.alive and serial == self.projection_serial

        def update():
            if not active():
                return
            player = self.player_origin()
            center = tuple((player[i] - origin[i]) // 16 for i in range(3))
            candidates = []
            for key in document.blocks.chunks:
                if max(abs(key[i] - center[i]) for i in range(3)) <= 3 and any(
                        key[1] * 16 + y not in hidden and (not solo or key[1] * 16 + y == layer) for y in range(16)):
                    candidates.append(key)
            desired = set(sorted(candidates, key=lambda k: sum((k[i] - center[i]) ** 2 for i in range(3)))[:32])
            empty.intersection_update(desired)
            for key in list(self.projection_entities):
                if key not in desired:
                    self.system.DestroyClientEntity(self.projection_entities.pop(key))
            todo = [key for key in desired if key not in self.projection_entities and key not in preparing and key not in empty]
            if todo:
                key = min(todo, key=lambda k: sum((k[i] - center[i]) ** 2 for i in range(3)))
                preparing.add(key)
                local = Document((16, 16, 16))
                start = tuple(v * 16 for v in key)
                def build():
                    if not active():
                        return
                    try:
                        for y in range(16):
                            if start[1] + y in hidden or (solo and start[1] + y != layer):
                                continue
                            for z in range(16):
                                for x in range(16):
                                    pos = (start[0] + x, start[1] + y, start[2] + z)
                                    value = document.get(pos)
                                    if value != AIR:
                                        actual = info.GetBlock(add(origin, pos)) if missing else None
                                        if not missing or (actual is not None and tuple(actual) != value):
                                            local.blocks[(x, y, z)] = value
                            yield None
                        name = self.geometry(local)
                        if name:
                            world = add(origin, start)
                            entity = self.system.CreateClientEntityByTypeStr(native('modern_projection:anchor'), tuple(float(v) for v in world), (0., 0.))
                            if entity:
                                self.projection_entities[key] = entity
                                def attach():
                                    if active() and self.projection_entities.get(key) == entity:
                                        render = self.factory.CreateActorRender(entity)
                                        if render.AddActorBlockGeometry(name):
                                            render.EnableActorBlockGeometryTransparent(name, True)
                                            render.SetActorBlockGeometryTransparency(name, opacity)
                                self.later(.2, attach)
                        else:
                            empty.add(key)
                    finally:
                        preparing.discard(key)
                iterator = build()
                def advance():
                    if not active():
                        return
                    deadline = time.time() + .004
                    try:
                        while time.time() < deadline:
                            next(iterator)
                    except StopIteration:
                        return
                    except (ValueError, TypeError, RuntimeError) as error:
                        preparing.discard(key)
                        s.editor.message = str(error)
                        return
                    self.later(0., advance)
                self.later(0., advance)
            self.later(.1, update)
        self.later(0., update)

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
