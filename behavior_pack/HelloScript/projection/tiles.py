# -*- coding: utf-8 -*-
"""Bounded local palettes, independent uploads and retained meshes per 16-cube."""
from __future__ import unicode_literals
import time
from .large_preview import build_preview, MAX_SURFACE_BLOCKS
from .chunks import EDGE, tile_bounds, keys_in
try:
    text_type = unicode
except NameError:
    text_type = str


def tile_edge(size):
    return EDGE


class TiledPreview(object):
    def __init__(self, session):
        self.session = session
        self.context = None
        self.edge = EDGE
        self.parts = {}
        self.slots = ()
        self.pool_size = 1
        self.generation = 0
        self.dirty = set()
        self.versions = {}
        self.running = False
        self.iterator = None
        self.builds = 0
        self.seconds = 0.
        self.total = 0
        self.done = 0
        self.published = 0.
        self.report_progress = False

    def refresh(self, positions=None):
        s = self.session
        signature = s.preview_signature()
        context = signature[:1] + signature[2:]
        changed_context = context != self.context
        if changed_context:
            previous = self.context
            previous_slots = self.slots
            self.context = context
            self.iterator = None
            self.dirty.clear()
            if previous is None or previous[0] != context[0]:
                self.parts = {}
                self.generation = 1-self.generation
            origin, size = (0, 0, 0), s.editor.document.size
            s.scene_origin, s.scene_size, s.scene_scale = origin, size, 1
            self.slots = keys_in(origin, size)
            self.pool_size = max(self.pool_size, len(self.slots))
            self.dirty.update(k for k in self.slots if self.parts.get(k, {}).get('signature') != signature)
            # A hidden chunk no longer owns a warming renderer. A later visit
            # mounts its retained model into a new pair before further edits.
            for key, part in self.parts.items():
                if key not in self.slots:
                    part['pending'] = False
                elif key not in previous_slots:
                    part['pending'] = bool(part['name'])
            self.publish_visible()
            s.emit('preview')
        elif positions is not None:
            changed = set()
            for pos in positions:
                for offset in ((0,0,0), (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)):
                    point = tuple(pos[i]+offset[i] for i in range(3))
                    if s.editor.document.contains(point):
                        changed.add(tuple(v//EDGE for v in point))
            self.dirty.update(changed.intersection(self.slots))
        elif signature != s.model_revision:
            changed = getattr(s.editor, 'last_changed_chunks', set(self.slots))
            for key in changed:
                for offset in ((0,0,0), (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)):
                    neighbour = tuple(key[i]+offset[i] for i in range(3))
                    if neighbour in self.slots:
                        self.dirty.add(neighbour)
        waiting = sum(bool(self.parts[k]['pending']) for k in self.slots if k in self.parts)
        if not self.dirty and not self.running and not waiting:
            s.model_revision = signature
            return
        for key in self.dirty:
            self.versions[key] = self.versions.get(key, 0)+1
        was_reporting = self.report_progress
        # Point edits can accumulate dirty neighbours during a burst. They must
        # never raise a modal-sized progress surface over the next click.
        report = positions is None and (len(self.dirty) > 8 or (changed_context and len(self.slots) > 1))
        if not s.preview_pending:
            self.total, self.done = max(len(self.dirty), waiting), 0
        else:
            self.total = max(self.total, self.done+len(self.dirty))
        self.report_progress = report if changed_context or not s.preview_pending else self.report_progress or report
        s.preview_pending = True
        s.preview_error = ''
        if self.report_progress or was_reporting:
            s.emit('preview_status')
        if not self.running:
            self.running = True
            s.bridge.later(.016, self.advance)

    def publish_visible(self):
        s = self.session
        name = next((self.parts[k]['name'] for k in self.slots
                     if k in self.parts and self.parts[k]['name']), None)
        changed = bool(name) != bool(s.model_name)
        s.model_name = name
        if changed:
            s.emit('preview_visible')

    def progress(self):
        waiting = sum(bool(self.parts[k]['pending']) for k in self.slots if k in self.parts)
        remaining = len(self.dirty) + int(self.iterator is not None) + waiting
        total = max(1, self.total, self.done+len(self.dirty))
        return max(0, total-min(total, remaining)), total

    def advance(self):
        s = self.session
        started = time.time()
        try:
            if self.iterator is None:
                available = [k for k in self.dirty if not self.parts.get(k, {}).get('pending')]
                if not available:
                    if self.dirty or any(self.parts[k]['pending'] for k in self.slots if k in self.parts):
                        s.bridge.later(.016, self.advance)
                        return
                    self.running = s.preview_pending = False
                    s.model_revision = s.preview_signature()
                    if self.report_progress:
                        self.report_progress = False
                        s.emit('preview_status')
                    return
                self.key = min(available)
                self.dirty.remove(self.key)
                self.version = self.versions[self.key]
                low, size = tile_bounds(s.editor.document.size, self.key)
                high = tuple(low[i]+size[i] for i in range(3))
                self.iterator = build_preview(s.editor.document, s.preview_hidden(),
                    s.editor.layer if s.solo_layer else None,
                    None, s.depth_plane(), (low, high), True)
            result = None
            while time.time()-started < .003:
                result = next(self.iterator)
                if result is not None:
                    break
            if result is not None:
                self.iterator = None
                if self.versions.get(self.key) != self.version:
                    self.dirty.add(self.key)
                else:
                    self.submit(self.key, result[0], result[1])
                    self.done += 1
            if self.report_progress and time.time()-self.published > .1:
                self.published = time.time()
                s.emit('preview_status')
            # At most one <=4096-cell native upload per timer/render opportunity.
            s.bridge.later(.016, self.advance)
        except (ValueError, TypeError, RuntimeError, StopIteration) as error:
            self.iterator = None
            self.running = s.preview_pending = False
            s.preview_error = text_type(error)
            s.emit('preview')
        finally:
            self.seconds += time.time()-started

    def submit(self, key, palette, origin):
        part = self.parts.get(key)
        if part is not None and palette.common == part['data']:
            part['signature'] = self.session.preview_signature()
            return
        total = palette.count + sum(p['count'] for k,p in self.parts.items() if k != key and k in self.slots)
        if total > MAX_SURFACE_BLOCKS:
            raise ValueError('可见方块过多，请使用切面或单层；草稿完整保留')
        bank = 1-part['bank'] if part else 0
        cache = part['cache'] if part else {}
        reused = next((slot for slot, entry in cache.items() if entry[0] == palette.common), None)
        if reused is not None:
            bank, name = reused, cache[reused][1]
        else:
            name = self.session.bridge.geometry(palette, name='modern_projection_chunk_%d_%d_%d_%d_%d' % ((self.generation,)+key+(bank,)))
            cache[bank] = (palette.common, name)
            self.builds += 1
        self.parts[key] = {'data': palette.common, 'count': palette.count, 'origin': origin,
                           'size': palette.size, 'name': name, 'bank': bank, 'cache': cache,
                           'pending': bool(name), 'version': self.version,
                           'signature': self.session.preview_signature()}
        self.publish_visible()
