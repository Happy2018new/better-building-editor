# -*- coding: utf-8 -*-
"""Client SDK boundary: local library, previews, selection outline and ghost models."""
from __future__ import unicode_literals
import math
import zlib
import json
import time
import traceback
import mod.client.extraClientApi as clientApi
from .model import AIR, Document, Editor, add, bounds, block
from .world import coordinate
from .transfer import Receiver, packets


def native(value):
    return value.encode('utf8') if bytes is str and isinstance(value, type('')) else value


def _native_tree(value):
    if isinstance(value, dict):
        return dict((_native_tree(key), _native_tree(item)) for key, item in value.items())
    if isinstance(value, tuple):
        return tuple(_native_tree(item) for item in value)
    if isinstance(value, list):
        return [_native_tree(item) for item in value]
    return native(value)


def _stable_palette(value):
    if isinstance(value, dict):
        rows = [(_stable_palette(key), _stable_palette(item))
                for key, item in value.items()]
        return tuple(sorted(rows, key=repr))
    if isinstance(value, (list, tuple)):
        return tuple(_stable_palette(item) for item in value)
    return value


def _native_palette(data):
    """Convert SDK strings without copying the potentially large integer lists."""
    result = {}
    for key, value in data.items():
        if key in ('common', 'extra'):
            result[native(key)] = dict((_native_tree(material), indices)
                                       for material, indices in value.items())
        else:
            result[native(key)] = _native_tree(value)
    return result


