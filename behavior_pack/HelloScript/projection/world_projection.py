# -*- coding: utf-8 -*-
"""Build every occupied world tile once, retaining it until projection stops."""
from __future__ import unicode_literals
import time
from .model import Document, add
from .storage import integer_types
from .large_preview import SurfacePalette


class WorldProjection(object):
    def __init__(self, bridge, origin):
        self.bridge = bridge
        self.serial = bridge.projection_serial
        self.origin = origin
        s = bridge.session
        self.document = Document(s.editor.document.size)
        self.document.blocks = s.editor.document.blocks.copy()
        # Keep all invisible anchors at the building centre. Native actor
        # visibility uses the actor location independently of its attached
        # geometry; tile-corner anchors can cull a visible upper cap. Offsets
        # below preserve the exact world coordinates of every voxel.
        self.center = tuple(v/2. for v in self.document.size)
        self.anchor = add(origin, self.center)
        self.hidden = set(s.preview_hidden())
        self.layer = s.editor.layer if s.solo_layer else None
        self.opacity, self.missing = s.opacity, s.projection_missing
        player = bridge.player_origin()
        center = tuple((player[i]-origin[i])/16. for i in range(3))
        # Distance orders preparation only. It must never discard distant tiles
        # or evict an already built part when the player enters a hollow shell.
        self.keys = tuple(sorted((key for key in self.document.blocks.chunks if any(
            self.visible_y(key[1]*16+y) for y in range(16))),
            key=lambda key: (sum((key[i]+.5-center[i])**2 for i in range(3)), key)))
        self.queue = list(self.keys)
        self.completed = set()
        self.failures = {}
        self.models = {}
        self.iterator = None
        self.current = None
        self.total = len(self.keys)
        self.published = 0.

    def active(self):
        return self.bridge.alive and self.bridge.projection_serial == self.serial

    def visible_y(self, y):
        return y < self.document.size[1] and y not in self.hidden and (self.layer is None or y == self.layer)

    def palette(self, key):
        start = tuple(v*16 for v in key)
        size = tuple(min(16, self.document.size[i]-start[i]) for i in range(3))
        out = SurfacePalette(size)
        store = self.document.blocks
        chunk = store.chunks[key]
        uniform = isinstance(chunk, integer_types)
        info = self.bridge.factory.CreateBlockInfo(self.bridge.level) if self.missing else None
        for y in range(size[1]):
            if not self.visible_y(start[1]+y):
                continue
            for z in range(size[2]):
                for x in range(size[0]):
                    identity = chunk if uniform else chunk[(y << 8) | (z << 4) | x]
                    if not identity:
                        continue
                    value = store.palette[identity]
                    if info is None or self.bridge.needs_projection(info, add(self.origin, add(start, (x,y,z))), value):
                        out.add((x,y,z), value)
            yield None
        yield out

    def publish(self, force=False):
        if not self.active():
            return
        now = time.time()
        if not force and now-self.published < .2:
            return
        self.published = now
        s = self.bridge.session
        done = len(self.completed)
        if done == self.total:
            s.editor.message = '完整投影已生成，关闭工作台即可查看'
        elif self.failures and not self.queue and self.iterator is None:
            s.editor.message = '投影已准备 %d/%d，未就绪的部分将自动重试' % (done, self.total)
        else:
            s.editor.message = '正在准备完整投影 %d%%' % (100*done//max(1,self.total))
        s.emit()

    def failed(self, key):
        entity = self.bridge.projection_entities.pop(key, None)
        if entity:
            self.bridge.system.DestroyClientEntity(entity)
        self.failures[key] = time.time()+2.
        self.publish(True)

    def attach(self, key, entity, name):
        b = self.bridge
        if not self.active() or b.projection_entities.get(key) != entity:
            return
        try:
            render = b.factory.CreateActorRender(entity)
            offset = (self.center[0]-.5-key[0]*16,
                      key[1]*16-self.center[1], self.center[2]-.5-key[2]*16)
            success = (render.AddActorBlockGeometry(name, offset, (0.,180.,0.)) and
                       render.EnableActorBlockGeometryTransparent(name, True) and
                       render.SetActorBlockGeometryTransparency(name, self.opacity) and
                       render.SetEntityExtraUniforms(4, (19487.,0.,0.,0.)))
        except (ValueError, TypeError, RuntimeError):
            success = False
        if success:
            self.completed.add(key)
            self.publish(len(self.completed) == self.total)
        else:
            self.failed(key)

    def submit(self, key, palette):
        b = self.bridge
        # Attachment retries reuse the geometry; unloaded missing-block checks
        # are retried from the snapshot once their world area becomes available.
        if key not in self.models:
            name = b.geometry(palette)
            if palette.count and not name:
                raise ValueError('投影模型生成失败')
            self.models[key] = name
        name = self.models[key]
        if not name:
            self.completed.add(key)
            self.publish(len(self.completed) == self.total)
            return
        entity = b.system.CreateClientEntityByTypeStr(b'modern_projection:anchor', self.anchor, (0.,0.))
        if not entity:
            self.failed(key)
            return
        b.projection_entities[key] = entity
        # Do not mark ready before the native renderer has actually accepted it.
        b.later(.2, lambda: self.attach(key, entity, name))

    def advance(self):
        if not self.active():
            return
        b = self.bridge
        deadline = time.time()+.003
        try:
            while time.time() < deadline:
                if self.iterator is None:
                    if not self.queue:
                        if self.failures:
                            now = time.time()
                            self.queue = [k for k in self.keys if self.failures.get(k, now+1.) <= now]
                            for key in self.queue:
                                self.failures.pop(key)
                        if not self.queue:
                            # Wait for renderer acknowledgements or retryable
                            # failures, then become completely idle on success.
                            if len(self.completed) < self.total:
                                b.later(.5, self.advance)
                            return
                    self.current = self.queue.pop(0)
                    self.iterator = self.palette(self.current)
                result = next(self.iterator)
                if result is not None:
                    self.iterator = None
                    self.submit(self.current, result)
                    break  # At most one synchronous native mesh build per frame.
        except (ValueError, TypeError, RuntimeError, StopIteration):
            self.iterator = None
            self.failed(self.current)
        self.publish()
        b.next_frame(self.advance)
