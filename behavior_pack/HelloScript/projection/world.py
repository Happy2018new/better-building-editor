# -*- coding: utf-8 -*-
"""Bounded world jobs. Preflight every cell; preserve a recovery journal on failure."""
from __future__ import unicode_literals
from .model import AIR, Document, add, block


def coordinate(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError('需要三个整数坐标')
    if any(type(v) is not int or abs(v) > 30000000 for v in value):
        raise ValueError('世界坐标超出范围')
    return tuple(value)


class WorldJob(object):
    """Adapter implements read / write / protected / valid / allowed, for one dimension."""
    def __init__(self, adapter, document, origin, undo=None, include_air=False):
        self.adapter = adapter
        self.origin = coordinate(origin)
        self.document = document
        self.source = list(undo) if undo is not None else [
            (add(self.origin, p), None, document.get(p)) for p in
            (document.points() if include_air else sorted(document.blocks))]
        self.undoing = undo is not None
        self.phase = 'preflight'
        self.cursor = 0
        self.plan = []
        self.journal = []
        self.recovery = []
        self.skipped = 0
        self.error = ''
        self.done = False

    def fail(self, message):
        self.error = message
        self.phase = 'rollback'
        self.cursor = len(self.journal) - 1

    def step(self, budget=128):
        if self.done:
            return
        for unused in range(budget):
            if self.phase == 'preflight':
                if not self.adapter.allowed():
                    self.error, self.done = '仅创造模式可写入世界', True
                    return
                if self.cursor == len(self.source):
                    self.phase, self.cursor = 'write', 0
                    continue
                pos, before, after = self.source[self.cursor]
                current = self.adapter.read(pos)
                desired = before if self.undoing else after
                if current is None:
                    self.error, self.done = '区域尚未加载，请靠近后重试；未写入方块', True
                    return
                if self.undoing and current != after:
                    self.skipped += 1
                elif current != desired:
                    if self.adapter.protected(pos, current) or not self.adapter.valid(desired):
                        self.error, self.done = '目标含受保护方块实体，或材质无效；未写入方块', True
                        return
                    self.plan.append((pos, current, desired))
                self.cursor += 1
            elif self.phase == 'write':
                if self.cursor == len(self.plan):
                    self.done = True
                    return
                pos, before, after = self.plan[self.cursor]
                if not self.adapter.allowed() or self.adapter.read(pos) != before or self.adapter.protected(pos, before):
                    self.fail('目标或权限发生变化，正在回滚本次写入')
                    continue
                changed = self.adapter.write(pos, after)
                actual = self.adapter.read(pos)
                if actual == after:
                    self.journal.append((pos, before, after))
                elif actual != before:
                    self.recovery.append((pos, before, actual))
                if not changed or actual != after:
                    self.fail('方块写入失败，已尝试恢复本次修改')
                    continue
                self.cursor += 1
            else:
                if self.cursor < 0:
                    self.journal = list(self.recovery)
                    if self.recovery:
                        self.error += '；仍有 %d 格需要重试撤销' % len(self.recovery)
                    self.done = True
                    return
                pos, before, after = self.journal[self.cursor]
                current = self.adapter.read(pos)
                if current == after and not self.adapter.protected(pos, current):
                    self.adapter.write(pos, before)
                    if self.adapter.read(pos) != before:
                        self.recovery.append((pos, before, after))
                elif current is None:
                    self.recovery.append((pos, before, after))
                self.cursor -= 1
