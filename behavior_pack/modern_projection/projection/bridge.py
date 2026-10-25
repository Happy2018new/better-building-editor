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
from .error_text import error_text
from .transfer import Receiver, packets, _wire_text


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
        if key in ('_native_render_profile', '_cauldron_profile', '_liquid_render_profile', '_spawner_profile', '_portal_profile'):
            continue
        if key in ('common', 'extra'):
            result[native(key)] = dict((_native_tree(material), indices)
                                       for material, indices in value.items())
        else:
            result[native(key)] = _native_tree(value)
    return result


class ClientBridge(object):
    def __init__(self, system):
        self.system = system
        self.engine_version = clientApi.GetEngineVersion()
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
        self.projection_entity_shaders = {}
        self.projection_retired_outlines = []
        self.projection_work = None
        self.projection_target = None
        self.projection_preparation = None
        self.projection_occupancy = None
        self.projection_shader = None
        self.projection_liquid = None
        self.projection_retired_liquids = []
        self.projection_distance = None
        self.projection_requested = False
        self.projection_palette = {}
        from .projection_outline import ProjectionOutline
        self.projection_outline = ProjectionOutline(self)
        self.frame_pumps = 0
        self.frame_work = []
        self.frame_watchdog = False
        self._projection_follow_position = None
        self._projection_follow_restore = None

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
        if not self.restore_projection_follow():
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
        shader = self.projection_shader
        if not self.restore_projection_publication():
            return
        if shader is not None and not shader.restore_offsets():
            return
        repairing_overlays = shader is not None and shader.overlay_restore
        if signature == self._projection_follow_position and not repairing_overlays:
            self.projection_outline.follow(position, tuple(centre))
            return
        if not self.prepare_projection_follow(mesh_position, centre, repairing_overlays):
            self.restore_projection_follow()
            return
        try:
            followed = self.projection_outline.follow(position, tuple(centre))
        except (ValueError, TypeError, RuntimeError):
            traceback.print_exc()
            followed = False
        if not followed:
            self.restore_projection_follow()
            return
        pending = self._projection_follow_restore
        if pending is not None:
            entity, model, origin, previous = pending['mesh']
            if shader is not None:
                shader.commit_follow()
            self.projection_mesh = (entity, model, origin, mesh_position)
            self._projection_follow_restore = None
        self._projection_follow_position = signature

    def prepare_projection_follow(self, position, camera, repairing_overlays):
        mesh = self.projection_mesh
        if not mesh or mesh[0] != self.entity or (mesh[3] == position and not repairing_overlays):
            return True
        entity, model, origin, previous = mesh
        shader = self.projection_shader
        pending = {'mesh': mesh, 'shader': shader, 'position': previous if position != previous else None,
                   'offset': None}
        self._projection_follow_restore = pending
        try:
            if pending['position'] is not None and not self.factory.CreatePos(entity).SetPosForClientEntity(position):
                return False
            if shader is not None:
                return shader.prepare_follow(position, camera)
            pending['offset'] = (previous[0]-origin[0]-.5, origin[1]-previous[1], previous[2]-origin[2]-.5)
            offset = (position[0]-origin[0]-.5, origin[1]-position[1], position[2]-origin[2]-.5)
            return self.factory.CreateActorRender(entity).SetActorBlockGeometryOffset(model, offset)
        except (ValueError, TypeError, RuntimeError):
            traceback.print_exc()
            return False

    def restore_projection_follow(self):
        pending = self._projection_follow_restore
        if pending is None:
            return True
        mesh, shader = pending['mesh'], pending['shader']
        entity, model, origin, previous = mesh
        if (not self.projection_mesh or self.projection_mesh[0] != entity or
                entity != self.entity or shader is not self.projection_shader):
            # Replacement/stop transfers old actors to the retirement owner.
            self._projection_follow_restore = None
            return True
        restored = shader.restore_offsets() if shader is not None else True
        if pending['offset'] is not None:
            try:
                moved = self.factory.CreateActorRender(entity).SetActorBlockGeometryOffset(model, pending['offset'])
            except (ValueError, TypeError, RuntimeError):
                traceback.print_exc()
                moved = False
            if moved:
                pending['offset'] = None
            restored = moved and restored
        if pending['position'] is not None:
            try:
                moved = self.factory.CreatePos(entity).SetPosForClientEntity(pending['position'])
            except (ValueError, TypeError, RuntimeError):
                traceback.print_exc()
                moved = False
            if moved:
                pending['position'] = None
            restored = moved and restored
        if restored:
            self._projection_follow_restore = None
        return restored

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
        # ConfigClient returns UTF-8 protocol bytes, as SDK network packets do.
        # Decode the encoded wire tree before strict semantic/NBT validation.
        return _wire_text(self.factory.CreateConfigClient(self.level).GetConfigData('modern_projection_library', True))

    def load_preferences(self):
        return _wire_text(self.factory.CreateConfigClient(self.level).GetConfigData('modern_projection_preferences', True))

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
        return _wire_text(self.factory.CreateConfigClient(self.level).GetConfigData(key, True))

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

    def geometry(self, document, visible=None, name=None, context_document=None, prepared=None,
                 render_origin=(0, 0, 0), context_visible_layer=None):
        from .native_render_profile import for_preview
        preview_profile = for_preview(getattr(self.session, 'native_render_profile', None))
        if prepared is not None:
            data = prepared
        elif context_document is not None:
            from .render_context import prepare_context_batches
            data = prepare_context_batches(context_document, document.palette_data(visible),
                                           render_origin=render_origin,
                                           item_profile=getattr(self.session, 'item_profile', None),
                                           native_render_profile=preview_profile,
                                           cauldron_profile=getattr(self.session, 'cauldron_profile', None),
                                           liquid_profile=getattr(self.session, 'liquid_profile', None),
                                           spawner_profile=getattr(self.session, 'spawner_profile', None),
                                           portal_profile=getattr(self.session, 'portal_profile', None),
                                           visible_layer=context_visible_layer)
        else:
            from .geometry_palette import prepare_palette
            from .kelp_render import palette_parts
            biome = getattr(document, 'biome', None)
            if biome is None:
                biome = self.session.editor.document.biome
            # One empty Y cell separates source top vertices from overlay
            # bottom vertices so the shader never classifies both alike.
            source = document.palette_data(visible)
            complete = document if hasattr(document, 'blocks') else getattr(document, 'source_document', None)
            kelp_parts = palette_parts(source, complete, getattr(document, 'source_origin', (0, 0, 0)))
            data = prepare_palette(source, overlay_base=document.size[1]+1,
                                   kelp_parts=kelp_parts,
                                   render_origin=render_origin,
                                   item_profile=getattr(self.session, 'item_profile', None),
                                   native_render_profile=preview_profile,
                                   cauldron_profile=getattr(self.session, 'cauldron_profile', None),
                                   biome=biome,
                                   liquid_profile=getattr(self.session, 'liquid_profile', None),
                                   spawner_profile=getattr(self.session, 'spawner_profile', None),
                                   portal_profile=getattr(self.session, 'portal_profile', None))
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

    def update_projection_opacity(self):
        if not self.restore_projection_publication():
            self.session.editor.message = '投影状态恢复尚未完成，请调整透明度或更新投影重试'
            return
        shader = self.projection_shader
        if shader is None or shader.render is None:
            return
        try:
            shader.control()
        except ValueError as error:
            traceback.print_exc()
            self.session.editor.message = '投影透明度更新失败，请调整透明度或更新投影重试：%s' % error

    def update_biome_tint(self, value):
        if not self.restore_projection_publication():
            raise ValueError('Could not restore projection publication before updating biome tint')
        from .biomes import actor_uniform
        work = getattr(self, 'projection_work', None)
        if work is not None:
            work.document.biome = value
            if getattr(work, 'liquid', None) is not None:
                work.liquid.set_biome(value)
        liquid = getattr(self, 'projection_liquid', None)
        if liquid is not None:
            liquid.set_biome(value)
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
        state = self.world_request_state(action)
        outgoing = dict(data)
        upload = None
        document = outgoing.pop('document', None)
        if isinstance(document, Document):
            snapshot = Document(document.size, name=document.name, biome=document.biome)
            snapshot.blocks = document.blocks.copy()
            upload = packets(snapshot)
            outgoing['stream'] = next(upload)
        self.request_id += 1
        self.pending = self.request_id
        self.pending_data = (action, dict(data))
        self.pending_state = state
        outgoing.update(action=action, request=self.request_id)
        self.upload = upload
        if upload is not None:
            self.upload_sequence = outgoing['stream']['seq']
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
        outgoing.pop('captureDocument', None)
        self.system.NotifyToServer('ProjectionRequest', outgoing)
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
            self.session.editor.message = '世界读取初始化失败：%s' % error_text(error)
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
                self.session.editor.message = error_text(error)
                self.session.emit()
                return
            self.session.editor.message = '正在读取世界方块层与方块实体… %d/%d' % (index + 1, len(chunks))
            self.session.emit()
            self.next_frame(lambda: read_chunk(index + 1))

        read_chunk()

    def check_progress(self):
        from .projection_target import placement_target, start
        return start(self, 'check', placement_target(self))

    def apply_world(self):
        from .projection_target import placement_target, start
        return start(self, 'apply', placement_target(self), self.session.apply_air)

    def confirm_apply_world(self):
        from .projection_target import placement_target, WorldApplyConfirmation, describe
        target = placement_target(self)
        include_air = bool(self.session.apply_air)
        title = '将整个建筑写入世界？\n原点 %d, %d, %d\n范围 %d × %d × %d\n%s\n' % (
            target.origin + target.size + (describe(target.operations),))
        if include_air:
            title += '空气位置的已有方块也会被清除。\n'
        title += '此操作无法撤销。'
        self.session.confirm(title, WorldApplyConfirmation(self, target, include_air))

    def cancel_world(self):
        if self.projection_preparation is not None:
            if self.projection_preparation.action == 'project':
                self.projection_requested = bool(self.session.projection_active)
            self.projection_preparation = None
            self.session.busy = False
            self.session.editor.message = '已取消投影变换准备'
            self.session.emit()
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
        if (self.pending is None or not isinstance(args, dict) or
                type(args.get('request')) is not int or args['request'] != self.pending):
            return
        self.capture_activity = time.time()
        s = self.session
        if not args.get('done'):
            if 'uploadAck' in args:
                if (self.upload is not None and type(args['uploadAck']) is int and
                        args['uploadAck'] == self.upload_sequence):
                    request = self.pending
                    sequence = self.upload_sequence
                    def send_next():
                        if (self.pending != request or self.upload is None or
                                self.upload_sequence != sequence):
                            return
                        packet = next(self.upload, None)
                        if packet is None:
                            self.upload = None
                            return
                        self.upload_sequence = packet['seq']
                        self.system.NotifyToServer('ProjectionRequest', {'request': request, 'action': 'upload', 'stream': packet})
                    self.later(0., send_next)
                return
            if 'documentPacket' in args:
                if self.download is None:
                    return
                try:
                    packet = args['documentPacket']
                    if not (isinstance(packet, dict) and type(packet.get('seq')) is int and
                            0 <= packet['seq'] < self.download.sequence):
                        self.download.feed(packet)
                    self.system.NotifyToServer('ProjectionRequest', {
                        'request': self.pending, 'action': 'captureAck',
                        'sequence': packet['seq']})
                except (ValueError, TypeError, KeyError, RuntimeError) as error:
                    self.cancel_world()
                    s.editor.message = error_text(error)
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
        download, self.download = self.download, None
        s.busy = False
        if args.get('error'):
            self.download = None
            s.editor.message = args['error']
            if sent.get('source') == 'world_item':
                self.notify(s.editor.message)
        elif action in ('capture', 'check', 'resolve') and sent.get('source') != 'world_item' and state != self.world_request_state(action):
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
                    s.editor.message = error_text(error)
        elif action == 'capture':
            document = (sent.get('captureDocument') if sent.get('clientCapture') else
                        download.result if args.get('streamed') and download else
                        Document.from_data(args['document']))
            if sent.get('clientCapture'):
                try:
                    from .world_capture import merge_entity_document
                    if download is None or download.result is None:
                        raise ValueError('方块实体传输不完整，请重新读取')
                    merge_entity_document(document, download.result)
                except (ValueError, TypeError, KeyError) as error:
                    self.download = None
                    s.editor.message = error_text(error)
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
                    s.editor.message = error_text(error)
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
        from .projection_target import start
        return start(self, 'project')

    def world_request_state(self, action):
        s = self.session
        state = (id(s.editor), s.editor.revision, tuple(s.origin))
        if action == 'check':
            dimension = self.factory.CreateGame(self.level).GetCurrentDimension()
            return state + (tuple(s.projection_transform), dimension)
        return state

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
        liquid = getattr(self, 'projection_liquid', None)
        if liquid is not None:
            occupancy = self.projection_occupancy
            if ((occupancy is None or occupancy.pending_pair is None) and
                    self.restore_projection_publication()):
                liquid.advance()
            if liquid.error is not None and not getattr(liquid, 'reported_error', False):
                liquid.reported_error = True
                self.session.editor.message = '附加投影更新失败，请更新投影：%s' % liquid.error
                self.session.emit()

    def own_projection_entity(self, entity, shader):
        if entity is not None and shader is not None:
            self.projection_entity_shaders[entity] = shader

    def restore_projection_publication(self):
        occupancy = getattr(self, 'projection_occupancy', None)
        if occupancy is not None:
            return occupancy.recover_pair()
        shader = self.projection_shader
        body = shader is None or shader.restore_commit()
        liquid = getattr(self, 'projection_liquid', None)
        water = liquid is None or liquid.restore_publication()
        return body and water

    def available_projection_pool(self):
        old = self.projection_shader
        if old is None and self.projection_occupancy is not None:
            old = self.projection_occupancy.shader
        occupied = set(shader.pool for shader in self.projection_entity_shaders.values())
        if old is not None:
            occupied.add(old.pool)
        preferred = 1-old.pool if old is not None else 0
        for pool in (preferred, 1-preferred):
            if pool not in occupied:
                return pool
        return None

    def release_projection_resources(self, entities=(), outlines=(), liquids=()):
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
            shader = self.projection_entity_shaders.get(entity)
            if shader is not None:
                errors.extend(shader.retire())
            try:
                self.system.DestroyClientEntity(entity)
            except Exception as error:
                traceback.print_exc()
                errors.append(error_text(error))
            else:
                pending.remove(entity)
                self.projection_entity_shaders.pop(entity, None)
        for outline in tuple(retired):
            try:
                outline.clear()
            except Exception as error:
                traceback.print_exc()
                errors.append(error_text(error))
            else:
                retired.remove(outline)
        retired_liquids = getattr(self, 'projection_retired_liquids', [])
        self.projection_retired_liquids = retired_liquids
        for liquid in liquids:
            if liquid is not None and liquid not in retired_liquids:
                retired_liquids.append(liquid)
        for liquid in tuple(retired_liquids):
            if liquid.close():
                retired_liquids.remove(liquid)
            else:
                errors.append('Liquid model cleanup failed')
        return errors

    def stop_projection(self):
        if self.projection_preparation is not None:
            self.projection_preparation = None
            self.session.busy = False
        self.projection_target = None
        self.own_projection_entity(self.entity, self.projection_shader)
        self.own_projection_entity(self.preparing_entity,
                                   getattr(self.projection_work, 'shader', None))
        liquids = (getattr(self, 'projection_liquid', None),
                   getattr(self.projection_work, 'liquid', None))
        self.projection_liquid = None
        self.projection_occupancy = None
        self.projection_shader = None
        self.projection_requested = False
        if self.pending_data and self.pending_data[0] == 'resolve':
            self.cancel_world()
        self.projection_serial += 1
        self.projection_work = None
        distance_restored = self.restore_projection_distance()
        entities = tuple(self.projection_entities.values()) + (self.preparing_entity, self.entity)
        self.projection_entities = {}
        self.preparing_entity = None
        self.entity = None
        self._projection_follow_position = None
        self.projection_mesh = None
        self.session.projection_active = False
        errors = self.release_projection_resources(entities, (self.projection_outline,), liquids)
        if distance_restored is False:
            errors.append('Projection render distance cleanup failed')
        self.session.editor.message = ('投影已关闭' if not errors else
                                       '投影已关闭，部分资源清理失败，请再次关闭重试')

    def project_large(self, origin, target=None):
        """Prepare one exact full model while retaining the previous projection."""
        from .world_projection import WorldProjection
        occupancy = self.projection_occupancy
        restored = occupancy.cancel_pending() if occupancy is not None else self.restore_projection_publication()
        if not restored:
            self.session.editor.message = '投影状态恢复尚未完成，请更新投影重试'
            self.session.emit()
            return
        self.projection_requested = True
        self.projection_serial += 1
        previous_work = self.projection_work
        pending_liquid = None
        if previous_work is not None and not previous_work.ready:
            pending_liquid = getattr(previous_work, 'liquid', None)
        pending = self.preparing_entity
        self.own_projection_entity(pending, getattr(previous_work, 'shader', None))
        self.preparing_entity = None
        self.release_projection_resources((pending,), liquids=(pending_liquid,))
        if self.available_projection_pool() is None:
            self.projection_work = None
            self.projection_requested = bool(self.session.projection_active)
            if not self.session.projection_active:
                self.restore_projection_distance()
            self.session.editor.message = '旧投影实体尚未销毁，请关闭投影或更新投影重试'
            self.session.emit()
            return
        had_projection = bool(self.entity or self.projection_entities)
        self.projection_work = WorldProjection(self, origin, target)
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
        lease = self.projection_distance
        if lease is None:
            return True
        render = self.factory.CreateActorRender(self.player)
        if render.GetEntityRenderDistance() == lease[1] and not render.SetEntityRenderDistance(lease[0]):
            return False
        self.projection_distance = None
        return True

    def dimension_changed(self, unused):
        from .projection_target import WorldApplyConfirmation
        pending = self.session.pending_confirm
        if pending is not None and isinstance(pending[1], WorldApplyConfirmation):
            pending[1].cancel()
            self.session.pending_confirm = None
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
