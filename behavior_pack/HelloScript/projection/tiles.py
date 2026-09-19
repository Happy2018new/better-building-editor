# -*- coding: utf-8 -*-
"""Incremental surface extraction with one coherent native depth buffer."""
from __future__ import unicode_literals
import time
from .large_preview import build_preview, MAX_SURFACE_BLOCKS, SurfacePalette
try:
    text_type = unicode
except NameError:
    text_type = str


def tile_edge(size):
    edge = 8
    while True:
        count = ((size[0]+edge-1)//edge)*((size[1]+edge-1)//edge)*((size[2]+edge-1)//edge)
        if count <= 128:
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
        self.slots = ((0, 0, 0),)
        self.surface = None
        self.upload_dirty = False
        self.next_submit = 0.
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
                self.surface = None
                self.upload_dirty = True
            keys = set((x, y, z) for x in range((size[0]+self.edge-1)//self.edge)
                       for y in range((size[1]+self.edge-1)//self.edge)
                       for z in range((size[2]+self.edge-1)//self.edge))
            if previous is None or previous[0] != context[0]:
                self.dirty = keys
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
                if not self.dirty:
                    if self.surface and self.surface['pending']:
                        s.bridge.later(.016, self.advance)
                        return
                    if self.upload_dirty:
                        if time.time() < self.next_submit:
                            s.bridge.later(.016, self.advance)
                            return
                        self.submit_surface()
                        s.bridge.later(.016, self.advance)
                        return
                    self.running = s.preview_pending = False
                    s.model_revision = s.preview_signature()
                    s.preview_error = ''
                    s.emit('preview_status')
                    return
                self.key = min(self.dirty)
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
                    self.parts[self.key] = {'data': data, 'count': palette.count, 'version': self.version}
                    self.upload_dirty = True
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

    def submit_surface(self):
        # Separate PaperDolls do not sort translucent faces across renderers.
        # Keep incremental CPU extraction, then submit one complete palette so
        # opaque walls and glass share the engine's native depth ordering.
        s = self.session
        palette = SurfacePalette(s.scene_size)
        for key in sorted(self.parts):
            part = self.parts[key]
            palette.count += part['count']
            for material, indices in part['data'].items():
                palette.common.setdefault(material, []).extend(indices)
        self.upload_dirty = False
        if self.surface is not None and palette.common == self.surface['data']:
            return
        bank = 1-self.surface['bank'] if self.surface else 0
        name = s.bridge.geometry(palette, name='modern_projection_surface_%d' % bank)
        self.surface = {'name': name, 'bank': bank, 'data': palette.common,
                        'count': palette.count, 'pending': bool(name)}
        self.builds += 1
        self.next_submit = time.time() + .08
        if bool(name) != bool(s.model_name):
            s.model_name = name
            s.emit('preview_visible')
        else:
            s.model_name = name
