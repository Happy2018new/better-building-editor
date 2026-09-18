# -*- coding: utf-8 -*-
"""Pure Python 2.7/3 editing engine. No engine APIs and no world writes here."""
from __future__ import unicode_literals
import math
import random
from collections import Counter, deque
from .catalog import BY_ID

AIR = ('minecraft:air', 0)
MAX_VOLUME = 32768
MAX_AXIS = 64
MAX_HISTORY_CELLS = 262144
DIRECTIONS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


def add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def bounds(points):
    points = list(points)
    if not points:
        raise ValueError('选区为空，请先选择方块')
    return (tuple(min(p[i] for p in points) for i in range(3)),
            tuple(max(p[i] for p in points) for i in range(3)))


def box_points(lo, hi):
    for y in range(lo[1], hi[1] + 1):
        for z in range(lo[2], hi[2] + 1):
            for x in range(lo[0], hi[0] + 1):
                yield (x, y, z)


def block(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError('无效的方块数据')
    name, aux = value
    if not isinstance(name, type('')) or ':' not in name or len(name) > 160:
        # SDK/Python2 may supply UTF-8 str rather than unicode.
        try:
            name = name.decode('utf8')
        except (AttributeError, UnicodeError):
            raise ValueError('无效的方块标识符')
    if ':' not in name or not isinstance(aux, int) or not 0 <= aux <= 32767:
        raise ValueError('无效的方块附加值')
    return (name, aux)


class Document(object):
    def __init__(self, size=(24, 16, 24), blocks=None, name='未命名建筑'):
        if len(size) != 3 or any(type(v) is not int or v < 1 or v > MAX_AXIS for v in size):
            raise ValueError('每个轴须为 1–64 格')
        if size[0] * size[1] * size[2] > MAX_VOLUME:
            raise ValueError('建筑范围最多 32768 格')
        self.size = tuple(size)
        self.blocks = {}
        self.name = name
        for pos, value in (blocks or {}).items():
            if not self.contains(pos):
                raise ValueError('方块超出建筑范围')
            value = block(value)
            if value != AIR:
                self.blocks[tuple(pos)] = value

    def contains(self, pos):
        return len(pos) == 3 and all(type(pos[i]) is int and 0 <= pos[i] < self.size[i] for i in range(3))

    def get(self, pos):
        return self.blocks.get(tuple(pos), AIR)

    def points(self):
        return box_points((0, 0, 0), tuple(v - 1 for v in self.size))

    def to_data(self):
        return {'version': 1, 'name': self.name, 'size': list(self.size),
                'blocks': [[p[0], p[1], p[2], b[0], b[1]] for p, b in sorted(self.blocks.items())]}

    @classmethod
    def from_data(cls, data):
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('不支持的建筑配置版本')
        entries = data.get('blocks', [])
        if not isinstance(entries, list) or len(entries) > MAX_VOLUME:
            raise ValueError('配置方块数量超限')
        values = {}
        for row in entries:
            if not isinstance(row, (list, tuple)) or len(row) != 5:
                raise ValueError('配置包含无效方块')
            pos = tuple(row[:3])
            if pos in values:
                raise ValueError('配置包含重复坐标')
            values[pos] = block(row[3:])
        name = data.get('name', '未命名建筑')
        if not isinstance(name, type('')):
            try:
                name = name.decode('utf8')
            except (AttributeError, UnicodeError):
                raise ValueError('配置名称无效')
        if not 1 <= len(name) <= 64:
            raise ValueError('名称长度须为 1–64 字')
        return cls(data.get('size', ()), values, name)

    def materials(self):
        return Counter(self.blocks.values()).most_common()

    def palette_data(self, visible=None):
        common = {}
        sx, sy, sz = self.size
        for pos, value in self.blocks.items():
            if not self.contains(pos):
                raise ValueError('方块超出建筑范围，已停止生成预览')
            value = block(value)
            if visible is None or visible(pos):
                # Native SDK volume is (z, x, y), with z contiguous, then x, then y.
                # Verified by GetLocalPosListOfBlocks on asymmetric (2, 3, 4) palettes.
                index = pos[1] * sx * sz + pos[0] * sz + pos[2]
                common.setdefault(value, []).append(index)
        return {'extra': {}, 'actor': {}, 'void': False, 'volume': (sz, sx, sy),
                'common': common, 'eliminateAir': True}


class Editor(object):
    def __init__(self, document=None):
        self.document = document or Document()
        self.selection = set(self.document.points())
        self.material = ('minecraft:quartz_block', 0)
        self.secondary = ('minecraft:planks', 1)
        self.source = ('minecraft:stone', 0)
        self.start = (0, 0, 0)
        self.end = tuple(v - 1 for v in self.document.size)
        self.layer = 0
        self.thickness = 1
        self.step = 2
        self.ratio = .35
        self.seed = 42
        self.mask = 'all'
        self.locked_layers = set()
        self.hidden_layers = set()
        self.undo_stack = []
        self.redo_stack = []
        self.clipboard = None
        self.revision = 0
        self.selection_revision = 0
        self.saved_revision = 0
        self.message = '工作台已就绪'

    def _writable(self, pos, respect_selection=True):
        value = self.document.get(pos)
        return ((not respect_selection or pos in self.selection) and pos[1] not in self.locked_layers and
                (self.mask == 'all' or (self.mask == 'solid' and value != AIR) or
                 (self.mask == 'air' and value == AIR) or
                 (self.mask == 'material' and value == self.source)))

    def _commit(self, name, changes, respect_selection=True):
        delta = {}
        for pos, new in changes.items():
            if not self.document.contains(pos):
                raise ValueError('操作超出建筑范围，请缩小选区或调整起点')
            if pos[1] in self.locked_layers:
                continue
            if respect_selection and not self._writable(pos):
                continue
            old = self.document.get(pos)
            if old != new:
                delta[pos] = (old, new)
        if not delta:
            self.message = '没有方块改变 · 请检查选区、蒙版和图层锁定'
            return 0
        self._apply(delta, 1)
        self.undo_stack.append((name, delta))
        self.redo_stack = []
        while len(self.undo_stack) > 50 or sum(len(item[1]) for item in self.undo_stack) > MAX_HISTORY_CELLS:
            self.undo_stack.pop(0)
        self.message = '%s · 已修改 %d 格' % (name, len(delta))
        return len(delta)

    def _apply(self, delta, side):
        for pos, pair in delta.items():
            if pair[side] == AIR:
                self.document.blocks.pop(pos, None)
            else:
                self.document.blocks[pos] = pair[side]
        self.revision += 1

    def undo(self):
        if not self.undo_stack:
            self.message = '没有可以撤销的操作'
            return False
        name, delta = self.undo_stack.pop()
        self._apply(delta, 0)
        self.redo_stack.append((name, delta))
        self.message = '已撤销：' + name
        return True

    def redo(self):
        if not self.redo_stack:
            self.message = '没有可以重做的操作'
            return False
        name, delta = self.redo_stack.pop()
        self._apply(delta, 1)
        self.undo_stack.append((name, delta))
        self.message = '已重做：' + name
        return True

    def select_box(self, start, end):
        if not self.document.contains(start) or not self.document.contains(end):
            raise ValueError('选区起终点必须位于建筑范围内')
        lo, hi = bounds((start, end))
        self.selection = set(box_points(lo, hi))
        self.selection_revision += 1

    def surface(self, pos):
        return self.document.get(pos) != AIR and any(self.document.get(add(pos, d)) == AIR for d in DIRECTIONS)

    def _select(self, tool):
        doc = self.document
        all_points = set(doc.points())
        if tool == 'select_all':
            self.selection = all_points
        elif tool == 'select_nonair':
            self.selection = set(doc.blocks)
        elif tool == 'select_air':
            self.selection = all_points - set(doc.blocks)
        elif tool == 'select_material':
            self.selection = set(p for p, b in doc.blocks.items() if b == self.source)
            if self.source == AIR:
                self.selection = all_points - set(doc.blocks)
        elif tool == 'select_layer':
            self.selection = set(p for p in all_points if p[1] == self.layer)
        elif tool == 'select_invert':
            self.selection = all_points - self.selection
        elif tool == 'select_expand':
            self.selection |= set(add(p, d) for p in self.selection for d in DIRECTIONS if doc.contains(add(p, d)))
        elif tool == 'select_contract':
            self.selection = set(p for p in self.selection if all(add(p, d) in self.selection for d in DIRECTIONS))
        elif tool == 'select_surface':
            self.selection = set(p for p in doc.blocks if self.surface(p))
        elif tool == 'select_box':
            self.select_box(self.start, self.end)
        self.selection_revision += 1
        self.message = '已选择 %d 格' % len(self.selection)
        return len(self.selection)

    def paint_at(self, pos, erase=False, respect_selection=True):
        if not self.document.contains(pos):
            raise ValueError('目标超出建筑范围')
        if not self._writable(pos, respect_selection):
            self.message = ('目标图层已锁定' if pos[1] in self.locked_layers else
                            '目标不在选区内' if respect_selection and pos not in self.selection else
                            '目标不符合当前蒙版')
            return 0
        return self._commit('擦除单格' if erase else '绘制单格',
                            {pos: AIR if erase else block(self.material)}, respect_selection=False)

    def _copy(self):
        lo, hi = bounds(self.selection)
        self.clipboard = {'size': tuple(hi[i] - lo[i] + 1 for i in range(3)),
                          'blocks': dict((tuple(p[i] - lo[i] for i in range(3)), self.document.get(p))
                                         for p in self.selection)}

    def _transform(self, tool):
        lo, hi = bounds(self.selection)
        ext = tuple(hi[i] - lo[i] + 1 for i in range(3))
        source = dict((p, self.document.get(p)) for p in self.selection)
        if self.mask != 'all' or any(p[1] in self.locked_layers for p in source):
            raise ValueError('整体变换前请关闭蒙版并解锁选区内图层')
        # Directional metadata must not silently acquire an incorrect orientation.
        neutral = ('stone', 'stonebrick', 'planks', 'quartz_block', 'concrete', 'wool',
                   'glass', 'stained_glass', 'leaves', 'grass', 'sea_lantern',
                   'brick_block', 'sandstone', 'air', 'dirt', 'cobblestone')
        if tool.startswith(('rotate', 'mirror')):
            if any(b[0].split(':')[-1] not in neutral or
                   (b[0] == 'minecraft:quartz_block' and b[1] > 1) for b in source.values()):
                raise ValueError('此选区含方向性或未知方块；为保留朝向，请先替换为普通建材')
        mapping = {}
        for pos, value in source.items():
            q = [pos[i] - lo[i] for i in range(3)]
            if tool.startswith('rotate_y'):
                turns = int(tool[8:]) // 90
                width, depth = ext[0], ext[2]
                for unused in range(turns):
                    q[0], q[2] = depth - 1 - q[2], q[0]
                    width, depth = depth, width
            elif tool.startswith('mirror_'):
                axis = 'xyz'.index(tool[-1])
                q[axis] = ext[axis] - 1 - q[axis]
            elif tool.startswith('move_'):
                axis = 'xyz'.index(tool[-2])
                q[axis] += self.step * (1 if tool[-1] == 'p' else -1)
            elif tool.startswith('stack_'):
                axis = 'xyz'.index(tool[-1])
                q[axis] += ext[axis]
            target = tuple(q[i] + lo[i] for i in range(3))
            if not self.document.contains(target):
                raise ValueError('变换将超出建筑范围，操作已取消')
            if target[1] in self.locked_layers:
                raise ValueError('目标图层已锁定，操作已取消')
            mapping[target] = value
        changes = {} if tool.startswith('stack_') else dict((p, AIR) for p in source)
        changes.update(mapping)
        count = self._commit(BY_ID[tool][2], changes, False)
        self.selection = set(mapping)
        self.selection_revision += 1
        return count

    def _shape(self, tool, lo, hi):
        size = [hi[i] - lo[i] + 1 for i in range(3)]
        center = [(hi[i] + lo[i]) / 2. for i in range(3)]
        radii = [max(.5, v / 2.) for v in size]
        thickness = max(1, self.thickness)
        out = {}
        if tool == 'line':
            a, b = self.start, self.end
            steps = max(abs(a[i] - b[i]) for i in range(3))
            for n in range(steps + 1):
                pos = tuple(int(round(a[i] + (b[i] - a[i]) * n / float(max(1, steps)))) for i in range(3))
                out[pos] = self.material
            return out
        for p in self.selection:
            q = [p[i] - lo[i] for i in range(3)]
            edge = [q[i] < thickness or q[i] >= size[i] - thickness for i in range(3)]
            norm = [(p[i] - center[i]) / radii[i] for i in range(3)]
            ellipsoid = sum(v * v for v in norm)
            cylinder = norm[0] ** 2 + norm[2] ** 2
            inner = sum(((p[i] - center[i]) / max(.01, radii[i] - thickness)) ** 2 for i in range(3))
            inner_cyl = sum(((p[i] - center[i]) / max(.01, radii[i] - thickness)) ** 2 for i in (0, 2))
            yes = False
            if tool in ('box', 'fill'):
                yes = True
            elif tool == 'shell':
                yes = any(edge)
            elif tool == 'walls':
                yes = edge[0] or edge[2]
            elif tool == 'frame':
                yes = sum(edge) >= 2
            elif tool == 'sphere':
                yes = ellipsoid <= 1
            elif tool == 'sphere_shell':
                yes = ellipsoid <= 1 and inner >= 1
            elif tool == 'cylinder':
                yes = cylinder <= 1
            elif tool == 'tube':
                yes = cylinder <= 1 and inner_cyl >= 1
            elif tool == 'pyramid':
                f = 1. - q[1] / float(max(1, size[1]))
                yes = abs(norm[0]) <= f and abs(norm[2]) <= f
            elif tool == 'dome':
                v = norm[0] ** 2 + norm[2] ** 2 + (q[1] / float(max(1, size[1] - 1))) ** 2
                inside = ((p[0] - center[0]) / max(.01, radii[0] - thickness)) ** 2
                inside += ((p[2] - center[2]) / max(.01, radii[2] - thickness)) ** 2
                inside += (q[1] / max(.01, size[1] - 1 - thickness)) ** 2
                yes = v <= 1.03 and inside >= 1
            elif tool == 'arch':
                spring = max(0., size[1] - radii[0])
                if q[1] < spring:
                    yes = edge[0]
                else:
                    distance = math.sqrt((p[0] - center[0]) ** 2 + (q[1] - spring) ** 2)
                    yes = radii[0] - thickness <= distance <= radii[0]
            elif tool == 'stairs':
                yes = q[1] <= int(q[0] * size[1] / float(size[0]))
            elif tool == 'floor':
                yes = q[1] < thickness
            elif tool == 'roof':
                target = int((1. - abs(norm[0])) * (size[1] - 1))
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
            if tool == 'checker':
                second = sum(v // self.step for v in q) % 2 == 1
            elif tool.startswith('stripe_'):
                second = (q['xyz'.index(tool[-1])] // self.step) % 2 == 1
            elif tool == 'noise':
                second = randomizer.random() < self.ratio
            elif tool == 'gradient':
                second = randomizer.random() < q[1] / float(max(1, hi[1] - lo[1]))
            elif tool == 'brick':
                second = q[1] % 3 == 0 or (q[0] + (q[1] // 3 % 2) * self.step) % (2 * self.step + 1) == 0
            elif tool == 'lattice':
                if sum(v % (self.step + 1) == 0 for v in q) < 2:
                    out[p] = AIR
                    continue
                second = all(v % (self.step + 1) == 0 for v in q)
            out[p] = self.secondary if second else self.material
        return out

    def _finish(self, tool, lo, hi):
        doc = self.document
        out = {}
        if tool in ('hollow', 'clean_isolated', 'fill_holes'):
            for p in self.selection:
                neighbors = [doc.get(add(p, d)) != AIR for d in DIRECTIONS]
                if tool == 'hollow' and doc.get(p) != AIR and all(neighbors):
                    out[p] = AIR
                elif tool == 'clean_isolated' and doc.get(p) != AIR and not any(neighbors):
                    out[p] = AIR
                elif tool == 'fill_holes' and doc.get(p) == AIR and all(neighbors):
                    out[p] = self.material
            return out
        for x in range(lo[0], hi[0] + 1):
            for z in range(lo[2], hi[2] + 1):
                column = [(x, y, z) for y in range(lo[1], hi[1] + 1) if (x, y, z) in self.selection]
                filled = [(p, doc.get(p)) for p in column if doc.get(p) != AIR]
                if not filled:
                    continue
                if tool == 'gravity':
                    if any(p[1] in self.locked_layers for p in column) or self.mask != 'all':
                        raise ValueError('垂直压实前请关闭蒙版并解锁相关图层')
                    out.update((p, filled[i][1] if i < len(filled) else AIR) for i, p in enumerate(column))
                elif tool == 'foundation':
                    out.update((p, filled[0][1]) for p in column if p[1] < filled[0][0][1])
                elif tool == 'heightmap':
                    out.update((p, AIR) for p, unused in filled[:-1])
        return out

    def run(self, tool):
        if tool not in BY_ID:
            raise ValueError('未知工具')
        group = BY_ID[tool][1]
        if group == 'select':
            return self._select(tool)
        if not self.selection:
            raise ValueError('选区为空，请先框选或全选')
        lo, hi = bounds(self.selection)
        if group == 'transform':
            return self._transform(tool)
        if group == 'shape':
            changes = self._shape(tool, lo, hi)
        elif group == 'pattern':
            changes = self._pattern(tool, lo, hi)
        elif group == 'finish':
            changes = self._finish(tool, lo, hi)
        else:
            changes = self._edit(tool)
            if changes is None:
                return 0
        return self._commit(BY_ID[tool][2], changes)

    def _edit(self, tool):
        doc = self.document
        if tool in ('copy', 'cut'):
            self._copy()
            self.message = '已复制 %d 格' % len(self.selection)
            return dict((p, AIR) for p in self.selection) if tool == 'cut' else None
        if tool.startswith('paste'):
            if self.clipboard is None:
                raise ValueError('请先复制一个选区')
            return dict((add(p, self.start), b) for p, b in self.clipboard['blocks'].items()
                        if tool == 'paste' or b != AIR)
        if tool == 'flood':
            if self.start not in self.selection:
                raise ValueError('填充起点不在选区内')
            old = doc.get(self.start)
            visited, pending = set(), deque([self.start])
            while pending:
                p = pending.popleft()
                if p in visited or not self._writable(p) or doc.get(p) != old:
                    continue
                visited.add(p)
                pending.extend(add(p, d) for d in DIRECTIONS)
            return dict((p, self.material) for p in visited)
        out = {}
        for p in self.selection:
            old = doc.get(p)
            if tool == 'erase':
                out[p] = AIR
            elif tool == 'fill' or (tool == 'fill_air' and old == AIR):
                out[p] = self.material
            elif tool == 'replace' and old == self.source:
                out[p] = self.material
            elif tool == 'paint' and self.surface(p):
                out[p] = self.material
            elif tool == 'swap':
                if old == self.material:
                    out[p] = self.source
                elif old == self.source:
                    out[p] = self.material
        return out


def demo_document():
    """Editable modern courtyard, built from real blocks, not a preview image."""
    doc = Document((24, 16, 24), name='林间白盒 · 建筑练习')
    quartz, wood = ('minecraft:quartz_block', 0), ('minecraft:planks', 1)
    glass, grass = ('minecraft:glass', 0), ('minecraft:grass', 0)
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
            doc.blocks[(x, 2, z)] = ('minecraft:stained_glass', 9)
    for x, z in ((3, 19), (20, 19), (20, 3)):
        for y in range(1, 4):
            doc.blocks[(x, y, z)] = wood
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for y in (4, 5):
                    doc.blocks[(x + dx, y, z + dz)] = ('minecraft:leaves', 0)
    return doc
