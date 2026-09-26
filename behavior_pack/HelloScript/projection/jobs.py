# -*- coding: utf-8 -*-
"""Atomic, cancellable editor jobs. No engine calls and no 25M-cell dictionaries."""
from __future__ import unicode_literals
import copy
import math
import random
import time
from collections import deque
from .model import AIR, BY_ID, DIRECTIONS, add, bounds, box_points
from .storage import Selection, FULL, CELLS, integer_types, indices, position


class SnapshotDelta(object):
    def __init__(self, before, after, count):
        self.stores = (before.copy(), after.copy())
        self.count = count
        self.changed_chunks = set(k for k in set(before.chunks) | set(after.chunks)
                                  if before.chunks.get(k, 0) != after.chunks.get(k, 0))

    def __len__(self):
        return self.count

    def memory_bytes(self):
        return sum(s.memory_bytes() for s in self.stores)


def difference_count(chunk, identity):
    return (0 if chunk == identity else CELLS) if isinstance(chunk, integer_types) else sum(v != identity for v in chunk)


class EditJob(object):
    def __init__(self, editor, tool):
        if tool not in BY_ID:
            raise ValueError('未知工具')
        self.editor, self.tool = editor, tool
        self.source = editor.document
        self.selection = editor.selection.copy() if isinstance(editor.selection, Selection) else Selection(editor.selection)
        self.work = copy.copy(editor)
        self.work.locked_layers = set(editor.locked_layers)
        self.work.hidden_layers = set(editor.hidden_layers)
        self.work.selection = self.selection
        self.staged = self.source.blocks.copy()
        self.result_selection = None
        self.result_clipboard = None
        self.changed = self.processed = 0
        self.total = max(1, len(self.selection))
        self.done = self.cancelled = False
        self.error = ''
        self.iterator = self._run()

    def cancel(self):
        self.cancelled = True

    def step(self, budget=2048, seconds=.006):
        if self.done:
            return
        deadline = time.time() + seconds
        try:
            for index in range(budget):
                if self.cancelled:
                    self.done = True
                    self.editor.message = '操作已取消，草稿未改变'
                    return
                next(self.iterator)
                if time.time() >= deadline:
                    return
        except StopIteration:
            self._publish()
            self.done = True
        except (ValueError, TypeError, KeyError) as error:
            self.error = str(error)
            self.done = True

    def _publish(self):
        e = self.editor
        if self.result_selection is not None:
            e.selection = self.result_selection
            e.selection_revision += 1
            e.sync_selection_bounds()
        if self.result_clipboard is not None:
            e.clipboard = self.result_clipboard
        if self.changed:
            delta = SnapshotDelta(self.source.blocks, self.staged, self.changed)
            self.source.blocks = self.staged
            e.last_changed_positions = None
            e.last_changed_chunks = delta.changed_chunks
            e.revision += 1
            e._remember(BY_ID[self.tool][2], delta)
        e.message = ('已选择 %d 格' % len(e.selection) if BY_ID[self.tool][1] == 'select' else
                     '已复制 %d 格' % len(self.selection) if self.tool == 'copy' else
                     '%s，已修改 %d 格' % (BY_ID[self.tool][2], self.changed))

    def _set(self, pos, value, respect=True):
        if not self.source.contains(pos):
            raise ValueError('操作超出建筑范围，草稿未改变')
        if not self.work._writable(pos, respect):
            return
        if pos[1] in self.work.locked_layers:
            return
        original, previous = self.source.get(pos), self.staged.get(pos, AIR)
        self.changed += int(value != original) - int(previous != original)
        self.staged[pos] = value

    def _chunk(self, key, value):
        identity = self.staged.palette_id(value)
        # Source ids are a prefix of the staged palette.
        original = self.source.blocks.chunks.get(key, 0)
        previous = self.staged.chunks.get(key, 0)
        if isinstance(previous, integer_types):
            before = difference_count(original, previous)
        elif isinstance(original, integer_types):
            before = difference_count(previous, original)
        else:
            before = sum(a != b for a, b in zip(original, previous))
        self.changed += difference_count(original, identity) - before
        self.staged.fill_chunk(key, value)

    def _fill_selected_chunk(self, key, mask, value):
        """For disjoint fill/shape chunks; source cells are visited only once."""
        self.processed += CELLS if mask == FULL else bin(mask).count('1')
        for y in self.work.locked_layers:
            local_y = y-(key[1] << 4)
            if 0 <= local_y < 16:
                mask &= ~(((1 << 256)-1) << (local_y << 8))
        mode = self.work.mask
        allowed = None
        if mode != 'all':
            palette = self.staged.palette
            allowed = [entry != AIR if mode == 'solid' else entry == AIR if mode == 'air' else
                       entry == self.work.filter_material for entry in palette]
        self.changed += self.staged.fill_mask(key, mask, value, allowed)

    def _select(self):
        tool, doc = self.tool, self.source
        universe = Selection.box((0, 0, 0), tuple(v - 1 for v in doc.size))
        if tool == 'select_all':
            self.result_selection = universe
        elif tool == 'select_box':
            if not doc.contains(self.work.start) or not doc.contains(self.work.end):
                raise ValueError('选区起终点必须位于建筑范围内')
            self.result_selection = Selection.box(*bounds((self.work.start, self.work.end)))
        elif tool == 'select_layer':
            self.result_selection = Selection.box((0, self.work.layer, 0), (doc.size[0] - 1, self.work.layer, doc.size[2] - 1))
        elif tool == 'select_invert':
            self.result_selection = universe.difference(self.selection)
        else:
            result = Selection()
            if tool in ('select_expand', 'select_contract'):
                for pos in self.selection:
                    if tool == 'select_expand':
                        result.add(pos)
                        for direction in DIRECTIONS:
                            target = add(pos, direction)
                            if doc.contains(target):
                                result.add(target)
                    elif all(add(pos, d) in self.selection for d in DIRECTIONS):
                        result.add(pos)
                    self.processed += 1
                    yield None
            else:
                for key, mask in universe.chunks.items():
                    chunk = doc.blocks.chunks.get(key, 0)
                    if isinstance(chunk, integer_types) and tool != 'select_surface':
                        value = doc.blocks.palette[chunk]
                        selected = (bool(chunk) if tool == 'select_nonair' else
                                    not chunk if tool == 'select_air' else value == self.work.source)
                        if selected:
                            result.chunks[key] = mask
                            result.count += bin(mask).count('1')
                        self.processed += bin(mask).count('1')
                        yield None
                        continue
                    for index in indices(mask):
                        pos = position(key, index)
                        value = doc.get(pos)
                        selected = (value != AIR if tool == 'select_nonair' else value == AIR if tool == 'select_air' else
                                    self.work.surface(pos) if tool == 'select_surface' else value == self.work.source)
                        if selected:
                            result.add(pos)
                        self.processed += 1
                        yield None
            self.result_selection = result

    def _target(self, pos, lo, ext):
        q = [pos[i] - lo[i] for i in range(3)]
        tool = self.tool
        if tool.startswith('rotate_y'):
            width, depth = ext[0], ext[2]
            for unused in range(int(tool[8:]) // 90):
                q[0], q[2] = depth - 1 - q[2], q[0]
                width, depth = depth, width
        elif tool.startswith('mirror_'):
            axis = 'xyz'.index(tool[-1])
            q[axis] = ext[axis] - 1 - q[axis]
        elif tool.startswith('move_'):
            q['xyz'.index(tool[-2])] += self.work.step * (1 if tool[-1] == 'p' else -1)
        elif tool.startswith('stack_'):
            q['xyz'.index(tool[-1])] += ext['xyz'.index(tool[-1])]
        return tuple(q[i] + lo[i] for i in range(3))

    def _transform(self, lo, hi):
        ext = tuple(hi[i] - lo[i] + 1 for i in range(3))
        corners = [self._target((x, y, z), lo, ext) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        if any(not self.source.contains(p) for p in corners):
            raise ValueError('变换将超出建筑范围，操作已取消')
        target_lo, target_hi = bounds(corners)
        if self.work.mask != 'all' or any(lo[1] <= y <= hi[1] or target_lo[1] <= y <= target_hi[1] for y in self.work.locked_layers):
            raise ValueError('整体变换前请关闭蒙版并解锁相关图层')
        neutral = ('stone', 'stonebrick', 'planks', 'quartz_block', 'concrete', 'wool', 'glass', 'stained_glass',
                   'leaves', 'grass', 'sea_lantern', 'brick_block', 'sandstone', 'air', 'dirt', 'cobblestone')
        def validate(value):
            if self.tool.startswith(('rotate', 'mirror')) and (value[0].split(':')[-1] not in neutral or
                    (value[0] == 'minecraft:quartz_block' and value[1] > 1)):
                raise ValueError('此选区含方向性或未知方块；请先替换为普通建材')
        compact = (all(mask == FULL and isinstance(self.source.blocks.chunks.get(key, 0), integer_types)
                       for key, mask in self.selection.chunks.items()) and
                   all(v % 16 == 0 for v in lo + ext + target_lo))
        if compact:
            mapped = []
            result = Selection()
            for key in self.selection.chunks:
                value = self.source.blocks.palette[self.source.blocks.chunks.get(key, 0)]
                validate(value)
                a = position(key, 0); b = position(key, CELLS - 1)
                target = bounds([self._target((x, y, z), lo, ext) for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])])[0]
                new_key = tuple(v >> 4 for v in target)
                mapped.append((new_key, value))
                result.chunks[new_key] = FULL
                result.count += CELLS
                if not self.tool.startswith('stack_'):
                    self._chunk(key, AIR)
                yield None
            for key, value in mapped:
                self._chunk(key, value)
                self.processed += CELLS
                yield None
            self.result_selection = result
            return
        if not self.tool.startswith('stack_'):
            for pos in self.selection:
                self._set(pos, AIR, False)
                yield None
        result = Selection()
        for pos in self.selection:
            value = self.source.get(pos)
            validate(value)
            target = self._target(pos, lo, ext)
            self._set(target, value, False)
            result.add(target)
            self.processed += 1
            yield None
        self.result_selection = result

    def _sphere_shell(self, lo, hi):
        """Visit the ellipsoid's outer and inner X bands, not its empty core."""
        size = [hi[i] - lo[i] + 1 for i in range(3)]
        center = [(hi[i] + lo[i]) / 2. for i in range(3)]
        radius = [max(.5, value / 2.) for value in size]
        inner = [max(.01, value - max(1, self.work.thickness)) for value in radius]
        width = size[0]
        for y in range(lo[1], hi[1] + 1):
            ny = (y - center[1]) / radius[1]
            iy = (y - center[1]) / inner[1]
            for z in range(lo[2], hi[2] + 1):
                nz = (z - center[2]) / radius[2]
                iz = (z - center[2]) / inner[2]
                outer_rest = 1. - ny * ny - nz * nz
                if outer_rest >= -1e-12:
                    reach = radius[0] * math.sqrt(max(0., outer_rest))
                    first = max(lo[0], int(math.ceil(center[0] - reach - 1e-8)))
                    last = min(hi[0], int(math.floor(center[0] + reach + 1e-8)))
                    inner_rest = 1. - iy * iy - iz * iz
                    if inner_rest > 0.:
                        gap = inner[0] * math.sqrt(inner_rest)
                        left = min(last, int(math.floor(center[0] - gap + 1e-8)) + 1)
                        right = max(first, int(math.ceil(center[0] + gap - 1e-8)) - 1)
                    else:
                        left, right = last, last + 1
                    for start, stop in ((first, left + 1), (max(left + 1, right), last + 1)):
                        for x in range(start, stop):
                            # Match Editor._shape exactly at fractional boundaries.
                            outer = sum(v * v for v in ((x-center[0])/radius[0], ny, nz))
                            inside = sum(v * v for v in ((x-center[0])/inner[0], iy, iz))
                            if outer <= 1. and inside >= 1.:
                                self._set((x, y, z), self.work.material)
                self.processed += width
                yield None

    def _run(self):
        tool, work = self.tool, self.work
        group = BY_ID[tool][1]
        if group == 'select':
            for step in self._select():
                yield step
            return
        if tool.startswith('paste'):
            from .pasting import paste_bounds, paste_error
            clip = work.clipboard
            error = paste_error(self.source, clip, work.start)
            if error:
                raise ValueError(error)
            points = clip.get('selection', clip['blocks'])
            origin = clip.get('origin', (0, 0, 0))
            self.total = max(1, len(points))
            for pos in points:
                value = clip['blocks'].get(pos, AIR)
                if tool == 'paste' or value != AIR:
                    target = tuple(pos[i]-origin[i]+work.start[i] for i in range(3))
                    self._set(target, value, False)
                self.processed += 1
                yield None
            self.result_selection = Selection.box(*paste_bounds(clip, work.start))
            return
        if not self.selection:
            raise ValueError('选区为空，请先框选或全选')
        lo, hi = self.selection.bounds()
        if not self.source.contains(lo) or not self.source.contains(hi):
            raise ValueError('操作超出建筑范围，草稿未改变')
        if group == 'transform':
            for step in self._transform(lo, hi):
                yield step
            return
        if tool in ('copy', 'cut'):
            # Keep original coordinates plus an origin; membership records which
            # air cells belong to an irregular selection without materializing them.
            self.result_clipboard = {'size': tuple(hi[i] - lo[i] + 1 for i in range(3)),
                'blocks': self.source.blocks.copy(), 'origin': lo, 'selection': self.selection.copy()}
            if tool == 'copy':
                return
            tool = 'erase'
        if tool == 'flood':
            if work.start not in self.selection:
                raise ValueError('填充起点不在选区内')
            old = self.source.get(work.start)
            seen, pending = Selection([work.start]), deque([work.start])
            while pending:
                pos = pending.popleft()
                if work._writable(pos) and self.source.get(pos) == old:
                    self._set(pos, work.material)
                    for direction in DIRECTIONS:
                        target = add(pos, direction)
                        if target in self.selection and target not in seen:
                            seen.add(target)
                            pending.append(target)
                self.processed += 1
                yield None
            return
        if tool in ('gravity', 'foundation', 'heightmap'):
            for x in range(lo[0], hi[0] + 1):
                for z in range(lo[2], hi[2] + 1):
                    changes = work._finish(tool, (x, lo[1], z), (x, hi[1], z))
                    for pos, value in changes.items():
                        self._set(pos, value)
                    self.processed += hi[1] - lo[1] + 1
                    yield None
            return
        if tool == 'line':
            for pos, value in work._shape(tool, lo, hi).items():
                self._set(pos, value)
                yield None
            return
        if tool == 'sphere_shell' and len(self.selection) == (
                (hi[0]-lo[0]+1) * (hi[1]-lo[1]+1) * (hi[2]-lo[2]+1)):
            for step in self._sphere_shell(lo, hi):
                yield step
            return
        if tool in ('shell', 'walls', 'frame', 'floor'):
            # Construct axis-aligned slabs as bitsets. A thin shell visits its
            # surface only, instead of evaluating every cell of its volume.
            thickness = max(1, work.thickness)
            bands = []
            for axis in range(3):
                faces = Selection()
                for side in (0, 1):
                    a, b = list(lo), list(hi)
                    if side:
                        a[axis] = max(lo[axis], hi[axis]-thickness+1)
                    else:
                        b[axis] = min(hi[axis], lo[axis]+thickness-1)
                    slab = Selection.box(a, b)
                    for key, mask in slab.chunks.items():
                        faces.chunks[key] = faces.chunks.get(key, 0) | mask
                    if tool == 'floor':
                        break
                bands.append(faces.chunks)
            candidates = Selection()
            for key, mask in self.selection.chunks.items():
                x, y, z = [band.get(key, 0) for band in bands]
                shape = (x | y | z) if tool == 'shell' else (x | z) if tool == 'walls' else (
                    (x & y) | (x & z) | (y & z)) if tool == 'frame' else y
                selected = mask & shape
                if selected:
                    candidates.chunks[key] = selected
                    candidates.count += bin(selected).count('1')
            self.total = max(1, len(candidates))
            for key in sorted(candidates.chunks):
                self._fill_selected_chunk(key, candidates.chunks[key], work.material)
                yield None
            return
        randomizer = random.Random(work.seed)
        for key in sorted(self.selection.chunks):
            mask = self.selection.chunks[key]
            if tool in ('fill', 'box', 'erase'):
                self._fill_selected_chunk(key, mask, AIR if tool == 'erase' else work.material)
                yield None
                continue
            batch = []
            for index in indices(mask):
                batch.append(position(key, index))
                if len(batch) < 128:
                    continue
                for step in self._batch(tool, group, batch, lo, hi, randomizer):
                    yield step
                batch = []
            if batch:
                for step in self._batch(tool, group, batch, lo, hi, randomizer):
                    yield step
            self.staged.compact(key)

    def _batch(self, tool, group, batch, lo, hi, randomizer):
        work = self.work
        work.selection = set(batch)
        if group == 'shape':
            changes = work._shape(tool, lo, hi)
        elif group == 'pattern':
            if tool in ('noise', 'gradient'):
                changes = dict((p, work.secondary if randomizer.random() <
                    (work.ratio if tool == 'noise' else (p[1] - lo[1]) / float(max(1, hi[1] - lo[1])))
                    else work.material) for p in batch)
            else:
                changes = work._pattern(tool, lo, hi)
        elif group == 'finish':
            changes = work._finish(tool, lo, hi)
        else:
            changes = work._edit(tool)
        # All changes in this batch are still part of the original selection.
        for pos, value in changes.items():
            self._set(pos, value)
        work.selection = self.selection
        self.processed += len(batch)
        yield None
