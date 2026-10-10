# -*- coding: utf-8 -*-
"""Atomic, cancellable editor jobs. No engine calls and no 25M-cell dictionaries."""
from __future__ import unicode_literals
import copy
import math
import random
import time
from collections import deque
from .model import AIR, BY_ID, DIRECTIONS, add, bounds, box_points, close_group_selection
from .storage import Selection, FULL, CELLS, integer_types, indices, position
from .cell import Cell, foreground, layer, has_complete_cells, rebase as rebase_cell, transform as transform_cell
from .block_edits import edit_material, material_changes


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
        self.selection_before = editor._selection_state()
        self.selection = editor.selection.copy() if isinstance(editor.selection, Selection) else Selection(editor.selection)
        if BY_ID[tool][1] != 'select':
            selected_layer = None if BY_ID[tool][1] == 'transform' or tool in ('copy', 'cut', 'gravity', 'foundation', 'heightmap') or (editor.edit_layer == 2 and tool != 'erase') else editor.edit_layer
            self.selection = close_group_selection(self.source, self.selection, index=selected_layer)
        self.work = copy.copy(editor)
        self.work.locked_layers = set(editor.locked_layers)
        self.work.hidden_layers = set(editor.hidden_layers)
        self.work.selection = self.selection
        self.staged = self.source.blocks.copy()
        self.group_written = set()
        self.batch_changes = None
        self.preserve_connections = Selection()
        self.result_selection = None
        self.result_clipboard = None
        self.changed = self.processed = 0
        self.total = max(1, len(self.selection))
        self.done = self.cancelled = False
        self.error = ''
        self.iterator = self._run_with_neighbors()

    def cancel(self):
        self.cancelled = True

    def _run_with_neighbors(self):
        for step in self._run():
            yield step
        if not self.changed:
            return
        from .block_neighbors import reconcile_steps

        def write_neighbor(pos, value):
            original, previous = self.source.get(pos), self.staged.get(pos, AIR)
            self.changed += int(value != original) - int(previous != original)
            self.staged[pos] = value

        for step in reconcile_steps(self.source, self.staged, write_neighbor, self.work.locked_layers,
                                    self.preserve_connections):
            yield step

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
        selection_after = None
        if self.result_selection is not None:
            updated_document = copy.copy(self.source)
            updated_document.blocks = self.staged
            selected_layer = self.work.edit_layer if self.tool == 'select_material' else None
            result = close_group_selection(updated_document, self.result_selection, strict=False, index=selected_layer)
            selection_after = e._selection_state(result)
        if self.result_clipboard is not None:
            e.clipboard = self.result_clipboard
        selection_changed = selection_after is not None and self.selection_before != selection_after
        if self.changed or (selection_changed and BY_ID[self.tool][1] != 'select'):
            delta = SnapshotDelta(self.source.blocks, self.staged, self.changed)
            if selection_changed:
                delta.selections = self.selection_before, selection_after
            e._apply(delta, 1)
            e._remember(BY_ID[self.tool][2], delta)
        elif selection_changed:
            e._restore_selection(selection_after)
        e.message = ('已选择 %d 格' % len(e.selection) if BY_ID[self.tool][1] == 'select' else
                     '已复制 %d 格' % len(self.selection) if self.tool == 'copy' else
                     '%s，已修改 %d 格' % (BY_ID[self.tool][2], self.changed))

    def _set(self, pos, value, respect=True, whole=False):
        if whole:
            self._set_one(pos, value, respect, True)
            return
        if pos in self.group_written:
            return

        def get_cell(target):
            return self.staged.get(target, AIR) if self.source.contains(target) else None

        planned = material_changes(get_cell, pos, value, self.work.edit_layer)
        from .block_groups import group_partner
        for target in planned.removed:
            requested = self.batch_changes.get(target, AIR) if self.batch_changes is not None else value
            if requested != AIR and group_partner(requested) is None:
                planned[target] = edit_material(get_cell(target) or AIR, requested, self.work.edit_layer)
        if any(not self.source.contains(target) or not self.work._writable(target, respect)
               for target in planned):
            return
        if len(planned) > 1:
            self.group_written.update(planned)
        for target, cell in planned.items():
            self._store(target, cell)

    def _set_one(self, pos, value, respect=True, whole=False):
        if not self.source.contains(pos):
            raise ValueError('操作超出建筑范围，草稿未改变')
        if not self.work._writable(pos, respect):
            return
        if pos[1] in self.work.locked_layers:
            return
        original, previous = self.source.get(pos), self.staged.get(pos, AIR)
        if not whole:
            value = edit_material(previous, value, self.work.edit_layer)
        self.changed += int(value != original) - int(previous != original)
        self.staged[pos] = value
        if whole:
            self.preserve_connections.add(pos)

    def _store(self, pos, value):
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
        if BY_ID[self.tool][1] == 'transform':
            self.preserve_connections.chunks[key] = FULL
            self.preserve_connections.count += CELLS

    def _fill_selected_chunk(self, key, mask, value):
        """For disjoint fill/shape chunks; source cells are visited only once."""
        self.processed += CELLS if mask == FULL else bin(mask).count('1')
        for y in self.work.locked_layers:
            local_y = y-(key[1] << 4)
            if 0 <= local_y < 16:
                mask &= ~(((1 << 256)-1) << (local_y << 8))
        grouped = False
        if self.work.edit_layer != 1:
            from .block_groups import group_partner
            grouped = group_partner(value) is not None
            if not grouped:
                chunk = self.staged.chunks.get(key, 0)
                palette = self.staged.palette
                if isinstance(chunk, integer_types):
                    grouped = bool(mask) and group_partner(palette[chunk]) is not None
                else:
                    grouped = any(mask & (1 << index) and group_partner(palette[chunk[index]]) is not None
                                  for index in range(CELLS))
        automatic = False
        if self.work.edit_layer == 2:
            chunk = self.staged.chunks.get(key, 0)
            identities = (chunk,) if isinstance(chunk, integer_types) else set(chunk)
            automatic = any(edit_material(self.staged.palette[identity], value, 2) != value
                            for identity in identities)
        if self.work.edit_layer == 1 or has_complete_cells(self.staged) or grouped or automatic:
            for index in indices(mask):
                self._set(position(key, index), value)
            return
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
                                    not chunk if tool == 'select_air' else layer(value, self.work.edit_layer) == self.work.source)
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
                                    self.work.surface(pos) if tool == 'select_surface' else layer(value, self.work.edit_layer) == self.work.source)
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
        compact = (not has_complete_cells(self.source.blocks) and all(mask == FULL and isinstance(self.source.blocks.chunks.get(key, 0), integer_types)
                       for key, mask in self.selection.chunks.items()) and
                   all(v % 16 == 0 for v in lo + ext + target_lo))
        if compact:
            mapped = []
            result = Selection()
            for key in self.selection.chunks:
                value = self.source.blocks.palette[self.source.blocks.chunks.get(key, 0)]
                value = transform_cell(value, self.tool)
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
                self._set(pos, AIR, False, whole=True)
                yield None
        result = Selection()
        for pos in self.selection:
            value = self.source.get(pos)
            value = transform_cell(value, self.tool, pos)
            target = self._target(pos, lo, ext)
            value = rebase_cell(value, tuple(target[i] - pos[i] for i in range(3)))
            self._set(target, value, False, whole=True)
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
            relative_clip = 'selection' not in clip
            self.total = max(1, len(points))
            for pos in points:
                value = clip['blocks'].get(pos, AIR)
                if tool == 'paste' or value != AIR:
                    if relative_clip:
                        source_pos = tuple(pos[i] + origin[i] for i in range(3))
                        target = tuple(pos[i] + work.start[i] for i in range(3))
                    else:
                        source_pos = pos
                        target = tuple(pos[i]-origin[i]+work.start[i] for i in range(3))
                    value = rebase_cell(value, tuple(target[i] - source_pos[i] for i in range(3)))
                    self._set(target, value, False, whole=True)
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
            for pos in self.selection:
                self._set(pos, AIR, whole=True)
                yield None
            return
        if tool == 'flood':
            if work.start not in self.selection:
                raise ValueError('填充起点不在选区内')
            old = self.source.get_layer(work.start, work.edit_layer)
            seen, pending = Selection([work.start]), deque([work.start])
            while pending:
                pos = pending.popleft()
                if work._writable(pos) and self.source.get_layer(pos, work.edit_layer) == old:
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
                        self._set(pos, value, whole=True)
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
        if tool == 'replace' and changes:
            from .block_groups import paired_cell_position
            for pos in tuple(changes):
                partner = paired_cell_position(
                    lambda target: self.source.get(target) if self.source.contains(target) else None, pos, work.edit_layer)
                if partner is not None and partner in self.selection:
                    changes[partner] = changes[pos]
        # All changes in this batch are still part of the original selection.
        self.batch_changes = changes
        for pos, value in changes.items():
            self._set(pos, value)
        self.batch_changes = None
        work.selection = self.selection
        self.processed += len(batch)
        yield None
