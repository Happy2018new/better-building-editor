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
        self.document_size = None
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
        self.publication = 0
        self.report_progress = False
        self.extractions = 0
        self.render_keys = ()
        self.last_render = 0.
        self.renderer_active = False
        self.serial = 0
        self.point_defer_started = 0.
        self.point_defer_until = 0.

    def cancel(self):
        self.serial += 1
        self.point_defer_started = self.point_defer_until = 0.
        self.iterator = None
        self.dirty.clear()
        self.running = self.session.preview_pending = False
        self.report_progress = False
        self.session.preview_error = '已取消更新，可重试'
        self.session.emit('preview')

    def retry(self):
        self.cancel()
        self.dirty.update(self.slots)
        for part in self.parts.values():
            part['pending'] = False
        self.refresh()

    def schedule(self):
        serial = self.serial
        def advance():
            if serial == self.serial and self.running:
                self.advance()
        self.session.next_frame(advance)

    def source_state(self, key):
        store = self.session.editor.document.blocks
        neighbours = [tuple(key[i]+offset[i] for i in range(3)) for offset in
                      ((0,0,0),(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))]
        # Retained arrays become snapshots: later writes copy them. This makes
        # undo/repeated neighbours comparable without rebuilding their surfaces.
        for neighbour in neighbours:
            store.compact(neighbour)
            store.owned.discard(neighbour)
        # Snapshot undo can restore an older palette; a later branch may reuse
        # the same numeric material id for a different block.
        # The editor identity changes on reload; equal content and visibility
        # still describe exactly the same mesh, including its boundary halo.
        context = (self.session.editor.document.size,) + self.context[1:]
        return (context, tuple(store.palette), tuple(store.chunks.get(k, 0) for k in neighbours))

    def restore_cached(self, key, source):
        part = self.parts.get(key)
        if part is None:
            return False
        if part.get('source') == source:
            part['signature'] = self.session.preview_signature()
            return True
        for bank, entry in part['cache'].items():
            if source not in entry[2]:
                continue
            part.update(data=entry[0], name=entry[1], source=source, bank=bank,
                        count=sum(len(v) for v in entry[0].values()), pending=bool(entry[1]),
                        pending_at=time.time(),
                        signature=self.session.preview_signature())
            self.publish_visible()
            return True
        return False

    def refresh(self, positions=None):
        s = self.session
        signature = s.preview_signature()
        context = signature[:1] + signature[2:]
        changed_context = context != self.context
        if positions is None and not changed_context and signature != s.model_revision:
            positions = getattr(s.editor, 'last_changed_positions', None)
        if changed_context:
            self.point_defer_started = self.point_defer_until = 0.
            previous_slots = self.slots
            self.context = context
            self.iterator = None
            self.dirty.clear()
            if self.document_size != s.editor.document.size:
                self.parts = {}
                self.render_keys = tuple(sorted(s.editor.document.blocks.chunks))
                self.generation = 1-self.generation
                self.document_size = s.editor.document.size
            origin, size = (0, 0, 0), s.editor.document.size
            s.scene_origin, s.scene_size, s.scene_scale = origin, size, 1
            self.slots = keys_in(origin, size)
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
            if s.touch_mode and hasattr(s.bridge, 'next_frame'):
                now = time.time()
                if not self.point_defer_started:
                    self.point_defer_started = now
                self.point_defer_until = min(now + .1, self.point_defer_started + .25)
            changed = set()
            for pos in positions:
                for offset in ((0,0,0), (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)):
                    point = tuple(pos[i]+offset[i] for i in range(3))
                    if s.editor.document.contains(point):
                        changed.add(tuple(v//EDGE for v in point))
            self.dirty.update(changed.intersection(self.slots))
        elif signature != s.model_revision:
            self.point_defer_started = self.point_defer_until = 0.
            changed = getattr(s.editor, 'last_changed_chunks', set(self.slots))
            for key in changed:
                for offset in ((0,0,0), (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)):
                    neighbour = tuple(key[i]+offset[i] for i in range(3))
                    if neighbour in self.slots:
                        self.dirty.add(neighbour)
        keys = tuple(sorted(set(self.render_keys).union(s.editor.document.blocks.chunks)))
        if keys != self.render_keys:
            self.render_keys = keys
            s.emit('preview')
        self.pool_size = len(self.render_keys)
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
            self.started = time.time()
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
            self.schedule()

    def publish_visible(self):
        self.publication += 1
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
        uploads = 0
        try:
            # Keep native model replacement and extraction out of held gestures.
            # The authoritative document already contains every completed click.
            if s.camera_dragging:
                s.bridge.later(.03, self.schedule)
                return
            if self.point_defer_until > started:
                s.bridge.later(self.point_defer_until - started, self.schedule)
                return
            self.point_defer_started = self.point_defer_until = 0.
            while time.time()-started < .003:
                if self.iterator is None:
                    if not self.renderer_active or time.time()-self.last_render > .5:
                        for part in self.parts.values():
                            part['pending'] = False
                    available = [k for k in self.dirty if not self.parts.get(k, {}).get('pending')]
                    if not available:
                        if not self.dirty:
                            self.running = s.preview_pending = False
                            s.performance['previewWall'] = time.time()-self.started
                            s.model_revision = s.preview_signature()
                            if self.report_progress:
                                self.report_progress = False
                                s.emit('preview_status')
                            return
                        if not s.camera_dragging and any(time.time()-self.parts[k].get('pending_at', time.time()) > 8. for k in self.dirty):
                            raise RuntimeError('预览显示未完成，请重试')
                        break
                    self.key = min(available)
                    self.dirty.remove(self.key)
                    self.version = self.versions[self.key]
                    self.source = self.source_state(self.key)
                    if self.restore_cached(self.key, self.source):
                        self.done += 1
                        continue
                    low, size = tile_bounds(s.editor.document.size, self.key)
                    high = tuple(low[i]+size[i] for i in range(3))
                    self.iterator = build_preview(s.editor.document, s.preview_hidden(),
                        s.editor.layer if s.solo_layer else None,
                        None, None, (low, high), True)
                    self.extractions += 1
                result = next(self.iterator)
                if result is None:
                    continue
                self.iterator = None
                if self.versions.get(self.key) != self.version:
                    self.dirty.add(self.key)
                    continue
                builds = self.builds
                self.submit(self.key, result[0], result[1])
                self.done += 1
                if self.builds != builds:
                    uploads += 1
                    if uploads >= 2:
                        break
            if self.report_progress and time.time()-self.published > .1:
                self.published = time.time()
                s.emit('preview_status')
            # At most two small uploads, still within the shared 3 ms budget.
            self.schedule()
        except Exception as error:
            self.iterator = None
            self.running = s.preview_pending = False
            s.preview_error = text_type(error) or '预览构建失败，请重试'
            s.emit('preview')
        finally:
            self.seconds += time.time()-started

    def submit(self, key, palette, origin):
        part = self.parts.get(key)
        if part is not None and palette.common == part['data']:
            part['signature'] = self.session.preview_signature()
            part['source'] = self.source
            sources = part['cache'][part['bank']][2]
            part['cache'][part['bank']] = (part['data'], part['name'], (sources+(self.source,))[-2:])
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
            name = None
            if palette.common:
                name = self.session.bridge.geometry(palette, name='modern_projection_chunk_%d_%d_%d_%d_%d' % ((self.generation,)+key+(bank,)))
                self.builds += 1
        cache[bank] = (palette.common, name, (self.source,))
        self.parts[key] = {'data': palette.common, 'count': palette.count, 'origin': origin,
                           'size': palette.size, 'name': name, 'bank': bank, 'cache': cache,
                           'pending': bool(name), 'version': self.version, 'source': self.source,
                           'pending_at': time.time(),
                           'signature': self.session.preview_signature()}
        self.publish_visible()
