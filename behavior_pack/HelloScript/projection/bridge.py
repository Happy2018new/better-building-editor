# -*- coding: utf-8 -*-
"""Client SDK boundary: local library, previews, selection outline and ghost models."""
from __future__ import unicode_literals
import math
import zlib
import json
import time
import mod.client.extraClientApi as clientApi
from .model import AIR, Document, Editor, add, bounds, block
from .world import coordinate
from .transfer import Receiver, packets
from .model import SMALL_VOLUME


def native(value):
    return value.encode('utf8') if bytes is str and isinstance(value, type('')) else value


class ClientBridge(object):
    def __init__(self, system):
        self.system = system
        self.factory = clientApi.GetEngineCompFactory()
        self.level = clientApi.GetLevelId()
        self.player = clientApi.GetLocalPlayerId()
        self.session = None
        self.corners = [None, None]
        from .survey_effects import SurveyEffects
        self.survey_effects = SurveyEffects(self)
        self.entity = None
        self.projection_mesh = None
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
        self.projection_work = None
        self.projection_distance = None
        self.projection_requested = False
        self.projection_palette = {}
        from .projection_outline import ProjectionOutline
        self.projection_outline = ProjectionOutline(self)
        self.frame_pumps = 0
        self.frame_work = []
        self.frame_watchdog = False
        self._projection_follow_position = None

    def later(self, delay, callback):
        def invoke():
            if self.alive:
                callback()
        return self.factory.CreateGame(self.level).AddTimer(delay, invoke)

    def next_frame(self, callback):
        if self.frame_pumps:
            self.frame_work.append(callback)
            if not self.frame_watchdog:
                self.frame_watchdog = True
                self.later(.2, self.check_frame_work)
        else:
            self.later(0., callback)

    def follow_projection(self):
        """Keep large client-only actors inside the native view culler.

        Actor geometry offsets and the outline shader compensate for the
        temporary anchor position, so the visible projection remains fixed in
        world space. This is a transform-only update; no palette or model is
        rebuilt while the camera moves.
        """
        if not self.alive or not self.session:
            return
        if not self.session.projection_active and not self.survey_effects.active():
            self._projection_follow_position = None
            return
        try:
            camera = self.factory.CreateCamera(self.level)
            centre, forward = camera.GetPosition(), camera.GetForward()
            position = tuple(float(centre[i]) + 4. * forward[i] for i in range(3))
        except Exception:
            return
        self.survey_effects.follow(position)
        if not self.session.projection_active:
            return
        signature = (position, self.entity, self.projection_outline.entity)
        if signature == self._projection_follow_position:
            return
        if self.projection_mesh:
            entity, model, origin, previous = self.projection_mesh
            if entity == self.entity and position != previous:
                if not self.factory.CreatePos(entity).SetPosForClientEntity(position):
                    return
                offset = (position[0]-origin[0]-.5, origin[1]-position[1], position[2]-origin[2]-.5)
                if not self.factory.CreateActorRender(entity).SetActorBlockGeometryOffset(model, offset):
                    return
                self.projection_mesh = (entity, model, origin, position)
        if self.projection_outline.follow(position):
            self._projection_follow_position = signature

    def check_frame_work(self):
        self.frame_watchdog = False
        if self.frame_work and time.time()-getattr(self, 'last_frame_pump', 0.) >= .15:
            self.pump_frame()

    def pump_frame(self):
        self.last_frame_pump = time.time()
        pending, self.frame_work = self.frame_work, []
        for callback in pending:
            if self.alive:
                try:
                    callback()
                except Exception:
                    # One failed consumer must not discard other queued jobs.
                    import traceback
                    traceback.print_exc()

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

    def set_clipboard(self, value):
        return bool(self.factory.CreateGame(self.level).SetClipboardContent(native(value)))

    def get_clipboard(self):
        value = self.factory.CreateGame(self.level).GetClipboardContent()
        if value is None:
            return ''
        return value.decode('utf8') if isinstance(value, bytes) else value

    def describe_material(self, value):
        from .materials import clean_name
        info = self.factory.CreateItem(self.level).GetItemBasicInfo(native(value[0]), value[1])
        name = clean_name((info or {}).get('itemName', ''))
        return name if name and not name.startswith(('tile.', 'item.')) else None

    def request_catalogue(self):
        self.system.NotifyToServer('BlockCatalogueRequest', {})
        def timeout():
            if self.session.catalogue_loading and not getattr(self, 'catalogue_work', None):
                self.session.catalogue_loading = False
                self.session.emit('block_catalogue')
        self.later(10., timeout)

    def receive_catalogue(self, args):
        from .materials import entry, clean_name, inventory_info, unique_inventory
        from .block_registry import catalogue_values
        names = args.get('names', [])
        if not isinstance(names, list):
            return
        modern = catalogue_values()
        custom = [(clean_name(name), 0) for name in names
                  if not clean_name(name).startswith('minecraft:')]
        queue = list(modern) + custom
        self.catalogue_work = queue
        comp = self.factory.CreateItem(self.level)
        found = {}
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

    def notify(self, message):
        self.factory.CreateTextNotifyClient(self.level).SetLeftCornerNotify(native(message))

    def world_tool_point(self, args):
        if args.get('clear'):
            self.corners = [None, None]
            self.draw_bounds()
        if args.get('error'):
            self.notify(args['error'])
            self.session.editor.message = args['error']
            self.session.emit()
            return
        index = args.get('index')
        pos = args.get('pos')
        if index not in (0, 1) or not isinstance(pos, (tuple, list)) or len(pos) != 3:
            return
        if index == 0:
            self.corners = [tuple(pos), None]
            self.notify('第一个角点已设置，请选择另一方块')
        elif self.corners[0] is not None:
            self.corners[1] = tuple(pos)
            from .input_mode import is_touch
            action = '点击“导入选区”' if is_touch() else '左键导入，右键重选，潜行右键清除'
            self.notify(('已选择 %d × %d × %d，' % tuple(args['size'])) + action)
        self.draw_bounds()
        self.survey_effects.strike(tuple(pos))
        self.session.emit()

    def capture_new(self):
        if self.session.world_import_document is not None:
            raise ValueError('待导入选区尚未保存，请先到建筑库重试')
        if None in self.corners:
            raise ValueError('请先用投影测绘器选择两个角点')
        from .tool_items import selection
        origin, size = selection(*self.corners)
        self.request('capture', {'origin': origin, 'size': size, 'source': 'world_item'})
        self.notify('正在读取选区；导入后将新建配置，不覆盖当前草稿')

    def use_player_origin(self):
        self.session.origin = self.player_origin()
        self.session.progress = None
        self.session.editor.message = '已将投影原点设为玩家脚下'
        self.session.emit()

    def geometry(self, document, visible=None, name=None):
        from .block_registry import canonical, states
        data = document.palette_data(visible)
        if not data['common']:
            return None
        common = {}
        for value, positions in data['common'].items():
            value = canonical(value)
            if value in common:
                common[value] = common[value] + positions
            else:
                common[value] = positions
        data['common'] = common
        # Empty records are meaningful: omitting cyan stained glass (or a
        # modern plank) lets the native converter choose the first variant.
        data['states'] = {}
        for value in common:
            record = states(value)
            if record is not None:
                data['states'][value] = record
        # The embedded Python omits hashlib.sha256. An exact compressed key
        # avoids collisions and retains no second Python list of voxel indices.
        state_key = sorted((key, sorted(record.items())) for key,record in data['states'].items())
        fingerprint = None if name is not None else zlib.compress(repr((document.size, sorted(data['common'].items()), state_key)).encode('utf8'), 1)
        if fingerprint is not None and fingerprint in self.models:
            return self.models[fingerprint]
        # Identical content reuses native geometry across undo and page changes.
        name = native(name or 'modern_projection_%d' % len(self.models))
        data['common'] = dict(((native(k[0]), k[1]), v) for k, v in data['common'].items())
        data['states'] = dict(((native(k[0]), k[1]), dict((native(key),native(val))
                              for key,val in v.items())) for k, v in data['states'].items())
        data = dict((native(k), v) for k, v in data.items())
        palette = self.factory.CreateBlock(self.level).GetBlankBlockPalette()
        if palette is None or not palette.DeserializeBlockPalette(data):
            raise ValueError('方块调色板生成失败')
        result = self.factory.CreateBlockGeometry(self.level).CombineBlockPaletteToGeometry(palette, name, 0)
        if result and fingerprint is not None:
            self.models[fingerprint] = result
        return result

    def update_biome_tint(self, value):
        from .biomes import actor_uniform
        work = getattr(self, 'projection_work', None)
        if work is not None:
            work.document.biome = value
        if self.entity:
            self.factory.CreateActorRender(self.entity).SetEntityExtraUniforms(4, actor_uniform(value))

    def use_current_biome(self):
        from .biomes import from_native
        name = self.factory.CreateBiome(self.level).GetBiomeName(self.player_origin())
        if name is None:
            raise ValueError('当前位置尚未加载，请稍后重试')
        value = from_native(name)
        if value is None:
            raise ValueError('当前群系暂无染色预设，请从列表选择')
        self.session.set_biome(value)

    def mark(self, index):
        pick = self.factory.CreateCamera(self.level).PickFacing()
        pos = tuple(int(pick[k]) for k in ('x', 'y', 'z')) if pick and pick.get('type') == 'Block' else self.player_origin()
        self.corners[index] = pos
        self.draw_bounds()
        self.session.editor.message = '已标记%s：%d, %d, %d' % tuple(['起点' if index == 0 else '终点'] + list(pos))
        self.factory.CreateTextNotifyClient(self.level).SetLeftCornerNotify(native(self.session.editor.message))
        self.session.emit()

    def draw_bounds(self):
        points = [p for p in self.corners if p is not None]
        if not points:
            self.survey_effects.clear()
            return
        lo, hi = bounds(points)
        self.survey_effects.replace(lo,tuple(hi[i]-lo[i]+1 for i in range(3)))

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
        if action == 'capture':
            self.capture_activity = time.time()
            request = self.pending
            def watchdog():
                if self.pending != request:
                    return
                if time.time() - self.capture_activity >= 30.:
                    self.cancel_world()
                    self.pending = self.pending_data = self.pending_state = None
                    self.download = None
                    self.session.busy = False
                    self.session.editor.message = '世界读取超时，请重试导入选区'
                    self.notify(self.session.editor.message)
                    self.session.emit()
                else:
                    self.later(5., watchdog)
            self.later(5., watchdog)
        document = data.get('document')
        if isinstance(document, Document):
            data.pop('document')
            snapshot = Document(document.size, name=document.name, biome=document.biome)
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

    def cancel_world(self):
        if self.pending is not None:
            self.upload = None
            self.system.NotifyToServer('ProjectionRequest', {'request': self.pending, 'action': 'cancel'})

    def receive(self, args):
        if args.get('request') != self.pending:
            return
        self.capture_activity = time.time()
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
            self.download = None
            s.editor.message = args['error']
            if sent.get('source') == 'world_item':
                self.notify(s.editor.message)
        elif action in ('capture', 'check', 'resolve') and sent.get('source') != 'world_item' and state != (id(s.editor), s.editor.revision, tuple(s.origin)):
            s.editor.message = '草稿或原点已改变，请重新读取或检查'
        elif action == 'resolve':
            values = args.get('palette')
            if not isinstance(values, list) or len(values) != len(sent['palette']):
                s.editor.message = '投影材质检查失败，请重试'
            else:
                try:
                    normalized = [block(value) for value in values]
                    self.projection_palette.update((block(old), new) for old, new in zip(sent['palette'], normalized))
                    if self.projection_requested:
                        self.project()
                except (ValueError, TypeError, RuntimeError) as error:
                    s.editor.message = type('')(error)
        elif action == 'capture':
            document = self.download.result if args.get('streamed') and self.download else Document.from_data(args['document'])
            self.download = None
            if document is None:
                s.editor.message = '建筑传输不完整，请重新读取'
                s.emit()
                return
            if sent.get('source') == 'world_item':
                try:
                    s.import_world_capture(document, sent['origin'])
                except (ValueError, TypeError, KeyError) as error:
                    s.editor.message = type('')(error)
                    self.notify(s.editor.message)
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
        self.projection_requested = True
        if s.projection_missing:
            unresolved = [value for value, count in s.editor.document.materials() if value not in self.projection_palette]
            if unresolved:
                s.editor.message = '正在检查投影材质…'
                return self.request('resolve', {'palette': [list(value) for value in unresolved[:64]]})
        if s.editor.document.volume > SMALL_VOLUME:
            return self.project_large(origin)
        self.projection_serial += 1
        if self.projection_entities:
            self.stop_projection()
            self.projection_requested = True
        info = self.factory.CreateBlockInfo(self.level)

        def visible(pos):
            if not s.visible_layer(pos[1]):
                return False
            if s.projection_missing:
                return self.needs_projection(info, add(origin, pos), s.editor.document.get(pos))
            return True
        name = self.geometry(s.editor.document, visible)
        if not name:
            self.stop_projection()
            self.projection_requested = s.projection_active = True
            self.projection_outline.replace(origin, tuple(s.editor.document.size))
            s.editor.message = '当前没有需要投影的方块，范围框已保留'
            return
        entity = self.system.CreateClientEntityByTypeStr(native('modern_projection:anchor'), tuple(float(v) for v in origin), (0., 0.))
        if not entity:
            raise ValueError('无法创建投影，请靠近目标区域')
        if self.preparing_entity:
            self.system.DestroyClientEntity(self.preparing_entity)
        self.preparing_entity = entity
        opacity = s.opacity
        size = tuple(s.editor.document.size)
        s.editor.message = '正在准备透明投影…'

        def attach():
            if self.preparing_entity != entity:
                return
            # A newly created client actor has no renderer until a later frame.
            # Attaching in its creation tick returns True but produces no model.
            self.factory.CreateModel(entity).SetEntityShadowShow(False)
            render = self.factory.CreateActorRender(entity)
            # Native actor block geometry starts at half-cell centres and flips
            # X/Z. Match document cells to origin + local world coordinates.
            from .biomes import actor_uniform
            success = (render.AddActorBlockGeometry(name, (-.5, 0., -.5), (0., 180., 0.)) and render.EnableActorBlockGeometryTransparent(name, True)
                       and render.SetActorBlockGeometryTransparency(name, opacity)
                       and render.SetEntityExtraUniforms(4, actor_uniform(s.editor.document.biome)))
            self.preparing_entity = None
            if success:
                if self.entity:
                    self.system.DestroyClientEntity(self.entity)
                self.entity = entity
                self.projection_mesh = (entity, name, origin, origin)
                s.projection_active = True
                s.editor.message = '投影已生成，关闭工作台即可在世界中查看'
                self.projection_outline.replace(origin, size)
            else:
                self.system.DestroyClientEntity(entity)
                s.editor.message = '透明投影生成失败，原投影已保留'
            s.emit()
        self.later(.2, attach)

    def toggle_missing(self):
        s = self.session
        s.projection_missing = not s.projection_missing
        if s.projection_active or self.projection_requested:
            self.project()
        s.emit()

    def needs_projection(self, info, pos, value):
        actual = info.GetBlock(pos)
        if actual is None or actual[0] == 'minecraft:unknown':
            raise ValueError('投影区域尚未加载，请靠近目标位置')
        return block(actual) != self.projection_palette.get(value, value)

    def stop_projection(self):
        self.projection_requested = False
        if self.pending_data and self.pending_data[0] == 'resolve':
            self.cancel_world()
        self.projection_serial += 1
        self.projection_work = None
        self.restore_projection_distance()
        self.projection_outline.clear()
        for entity in self.projection_entities.values():
            self.system.DestroyClientEntity(entity)
        self.projection_entities = {}
        if self.preparing_entity:
            self.system.DestroyClientEntity(self.preparing_entity)
        self.preparing_entity = None
        if self.entity:
            self.system.DestroyClientEntity(self.entity)
        self.entity = None
        self._projection_follow_position = None
        self.projection_mesh = None
        self.session.projection_active = False
        self.session.editor.message = '投影已关闭'

    def project_large(self, origin):
        """Prepare one exact full model while retaining the previous projection."""
        from .world_projection import WorldProjection
        self.projection_requested = True
        self.projection_serial += 1
        if self.preparing_entity:
            self.system.DestroyClientEntity(self.preparing_entity)
            self.preparing_entity = None
        had_projection = bool(self.entity or self.projection_entities)
        self.projection_work = WorldProjection(self, origin)
        self.ensure_projection_distance(self.projection_work.document.size)
        # Keep the selected region visible while the exact model is prepared;
        # the outline is independent of the eventual mesh commit.
        self.session.projection_active = True
        if not had_projection:
            self.projection_outline.replace(origin, self.projection_work.document.size)
        self.projection_work.publish(True)
        self.next_frame(self.projection_work.advance)

    def ensure_projection_distance(self, size):
        # This SDK setting belongs to the local player, not an individual
        # ghost. Lease it only while projecting, and preserve external changes.
        render = self.factory.CreateActorRender(self.player)
        current = render.GetEntityRenderDistance()
        required = max(256., math.sqrt(sum(v*v for v in size))+64.)
        # A negative value means the engine default, not unlimited distance.
        if self.projection_distance is None and current < required:
            if render.SetEntityRenderDistance(required):
                self.projection_distance = (current, required)

    def restore_projection_distance(self):
        lease, self.projection_distance = self.projection_distance, None
        if lease is not None:
            render = self.factory.CreateActorRender(self.player)
            if render.GetEntityRenderDistance() == lease[1]:
                render.SetEntityRenderDistance(lease[0])

    def dimension_changed(self, unused):
        if self.pending_data and self.pending_data[0] == 'capture':
            self.cancel_world()
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
