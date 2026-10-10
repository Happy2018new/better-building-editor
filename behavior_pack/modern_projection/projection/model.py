# -*- coding: utf-8 -*-
"""Pure Python 2.7/3 editing engine. No engine APIs and no world writes here."""

from __future__ import unicode_literals
import math
import random
from collections import Counter, deque
from .catalog import BY_ID
from .storage import BlockStore, Selection, integer_types, indices, position
from .cell import (Cell, foreground, background, actor_data, make_cell, layer,
                   replace_layer, has_complete_cells, rebase as rebase_cell,
                   transform as transform_cell)

AIR = ("minecraft:air", 0)
MAX_VOLUME = 64 * 128 * 64
MAX_AXES = (64, 128, 64)
MAX_AXIS = 128
SMALL_VOLUME = 32768
MAX_HISTORY_CELLS = 262144
MAX_HISTORY_BYTES = 64 * 1024 * 1024
DIRECTIONS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def bounds(points):
    if isinstance(points, Selection):
        return points.bounds()
    points = list(points)
    if not points:
        raise ValueError("选区为空，请先选择方块")
    return (
        tuple(min(p[i] for p in points) for i in range(3)),
        tuple(max(p[i] for p in points) for i in range(3)),
    )


def box_points(lo, hi):
    for y in range(lo[1], hi[1] + 1):
        for z in range(lo[2], hi[2] + 1):
            for x in range(lo[0], hi[0] + 1):
                yield (x, y, z)


def close_group_selection(document, selection, strict=True):
    """Expand a selection to include complete native multi-cell structures."""
    from .block_groups import has_group_link, paired_cell_position

    result = selection.copy() if isinstance(selection, Selection) else Selection(selection)

    def get_cell(pos):
        return document.get(pos) if document.contains(pos) else None

    for key, mask in tuple(result.chunks.items()):
        chunk = document.blocks.chunks.get(key, 0)
        if isinstance(chunk, integer_types):
            if not chunk:
                continue
            candidates = indices(mask)
            for index in candidates:
                pos = position(key, index)
                value = document.get(pos)
                try:
                    if not has_group_link(value, pos, get_cell):
                        continue
                    partner = paired_cell_position(get_cell, pos)
                except ValueError:
                    if strict:
                        raise
                    continue
                if partner is not None and partner not in result:
                    result.add(partner)
            continue
        for index in indices(mask):
            identity = chunk[index]
            if not identity:
                continue
            pos = position(key, index)
            value = document.blocks.palette[identity]
            try:
                if not has_group_link(value, pos, get_cell):
                    continue
                partner = paired_cell_position(get_cell, pos)
            except ValueError:
                if strict:
                    raise
                continue
            if partner is not None and partner not in result:
                result.add(partner)
    return result


