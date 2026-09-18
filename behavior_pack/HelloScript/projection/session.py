# -*- coding: utf-8 -*-
"""Application state, local building library, and coalesced preview generation."""
from __future__ import unicode_literals
import time
from .model import AIR, Document, Editor, demo_document, SMALL_VOLUME


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
        self.direct_selection = False
        self.focused = None
        self.box_anchor = None
        self.camera_pose = (35., 25., 1.)
        self.camera_revision = 0
        self.canvas_x = 0
        self.canvas_z = 0
        self.solo_layer = False
        self.grid = True
        self.reduced_motion = False
        self.origin = (0, 64, 0)
        self.opacity = .45
        self.apply_air = False
        self.projection_active = False
        self.projection_missing = False
        self.progress = None
        self.pending_confirm = None
        self.busy = False
        self.ready = False
        self.parameter_serial = 0
        self.edit_job = None
        self.io_job = None
        self.preview_detail = False
        self.preview_center = (0, 0, 0)
        self.scene_origin = (0, 0, 0)
        self.scene_size = self.editor.document.size
        self.scene_scale = 1

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
        if field in ('canvas_x', 'canvas_z') and self.preview_detail:
            self.focused = None
            self.preview_center = (self.canvas_x, self.editor.layer, self.canvas_z)
            self.refresh_preview()
        if field == 'origin':
            self.progress = None
        # Pane navigation only invalidates its owners. Document edits still
        # broadcast so retained panes refresh before becoming interactive.
        self.emit(field if field in ('inspector', 'view', 'page', 'group', 'query') else None)

    def set_editor(self, field, value):
        if getattr(self.editor, field) == value:
            return
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
            if self.preview_detail:
                self.preview_center = (self.preview_center[0], value, self.preview_center[2])
            self.refresh_preview()

        def settled():
            if serial == self.parameter_serial:
                self.emit()
        self.bridge.later(.16, settled)

    def choose_tool(self, tool):
        self.tool = tool
        self.direct_mode = 'browse'
        self.inspector = 'params'
        self.emit()

    def choose_group(self, group):
        if self.group == group and not self.query:
            return
        self.group = group
        self.query = ''
        self.emit('group')

    def action(self, callback, *args):
        if self.io_job is not None:
            self.editor.message = '建筑存取进行中，请稍候'
            self.emit('edit_progress')
            return False
        if self.edit_job is not None:
            self.editor.message = '编辑任务进行中，可点击取消'
            self.emit()
            return False
        try:
            if callback == self.editor.run and self.editor.document.volume > SMALL_VOLUME:
                return self.start_edit(args[0])
            result = callback(*args)
        except (ValueError, TypeError) as error:
            self.editor.message = str(error).decode('utf8') if isinstance(str(error), bytes) else str(error)
            self.emit()
            return False
        self.refresh_preview()
        self.emit()
        return result

    def run(self):
        return self.action(self.editor.run, self.tool)

    def start_edit(self, tool):
        if self.busy:
            self.editor.message = '请等待世界操作完成'
            self.emit()
            return False
        from .jobs import EditJob
        self.edit_job = EditJob(self.editor, tool)
        job = self.edit_job
        last = [0.]
        def advance():
            if self.edit_job is not job:
                return
            job.step()
            now = time.time()
            if job.done:
                self.edit_job = None
                if job.error:
                    self.editor.message = as_text(job.error)
                self.refresh_preview()
                self.emit()
            else:
                if now - last[0] >= .25:
                    last[0] = now
                    self.editor.message = '正在编辑 %d / %d · 可取消' % (min(job.total, job.processed), job.total)
                    self.emit('edit_progress')
                self.bridge.later(0., advance)
        self.bridge.later(0., advance)
        self.emit()
        return True

    def cancel_edit(self):
        if self.edit_job is not None:
            self.edit_job.cancel()

    def refresh_preview(self):
        signature = self.preview_signature()
        if signature == self.model_revision or self.preview_pending:
            return
        self.preview_pending = True
        self.bridge.later(.08, self._build_preview)

    def _build_preview(self):
        editor = self.editor
        signature = self.preview_signature()
        if editor.document.volume > SMALL_VOLUME:
            from .large_preview import build_preview
            focus = self.preview_center if self.preview_detail else None
            iterator = build_preview(editor.document, editor.hidden_layers, editor.layer if self.solo_layer else None, focus)
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
                            doc, origin, scale = result
                            self.model_name = self.bridge.geometry(doc)
                            self.scene_origin, self.scene_size, self.scene_scale = origin, tuple(v * scale for v in doc.size), scale
                            self.model_revision = signature
                            self.preview_pending = False
                            self.preview_error = '' if self.model_name else '当前范围没有可显示的方块'
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

        def visible(pos):
            return pos[1] not in editor.hidden_layers and (not self.solo_layer or pos[1] == editor.layer)
        try:
            self.model_name = self.bridge.geometry(editor.document, visible)
            self.model_revision = signature
            self.scene_origin, self.scene_size, self.scene_scale = (0, 0, 0), editor.document.size, 1
            self.preview_error = '' if self.model_name else '当前可见图层没有可显示的方块'
        except (ValueError, TypeError, RuntimeError) as error:
            # Keep the last usable preview, but permit the next action to retry.
            self.model_revision = None
            self.preview_error = str(error).decode('utf8') if isinstance(str(error), bytes) else str(error)
        self.emit()

    def preview_signature(self):
        return (id(self.editor), self.editor.revision, tuple(sorted(self.editor.hidden_layers)), self.solo_layer,
                self.editor.layer if self.solo_layer else -1, self.preview_detail,
                self.preview_center if self.preview_detail else None)

    def toggle_preview_detail(self):
        self.preview_detail = not self.preview_detail
        if self.preview_detail:
            self.preview_center = self.focused or (self.canvas_x, self.editor.layer, self.canvas_z)
        self.refresh_preview()
        self.emit()

    def focus_preview(self, pos):
        if not self.editor.document.contains(pos):
            raise ValueError('局部中心必须位于建筑范围内')
        self.focused = tuple(pos)
        self.preview_center = tuple(pos)
        self.canvas_x, self.editor.layer, self.canvas_z = pos
        self.preview_detail = True
        self.view = '3d'
        self.refresh_preview()
        self.emit()

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
        if self.preview_detail:
            self.preview_center = (self.preview_center[0], self.editor.layer, self.preview_center[2])
        self.refresh_preview()
        self.emit()

    def toggle_solo(self):
        self.solo_layer = not self.solo_layer
        self.refresh_preview()
        self.emit()

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
        self.direct_mode = mode
        self.box_anchor = None
        self.inspector = 'params'
        self.emit()

    def camera_view(self, yaw=None, pitch=None, zoom=None):
        actual_yaw, actual_pitch, actual_zoom = self.camera_pose
        self.camera_yaw = actual_yaw if yaw is None else yaw
        self.camera_pitch = actual_pitch if pitch is None else pitch
        self.zoom = actual_zoom if zoom is None else zoom
        self.camera_revision += 1
        self.emit()

    def point_action(self, pos, normal=(0, 0, 0)):
        """One click, one undo record. Dragging never reaches this method."""
        if self.edit_job is not None or self.io_job is not None:
            return False
        e = self.editor
        if not e.document.contains(pos):
            return False
        self.focused = pos
        mode = self.direct_mode
        if mode == 'place':
            target = tuple(pos[i] + normal[i] for i in range(3))
            if not e.document.contains(target):
                e.message = '目标超出建筑范围'
            elif target[1] in e.hidden_layers or (self.solo_layer and target[1] != e.layer):
                e.message = '目标图层不可见，请先显示该图层'
            else:
                self.focused = target
                return self.action(e.paint_at, target, False, self.direct_selection)
        elif mode in ('paint', 'erase'):
            return self.action(e.paint_at, pos, mode == 'erase', self.direct_selection)
        elif mode == 'pick':
            if e.document.get(pos) != AIR:
                e.material = e.document.get(pos)
                e.message = '已吸取材质：' + e.material[0]
        elif mode == 'select':
            e.start = e.end = pos
            e.select_box(pos, pos)
            e.layer = pos[1]
            self.refresh_preview()
        elif mode == 'box':
            if self.box_anchor is None:
                self.box_anchor = e.start = pos
                e.message = '起点已设置，请点击框选终点'
            else:
                e.start, e.end = self.box_anchor, pos
                self.box_anchor = None
                e.select_box(e.start, e.end)
        else:
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
        if data.get('version') == 3:
            from .archive import load_steps
            self._start_io(load_steps(self.bridge, identity, data), self._loaded, '正在载入建筑')
        elif data.get('version') == 2:
            from .codec import load_steps
            self._start_io(load_steps(data), self._loaded, '正在载入建筑')
        else:
            self._loaded(Document.from_data(data))

    def _loaded(self, document):
        self.editor = Editor(document)
        self.preview_detail = False
        self.focused = self.box_anchor = None
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

    def rename(self, identity):
        name = as_text(self.name).strip()
        if not 1 <= len(name) <= 64:
            raise ValueError('请输入 1–64 字的建筑名称')
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
        self.emit()

    def accept(self):
        if self.pending_confirm:
            callback = self.pending_confirm[1]
            self.pending_confirm = None
            self.action(callback)

    def demo(self):
        self.editor = Editor(demo_document())
        self.preview_detail = False
        self.focused = self.box_anchor = None
        self.name = self.editor.document.name
        self.refresh_preview()

    def empty(self):
        self.editor = Editor(Document(self.new_size))
        self.preview_detail = False
        self.focused = self.box_anchor = None
        self.name = '未命名建筑'
        self.canvas_x = self.canvas_z = 0
        self.page = 'workspace'
        self.progress = None
        self.refresh_preview()