class ClientBridge(object):
    def __init__(self, system):
        self.system = system
        self.factory = clientApi.GetEngineCompFactory()
        self.level = clientApi.GetLevelId()
        self.player = clientApi.GetLocalPlayerId()
        self.player_position = self.factory.CreatePos(self.player)
        self.session = None
        self.corners = [None, None]
        self.corner_faces = [None, None]
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
        self.model_layouts = {}
        self.context_models = {}
        self.alive = True
        self.upload = None
        self.upload_sequence = None
        self.download = None
        self.capture_serial = 0
        self.capture_active = None
        self.capture_dimension = None
        self.projection_serial = 0
        self.projection_entities = {}
        self.projection_retired_entities = set()
        self.projection_retired_outlines = []
        self.projection_work = None
        self.projection_occupancy = None
        self.projection_shader = None
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
        self.survey_effects.follow(position,tuple(centre))
        if not self.session.projection_active:
            return
        # Empty elevated subchunks can omit client actors before the camera
        # frustum test. Keep the mesh actor in the player's loaded section;
        # compensate its geometry offset to retain exact world coordinates.
        foot = self.player_position.GetFootPos()
        if foot is None:
            return
        mesh_position = (foot[0], foot[1]+1., foot[2])
        signature = (position, mesh_position, self.entity, self.projection_outline.entity)
        if signature == self._projection_follow_position:
            self.projection_outline.follow(position, tuple(centre))
            return
        if self.projection_mesh:
            entity, model, origin, previous = self.projection_mesh
            if entity == self.entity and mesh_position != previous:
                if mesh_position != previous and not self.factory.CreatePos(entity).SetPosForClientEntity(mesh_position):
                    return
                offset = (mesh_position[0]-origin[0]-.5, origin[1]-mesh_position[1], mesh_position[2]-origin[2]-.5)
                shader = self.projection_shader
                moved = (shader.follow(mesh_position, centre) if shader is not None else
                         self.factory.CreateActorRender(entity).SetActorBlockGeometryOffset(model, offset))
                if not moved:
                    return
                self.projection_mesh = (entity, model, origin, mesh_position)
        if self.projection_outline.follow(position, tuple(centre)):
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
        from .geometry_palette import INTERNAL_RENDER_BLOCKS
        names = args.get('names', [])
        if not isinstance(names, list):
            return
        modern = catalogue_values()
        custom = []
        for raw_name in names:
            name = clean_name(raw_name)
            if name.startswith('minecraft:') or name in INTERNAL_RENDER_BLOCKS:
                continue
            custom.append((name, 0))
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

    def survey_tip(self, message):
        hud = getattr(self.system, 'hud', None)
        if hud is not None:
            hud.show_tip(message)

    def world_tool_point(self, args):
        if args.get('silent'):
            return
        if args.get('clear'):
            self.corners = [None, None]
            self.corner_faces = [None, None]
            self.draw_bounds()
        if args.get('error'):
            self.survey_tip(args['error'])
            self.session.editor.message = args['error']
            self.session.emit()
            return
        if args.get('success') is not True or args.get('createBounds') is not True:
            return
        index = args.get('index')
        pos = args.get('pos')
        if index not in (0, 1) or not isinstance(pos, (tuple, list)) or len(pos) != 3:
            return
        if index == 0:
            self.corners = [tuple(pos), None]
            self.corner_faces = [args.get('face'), None]
            self.survey_tip('第一个角点已设置，请选择另一方块')
        elif isinstance(args.get('first'), (tuple, list)) and len(args['first']) == 3:
            self.corners[0] = tuple(args['first'])
            self.corners[1] = tuple(pos)
            self.corner_faces[1] = args.get('face')
            self.survey_tip('已选择 %d × %d × %d' % tuple(args['size']))
        self.draw_bounds()
        self.survey_effects.pulse_point(index)
        self.session.emit()

    def capture_new(self):
        if self.session.world_import_document is not None:
            raise ValueError('待导入选区尚未保存，请先到建筑库重试')
        if None in self.corners:
            raise ValueError('请先用投影测绘器选择两个角点')
        from .tool_items import selection
        origin, size = selection(*self.corners)
        self.capture_region(origin, size, source='world_item')

    def use_player_origin(self):
        self.session.origin = self.player_origin()
        self.session.progress = None
        self.session.editor.message = '已将投影原点设为玩家脚下'
        self.session.emit()

    def geometry(self, document, visible=None, name=None, context_document=None, prepared=None):
        if prepared is not None:
            data = prepared
        elif context_document is not None:
            from .render_context import prepare_context_batches
            data = prepare_context_batches(context_document, document.palette_data(visible))
        else:
            from .geometry_palette import prepare_palette
            # One empty Y cell separates source top vertices from overlay
            # bottom vertices so the shader never classifies both alike.
            data = prepare_palette(document.palette_data(visible), overlay_base=document.size[1]+1)
        if '_context_batches' in data:
            if not hasattr(self, 'context_models'):
                self.context_models = {}
            base = native(name or 'modern_projection_context_%d' % len(self.context_models))
            parts = []
            for origin, context, palette in data['_context_batches']:
                suffix = '_%s_%d_%d_%d' % ('c' if context else 'o', origin[0], origin[1], origin[2])
                part = self.geometry(document, name=base + native(suffix), prepared=palette)
                if not part:
                    raise ValueError('Context chunk geometry generation failed')
                parts.append((part, origin, context))
            self.context_models[base] = tuple(parts)
            alternate = base.decode('utf8') if isinstance(base, bytes) else base.encode('utf8')
            self.context_models[alternate] = tuple(parts)
            if parts:
                layout = (tuple(document.size), tuple(data['_context_batches'][0][2]['volume']))
                self.model_layouts[base] = self.model_layouts[alternate] = layout
            return base if parts else None
        if not data['common'] and not data['extra']:
            return None
        # Include both layers and actor data so edits cannot reuse stale geometry.
        fingerprint = (None if name is not None else
                       zlib.compress(repr(_stable_palette((document.size, data))).encode('utf8'), 1))
        if fingerprint is not None and fingerprint in self.models:
            return self.models[fingerprint]
        # Identical content reuses native geometry across undo and page changes.
        name = native(name or 'modern_projection_%d' % len(self.models))
        data = _native_palette(data)
        palette = self.factory.CreateBlock(self.level).GetBlankBlockPalette()
        if palette is None or not palette.DeserializeBlockPalette(data):
            raise ValueError('方块调色板生成失败')
        result = self.factory.CreateBlockGeometry(self.level).CombineBlockPaletteToGeometry(palette, name, 0)
        if result:
            if fingerprint is not None:
                self.models[fingerprint] = result
            layout = (tuple(document.size), tuple(data.get(native('volume'), ())))
            self.model_layouts[name] = layout
            self.model_layouts[result] = layout
            for key in (name, result):
                alternate = key.decode('utf8') if isinstance(key, bytes) else key.encode('utf8')
                self.model_layouts[alternate] = layout
        return result

    def update_biome_tint(self, value):
        from .biomes import actor_uniform
        work = getattr(self, 'projection_work', None)
        if work is not None:
            work.document.biome = value
        if self.projection_occupancy is not None:
            self.projection_occupancy.document.biome = value
            if self.projection_occupancy.shader.render is not None:
                self.projection_occupancy.shader.control()
                return
        if self.projection_shader is not None:
            self.projection_shader.tracker.document.biome = value
            self.projection_shader.control()
            return
        if self.entity:
            self.factory.CreateActorRender(self.entity).SetEntityExtraUniforms(4, actor_uniform(value))

    def use_current_biome(self):
        from .biomes import from_native
        # Sample only on this explicit action. Store one preset on the
        # building; moving to another biome must not replace that choice.
        name = self.factory.CreateBiome(self.level).GetBiomeName(self.player_origin())
        if name is None:
            raise ValueError('当前位置尚未加载，请稍后重试')
        value = from_native(name)
        if value is None:
            raise ValueError('无法匹配当前群系的颜色，请从列表选择')
        self.session.set_biome(value)

    def mark(self, index):
        raise ValueError('请使用测绘器点击实际方块来选择角点')

    def draw_bounds(self):
        points = [p for p in self.corners if p is not None]
        if not points:
            self.survey_effects.clear()
            return
        lo, hi = bounds(points)
        self.survey_effects.replace(lo,tuple(hi[i]-lo[i]+1 for i in range(3)))
        self.survey_effects.sync_points(self.corners, self.corner_faces)

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
        data.pop('captureDocument', None)
        self.system.NotifyToServer('ProjectionRequest', data)
        self.session.emit()

    def capture(self):
        if None in self.corners:
            raise ValueError('尚未设置世界选区，无法读取')
        lo, hi = bounds(self.corners)
        size = tuple(hi[i] - lo[i] + 1 for i in range(3))
        self.capture_region(lo, size)

    def capture_region(self, origin, size, source=None):
        document = Document(size)
        self.capture_serial += 1
        serial = self.capture_serial
        self.capture_active = serial
        self.capture_dimension = self.factory.CreateGame(self.level).GetCurrentDimension()
        self.session.busy = True
        self.session.editor.message = '正在读取世界方块层与方块实体…'
        self.session.emit()
        try:
            block_component = self.factory.CreateBlock(self.level)
            block_info = self.factory.CreateBlockInfo(self.level)
            loaded_chunks = getattr(self.system, 'projection_loaded_chunks', None)
            chunks = []
            for cy in range((size[1] + 15) // 16):
                for cx in range((size[0] + 15) // 16):
                    for cz in range((size[2] + 15) // 16):
                        local = (cx * 16, cy * 16, cz * 16)
                        chunk_size = tuple(min(16, size[i] - local[i]) for i in range(3))
                        chunks.append((local, chunk_size))
        except Exception as error:
            self.capture_active = None
            self.capture_dimension = None
            self.session.busy = False
            self.session.editor.message = '世界读取初始化失败：%s' % error
            self.session.emit()
            return

        def read_chunk(index=0):
            if self.capture_active != serial:
                return
            if self.factory.CreateGame(self.level).GetCurrentDimension() != self.capture_dimension:
                self.capture_active = None
                self.capture_dimension = None
                self.session.busy = False
                self.session.editor.message = '维度已改变，已取消世界读取'
                self.session.emit()
                return
            if index >= len(chunks):
                self.capture_active = None
                self.capture_dimension = None
                self.request('capture', {
                    'origin': origin, 'size': size, 'source': source,
                    'clientCapture': True, 'captureDocument': document,
                })
                return
            local, chunk_size = chunks[index]
            low = tuple(origin[i] + local[i] for i in range(3))
            high = tuple(low[i] + chunk_size[i] - 1 for i in range(3))
            try:
                from .world_capture import validate_loaded_chunk
                validate_loaded_chunk(loaded_chunks, self.capture_dimension, low, high,
                                      block_info.GetBlock)
                palette = block_component.GetBlockPaletteBetweenPos(low, high, False)
                if palette is None:
                    raise ValueError('世界选区有未加载区块或无法读取的 palette，请靠近后重试')
                from .world_capture import merge_palette, restore_omitted_palette_cells
                source_palette = palette.SerializeBlockPalette()
                merge_palette(document, source_palette, local,
                              chunk_size, origin)
                restore_omitted_palette_cells(document, source_palette, local,
                                              chunk_size, origin, block_info.GetBlock)
            except Exception as error:
                self.capture_active = None
                self.capture_dimension = None
                self.session.busy = False
                self.session.editor.message = str(error)
                self.session.emit()
                return
            self.session.editor.message = '正在读取世界方块层与方块实体… %d/%d' % (index + 1, len(chunks))
            self.session.emit()
            self.next_frame(lambda: read_chunk(index + 1))

        read_chunk()

    def check_progress(self):
        s = self.session
        self.request('check', {'origin': coordinate(s.origin), 'document': s.editor.document})

    def apply_world(self):
        s = self.session
        self.request('apply', {'origin': coordinate(s.origin), 'document': s.editor.document, 'includeAir': s.apply_air})

    def cancel_world(self):
        if self.capture_active is not None:
            self.capture_active = None
            self.capture_dimension = None
            self.session.busy = False
            self.session.editor.message = '已取消世界读取'
            self.session.emit()
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
                    self.system.NotifyToServer('ProjectionRequest', {
                        'request': self.pending, 'action': 'captureAck',
                        'sequence': args['documentPacket']['seq']})
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
            document = (sent.get('captureDocument') if sent.get('clientCapture') else
                        self.download.result if args.get('streamed') and self.download else
                        Document.from_data(args['document']))
            if sent.get('clientCapture'):
                try:
                    from .world_capture import merge_entity_document
                    if self.download is None or self.download.result is None:
                        raise ValueError('方块实体传输不完整，请重新读取')
                    merge_entity_document(document, self.download.result)
                except (ValueError, TypeError, KeyError) as error:
                    self.download = None
                    s.editor.message = str(error)
                    s.emit()
                    return
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
            s.editor.message = '已读取世界选区，包括方块状态、背景层和方块实体数据'
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
        self.ensure_projection_distance(s.editor.document.size)
        self.projection_requested = True
        return self.project_large(origin)

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
        from .occupancy import AIR_NAMES
        return actual[0] in AIR_NAMES

    def set_projection_occupancy(self, occupancy, entity, model):
        if occupancy is not None:
            occupancy.start(entity, model)
            self.projection_shader = occupancy.shader
        else:
            self.projection_occupancy = None

    def projection_interaction(self, pos=None, touch=False):
        occupancy = self.projection_occupancy
        if occupancy is None or not occupancy.active():
            return
        if pos is None:
            pick = occupancy.camera.GetChosen() if touch else occupancy.camera.PickFacing()
            if not pick or pick.get('type') != 'Block':
                return
            pos = tuple(int(pick[axis]) for axis in ('x', 'y', 'z'))
        occupancy.hint(pos)

    def update_projection_occupancy(self):
        work = self.projection_work
        if work is not None and not work.ready and not work.error:
            # Render frames continue while the editor is closed; SDK timers
            # alone may advance only every 50-100 ms on this engine version.
            work.advance(False)
        if self.projection_occupancy is not None:
            self.projection_occupancy.tick()

    def release_projection_resources(self, entities=(), outlines=()):
        """Retain failed releases for the next commit or explicit close."""
        pending = getattr(self, 'projection_retired_entities', set())
        retired = getattr(self, 'projection_retired_outlines', [])
        self.projection_retired_entities, self.projection_retired_outlines = pending, retired
        pending.update(entity for entity in entities if entity is not None)
        for outline in outlines:
            if outline not in retired:
                retired.append(outline)
        errors = []
        for entity in tuple(pending):
            try:
                self.system.DestroyClientEntity(entity)
            except Exception as error:
                traceback.print_exc()
                errors.append(type('')(error))
            else:
                pending.remove(entity)
        for outline in tuple(retired):
            try:
                outline.clear()
            except Exception as error:
                traceback.print_exc()
                errors.append(type('')(error))
            else:
                retired.remove(outline)
        return errors

    def stop_projection(self):
        self.projection_occupancy = None
        self.projection_shader = None
        self.projection_requested = False
        if self.pending_data and self.pending_data[0] == 'resolve':
            self.cancel_world()
        self.projection_serial += 1
        self.projection_work = None
        self.restore_projection_distance()
        entities = tuple(self.projection_entities.values()) + (self.preparing_entity, self.entity)
        self.projection_entities = {}
        self.preparing_entity = None
        self.entity = None
        self._projection_follow_position = None
        self.projection_mesh = None
        self.session.projection_active = False
        errors = self.release_projection_resources(entities, (self.projection_outline,))
        self.session.editor.message = ('投影已关闭' if not errors else
                                       '投影已关闭，部分资源清理失败，请再次关闭重试')

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
        loaded = getattr(self.system, 'projection_loaded_chunks', None)
        if loaded is not None:
            dimension = self.factory.CreateGame(self.level).GetCurrentDimension()
            loaded.intersection_update(key for key in tuple(loaded) if key[0] == dimension)
        if self.capture_active is not None or (self.pending_data and self.pending_data[0] == 'capture'):
            self.cancel_world()
        self.stop_projection()
        self.corners = [None, None]
        self.corner_faces = [None, None]
        self.draw_bounds()
        self.session.progress = None
        self.session.emit()

    def destroy(self):
        self.alive = False
        self.stop_projection()
        self.corners = [None, None]
        self.corner_faces = [None, None]
        self.draw_bounds()
