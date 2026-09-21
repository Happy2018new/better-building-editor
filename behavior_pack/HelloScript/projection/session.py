# -*- coding: utf-8 -*-
"""Application state, local building library, and coalesced preview generation."""
from __future__ import unicode_literals
import time
from .model import AIR, Document, Editor, RegionSizeError, demo_document, SMALL_VOLUME, bounds


def as_text(value):
    return value.decode('utf8') if isinstance(value, bytes) else value


class Session(object):
    def __init__(self, bridge):
        self.bridge = bridge
        self.editor = Editor(demo_document())
        self.page = 'workspace'
        self.group = 'edit'
        self.tool = 'fill'
        self.query = ''
        self.inspector = 'params'
        self.name = self.editor.document.name
        self.new_size = (24, 16, 24)
        self.new_size_valid = True
        self.listeners = []
        self.ui_revision = 0
        self.content_revision = 0
        self.library = []
        self.library_serial = 0
        self.model_name = None
        self.model_revision = None
        self.preview_pending = False
        self.preview_error = ''
        self.camera_yaw = 35.
        self.camera_pitch = 25.
        self.zoom = 1.
        self.view = '3d'
        self.focus_view = False
        self.focus_inspector = False
        self.paint_mode = 'paint'
        self.direct_mode = 'browse'
        self.touch_mode = False
        self.erase_scope = 'single'
        self.focused = None
        self.box_anchor = None
        self.paste_origin = (0, 0, 0)
        self.paste_pinned = False
        self.camera_pose = (35., 25., 1.)
        self.camera_dragging = False
        self.camera_revision = 0
        self.camera_reset_revision = 0
        self.camera_reset_animated = False
        self.camera_pivot = None
        self.camera_pan = (0., 0.)
        self.camera_depth = self.camera_depth_pose = 0.
        self.camera_focus_request = None
        self.canvas_x = 0
        self.canvas_z = 0
        self.solo_layer = False
        self.section = False
        self.grid = True
        self.brightness = 1.
        self.reduced_motion = False
        self.spectrum_speed = 3.
        from .materials import initial_catalogue, normalize_palette
        self.palette = normalize_palette(None)
        self.block_catalogue = initial_catalogue()
        self.catalogue_loading = False
        self.catalogue_ready = False
        self.material_browser = None
        self.origin = (0, 64, 0)
        self.opacity = .45
        self.apply_air = False
        self.projection_active = False
        self.projection_missing = False
        self.projection_outline = True
        self.progress = None
        self.pending_confirm = None
        self.pending_rename = None
        self.rename_error = ''
        self.busy = False
        self.ready = False
        self.parameter_serial = 0
        self.performance = {}
        self.edit_job = None
        self.io_job = None
        self.scene_origin = (0, 0, 0)
        self.scene_size = self.editor.document.size
        self.scene_scale = 1
        from .tiles import TiledPreview
        self.tiles = TiledPreview(self)
        from .sharing import Sharing
        self.sharing = Sharing(self)
        self.point_publish = 0
        self.pointer_stats = [0, 0, 0, 0]

    def subscribe(self, callback, fields=None):
        entry = (callback, fields)
        self.listeners.append(entry)

        def remove():
            if entry in self.listeners:
                self.listeners.remove(entry)
        return remove

    def emit(self, field=None):
        self.ui_revision += 1
        if field is None:
            self.content_revision += 1
        for callback, fields in list(self.listeners):
            if field is None or fields is None or field in fields:
                callback()

    def initialize(self):
        if hasattr(self.bridge, 'load_preferences'):
            preferences = self.bridge.load_preferences() or {}
            speed = preferences.get('spectrum_speed', 3.) if isinstance(preferences, dict) else 3.
            if isinstance(speed, (int, float)) and .25 <= speed <= 6.:
                self.spectrum_speed = float(speed)
            if isinstance(preferences, dict) and 'palette' in preferences:
                from .materials import normalize_palette
                self.palette = normalize_palette(preferences['palette'])
            if isinstance(preferences, dict) and isinstance(preferences.get('projection_outline'), bool):
                self.projection_outline = preferences['projection_outline']
        data = self.bridge.load_library()
        if isinstance(data, dict):
            for entry in data.get('buildings', [])[:32]:
                try:
                    if entry['data'].get('version') == 3:
                        from .archive import validate
                        validate(entry['data'])
                    else:
                        entry['data'] = Document.from_data(entry['data']).to_data()
                    if type(entry['id']) is int:
                        self.library.append(entry)
                except RegionSizeError:
                    # A reduced editing cap must never erase older archives
                    # when another configuration is saved or renamed.
                    saved = entry['data']
                    name = as_text(saved.get('name', ''))
                    if (type(entry.get('id')) is int and saved.get('version') in (1, 2, 3)
                            and isinstance(name, type('')) and 1 <= len(name) <= 64):
                        saved['name'] = name
                        self.library.append(entry)
                        self.editor.message = '超出当前尺寸上限的旧配置已保留'
                except (ValueError, TypeError, KeyError):
                    self.editor.message = '已跳过损坏的本地配置'
            self.library_serial = max([0] + [entry['id'] for entry in self.library])
            if type(data.get('serial')) is int:
                self.library_serial = max(self.library_serial, data['serial'])
        self.origin = self.bridge.player_origin()
        self.ready = True
        self.refresh_preview()

    def set(self, field, value):
        value = as_text(value)
        if getattr(self, field) == value:
            return
        setattr(self, field, value)
        if field == 'origin':
            self.progress = None
        if field in ('projection_outline', 'reduced_motion') and hasattr(self.bridge, 'projection_outline'):
            self.bridge.projection_outline.sync()
        if field == 'projection_outline':
            self.save_preferences()
        # Pane navigation only invalidates its owners. Document edits still
        # broadcast so retained panes refresh before becoming interactive.
        self.emit(field if field in ('inspector', 'view', 'page', 'group', 'query', 'material_browser', 'name', 'pending_rename', 'pending_confirm') else None)

    def set_editor(self, field, value):
        if getattr(self.editor, field) == value:
            return
        if field in ('start', 'end'):
            start = value if field == 'start' else self.editor.start
            end = value if field == 'end' else self.editor.end
            self.box_anchor = None
            return self.action(self.editor.select_box, start, end)
        setattr(self.editor, field, value)
        self.emit()

    def range_value(self, field, value, editor=True):
        """Store every slider change now; publish expensive panels after release."""
        target = self.editor if editor else self
        if getattr(target, field) == value:
            return
        setattr(target, field, value)
        self.parameter_serial += 1
        serial = self.parameter_serial
        if field == 'layer':
            self.refresh_preview()

        def settled():
            if serial == self.parameter_serial:
                self.emit()
            if field == 'spectrum_speed' and self.spectrum_speed == value:
                if hasattr(self.bridge, 'projection_outline'):
                    self.bridge.projection_outline.sync()
                self.save_preferences()
        self.bridge.later(.16, settled)

    def save_preferences(self):
        if hasattr(self.bridge, 'save_preferences'):
            self.bridge.save_preferences({'spectrum_speed': self.spectrum_speed, 'palette': self.palette,
                                          'projection_outline': self.projection_outline})

    def open_materials(self, channel):
        self.material_browser = channel
        self.emit('material_browser')
        if not self.catalogue_loading and not self.catalogue_ready:
            self.catalogue_loading = True
            self.bridge.request_catalogue()

    def add_material(self, value):
        if self.material_browser not in ('material', 'secondary', 'source', 'filter_material'):
            return
        if value not in self.palette:
            if len(self.palette) >= 64:
                self.editor.message = '常用方块已满，请先移除不需要的方块'
                self.emit()
                return
            self.palette.append(value)
        setattr(self.editor, self.material_browser, value)
        self.material_browser = None
        self.save_preferences()
        self.emit()

    def edit_palette(self, value, direction=None):
        if value not in self.palette:
            return
        index = self.palette.index(value)
        if direction is None:
            self.palette.pop(index)
        else:
            destination = max(0, min(len(self.palette)-1, index+direction))
            self.palette[index], self.palette[destination] = self.palette[destination], self.palette[index]
        self.save_preferences()
        self.emit()

    def adjust_boundary(self, axis, side, delta):
        e = self.editor
        if not e.selection:
            e.select_box(e.start, e.end)
        lo, hi = [list(p) for p in bounds(e.selection)]
        edge = lo if side == 0 else hi
        edge[axis] = max(0, min(e.document.size[axis] - 1, edge[axis] + delta))
        if lo[axis] > hi[axis]:
            return False
        self.box_anchor = None
        e.select_box(tuple(lo), tuple(hi))
        self.emit()
        return True

    def choose_tool(self, tool):
        self.tool = tool
        self.direct_mode = 'browse'
        self.box_anchor = None
        if tool.startswith('paste'):
            self.paste_origin = tuple(self.editor.start)
            self.paste_pinned = False
        self.inspector = 'params'
        self.emit('editing_mode')

    def choose_group(self, group):
        if self.group == group and not self.query:
            return
        self.group = group
        self.query = ''
        self.emit('group')

    def action(self, callback, *args):
        if self.io_job is not None:
            self.editor.message = '建筑存取进行中，请稍后'
            self.emit('edit_progress')
            return False
        if self.edit_job is not None:
            self.editor.message = '正在编辑，可点击取消'
            self.emit()
            return False
        try:
            if callback == self.editor.run and self.editor.document.volume > SMALL_VOLUME:
                return self.start_edit(args[0])
            result = callback(*args)
            if callback == self.editor.run and args and args[0].startswith('select_'):
                self.box_anchor = None
        except (ValueError, TypeError) as error:
            self.editor.message = str(error).decode('utf8') if isinstance(str(error), bytes) else str(error)
            self.emit()
            return False
        self.refresh_preview()
        self.emit()
        return result

    def run(self):
        if self.box_anchor is not None:
            self.editor.message = '请先点击框选终点，或取消框选'
            self.emit()
            return False
        if self.paste_active():
            from .pasting import paste_error
            error = paste_error(self.editor.document, self.editor.clipboard, self.paste_origin)
            if error:
                self.editor.message = error
                self.emit()
                return False
            self.editor.start = self.paste_origin
            self.paste_pinned = True
        return self.action(self.editor.run, self.tool)

    def paste_active(self):
        return self.direct_mode == 'browse' and self.tool in ('paste', 'paste_airless')

    def set_paste_origin(self, value):
        self.paste_origin = tuple(int(v) for v in value)
        self.paste_pinned = True
        self.emit()

    def move_paste(self, axis, amount):
        value = list(self.paste_origin)
        value[axis] = max(0, min(self.editor.document.size[axis]-1, value[axis]+amount))
        self.set_paste_origin(value)

    def erase_selection(self):
        if self.box_anchor is not None or not self.editor.selection:
            self.editor.message = '请先完成框选，再擦除选区'
            self.emit()
            return False
        return self.action(self.editor.run, 'erase')

    def start_edit(self, tool):
        if self.busy:
            self.editor.message = '请等待世界操作完成'
            self.emit()
            return False
        from .jobs import EditJob
        self.edit_job = EditJob(self.editor, tool)
        job = self.edit_job
        last = [0.]
        started = time.time()
        self.performance.update(editCPU=0., editSteps=0, editWall=None)
        def advance():
            if self.edit_job is not job:
                return
            tick_start = time.time()
            job.step()
            self.performance['editCPU'] += time.time()-tick_start
            self.performance['editSteps'] += 1
            now = time.time()
            if job.done:
                self.performance['editWall'] = now-started
                self.edit_job = None
                if job.tool.startswith('select_'):
                    self.box_anchor = None
                if job.error:
                    self.editor.message = as_text(job.error)
                self.refresh_preview()
                self.emit()
            else:
                if now - last[0] >= .25:
                    last[0] = now
                    self.editor.message = '正在编辑 %d / %d，可取消' % (min(job.total, job.processed), job.total)
                    self.emit('edit_progress')
                self.next_frame(advance)
        self.next_frame(advance)
        self.emit()
        return True

    def next_frame(self, callback):
        if hasattr(self.bridge, 'next_frame'):
            self.bridge.next_frame(callback)
        else:
            self.bridge.later(0., callback)

    def cancel_edit(self):
        if self.edit_job is not None:
            self.edit_job.cancel()

    def refresh_preview(self):
        if hasattr(self.bridge, 'geometry'):
            self.tiles.refresh()
            return
        signature = self.preview_signature()
        if signature == self.model_revision or self.preview_pending:
            return
        self.preview_pending = True
        self.bridge.later(.08, self._build_preview)

    def point_edit(self, pos, erase=False):
        result = self.editor.paint_at(pos, erase, False)
        if result:
            self.tiles.refresh([pos])
        # The cursor and native tiles read current data every frame. Inspector,
        # history and document statistics only need one update after a burst.
        self.point_publish += 1
        serial = self.point_publish
        def settled():
            if serial == self.point_publish:
                self.emit()
        self.bridge.later(.4, settled)
        return result

    def _build_preview(self):
        editor = self.editor
        signature = self.preview_signature()
        if editor.document.volume > SMALL_VOLUME:
            from .large_preview import build_preview
            focus = None
            def prepare():
                for result in build_preview(editor.document, self.preview_hidden(), editor.layer if self.solo_layer else None, focus,
                                            self.depth_plane()):
                    if result is None:
                        yield None
                        continue
                    doc, origin, scale = result
                    yield self.bridge.geometry(doc), origin, doc.size, scale
                    return
            iterator = prepare()
            def advance():
                if signature != self.preview_signature():
                    self.preview_pending = False
                    self.refresh_preview()
                    return
                deadline = time.time() + .004
                try:
                    while time.time() < deadline:
                        result = next(iterator)
                        if result is not None:
                            name, origin, size, scale = result
                            self.model_name = name
                            self.scene_origin, self.scene_size, self.scene_scale = origin, size, scale
                            self.model_revision = signature
                            self.preview_pending = False
                            self.preview_error = ''
                            self.emit()
                            return
                except (ValueError, TypeError, RuntimeError) as error:
                    self.preview_pending = False
                    self.preview_error = as_text(str(error))
                    self.emit()
                    return
                self.bridge.later(0., advance)
            self.bridge.later(0., advance)
            return
        self.preview_pending = False

        from .camera import behind_plane
        plane = self.depth_plane()
        def visible(pos):
            return self.visible_layer(pos[1]) and behind_plane(pos, plane)
        try:
            self.model_name = self.bridge.geometry(editor.document, visible)
            self.model_revision = signature
            self.scene_origin, self.scene_size, self.scene_scale = (0, 0, 0), editor.document.size, 1
            self.preview_error = ''
        except (ValueError, TypeError, RuntimeError) as error:
            # Keep the last usable preview, but permit the next action to retry.
            self.model_revision = None
            self.preview_error = str(error).decode('utf8') if isinstance(str(error), bytes) else str(error)
        self.emit()

    def preview_signature(self):
        return (id(self.editor), self.editor.revision, tuple(sorted(self.editor.hidden_layers)), self.solo_layer,
                self.editor.layer if self.solo_layer or self.section else -1, self.section)

    def depth_plane(self):
        from .camera import OrbitCamera
        camera = OrbitCamera(*self.camera_pose)
        camera.depth = self.camera_depth_pose
        return camera.depth_plane(self.editor.document.size)

    def visible_position(self, pos):
        return self.editor.document.contains(pos) and self.visible_layer(pos[1])

    def move_depth(self, direction):
        step = max(1., max(self.editor.document.size)/16.)
        self.camera_depth = max(0., min(sum(self.editor.document.size)+1., self.camera_depth+direction*step))
        self.emit('camera_depth')

    def visible_layer(self, y):
        return (y not in self.editor.hidden_layers and
                (not self.solo_layer or y == self.editor.layer) and
                (not self.section or y <= self.editor.layer))

    def preview_hidden(self):
        hidden = set(self.editor.hidden_layers)
        if self.section:
            hidden.update(range(self.editor.layer + 1, self.editor.document.size[1]))
        return hidden

    def toggle_section(self):
        self.display_mode('full' if self.section else 'section')

    def display_mode(self, mode):
        if mode not in ('full', 'section', 'single'):
            raise ValueError('unknown scene display mode')
        self.view = '3d'
        self.section, self.solo_layer = mode == 'section', mode == 'single'
        self.refresh_preview()
        self.emit()

    def current_display_mode(self):
        return 'single' if self.solo_layer else 'section' if self.section else 'full'

    def toggle_layer(self, kind, layer):
        target = self.editor.locked_layers if kind == 'lock' else self.editor.hidden_layers
        if layer in target:
            target.remove(layer)
        else:
            target.add(layer)
        self.refresh_preview()
        self.emit()

    def layer(self, value):
        self.editor.layer = max(0, min(self.editor.document.size[1] - 1, int(round(value))))
        self.refresh_preview()
        self.emit()

    def toggle_solo(self):
        self.display_mode('full' if self.solo_layer else 'single')

    def paint(self, x, z):
        pos = (x, self.editor.layer, z)
        if self.paint_mode == 'pick':
            self.editor.material = self.editor.document.get(pos)
            self.editor.message = '已吸取当前格材质'
            self.emit()
        elif self.paint_mode in ('start', 'end'):
            setattr(self.editor, self.paint_mode, pos)
            self.action(self.editor.select_box, self.editor.start, self.editor.end)
        else:
            self.action(self.editor.paint_at, pos, self.paint_mode == 'erase')

    def choose_mode(self, mode):
        if mode == 'erase' and self.direct_mode != 'erase':
            self.erase_scope = 'selection' if len(self.editor.selection) > 1 else 'single'
        self.direct_mode = mode
        self.box_anchor = None
        self.inspector = 'params'
        self.emit('editing_mode')

    def camera_view(self, yaw=None, pitch=None, zoom=None):
        actual_yaw, actual_pitch, actual_zoom = self.camera_pose
        self.camera_yaw = actual_yaw if yaw is None else yaw
        self.camera_pitch = actual_pitch if pitch is None else pitch
        self.zoom = actual_zoom if zoom is None else zoom
        self.camera_revision += 1
        self.emit('view')

    def reset_camera(self, animated=True):
        self.camera_depth = 0.
        if not animated:
            self.camera_depth_pose = 0.
        self.camera_focus_request = None
        self.camera_pivot = None
        self.camera_pan = (0., 0.)
        self.camera_yaw, self.camera_pitch, self.zoom = 35., 25., 1.
        self.camera_reset_animated = animated
        if not animated:
            self.camera_pose = (35., 25., 1.)
        self.camera_reset_revision += 1
        self.camera_revision += 1
        self.emit('view')

    def pan_view(self, x, y):
        self.camera_pan = (self.camera_pan[0] + x, self.camera_pan[1] + y)
        self.emit('camera_pan')

    def locate_selected(self):
        if self.focused is None:
            return
        self.camera_focus_request = tuple(v + .5 for v in self.focused)
        self.emit('view')

    def placement_target(self, pos, normal):
        target = tuple(pos[i] + normal[i] for i in range(3))
        e = self.editor
        if not e.document.contains(target):
            return target, '目标超出建筑范围'
        if not self.visible_position(target):
            return target, '目标位置不可见，请先后退或显示该图层'
        if target[1] in e.locked_layers:
            return target, '目标图层已锁定'
        if e.document.get(target) != AIR:
            return target, '放置位置已有方块，请使用换材质'
        if not e._writable(target, False) or e.material == AIR:
            return target, '放置条件不匹配，请检查材质与方块条件'
        return target, None

    def cursor_target(self, pos, normal=(0, 0, 0)):
        if self.direct_mode == 'place':
            return self.placement_target(pos, normal)
        if self.direct_mode in ('erase', 'paint'):
            if not self.editor._writable(pos, False):
                return pos, '此位置受图层或方块条件限制'
        return pos, None

    def point_action(self, pos, normal=(0, 0, 0)):
        """One click, one undo record. Dragging never reaches this method."""
        if self.edit_job is not None or self.io_job is not None:
            return False
        e = self.editor
        if not e.document.contains(pos):
            return False
        if self.paste_active():
            self.focused = pos
            self.set_paste_origin(pos)
            e.message = '粘贴起点已定位，请确认范围后粘贴'
            return True
        mode = self.direct_mode
        if mode == 'erase' and self.erase_scope == 'selection':
            self.editor.message = '选区已保留，请点击擦除选区'
            self.emit()
            return False
        self.focused = pos
        if mode == 'place':
            target, error = self.placement_target(pos, normal)
            if error:
                e.message = error
            else:
                e.select_box(target, target)
                self.focused = target
                return self.point_edit(target)
        elif mode in ('paint', 'erase'):
            e.select_box(pos, pos)
            return self.point_edit(pos, mode == 'erase')
        elif mode == 'pick':
            e.select_box(pos, pos)
            if e.document.get(pos) != AIR:
                e.material = e.document.get(pos)
                e.message = '已吸取材质：' + e.material[0]
        elif mode == 'select':
            e.select_box(pos, pos)
        elif mode == 'box':
            if self.box_anchor is None:
                self.box_anchor = pos
                e.select_box(pos, pos)
                e.message = '起点已设置，请点击框选终点'
            else:
                start = self.box_anchor
                self.box_anchor = None
                e.select_box(start, pos)
                e.message = '已选择 %d 格，所有批量工具使用此选区' % len(e.selection)
        else:
            e.select_box(pos, pos)
            e.message = '方块坐标：%d, %d, %d' % pos
        self.emit()
        return True

    def save(self):
        name = as_text(self.name).strip()
        if not name or len(name) > 64:
            raise ValueError('请输入 1–64 字的建筑名称')
        if len(self.library) >= 32:
            raise ValueError('建筑库最多 32 个配置，请先删除不需要的配置')
        serial = self.library_serial + 1
        def commit(data):
            data['name'] = name
            entry = {'id': serial, 'data': data, 'saved': int(time.time())}
            candidate = self.library + [entry]
            if not self.bridge.save_library({'version': 1, 'serial': serial, 'buildings': candidate}):
                raise ValueError('保存失败，建筑仍在当前草稿中')
            self.library, self.library_serial = candidate, serial
            self.editor.document.name = name
            self.editor.saved_revision = self.editor.revision
            self.editor.message = '建筑已保存到本机建筑库'
        if self.editor.document.volume > SMALL_VOLUME:
            from .archive import save_steps
            doc = Document(self.editor.document.size, name=name)
            doc.blocks = self.editor.document.blocks.copy()
            self._start_io(save_steps(self.bridge, doc, serial), commit, '正在保存建筑')
        else:
            commit(self.editor.document.to_data())

    def load(self, identity):
        entry = next((item for item in self.library if item['id'] == identity), None)
        if entry is None:
            raise ValueError('找不到这份配置')
        data = entry['data']
        Document(data.get('size', ()))
        if data.get('version') == 3:
            from .archive import load_steps
            self._start_io(load_steps(self.bridge, identity, data), self._loaded, '正在载入建筑')
        elif data.get('version') == 2:
            from .codec import load_steps
            self._start_io(load_steps(data), self._loaded, '正在载入建筑')
        else:
            self._loaded(Document.from_data(data))

    def _loaded(self, document):
        self.camera_focus_request = None
        self.editor = Editor(document)
        self.section = self.solo_layer = False
        self.camera_pan = (0., 0.)
        self.canvas_x = self.canvas_z = 0
        self.reset_camera(False)
        self.focused = self.box_anchor = None
        self.paste_origin, self.paste_pinned = (0, 0, 0), False
        self.name = self.editor.document.name
        self.page = 'workspace'
        self.editor.message = '已载入建筑配置'
        self.refresh_preview()

    def delete(self, identity):
        previous = next((item for item in self.library if item['id'] == identity), None)
        candidate = [item for item in self.library if item['id'] != identity]
        if not self.bridge.save_library({'version': 1, 'serial': self.library_serial, 'buildings': candidate}):
            raise ValueError('删除失败，原配置已保留')
        self.library = candidate
        if previous and previous['data'].get('version') == 3:
            self.bridge.clear_archive(identity, previous['data']['parts'])
        self.editor.message = '已删除建筑配置'

    def _start_io(self, iterator, complete, message):
        self.io_job = iterator
        self.editor.message = message
        self.emit()
        def advance():
            if self.io_job is not iterator:
                return
            try:
                deadline = time.time() + .004
                while time.time() < deadline:
                    result = next(iterator)
                    if result is not None:
                        complete(result)
                        self.io_job = None
                        self.emit()
                        return
            except (ValueError, TypeError, KeyError, RuntimeError, StopIteration) as error:
                self.io_job = None
                self.editor.message = as_text(str(error)) or '建筑存取失败，当前草稿已保留'
                self.emit()
                return
            self.bridge.later(0., advance)
        self.bridge.later(0., advance)

    def open_rename(self, identity):
        entry = next((item for item in self.library if item['id'] == identity), None)
        if entry is None:
            return
        self.rename_error = ''
        self.pending_rename = (identity, entry['data']['name'])
        self.emit('pending_rename')

    def accept_rename(self, name):
        if self.pending_rename is None:
            return
        try:
            self.rename(self.pending_rename[0], name)
        except (ValueError, TypeError) as error:
            self.rename_error = as_text(str(error))
            self.emit('pending_rename')
            return
        self.pending_rename = None
        self.rename_error = ''
        self.emit('pending_rename')
        self.emit('library')

    def rename(self, identity, name):
        if self.io_job is not None:
            raise ValueError('建筑存取进行中，请稍后')
        name = as_text(name).strip()
        if not 1 <= len(name) <= 64:
            raise ValueError('请输入 1–64 字的建筑名称')
        if not any(item['id'] == identity for item in self.library):
            raise ValueError('这份配置已不存在，请重新选择')
        candidate = []
        for item in self.library:
            copy = dict(item)
            copy['data'] = dict(item['data'])
            if item['id'] == identity:
                copy['data']['name'] = name
            candidate.append(copy)
        if not self.bridge.save_library({'version': 1, 'serial': self.library_serial, 'buildings': candidate}):
            raise ValueError('重命名保存失败')
        self.library = candidate
        self.editor.message = '已重命名建筑配置'

    def confirm(self, title, callback):
        self.pending_confirm = (title, callback)
        self.emit('pending_confirm')

    def accept(self):
        if self.pending_confirm:
            callback = self.pending_confirm[1]
            self.pending_confirm = None
            self.action(callback)

    def demo(self):
        self._loaded(demo_document())

    def empty(self, size=None):
        if size is None and not self.new_size_valid:
            raise ValueError('请先输入有效的新建尺寸')
        self._loaded(Document(self.new_size if size is None else size))
        self.name = '未命名建筑'
        self.canvas_x = self.canvas_z = 0
        self.page = 'workspace'
        self.progress = None
        self.editor.message = '已新建 %d × %d × %d 的空白建筑' % self.editor.document.size
