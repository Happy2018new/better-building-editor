# -*- coding: utf-8 -*-
"""Bounded native preview tiles. Only edited tiles and their halo are rebuilt."""
from __future__ import unicode_literals
import time
from .large_preview import build_preview, MAX_SURFACE_BLOCKS
try:
    text_type = unicode
except NameError:
    text_type = str


def tile_edge(size):
    edge = 8
    volume = size[0]*size[1]*size[2]
    while True:
        count = ((size[0]+edge-1)//edge)*((size[1]+edge-1)//edge)*((size[2]+edge-1)//edge)
        # Each native mesh retains its declared palette volume, even when only
        # surface blocks are populated. Keep a common 3D origin for correct
        # depth, but bound declared cells per buffer bank as documents grow.
        if count <= 128 and (count == 1 or count*volume <= 32*1024*1024):
            return edge
        edge *= 2


def visibility_key(context, low, high):
    """Equal keys mean clipping cannot change any voxel in this tile."""
    unused_editor, hidden, solo, layer, detail, center, section, plane = context
    ys = tuple(y for y in range(low[1], high[1]) if y not in hidden and
               (not solo or y == layer) and (not section or y <= layer))
    if plane is None:
        depth = True
    else:
        normal, limit = plane
        near = sum((low[i]+.5 if normal[i] >= 0 else high[i]-.5)*normal[i] for i in range(3))
        far = sum((high[i]-.5 if normal[i] >= 0 else low[i]+.5)*normal[i] for i in range(3))
        depth = False if near > limit+1e-7 else True if far <= limit+1e-7 else plane
    return (detail, center, ys, depth)


class TiledPreview(object):
    def __init__(self, session):
        self.session = session
        self.context = None
        self.edge = 8
        self.parts = {}
        self.slots = ()
        self.dirty = set()
        self.versions = {}
        self.running = False
        self.iterator = None
        self.builds = 0
        self.seconds = 0.
        self.serial = 0

    def refresh(self, positions=None):
        s = self.session
        signature = s.preview_signature()
        context = signature[:1] + signature[2:]
        if context != self.context:
            previous = self.context
            self.context = context
            self.iterator = None
            self.serial += 1
            size = s.editor.document.size
            self.edge = tile_edge(size)
            # Preserve surfaces for filter changes; a different document has a
            # different origin/size and must never retain old coordinate frames.
            if s.model_revision is None or s.model_revision[0] != signature[0]:
                self.parts = {}
            keys = set((x, y, z) for x in range((size[0]+self.edge-1)//self.edge)
                       for y in range((size[1]+self.edge-1)//self.edge)
                       for z in range((size[2]+self.edge-1)//self.edge))
            if previous is None or previous[0] != context[0]:
                self.dirty = keys
                self.slots = tuple(sorted(keys))
                s.emit('preview')
            else:
                if hasattr(self, 'key'):
                    self.dirty.add(self.key)
                changed = set()
                for key in keys:
                    low = tuple(v*self.edge for v in key)
                    high = tuple(min(size[i], low[i]+self.edge) for i in range(3))
                    if visibility_key(previous, low, high) != visibility_key(context, low, high):
                        changed.add(key)
                for key in changed:
                    for offset in ((0,0,0), (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)):
                        neighbour = tuple(key[i]+offset[i] for i in range(3))
                        if neighbour in keys:
                            self.dirty.add(neighbour)
            focus = s.preview_center if s.preview_detail else None
            s.scene_size = size if focus is None else tuple(min(32, v) for v in size)
            s.scene_origin = (0, 0, 0) if focus is None else tuple(
                max(0, min(size[i]-s.scene_size[i], focus[i]-s.scene_size[i]//2)) for i in range(3))
            s.scene_scale = 1
        elif positions is None:
            if signature == s.model_revision and not self.dirty:
                return
            size = s.editor.document.size
            self.dirty.update((x, y, z) for x in range((size[0]+self.edge-1)//self.edge)
                              for y in range((size[1]+self.edge-1)//self.edge)
                              for z in range((size[2]+self.edge-1)//self.edge))
        else:
            for pos in positions:
                for offset in ((0,0,0), (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)):
                    point = tuple(pos[i]+offset[i] for i in range(3))
                    if s.editor.document.contains(point):
                        self.dirty.add(tuple(v//self.edge for v in point))
        for key in self.dirty:
            self.versions[key] = self.versions.get(key, 0)+1
        s.preview_pending = True
        if not self.running:
            self.running = True
            s.bridge.later(0., self.advance)

    def advance(self):
        s = self.session
        started = time.time()
        try:
            if self.iterator is None:
                available = [key for key in self.dirty if not self.parts.get(key, {}).get('pending')]
                if not available:
                    if self.dirty:
                        s.bridge.later(.016, self.advance)
                    else:
                        self.running = s.preview_pending = False
                        s.model_revision = s.preview_signature()
                        self.publish_visibility()
                        s.preview_error = ''
                        s.emit('preview_status')
                    return
                self.key = min(available)
                self.dirty.discard(self.key)
                self.version = self.versions[self.key]
                low = tuple(v*self.edge for v in self.key)
                high = tuple(v+self.edge for v in low)
                self.iterator = build_preview(s.editor.document, s.preview_hidden(),
                    s.editor.layer if s.solo_layer else None,
                    s.preview_center if s.preview_detail else None, s.depth_plane(), (low, high))
            result = None
            while time.time()-started < .003:
                result = next(self.iterator)
                if result is not None:
                    break
            if result is not None:
                self.iterator = None
                palette, unused_origin, unused_scale = result
                part = self.parts.get(self.key)
                data = palette.common
                if (part is None and data) or (part is not None and data != part['data']):
                    total = palette.count + sum(p.get('count', 0) for k,p in self.parts.items() if k != self.key)
                    if total > MAX_SURFACE_BLOCKS:
                        raise ValueError('可见方块过多，请使用单层或精细视图；草稿完整保留')
                    bank = 1-part['bank'] if part else 0
                    name = 'modern_projection_tile_%d_%d_%d_%d' % (self.key+(bank,))
                    model = s.bridge.geometry(palette, name=name)
                    # Two names per tile bound native mesh allocations during
                    # long editing sessions. Never overwrite a warming surface.
                    self.parts[self.key] = {'name': model, 'bank': bank, 'data': data, 'count': palette.count, 'pending': bool(model)}
                    self.builds += 1
                    self.publish_visibility()
                if self.versions.get(self.key) != self.version:
                    self.dirty.add(self.key)
            s.bridge.later(0., self.advance)
        except (ValueError, TypeError, RuntimeError, StopIteration) as error:
            self.iterator = None
            self.running = s.preview_pending = False
            s.preview_error = text_type(error)
            s.emit('preview')
        finally:
            self.seconds += time.time()-started

    def publish_visibility(self):
        s = self.session
        name = 'tiled_preview' if any(p['name'] for p in self.parts.values()) else None
        if name != s.model_name:
            s.model_name = name
            s.emit('preview_visible')
