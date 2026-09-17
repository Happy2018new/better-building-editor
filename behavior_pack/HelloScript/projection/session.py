# -*- coding: utf-8 -*-
"""Application state, local building library, and coalesced preview generation."""
from __future__ import unicode_literals
import time
from .model import Document, Editor, demo_document


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
        self.paint_mode = 'paint'
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

    def subscribe(self, callback):
        self.listeners.append(callback)

        def remove():
            if callback in self.listeners:
                self.listeners.remove(callback)
        return remove

    def emit(self):
        self.ui_revision += 1
        for callback in list(self.listeners):
            callback()

    def initialize(self):
        data = self.bridge.load_library()
        if isinstance(data, dict):
            for entry in data.get('buildings', [])[:32]:
                try:
                    entry['data'] = Document.from_data(entry['data']).to_data()
                    if type(entry['id']) is int:
                        self.library.append(entry)
                except (ValueError, TypeError, KeyError):
                    self.editor.message = '已跳过损坏的本地配置'
            self.library_serial = max([0] + [entry['id'] for entry in self.library])
        self.origin = self.bridge.player_origin()
        self.ready = True
        self.refresh_preview()

    def set(self, field, value):
        value = as_text(value)
        setattr(self, field, value)
        if field == 'origin':
            self.progress = None
        self.emit()

    def set_editor(self, field, value):
        setattr(self.editor, field, value)
        self.emit()

    def choose_tool(self, tool):
        self.tool = tool
        self.inspector = 'params'
        self.emit()

    def choose_group(self, group):
        self.group = group
        self.query = ''
        self.emit()

    def action(self, callback, *args):
        try:
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

    def refresh_preview(self):
        signature = (id(self.editor), self.editor.revision, tuple(sorted(self.editor.hidden_layers)),
                     self.solo_layer, self.editor.layer if self.solo_layer else -1)
        if signature == self.model_revision or self.preview_pending:
            return
        self.preview_pending = True
        self.bridge.later(.08, self._build_preview)

    def _build_preview(self):
        self.preview_pending = False
        editor = self.editor
        self.model_revision = (id(editor), editor.revision, tuple(sorted(editor.hidden_layers)),
                               self.solo_layer, editor.layer if self.solo_layer else -1)

        def visible(pos):
            return pos[1] not in editor.hidden_layers and (not self.solo_layer or pos[1] == editor.layer)
        try:
            self.model_name = self.bridge.geometry(editor.document, visible)
            self.preview_error = '' if self.model_name else '当前可见图层没有可显示的方块'
        except ValueError as error:
            self.model_name = None
            self.preview_error = str(error).decode('utf8') if isinstance(str(error), bytes) else str(error)
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

    def save(self):
        name = as_text(self.name).strip()
        if not name or len(name) > 64:
            raise ValueError('请输入 1–64 字的建筑名称')
        if len(self.library) >= 32:
            raise ValueError('建筑库最多 32 个配置，请先删除不需要的配置')
        data = self.editor.document.to_data()
        data['name'] = name
        serial = self.library_serial + 1
        entry = {'id': serial, 'data': data, 'saved': int(time.time())}
        candidate = self.library + [entry]
        if not self.bridge.save_library({'version': 1, 'serial': serial, 'buildings': candidate}):
            raise ValueError('保存失败，建筑仍在当前草稿中')
        self.library, self.library_serial = candidate, serial
        self.editor.document.name = name
        self.editor.saved_revision = self.editor.revision
        self.editor.message = '建筑已保存到本机建筑库'

    def load(self, identity):
        entry = next((item for item in self.library if item['id'] == identity), None)
        if entry is None:
            raise ValueError('找不到这份配置')
        self.editor = Editor(Document.from_data(entry['data']))
        self.name = self.editor.document.name
        self.page = 'workspace'
        self.editor.message = '已载入建筑配置'
        self.refresh_preview()

    def delete(self, identity):
        candidate = [item for item in self.library if item['id'] != identity]
        if not self.bridge.save_library({'version': 1, 'serial': self.library_serial, 'buildings': candidate}):
            raise ValueError('删除失败，原配置已保留')
        self.library = candidate
        self.editor.message = '已删除建筑配置'

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
        self.name = self.editor.document.name
        self.refresh_preview()

    def empty(self):
        self.editor = Editor(Document(self.new_size))
        self.name = '未命名建筑'
        self.canvas_x = self.canvas_z = 0
        self.page = 'workspace'
        self.progress = None
        self.refresh_preview()
