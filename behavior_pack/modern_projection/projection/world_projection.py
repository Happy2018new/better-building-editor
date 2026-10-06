# -*- coding: utf-8 -*-
"""Prepare an exact full-size world palette incrementally, submit one mesh."""
from __future__ import unicode_literals
import time
from .model import Document, add
from .storage import integer_types
from .large_preview import SurfacePalette


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
        self.keys = tuple(sorted(self.document.blocks.chunks))
        self.total, self.completed = len(self.keys), set()
        self.output = SurfacePalette(self.document.size)
        self.iterator = self.prepare()
        self.published = 0.
        self.ready, self.error, self.model = False, None, None

    def active(self):
        return self.bridge.alive and self.bridge.projection_serial == self.serial

    def visible_y(self, y):
        return y < self.document.size[1] and y not in self.hidden and (self.layer is None or y == self.layer)

    def prepare(self):
        store = self.document.blocks
        for key in self.keys:
            start = tuple(v*16 for v in key)
            size = tuple(min(16, self.document.size[i]-start[i]) for i in range(3))
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
        else:
            s.editor.message = '正在准备完整投影 %d%%' % (100*len(self.completed)//max(1,self.total))
        s.emit()

    def fail(self, message):
        b = self.bridge
        if not self.active():
            return
        b.cancel_preparing_projection()
        # Keep the previous projection on failure; never retry forever.
        self.error = message
        self.iterator = self.output = None
        b.projection_requested = bool(b.session.projection_active)
        if not b.session.projection_active:
            b.restore_projection_distance()
        self.publish(True)

    def commit(self, entity):
        b = self.bridge
        b.commit_projection_actor(entity, self.model, self.origin, self.anchor)
        b.session.projection_active = True
        b.projection_outline.replace(self.origin, self.document.size)
        b.set_projection_occupancy(self.occupancy, entity, self.model)
        self.ready = True
        self.output = None
        self.publish(True)

    def attach(self, entity):
        b = self.bridge
        if not self.active() or b.preparing_entity != entity:
            return
        try:
            b.factory.CreateModel(entity).SetEntityShadowShow(False)
            render = b.factory.CreateActorRender(entity)
            # Rotation applies after offset. Anchor at the centre for native
            # visibility, preserving exact origin + document voxel coordinates.
            offset = (self.center[0]-.5, -self.center[1], self.center[2]-.5)
            from .biomes import actor_uniform
            success = (render.AddActorBlockGeometry(self.model, offset, (0.,180.,0.)) and
                       render.EnableActorBlockGeometryTransparent(self.model, True) and
                       render.SetActorBlockGeometryTransparency(self.model, self.opacity) and
                       render.SetEntityExtraUniforms(4, actor_uniform(self.document.biome)))
            if not success:
                raise ValueError('透明投影生成失败，原投影已保留，请重试')
            if self.occupancy is not None:
                self.occupancy.document.biome = self.document.biome
                self.occupancy.shader.bind(entity, self.model, self.anchor, attached=True,
                                           backdrop=b.preparing_backdrop)
            else:
                b.preparing_backdrop.bind((self.model,), self.model, self.document.biome)
            self.commit(entity)
        except Exception as exc:
            self.fail(type('')(exc))

    def submit(self):
        b = self.bridge
        self.model = (b.geometry(self.output, name=self.occupancy.shader.names[0])
                      if self.occupancy else b.geometry(self.output))
        if not self.model:
            if self.output.count:
                raise ValueError('投影模型生成失败，原投影已保留，请重试')
            self.commit(None)
            return
        entity = b.prepare_projection_actor(self.origin, self.anchor)
        b.later(.2, lambda: self.attach(entity))

    def advance(self):
        if not self.active() or self.iterator is None:
            return
        deadline = time.time()+.003
        try:
            while time.time() < deadline:
                if next(self.iterator, False) is False:
                    self.iterator = None
                    self.publish(True)
                    self.submit()  # One native model; no transparent tile seams.
                    return
        except Exception as exc:
            self.fail(type('')(exc))
            return
        self.publish()
        self.bridge.next_frame(self.advance)
