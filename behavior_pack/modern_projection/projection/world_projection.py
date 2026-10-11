# -*- coding: utf-8 -*-
"""Prepare bounded native palettes incrementally and attach them to one actor."""
from __future__ import unicode_literals
import time
import traceback
from .model import Document, add
from .storage import integer_types
from .large_preview import SurfacePalette, build_preview


class WorldProjection(object):
    def __init__(self, bridge, origin):
        self.bridge, self.serial, self.origin = bridge, bridge.projection_serial, origin
        s = bridge.session
        self.document = Document(s.editor.document.size, biome=s.editor.document.biome)
        self.document.blocks = s.editor.document.blocks.copy()
        self.center = tuple(v/2. for v in self.document.size)
        self.anchor = add(origin, self.center)
        self.hidden = set(s.preview_hidden())
        self.layer = s.editor.layer if s.solo_layer else None
        self.opacity, self.missing = s.opacity, s.projection_missing
        from .occupancy import ProjectionOccupancy
        self.occupancy = ProjectionOccupancy(bridge, origin, self.document) if self.missing else None
        self.size = tuple(self.document.size)
        self.targets = ()
        from .occupancy_shader import OccupancyShader
        self.shader = self.occupancy.shader if self.occupancy is not None else OccupancyShader(self)
        self.keys = tuple(sorted(self.document.blocks.chunks))
        self.total, self.completed = len(self.keys), set()
        self.output = SurfacePalette(self.document.size)
        self.prepared = None
        self.iterator = self.prepare()
        self.published = 0.
        self.ready, self.error, self.model = False, None, None
        self.cleanup_errors = []

    def active(self):
        return self.bridge.alive and self.bridge.projection_serial == self.serial

    def visible_y(self, y):
        return y < self.document.size[1] and y not in self.hidden and (self.layer is None or y == self.layer)

    def prepare(self):
        store = self.document.blocks
        for key in self.keys:
            start = tuple(v*16 for v in key)
            size = tuple(min(16, self.document.size[i]-start[i]) for i in range(3))
            if self.occupancy is None:
                end = tuple(start[i]+size[i] for i in range(3))
                for result in build_preview(self.document, self.hidden, self.layer, region=(start, end),
                                            chunks=(key,), output=self.output):
                    yield None
                self.completed.add(key)
                continue
            chunk = store.chunks[key]
            uniform = isinstance(chunk, integer_types)
            if self.occupancy is not None and self.occupancy.bulk is not None:
                from .occupancy_initial import prepare_chunk
                for unused in prepare_chunk(self.occupancy, store, key, size, self.output):
                    yield None
                self.completed.add(key)
                continue
            if not uniform:
                chunk = tuple(chunk)
            for y in range(size[1]):
                if not self.visible_y(start[1]+y):
                    continue
                for z in range(size[2]):
                    for x in range(size[0]):
                        identity = chunk if uniform else chunk[(y << 8) | (z << 4) | x]
                        if not identity:
                            continue
                        value = store.palette[identity]
                        pos = (start[0]+x, start[1]+y, start[2]+z)
                        if self.occupancy is None or self.occupancy.initial_visible(pos):
                            self.output.add(pos, value)
                yield None
            self.completed.add(key)
        from .render_context import ContextBatchBuilder
        builder = ContextBatchBuilder(self.document, self.output.palette_data())
        for unused in builder.prepare():
            yield None
        self.prepared = builder.data
        self.targets = builder.positions[:1]

    def publish(self, force=False):
        if not self.active():
            return
        now = time.time()
        if not force and now-self.published < .2:
            return
        self.published = now
        s = self.bridge.session
        if self.error:
            s.editor.message = self.error
        elif self.ready:
            s.editor.message = ('完整投影已生成，关闭工作台即可查看' if self.model else
                                '当前没有需要投影的方块，范围框已保留')
            if self.cleanup_errors:
                s.editor.message += '；旧投影资源清理失败，请关闭投影后重试'
        else:
            s.editor.message = '正在准备完整投影 %d%%' % (100*len(self.completed)//max(1,self.total))
        s.emit()

    def fail(self, message):
        b = self.bridge
        if not self.active():
            return
        if b.preparing_entity:
            pending = b.preparing_entity
            b.preparing_entity = None
            cleanup = b.release_projection_resources((pending,))
            if cleanup:
                message += '；临时投影资源清理失败，请关闭投影后重试'
        # Keep the previous projection on failure; never retry forever.
        self.error = message
        self.iterator = self.output = self.prepared = None
        b.projection_requested = bool(b.session.projection_active)
        if not b.session.projection_active:
            b.restore_projection_distance()
        self.publish(True)

    def commit(self, entity):
        b = self.bridge
        from .projection_outline import ProjectionOutline
        previous_outline = b.projection_outline
        outline = previous_outline
        if outline.bounds != (tuple(self.origin), tuple(self.document.size)):
            outline = ProjectionOutline(b)
        try:
            if self.occupancy is not None:
                self.occupancy.prepare_start(entity, self.model, self.anchor)
            if outline is not previous_outline:
                outline.replace(self.origin, self.document.size)
        except Exception:
            if outline is not previous_outline:
                b.release_projection_resources(outlines=(outline,))
            raise
        previous_entities = tuple(b.projection_entities.values()) + (b.entity,)
        # No native calls between publication of the prepared resources.
        b.entity, b.preparing_entity = entity, None
        b.projection_entities = {}
        b.projection_mesh = (entity, self.model, self.origin, self.anchor) if entity else None
        b.projection_outline = outline
        b.projection_occupancy = self.occupancy
        b.projection_shader = self.shader if entity else None
        b.session.projection_active = True
        self.ready = True
        self.output = self.prepared = None
        self.cleanup_errors = b.release_projection_resources(
            previous_entities, (previous_outline,) if outline is not previous_outline else ())
        try:
            self.publish(True)
        except Exception:
            # Rendering is committed; a UI listener cannot turn it into a failed build.
            traceback.print_exc()

    def attach(self, entity):
        b = self.bridge
        if not self.active() or b.preparing_entity != entity:
            return
        try:
            b.factory.CreateModel(entity).SetEntityShadowShow(False)
            self.shader.bind(entity, self.model, self.anchor)
            self.commit(entity)
        except Exception as exc:
            self.fail(type('')(exc))

    def submit(self):
        b = self.bridge
        self.model = b.geometry(self.output, name=self.shader.names[0], prepared=self.prepared)
        if not self.model:
            if self.output.count:
                raise ValueError('投影模型生成失败，原投影已保留，请重试')
            self.commit(None)
            return
        entity = b.system.CreateClientEntityByTypeStr(b'modern_projection:anchor', self.anchor, (0.,0.))
        if not entity:
            raise ValueError('无法创建投影，请靠近目标区域后重试')
        b.preparing_entity = entity
        b.later(.2, lambda: self.attach(entity))

    def advance(self, schedule=True):
        if not self.active() or self.iterator is None:
            return
        deadline = time.time()+.003
        try:
            while time.time() < deadline:
                if next(self.iterator, False) is False:
                    self.iterator = None
                    self.publish(True)
                    self.submit()  # One actor; all chunks share world depth.
                    return
        except Exception as exc:
            self.fail(type('')(exc))
            return
        self.publish()
        if schedule:
            self.bridge.next_frame(self.advance)
