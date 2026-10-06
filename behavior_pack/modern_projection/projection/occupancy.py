# -*- coding: utf-8 -*-
"""Budgeted client occupancy checks, batched double-buffered mesh updates."""
import math
import time
import traceback
from collections import deque
from .model import Document
from .large_preview import SurfacePalette
from .storage import Selection
from .packed import IntegerBuffer
from .occupancy_shader import OccupancyShader


POLL_INTERVAL = .1
POLL_BUDGET = .00075
POLL_LIMIT = 128
BUILD_BUDGET = .0015
MIN_REFRESH = .35
MAX_HINTS = 256
AIR_NAMES = ('minecraft:air', b'minecraft:air', 'minecraft:cave_air',
             b'minecraft:cave_air', 'minecraft:void_air', b'minecraft:void_air')
UNKNOWN_NAMES = ('minecraft:unknown', b'minecraft:unknown')


class ProjectionOccupancy(object):
    air_names, unknown_names = AIR_NAMES, UNKNOWN_NAMES

    def __init__(self, bridge, origin, document=None):
        self.bridge, self.serial, self.origin = bridge, bridge.projection_serial, origin
        source = document or bridge.session.editor.document
        self.document = Document(source.size, biome=source.biome)
        self.document.blocks = source.blocks.copy()
        self.size = tuple(source.size)
        self.hidden = set(bridge.session.preview_hidden())
        self.layer = bridge.session.editor.layer if bridge.session.solo_layer else None
        self.info = bridge.factory.CreateBlockInfo(bridge.level)
        self.camera = bridge.factory.CreateCamera(bridge.level)
        self.loaded_chunks = getattr(bridge.system, 'projection_loaded_chunks', None)
        self.dimension = (bridge.factory.CreateGame(bridge.level).GetCurrentDimension()
                          if self.loaded_chunks is not None else None)
        # Unknown cells remain visible until the client has loaded their chunk.
        self.state = bytearray(source.volume)
        self.rendered = bytearray(source.volume)
        self.changed = set()
        self.after_build = set()
        self.cache_dirty = set()
        self.cached = {}
        self.slots = IntegerBuffer('i', [-1]) * source.volume
        self.targets = Selection()
        self.hints, self.hint_queue = {}, deque()
        self.scan, self.near = None, None
        self.next_poll = self.next_near = self.next_build = 0.
        self.build = self.output = self.snapshot = None
        self.entity = self.model = None
        self.anchor = tuple(origin[i]+self.size[i]/2. for i in range(3))
        self.bank = 0
        self.attaching = self.failed = False
        self.pending_model = None
        self.preparing_entity = self.preparing_backdrop = None
        self.reads = self.builds = self.commits = 0
        self.last_poll_ms = self.max_poll_ms = self.last_build_ms = 0.
        self.last_prepare_ms = 0.
        self.resource_wait = .15
        self.shader = OccupancyShader(self)
        from .occupancy_scan import OccupancyScan
        self.bulk = OccupancyScan(self) if source.volume > 4096 else None
        self.bulk_job = None
        self.next_bulk = 0.

    def visible_layer(self, y):
        return y not in self.hidden and (self.layer is None or y == self.layer)

    def index(self, pos):
        return (pos[1] * self.size[0] + pos[0]) * self.size[2] + pos[2]

    def positions(self):
        # Built during initial preparation: no scans through hidden/empty layers.
        return iter(self.targets)

    def loaded(self, world):
        return (self.loaded_chunks is None or
                (self.dimension, world[0] >> 4, world[2] >> 4) in self.loaded_chunks)

    def read(self, pos, initial=False):
        x, y, z = pos
        ox, oy, oz = self.origin
        index = self.index(pos)
        if not self.loaded((ox+x, oy+y, oz+z)):
            return self.state[index] != 2
        state = self.bulk.initial_state(pos) if initial and self.bulk else 0
        if state:
            return self.observe(index, state, initial)
        actual = self.info.GetBlock((ox+x, oy+y, oz+z))
        self.reads += 1
        if not actual or actual[0] in UNKNOWN_NAMES:
            return self.state[index] != 2
        state = 1 if actual[0] in AIR_NAMES else 2
        if self.bulk is not None and state != self.state[index]:
            self.bulk.cache.pop((x >> 4, y >> 4, z >> 4), None)
        return self.observe(index, state, initial)

    def observe(self, index, state, initial=False):
        previous = self.state[index]
        self.state[index] = state
        if not initial:
            if (previous == 2) != (state == 2):
                self.cache_dirty.add(index)
            if (state == 2) != (self.rendered[index] == 2):
                self.changed.add(index)
            else:
                self.changed.discard(index)
            if self.snapshot is not None:
                if (state == 2) != (self.snapshot[index] == 2):
                    self.after_build.add(index)
                else:
                    self.after_build.discard(index)
        return state != 2

    def poll_bulk(self, now):
        if self.bulk is None or len(self.targets) < 1024:
            return
        if self.bulk_job is None:
            if now < self.next_bulk:
                return
            self.next_bulk = now + .05
            self.bulk_job = self.bulk.scan()
        deadline = time.time() + POLL_BUDGET
        for unused in range(256):
            if next(self.bulk_job, None) is None:
                self.bulk_job = None
                break
            if time.time() >= deadline:
                break

    def initial_visible(self, pos):
        if not self.visible_layer(pos[1]):
            return False
        self.targets.add(pos)
        visible = self.read(pos, True)
        if visible:
            self.cache_cell(self.index(pos), True)
        return visible

    def cache_cell(self, index, visible):
        slot = self.slots[index]
        if visible == (slot >= 0):
            return
        sx, sy, sz = self.size
        pos = (index // sz % sx, index // (sx*sz), index % sz)
        key = (pos[0] >> 4, pos[1] >> 4, pos[2] >> 4)
        value = self.document.blocks[pos]
        common = self.cached.setdefault(key, {})
        indices = common.setdefault(value, [])
        if visible:
            self.slots[index] = len(indices)
            indices.append(index)
        else:
            last = indices.pop()
            if slot < len(indices):
                indices[slot] = last
                self.slots[last] = slot
            self.slots[index] = -1


    def start(self, entity, model):
        self.entity, self.model = entity, model
        self.rendered = self.state[:]
        if self.bridge.projection_mesh:
            self.anchor = self.bridge.projection_mesh[3]
        if entity is not None and self.shader.render is None:
            self.shader.bind(entity, model, self.anchor, attached=True,
                             backdrop=self.bridge.projection_backdrop)
        self.bridge.projection_occupancy = self
        self.next_poll = time.time() + POLL_INTERVAL

    def active(self):
        return (self.bridge.alive and self.bridge.projection_occupancy is self and
                self.bridge.session.projection_active)

    def close(self):
        if self.preparing_entity is not None:
            self.bridge.system.DestroyClientEntity(self.preparing_entity)
        if self.preparing_backdrop is not None:
            self.preparing_backdrop.clear()
        self.preparing_entity = self.preparing_backdrop = None
        self.attaching = False
        self.pending_model = None

    def hint(self, world):
        # Client interaction is only a hint: retry after the world catches up.
        # Include adjacent cells for placement, doors and replaceable blocks.
        deadline = time.time() + .8
        ox, oy, oz = self.origin
        local = (world[0]-ox, world[1]-oy, world[2]-oz)
        for dx, dy, dz in ((0, 0, 0), (1, 0, 0), (-1, 0, 0),
                           (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            pos = (local[0]+dx, local[1]+dy, local[2]+dz)
            if pos not in self.targets:
                continue
            if pos not in self.hints:
                if len(self.hints) >= MAX_HINTS:
                    # Keep the far cursor: repeated input must not starve it.
                    break
                self.hint_queue.append(pos)
            self.hints[pos] = deadline

    def near_positions(self, centre):
        lo = tuple(max(0, centre[i]-5) for i in range(3))
        hi = tuple(min(self.size[i], centre[i]+6) for i in range(3))
        for y in range(lo[1], hi[1]):
            if not self.visible_layer(y):
                continue
            for x in range(lo[0], hi[0]):
                for z in range(lo[2], hi[2]):
                    pos = (x, y, z)
                    # Skipped cells yield too, so one next() cannot scan a region.
                    yield pos if pos in self.targets else False

    def poll(self, now):
        started = time.time()
        deadline = started + POLL_BUDGET
        if now >= self.next_near:
            camera = self.camera.GetPosition()
            centre = tuple(int(math.floor(camera[i]))-self.origin[i] for i in range(3))
            if centre != getattr(self, 'near_centre', None):
                self.near_centre, self.near = centre, None
            self.next_near = now + .5
        hints = min(24, len(self.hint_queue))
        hinted = 0
        for count in range(POLL_LIMIT):
            if count and count % 4 == 0 and time.time() >= deadline:
                break
            pos = None
            # Reserve the first and every fourth work unit for the full cursor.
            # Slow reads plus continuous input must not starve distant targets.
            if count % 4 and hinted < hints:
                hinted += 1
                pos = self.hint_queue.popleft()
                expiry = self.hints.pop(pos, 0.)
                if expiry > now:
                    self.hints[pos] = expiry
                    self.hint_queue.append(pos)
                self.read(pos)
                continue
            if count % 4:
                if self.near is None:
                    self.near = self.near_positions(self.near_centre)
                pos = next(self.near, None)
                if pos is None:
                    self.near = None
                elif pos is False:
                    continue
            if pos is None:
                if self.scan is None:
                    self.scan = self.positions()
                pos = next(self.scan, None)
                if pos is None:
                    self.scan = None
                    break
            self.read(pos)
        self.last_poll_ms = (time.time()-started)*1000.
        self.max_poll_ms = max(self.max_poll_ms, self.last_poll_ms)

    def prepare(self):
        # Update only cells changed since the last prepared palette. Lists
        # are partitioned into 16^3 chunks, with O(1) swap-delete by slot.
        dirty, self.cache_dirty = self.cache_dirty, set()
        for index in dirty:
            self.cache_cell(index, self.snapshot[index] != 2)
            yield True
        # Native Combine still consumes a whole palette, but assembling it
        # is bounded list.extend work, not a Python/document lookup per voxel.
        for common in self.cached.values():
            for value, indices in common.items():
                if indices:
                    self.output.common.setdefault(value, []).extend(indices)
                    self.output.count += len(indices)
            yield True

    def tick(self):
        if not self.active() or self.failed or not self.targets or self.bridge.preparing_entity:
            return
        pending = self.bridge.projection_work
        if pending is not None and not pending.ready and not pending.error:
            return
        now = time.time()
        try:
            self.poll_bulk(now)
            if now >= self.next_poll:
                self.next_poll = now + POLL_INTERVAL
                self.poll(now)
            if self.attaching:
                return
            if self.pending_model is not None:
                model, anchor, ready = self.pending_model
                if now < ready:
                    return
                self.pending_model = None
                self.replace(model, anchor)
                return
            if self.build is None:
                if not self.changed or now < self.next_build:
                    return
                self.snapshot = self.state[:]
                self.after_build.clear()
                self.output = SurfacePalette(self.size)
                self.build = self.prepare()
                self.build_started = now
            deadline = time.time() + BUILD_BUDGET
            while time.time() < deadline:
                if next(self.build, None) is None:
                    self.build = None
                    self.last_prepare_ms = (time.time()-self.build_started)*1000.
                    self.submit()
                    return
        except (ValueError, TypeError, KeyError, RuntimeError) as error:
            traceback.print_exc()
            self.close()
            self.failed = True
            self.build = self.output = self.snapshot = None
            self.bridge.session.editor.message = u'投影自动更新失败，请点击更新投影：%s' % error
            self.bridge.session.emit()

    def submit(self):
        # A short place/remove burst can cancel out while preparing.
        if not self.changed:
            self.output = self.snapshot = None
            self.after_build.clear()
            return
        self.bank = 1-self.shader.bank if self.entity is not None else 0
        name = self.shader.names[self.bank]
        started = time.time()
        model = self.bridge.geometry(self.output, name=name) if self.output.count else None
        self.last_build_ms = (time.time()-started)*1000.
        # Combine returning a name is not a render-thread completion fence.
        # Full-volume captures measured >0.5s of deferred generation, despite
        # a 6ms SDK call. Keep the old buffer throughout size-scaled warmup.
        self.resource_wait = max(.15, len(self.state)/419430.4,
                                 self.last_build_ms*.04) if model else 0.
        if self.output.count and not model:
            raise ValueError('Could not generate occupancy projection')
        self.builds += 1
        self.output = None
        if self.entity is None and model is not None:
            self.bridge.ensure_projection_distance(self.size)
            anchor = tuple(self.origin[i]+self.size[i]/2. for i in range(3))
            from .projection_backdrop import create_projection_actors
            entity, backdrop = create_projection_actors(self.bridge, self.origin, anchor)
            self.preparing_entity, self.preparing_backdrop = entity, backdrop
            self.attaching = True
            def attach():
                if self.active() and self.preparing_entity == entity:
                    self.attaching = False
                    # The render tick serializes this with manual regeneration.
                    self.pending_model = (model, anchor, 0.)
                elif self.preparing_entity == entity:
                    self.close()
            self.bridge.later(max(.2, self.resource_wait), attach)
            return
        mesh = self.bridge.projection_mesh
        anchor = mesh[3] if mesh else self.anchor
        # Let the inactive native resource reach the render thread before the
        # shader selector switches. The current geometry remains attached.
        self.pending_model = (model, anchor, time.time()+self.resource_wait)

    def replace(self, model, anchor):
        b = self.bridge
        if self.shader.render is None and model is not None:
            b.factory.CreateModel(self.preparing_entity).SetEntityShadowShow(False)
            self.shader.bind(self.preparing_entity, model, anchor,
                             backdrop=self.preparing_backdrop)
        self.shader.commit(model)
        if self.preparing_entity is not None:
            self.entity = b.entity = self.preparing_entity
            b.projection_backdrop = self.preparing_backdrop
            self.preparing_entity = self.preparing_backdrop = None
        self.model = model
        self.anchor = anchor
        # Keep the transform alive even when every cell is hidden by the shader.
        b.projection_mesh = (self.entity, model or self.shader.names[self.shader.bank],
                             self.origin, anchor) if self.entity else None
        b._projection_follow_position = None
        self.rendered = self.snapshot
        self.snapshot = None
        # Reads already maintain the exact delta against the in-flight snapshot.
        # Transfer it instead of rescanning a potentially large dirty set here.
        self.changed, self.after_build = self.after_build, set()
        self.commits += 1
        # Native Combine is synchronous: keep its duty cycle bounded as size grows.
        self.next_build = time.time() + max(MIN_REFRESH, self.last_build_ms*.008)
