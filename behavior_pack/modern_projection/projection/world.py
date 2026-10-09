# -*- coding: utf-8 -*-
"""Bounded world jobs that continue after individual cell write failures."""
from __future__ import unicode_literals
from .model import Document, add
import time


def coordinate(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError('需要三个整数坐标')
    if any(type(v) is not int or abs(v) > 30000000 for v in value):
        raise ValueError('世界坐标超出范围')
    return tuple(value)


class WorldJob(object):
    """Adapter implements write for one dimension."""
    def __init__(self, adapter, document, origin, include_air=False):
        self.adapter = adapter
        self.origin = coordinate(origin)
        self.document = document
        points = document.points() if include_air else iter(document.blocks)
        self.source = ((add(self.origin, pos), document.get(pos)) for pos in points)
        self.total = document.volume if include_air else len(document.blocks)
        self.cursor = 0
        self.written = 0
        self.failed = 0
        self.failures = []
        self.error = ''
        self.cancelled = False
        self.done = False

    def cancel(self, message='操作已取消'):
        if self.done:
            return
        self.cancelled = True
        self.done = True
        self.error = '%s：已写入 %d 格，%d 格失败，停止后续写入' % (
            message, self.written, self.failed)

    def step(self, budget=2048):
        if self.done:
            return
        deadline = time.time() + .006
        for unused in range(budget):
            if unused and time.time() >= deadline:
                return
            try:
                pos, value = next(self.source)
            except StopIteration:
                self.done = True
                if self.failed:
                    self.error = '写入完成：%d 格成功，%d 格失败' % (
                        self.written, self.failed)
                return
            self.cursor += 1
            try:
                result = self.adapter.write(pos, value, self.origin)
            except (ValueError, TypeError, KeyError, RuntimeError, AttributeError) as error:
                result = False
                detail = '%s' % error
            else:
                detail = '写入接口返回失败'
            if not result:
                self.failed += 1
                if len(self.failures) < 32:
                    self.failures.append((pos, detail))
                continue
            self.written += 1

        if self.cursor >= self.total:
            self.done = True
            if self.failed:
                self.error = '写入完成：%d 格成功，%d 格失败' % (
                    self.written, self.failed)
