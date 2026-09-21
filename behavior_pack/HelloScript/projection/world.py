# -*- coding: utf-8 -*-
"""Bounded world jobs. Preflight every cell; preserve a recovery journal on failure."""
from __future__ import unicode_literals
from .model import AIR, Document, add, block
from .journal import Journal
import time


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
        self.source = iter(undo) if undo is not None else (
            (add(self.origin, p), None, document.get(p)) for p in
            (document.points() if include_air else document.blocks))
        self.next_source = None
        self.undoing = undo is not None
        self.phase = 'preflight'
        self.cursor = 0
        self.plan = Journal()
        self.journal = Journal()
        self.recovery = Journal()
        self.skipped = 0
        self.error = ''
        self.done = False

    def fail(self, message):
        self.error = message
        self.phase = 'rollback'
        self.cursor = len(self.journal) - 1

    def step(self, budget=2048):
        if self.done:
            return
        try:
            # Server callbacks cannot interleave this synchronous batch. Check
            # once per bounded step, not three engine APIs for every cell.
            if self.phase in ('preflight', 'write') and not self.adapter.allowed():
                if self.phase == 'preflight':
                    self.error, self.done = '世界写入需要创造模式、操作员和建造权限', True
                else:
                    self.fail('权限发生变化，正在恢复本次修改')
                return
            self._step(budget)
        except (ValueError, TypeError, KeyError, RuntimeError, AttributeError) as error:
            message = '世界接口异常：%s' % error
            if self.phase == 'rollback':
                self.error += '；恢复未完成，请重试撤销'
                self.done = True
            elif self.journal:
                self.fail(message)
            else:
                self.error, self.done = message, True

    def _step(self, budget):
        deadline = time.time() + .006
        for unused in range(budget):
            if unused and time.time() >= deadline:
                return
            if self.phase == 'preflight':
                if self.next_source is None:
                    try:
                        self.next_source = next(self.source)
                    except StopIteration:
                        self.phase, self.cursor = 'write', 0
                        continue
                pos, before, after = self.next_source
                current = self.adapter.read(pos)
                if current is None and hasattr(self.adapter, 'ensure') and self.adapter.ensure(pos) is None:
                    return
                desired = before if self.undoing else after
                if hasattr(self.adapter, 'canonical'):
                    desired = self.adapter.canonical(desired)
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
                self.next_source = None
            elif self.phase == 'write':
                if self.cursor == len(self.plan):
                    self.done = True
                    return
                pos, before, after = self.plan[self.cursor]
                current = self.adapter.read(pos)
                if current is None and hasattr(self.adapter, 'ensure') and self.adapter.ensure(pos) is None:
                    return
                if current != before or self.adapter.protected(pos, before):
                    # Undo must also preserve edits occurring after preflight,
                    # including native leaf-state updates caused by neighbors.
                    if self.undoing and current is not None:
                        self.skipped += 1
                        self.cursor += 1
                        continue
                    self.fail('目标或权限发生变化，正在回滚本次写入')
                    continue
                try:
                    changed = self.adapter.write(pos, after)
                    actual = self.adapter.read(pos)
                except (ValueError, TypeError, KeyError, RuntimeError, AttributeError):
                    # A setter can succeed before readback fails. Include this
                    # cell in recovery rather than losing its original value.
                    self.journal.append((pos, before, after))
                    raise
                if actual is None:
                    self.journal.append((pos, before, after))
                elif actual != before:
                    self.journal.append((pos, before, actual))
                if not changed or actual != after:
                    self.fail('方块写入失败，已尝试恢复本次修改')
                    continue
                self.cursor += 1
            else:
                if self.cursor < 0:
                    self.journal = self.recovery
                    if self.recovery:
                        self.error += '；仍有 %d 格需要重试撤销' % len(self.recovery)
                    self.done = True
                    return
                pos, before, after = self.journal[self.cursor]
                current = self.adapter.read(pos)
                if current is None and hasattr(self.adapter, 'ensure') and self.adapter.ensure(pos) is None:
                    return
                if current == after and not self.adapter.protected(pos, current):
                    self.adapter.write(pos, before)
                    if self.adapter.read(pos) != before:
                        self.recovery.append((pos, before, after))
                elif current is None:
                    self.recovery.append((pos, before, after))
                self.cursor -= 1