def block(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("无效的方块数据")
    name, aux = value
    if not isinstance(name, type("")) or ":" not in name or len(name) > 160:
        # SDK/Python2 may supply UTF-8 str rather than unicode.
        try:
            name = name.decode("utf8")
        except (AttributeError, UnicodeError):
            raise ValueError("无效的方块标识符")
    if ":" not in name or not isinstance(aux, int) or not 0 <= aux <= 32767:
        raise ValueError("无效的方块附加值")
    return value if isinstance(value, Cell) else (name, aux)


class RegionSizeError(ValueError):
    """An intact saved document can exceed the current editing limit."""


class SelectionDelta(dict):
    """A cell delta carrying the selection changed by the same operation."""
    def __init__(self, changes, selections):
        dict.__init__(self, changes)
        self.selections = selections


def selection_history_bytes(delta):
    snapshots = getattr(delta, 'selections', ())
    return sum(192 + len(snapshot[0].chunks) * 640 for snapshot in snapshots)


class Document(object):
    def __init__(
        self, size=(24, 16, 24), blocks=None, name="未命名建筑", biome="plains"
    ):
        if len(size) != 3 or any(type(v) is not int or v < 1 for v in size):
            raise ValueError("X/Z 须为 1–64 格，Y 须为 1–128 格")
        if any(v > MAX_AXES[i] for i, v in enumerate(size)):
            raise RegionSizeError("建筑范围最多 64 × 128 × 64 格")
        self.size = tuple(size)
        self.blocks = BlockStore()
        self.name = name
        from .biomes import validate

        self.biome = validate(biome)
        for pos, value in (blocks or {}).items():
            if not self.contains(pos):
                raise ValueError("方块超出建筑范围")
            value = block(value)
            if value != AIR:
                self.blocks[tuple(pos)] = value

    def contains(self, pos):
        return len(pos) == 3 and all(
            type(pos[i]) is int and 0 <= pos[i] < self.size[i] for i in range(3)
        )

    def get(self, pos):
        return self.blocks.get(tuple(pos), AIR)

    get_cell = get

    def get_layer(self, pos, index=0):
        return layer(self.get(pos), index)

    def set_cell(self, pos, value):
        if not self.contains(pos):
            raise ValueError("方块超出建筑范围")
        self.blocks[tuple(pos)] = block(value)

    def set_layer(self, pos, value, index=0):
        self.set_cell(pos, replace_layer(self.get(pos), value, index))

    def points(self):
        return iter(Selection.box((0, 0, 0), tuple(v - 1 for v in self.size)))

    def to_data(self):
        if self.volume > SMALL_VOLUME or has_complete_cells(self.blocks):
            from .codec import to_data

            return to_data(self)
        return {
            "version": 1,
            "name": self.name,
            "size": list(self.size),
            "biome": self.biome,
            "blocks": [
                [p[0], p[1], p[2], b[0], b[1]] for p, b in sorted(self.blocks.items())
            ],
        }

    @classmethod
    def from_data(cls, data):
        if not isinstance(data, dict):
            raise ValueError("不支持的建筑配置版本")
        version = data.get("version", 1)
        if type(version) is not int or version not in (1, 2, 4):
            raise ValueError("不支持的建筑配置版本")
        if version == 1 and ("palette" in data or "chunks" in data):
            raise ValueError("分块配置缺少有效版本号")
        name = data.get("name", "未命名建筑")
        if isinstance(name, bytes):
            name = name.decode("utf8")
        if not isinstance(name, type("")) or not 1 <= len(name) <= 64:
            raise ValueError("名称长度须为 1–64 字")
        if version in (2, 4):
            from .codec import load_steps

            result = None
            for step in load_steps(data):
                if step is not None:
                    result = step
            return result
        entries = data.get("blocks", [])
        if not isinstance(entries, list) or len(entries) > SMALL_VOLUME:
            raise ValueError("配置方块数量超限")
        values = {}
        for row in entries:
            if not isinstance(row, (list, tuple)) or len(row) != 5:
                raise ValueError("配置包含无效方块")
            pos = tuple(row[:3])
            if pos in values:
                raise ValueError("配置包含重复坐标")
            values[pos] = block(row[3:])
        name = data.get("name", "未命名建筑")
        if not isinstance(name, type("")):
            try:
                name = name.decode("utf8")
            except (AttributeError, UnicodeError):
                raise ValueError("配置名称无效")
        if not 1 <= len(name) <= 64:
            raise ValueError("名称长度须为 1–64 字")
        return cls(data.get("size", ()), values, name, data.get("biome", "plains"))

    def materials(self):
        counts = Counter()
        for value, count in self.blocks.counts.items():
            if count <= 0:
                continue
            for material in (foreground(value), background(value)):
                if material != AIR:
                    counts[material] += count
        return counts.most_common()

    @property
    def volume(self):
        return self.size[0] * self.size[1] * self.size[2]

    def layer_count(self, y):
        return self.blocks.layers.get(y, 0)

    def palette_data(self, visible=None):
        common = {}
        extra = {}
        actor = {}
        sx, sy, sz = self.size
        for pos, value in self.blocks.items():
            if not self.contains(pos):
                raise ValueError("方块超出建筑范围，已停止生成预览")
            value = block(value)
            if visible is None or visible(pos):
                # Native SDK volume is (z, x, y), with z contiguous, then x, then y.
                # Verified by GetLocalPosListOfBlocks on asymmetric (2, 3, 4) palettes.
                index = pos[1] * sx * sz + pos[0] * sz + pos[2]
                front, back = foreground(value), background(value)
                if front != AIR:
                    common.setdefault(front, []).append(index)
                if back != AIR:
                    extra.setdefault(back, []).append(index)
                nbt = actor_data(value)
                if nbt is not None:
                    actor.setdefault(front[0], {})[index] = nbt
        return {
            "extra": extra,
            "actor": actor,
            "void": False,
            "volume": (sz, sx, sy),
            "common": common,
            "eliminateAir": True,
        }


class Editor(object):
    def __init__(self, document=None):
        self.document = document or Document()
        self.selection = Selection.box(
            (0, 0, 0), tuple(v - 1 for v in self.document.size)
        )
        self.material = ("minecraft:quartz_block", 0)
        self.secondary = ("minecraft:spruce_planks", 0)
        self.source = ("minecraft:stone", 0)
        self.filter_material = ("minecraft:stone", 0)
        self.start = (0, 0, 0)
        self.end = tuple(v - 1 for v in self.document.size)
        self.edit_layer = 0
        self.layer = 0
        self.thickness = 1
        self.step = 2
        self.ratio = 0.35
        self.seed = 42
        self.mask = "all"
        self.locked_layers = set()
        self.hidden_layers = set()
        self.undo_stack = []
        self.redo_stack = []
        self.clipboard = None
        self.revision = 0
        self.selection_revision = 0
        self.saved_revision = 0
        self.saved_biome = self.document.biome
        self.message = "工作台已就绪"

    def _writable(self, pos, respect_selection=True):
        value = self.document.get_layer(pos, self.edit_layer)
        return (
            (not respect_selection or pos in self.selection)
            and pos[1] not in self.locked_layers
            and (
                self.mask == "all"
                or (self.mask == "solid" and value != AIR)
                or (self.mask == "air" and value == AIR)
                or (self.mask == "material" and value == self.filter_material)
            )
        )

    def _selection_state(self, selection=None):
        if selection is None:
            selection = self.selection
            start, end = self.start, self.end
        else:
            start, end = bounds(selection) if selection else (self.start, self.end)
        selection = selection.copy() if isinstance(selection, Selection) else Selection(selection)
        return selection, tuple(start), tuple(end)

    def _restore_selection(self, snapshot):
        selection, start, end = snapshot
        self.selection = selection.copy()
        self.start, self.end = start, end
        self.selection_revision += 1

    def _commit(self, name, changes, respect_selection=True, whole=False, selection_after=None):
        if not whole and self.edit_layer == 0:
            from .block_groups import expand_group_changes
            changes = expand_group_changes(changes, lambda pos: (
                self.document.contains(pos) and pos[1] not in self.locked_layers and
                (not respect_selection or self._writable(pos))))
        delta = {}
        for pos, new in changes.items():
            if not self.document.contains(pos):
                raise ValueError("操作超出建筑范围，请缩小选区或调整起点")
            if pos[1] in self.locked_layers:
                continue
            if respect_selection and not self._writable(pos):
                continue
            old = self.document.get(pos)
            if whole:
                new = block(new)
            else:
                if self.edit_layer == 0:
                    from .block_groups import preserve_group_part
                    new = preserve_group_part(new, foreground(old))
                new = replace_layer(old, new, self.edit_layer)
            if old != new:
                delta[pos] = (old, new)
        if selection_after is not None:
            selections = (self._selection_state(), self._selection_state(selection_after))
            if selections[0] != selections[1]:
                delta = SelectionDelta(delta, selections)
        if not delta and not hasattr(delta, 'selections'):
            self.message = "没有方块改变，请检查选区、蒙版和图层锁定"
            return 0
        self._apply(delta, 1)
        self._remember(name, delta)
        self.message = "%s，已修改 %d 格" % (name, len(delta))
        return len(delta)

    def _remember(self, name, delta):
        self.undo_stack.append((name, delta))
        self.redo_stack = []

        def cost(item):
            value = item[1]
            if hasattr(value, "memory_bytes"):
                return value.memory_bytes() + selection_history_bytes(value)
            size = len(value) * 96
            if isinstance(value, dict):
                size += sum(cell.memory_bytes()
                            for pair in value.values() for cell in pair
                            if isinstance(cell, Cell))
            return size + selection_history_bytes(value)

        while len(self.undo_stack) > 1 and (
            len(self.undo_stack) > 50
            or sum(cost(item) for item in self.undo_stack) > MAX_HISTORY_BYTES
        ):
            self.undo_stack.pop(0)

    def _apply(self, delta, side):
        self.last_changed_positions = (
            tuple(delta) if isinstance(delta, dict) and len(delta) <= 32 else None
        )
        self.last_changed_chunks = (
            delta.changed_chunks
            if hasattr(delta, "changed_chunks")
            else set(tuple(v // 16 for v in pos) for pos in delta)
        )
        if len(delta):
            if hasattr(delta, "stores"):
                self.document.blocks = delta.stores[side].copy()
            else:
                for pos, pair in delta.items():
                    if pair[side] == AIR:
                        self.document.blocks.pop(pos, None)
                    else:
                        self.document.blocks[pos] = pair[side]
            self.revision += 1
        selections = getattr(delta, 'selections', None)
        if selections is not None:
            self._restore_selection(selections[side])

    def undo(self):
        if not self.undo_stack:
            self.message = "没有可以撤销的操作"
            return False
        name, delta = self.undo_stack.pop()
        self._apply(delta, 0)
        self.redo_stack.append((name, delta))
        self.message = "已撤销：" + name
        return True

    def redo(self):
        if not self.redo_stack:
            self.message = "没有可以重做的操作"
            return False
        name, delta = self.redo_stack.pop()
        self._apply(delta, 1)
        self.undo_stack.append((name, delta))
        self.message = "已重做：" + name
        return True

    def select_box(self, start, end):
        if not self.document.contains(start) or not self.document.contains(end):
            raise ValueError("选区起终点必须位于建筑范围内")
        lo, hi = bounds((start, end))
        self.start, self.end = tuple(start), tuple(end)
        self.selection = close_group_selection(self.document, Selection.box(lo, hi), strict=False)
        self.sync_selection_bounds()
        self.selection_revision += 1

    def sync_selection_bounds(self):
        if self.selection:
            self.start, self.end = bounds(self.selection)

    def surface(self, pos):
        return self.document.get(pos) != AIR and any(
            self.document.get(add(pos, d)) == AIR for d in DIRECTIONS
        )

    def _select(self, tool):
        doc = self.document
        all_points = Selection.box((0, 0, 0), tuple(v - 1 for v in doc.size))
        if tool == "select_all":
            self.selection = all_points
        elif tool == "select_nonair":
            self.selection = set(doc.blocks)
        elif tool == "select_air":
            self.selection = all_points.difference(doc.blocks)
        elif tool == "select_material":
            self.selection = set(p for p, b in doc.blocks.items() if layer(b, self.edit_layer) == self.source)
            if self.source == AIR:
                self.selection = all_points.difference(doc.blocks)
        elif tool == "select_layer":
            self.selection = Selection.box(
                (0, self.layer, 0), (doc.size[0] - 1, self.layer, doc.size[2] - 1)
            )
        elif tool == "select_invert":
            self.selection = all_points.difference(self.selection)
        elif tool == "select_expand":
            self.selection = set(self.selection) | set(
                add(p, d)
                for p in self.selection
                for d in DIRECTIONS
                if doc.contains(add(p, d))
            )
        elif tool == "select_contract":
            self.selection = set(
                p
                for p in self.selection
                if all(add(p, d) in self.selection for d in DIRECTIONS)
            )
        elif tool == "select_surface":
            self.selection = set(p for p in doc.blocks if self.surface(p))
        elif tool == "select_box":
            self.select_box(self.start, self.end)
        self.selection = close_group_selection(doc, self.selection, strict=False)
        self.selection_revision += 1
        self.sync_selection_bounds()
        self.message = "已选择 %d 格" % len(self.selection)
        return len(self.selection)

    def paint_at(self, pos, erase=False, respect_selection=True):
        if not self.document.contains(pos):
            raise ValueError("目标超出建筑范围")
        if not self._writable(pos, respect_selection):
            self.message = (
                "目标图层已锁定"
                if pos[1] in self.locked_layers
                else (
                    "目标不在选区内"
                    if respect_selection and pos not in self.selection
                    else "目标不符合当前蒙版"
                )
            )
            return 0
        changes = {pos: AIR if erase else block(self.material)}
        if self.edit_layer == 0:
            from .block_groups import group_partner, paired_cell_position

            document = self.document

            def get_cell(target):
                return document.get(target) if document.contains(target) else None

            old_partner = paired_cell_position(get_cell, pos)
            if old_partner is not None:
                changes[old_partner] = AIR
            if not erase:
                relationship = group_partner(foreground(changes[pos]))
                if relationship is not None:
                    offset, partner_value = relationship
                    partner = tuple(pos[i] + offset[i] for i in range(3))
                    changes[partner] = partner_value
            for target in changes:
                if not document.contains(target):
                    raise ValueError("多格方块对应部件超出建筑范围")
                if not self._writable(target, respect_selection):
                    self.message = "多格方块完整部件受到选区、蒙版或图层锁定限制"
                    return 0
        return self._commit(
            "擦除单格" if erase else "绘制单格",
            changes,
            respect_selection=False,
        )

    def _copy(self):
        self.selection = close_group_selection(self.document, self.selection)
        self.sync_selection_bounds()
        lo, hi = bounds(self.selection)
        self.clipboard = {
            "size": tuple(hi[i] - lo[i] + 1 for i in range(3)),
            "origin": lo,
            "blocks": dict(
                (tuple(p[i] - lo[i] for i in range(3)), self.document.get(p))
                for p in self.selection
            ),
        }

    def _transform(self, tool):
        lo, hi = bounds(self.selection)
        ext = tuple(hi[i] - lo[i] + 1 for i in range(3))
        source = dict((p, self.document.get(p)) for p in self.selection)
        if self.mask != "all" or any(p[1] in self.locked_layers for p in source):
            raise ValueError("整体变换前请关闭蒙版并解锁选区内图层")
        mapping = {}
        for pos, value in source.items():
            q = [pos[i] - lo[i] for i in range(3)]
            if tool.startswith("rotate_y"):
                turns = int(tool[8:]) // 90
                width, depth = ext[0], ext[2]
                for unused in range(turns):
                    q[0], q[2] = depth - 1 - q[2], q[0]
                    width, depth = depth, width
            elif tool.startswith("mirror_"):
                axis = "xyz".index(tool[-1])
                q[axis] = ext[axis] - 1 - q[axis]
            elif tool.startswith("move_"):
                axis = "xyz".index(tool[-2])
                q[axis] += self.step * (1 if tool[-1] == "p" else -1)
            elif tool.startswith("stack_"):
                axis = "xyz".index(tool[-1])
                q[axis] += ext[axis]
            target = tuple(q[i] + lo[i] for i in range(3))
            if not self.document.contains(target):
                raise ValueError("变换将超出建筑范围，操作已取消")
            if target[1] in self.locked_layers:
                raise ValueError("目标图层已锁定，操作已取消")
            value = transform_cell(value, tool, pos)
            mapping[target] = rebase_cell(value, tuple(target[i] - pos[i] for i in range(3)))
        changes = {} if tool.startswith("stack_") else dict((p, AIR) for p in source)
        changes.update(mapping)
        count = self._commit(BY_ID[tool][2], changes, False, whole=True,
                             selection_after=Selection(mapping))
        return count

    def _shape(self, tool, lo, hi):
        size = [hi[i] - lo[i] + 1 for i in range(3)]
        center = [(hi[i] + lo[i]) / 2.0 for i in range(3)]
        radii = [max(0.5, v / 2.0) for v in size]
        thickness = max(1, self.thickness)
        out = {}
        if tool == "line":
            a, b = self.start, self.end
            steps = max(abs(a[i] - b[i]) for i in range(3))
            for n in range(steps + 1):
                pos = tuple(
                    int(round(a[i] + (b[i] - a[i]) * n / float(max(1, steps))))
                    for i in range(3)
                )
                out[pos] = self.material
            return out
        for p in self.selection:
            q = [p[i] - lo[i] for i in range(3)]
            edge = [q[i] < thickness or q[i] >= size[i] - thickness for i in range(3)]
            norm = [(p[i] - center[i]) / radii[i] for i in range(3)]
            ellipsoid = sum(v * v for v in norm)
            cylinder = norm[0] ** 2 + norm[2] ** 2
            inner = sum(
                ((p[i] - center[i]) / max(0.01, radii[i] - thickness)) ** 2
                for i in range(3)
            )
            inner_cyl = sum(
                ((p[i] - center[i]) / max(0.01, radii[i] - thickness)) ** 2
                for i in (0, 2)
            )
            yes = False
            if tool in ("box", "fill"):
                yes = True
            elif tool == "shell":
                yes = any(edge)
            elif tool == "walls":
                yes = edge[0] or edge[2]
            elif tool == "frame":
                yes = sum(edge) >= 2
            elif tool == "sphere":
                yes = ellipsoid <= 1
            elif tool == "sphere_shell":
                yes = ellipsoid <= 1 and inner >= 1
            elif tool == "cylinder":
                yes = cylinder <= 1
            elif tool == "tube":
                yes = cylinder <= 1 and inner_cyl >= 1
            elif tool == "pyramid":
                f = 1.0 - q[1] / float(max(1, size[1]))
                yes = abs(norm[0]) <= f and abs(norm[2]) <= f
            elif tool == "dome":
                v = (
                    norm[0] ** 2
                    + norm[2] ** 2
                    + (q[1] / float(max(1, size[1] - 1))) ** 2
                )
                inside = ((p[0] - center[0]) / max(0.01, radii[0] - thickness)) ** 2
                inside += ((p[2] - center[2]) / max(0.01, radii[2] - thickness)) ** 2
                inside += (q[1] / max(0.01, size[1] - 1 - thickness)) ** 2
                yes = v <= 1.03 and inside >= 1
            elif tool == "arch":
                spring = max(0.0, size[1] - radii[0])
                if q[1] < spring:
                    yes = edge[0]
                else:
                    distance = math.sqrt((p[0] - center[0]) ** 2 + (q[1] - spring) ** 2)
                    yes = radii[0] - thickness <= distance <= radii[0]
            elif tool == "stairs":
                yes = q[1] <= int(q[0] * size[1] / float(size[0]))
            elif tool == "floor":
                yes = q[1] < thickness
            elif tool == "roof":
                target = int((1.0 - abs(norm[0])) * (size[1] - 1))
                yes = target - thickness < q[1] <= target
            if yes:
                out[p] = self.material
        return out

    def _pattern(self, tool, lo, hi):
        randomizer = random.Random(self.seed)
        out = {}
        for p in sorted(self.selection):
            q = [p[i] - lo[i] for i in range(3)]
            second = False
            if tool == "checker":
                second = sum(v // self.step for v in q) % 2 == 1
            elif tool.startswith("stripe_"):
                second = (q["xyz".index(tool[-1])] // self.step) % 2 == 1
            elif tool == "noise":
                second = randomizer.random() < self.ratio
            elif tool == "gradient":
                second = randomizer.random() < q[1] / float(max(1, hi[1] - lo[1]))
            elif tool == "brick":
                second = (
                    q[1] % 3 == 0
                    or (q[0] + (q[1] // 3 % 2) * self.step) % (2 * self.step + 1) == 0
                )
            elif tool == "lattice":
                if sum(v % (self.step + 1) == 0 for v in q) < 2:
                    out[p] = AIR
                    continue
                second = all(v % (self.step + 1) == 0 for v in q)
            out[p] = self.secondary if second else self.material
        return out

    def _finish(self, tool, lo, hi):
        doc = self.document
        out = {}
        if tool in ("hollow", "clean_isolated", "fill_holes"):
            for p in self.selection:
                neighbors = [doc.get(add(p, d)) != AIR for d in DIRECTIONS]
                if tool == "hollow" and doc.get(p) != AIR and all(neighbors):
                    out[p] = AIR
                elif (
                    tool == "clean_isolated"
                    and doc.get(p) != AIR
                    and not any(neighbors)
                ):
                    out[p] = AIR
                elif tool == "fill_holes" and doc.get(p) == AIR and all(neighbors):
                    out[p] = self.material
            return out
        for x in range(lo[0], hi[0] + 1):
            for z in range(lo[2], hi[2] + 1):
                column = [
                    (x, y, z)
                    for y in range(lo[1], hi[1] + 1)
                    if (x, y, z) in self.selection
                ]
                filled = [(p, doc.get(p)) for p in column if doc.get(p) != AIR]
                if not filled:
                    continue
                if tool == "gravity":
                    if (
                        any(p[1] in self.locked_layers for p in column)
                        or self.mask != "all"
                    ):
                        raise ValueError("垂直压实前请关闭蒙版并解锁相关图层")
                    out.update(
                        (p, filled[i][1] if i < len(filled) else AIR)
                        for i, p in enumerate(column)
                    )
                elif tool == "foundation":
                    out.update(
                        (p, filled[0][1]) for p in column if p[1] < filled[0][0][1]
                    )
                elif tool == "heightmap":
                    out.update((p, AIR) for p, unused in filled[:-1])
        return out

    def run(self, tool):
        if self.document.volume > SMALL_VOLUME or tool.startswith("paste"):
            from .jobs import EditJob

            job = EditJob(self, tool)
            while not job.done:
                job.step()
            if job.error:
                raise ValueError(job.error)
            return job.changed
        if tool not in BY_ID:
            raise ValueError("未知工具")
        group = BY_ID[tool][1]
        if group == "select":
            return self._select(tool)
        if self.edit_layer == 0 or group == "transform" or tool in ("copy", "cut"):
            self.selection = close_group_selection(self.document, self.selection)
            self.sync_selection_bounds()
        if not self.selection:
            raise ValueError("选区为空，请先框选或全选")
        lo, hi = bounds(self.selection)
        if group == "transform":
            return self._transform(tool)
        if group == "shape":
            changes = self._shape(tool, lo, hi)
        elif group == "pattern":
            changes = self._pattern(tool, lo, hi)
        elif group == "finish":
            changes = self._finish(tool, lo, hi)
        else:
            changes = self._edit(tool)
            if changes is None:
                return 0
        return self._commit(BY_ID[tool][2], changes, whole=tool in ("cut", "gravity", "foundation", "heightmap"))

    def _edit(self, tool):
        doc = self.document
        if tool in ("copy", "cut"):
            self._copy()
            self.message = "已复制 %d 格" % len(self.selection)
            return dict((p, AIR) for p in self.selection) if tool == "cut" else None
        if tool == "flood":
            if self.start not in self.selection:
                raise ValueError("填充起点不在选区内")
            old = doc.get_layer(self.start, self.edit_layer)
            visited, pending = set(), deque([self.start])
            while pending:
                p = pending.popleft()
                if p in visited or not self._writable(p) or doc.get_layer(p, self.edit_layer) != old:
                    continue
                visited.add(p)
                pending.extend(add(p, d) for d in DIRECTIONS)
            return dict((p, self.material) for p in visited)
        out = {}
        for p in self.selection:
            old = doc.get_layer(p, self.edit_layer)
            if tool == "erase":
                out[p] = AIR
            elif tool == "fill" or (tool == "fill_air" and old == AIR):
                out[p] = self.material
            elif tool == "replace" and old == self.source:
                out[p] = self.material
                if self.edit_layer == 0:
                    from .block_groups import paired_cell_position
                    partner = paired_cell_position(
                        lambda target: doc.get(target) if doc.contains(target) else None, p)
                    if partner is not None and partner in self.selection:
                        out[partner] = self.material
            elif tool == "paint" and self.surface(p):
                out[p] = self.material
            elif tool == "swap":
                if old == self.material:
                    out[p] = self.source
                elif old == self.source:
                    out[p] = self.material
        return out


def demo_document():
    """Editable modern courtyard, built from real blocks, not a preview image."""
    doc = Document((24, 16, 24), name="林间白盒建筑练习")
    quartz, wood = ("minecraft:quartz_block", 0), ("minecraft:planks", 1)
    glass, grass = ("minecraft:glass", 0), ("minecraft:grass", 0)
    for x in range(2, 22):
        for z in range(2, 22):
            doc.blocks[(x, 0, z)] = grass
    for x in range(4, 20):
        for z in range(5, 19):
            doc.blocks[(x, 1, z)] = quartz
            if x < 15 and z > 8:
                doc.blocks[(x, 2, z)] = wood
                doc.blocks[(x, 9, z)] = quartz
                doc.blocks[(x, 10, z)] = quartz
                for y in range(3, 9):
                    if x in (4, 14) or z == 18:
                        doc.blocks[(x, y, z)] = quartz
                    elif z == 9 and x not in (9, 10):
                        doc.blocks[(x, y, z)] = glass
    for x in (5, 8, 11, 14):
        for z in range(4, 10):
            doc.blocks[(x, 8, z)] = wood
    for x in (5, 14):
        for y in range(2, 8):
            doc.blocks[(x, y, 4)] = wood
    for x in range(16, 20):
        for z in range(6, 17):
            doc.blocks[(x, 2, z)] = ("minecraft:stained_glass", 9)
    for x, z in ((3, 19), (20, 19), (20, 3)):
        for y in range(1, 4):
            doc.blocks[(x, y, z)] = wood
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for y in (4, 5):
                    doc.blocks[(x + dx, y, z + dz)] = ("minecraft:leaves", 0)
    return doc
