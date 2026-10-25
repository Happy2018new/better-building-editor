# -*- coding: utf-8 -*-
"""Freeze one projection/placement target and prepare its document per frame."""
from __future__ import unicode_literals
import time
import traceback
from .model import Document
from .error_text import error_text
from .projection_transform import iter_snapshot, transform_size, validate_operations
from .world import coordinate


ROTATIONS = ('', 'rotate_y90', 'rotate_y180', 'rotate_y270')
MIRRORS = ('mirror_x', 'mirror_y', 'mirror_z')
LABELS = {'rotate_y90': 'Y轴90°', 'rotate_y180': 'Y轴180°',
          'rotate_y270': 'Y轴270°', 'mirror_x': 'X镜像',
          'mirror_y': 'Y镜像', 'mirror_z': 'Z镜像'}


def current_key(session):
    return (id(session.editor), session.editor.revision,
            coordinate(session.origin), tuple(getattr(session, 'projection_transform', ())))


def describe(operations):
    return '、'.join(LABELS[operation] for operation in operations) or '原始方向'


class ProjectionTarget(object):
    def __init__(self, session):
        self.source_key = current_key(session)
        self.origin = self.source_key[2]
        self.operations = validate_operations(self.source_key[3])
        source = session.editor.document
        self.size = transform_size(source.size, self.operations)
        self.hidden = frozenset(session.preview_hidden())
        self.layer = session.editor.layer if session.solo_layer else None
        if self.operations.count('mirror_y') % 2:
            self.hidden = frozenset(source.size[1] - 1 - y for y in self.hidden)
            if self.layer is not None:
                self.layer = source.size[1] - 1 - self.layer
        self.document = None
        self.iterator = iter_snapshot(source, self.operations)

    def advance(self, budget=384):
        if self.document is not None:
            return True
        deadline = time.time() + .004
        for index in range(budget):
            step = next(self.iterator, False)
            if isinstance(step, Document):
                self.document, self.iterator = step, None
                return True
            if step is False:
                raise ValueError('投影变换未生成完整建筑')
            if index and time.time() >= deadline:
                break
        return False

    def frozen(self):
        """Detach a completed publication before a later confirmation callback."""
        if self.document is None:
            raise ValueError('投影变换尚未完成，请等待后重试')
        result = object.__new__(ProjectionTarget)
        result.source_key, result.origin = self.source_key, self.origin
        result.operations, result.size = self.operations, self.size
        result.hidden, result.layer = self.hidden, self.layer
        source = self.document
        result.document = Document(source.size, name=source.name, biome=source.biome)
        result.document.blocks = source.blocks.copy()
        result.iterator = None
        return result


class WorldApplyConfirmation(object):
    """Keep a world-write confirmation bound to its original dimension."""
    def __init__(self, bridge, target, include_air):
        self.bridge, self.target, self.include_air = bridge, target, include_air
        self.dimension = bridge.factory.CreateGame(bridge.level).GetCurrentDimension()
        self.valid = True

    def cancel(self):
        self.valid = False

    def __call__(self):
        b = self.bridge
        if (not self.valid or
                b.factory.CreateGame(b.level).GetCurrentDimension() != self.dimension):
            raise ValueError('所在维度已改变，请重新确认写入世界')
        return start(b, 'apply', self.target, self.include_air, self.dimension)


class ProjectionPreparation(object):
    """Publish a complete target or leave the previous projection untouched."""
    def __init__(self, bridge, target, action, include_air=False, expected_dimension=None):
        self.bridge, self.target, self.action = bridge, target, action
        self.include_air = include_air
        self.expected_dimension = expected_dimension

    def advance(self):
        b, target = self.bridge, self.target
        if not b.alive or b.projection_preparation is not self:
            return
        try:
            if (self.expected_dimension is not None and
                    b.factory.CreateGame(b.level).GetCurrentDimension() != self.expected_dimension):
                raise ValueError('所在维度已改变，请重新检查或确认写入世界')
            if target.document is None and not target.advance():
                b.next_frame(self.advance)
                return
            b.projection_preparation = None
            b.session.busy = False
            if self.action == 'project':
                b.project_large(target.origin, target)
            else:
                if self.action == 'check' and target.source_key != current_key(b.session):
                    raise ValueError('草稿、原点或投影变换已改变，请重新检查')
                data = {'origin': target.origin, 'document': target.document,
                        'expectedDimension': self.expected_dimension}
                if self.action == 'apply':
                    data['includeAir'] = self.include_air
                b.request(self.action, data)
        except Exception as error:
            traceback.print_exc()
            if b.projection_preparation is self:
                b.projection_preparation = None
            if self.action == 'project':
                b.projection_requested = bool(b.session.projection_active)
            b.session.busy = False
            b.session.editor.message = error_text(error)
            b.session.emit()


def start(bridge, action, target=None, include_air=False, expected_dimension=None):
    session = bridge.session
    if session.edit_job is not None or session.io_job is not None:
        raise ValueError('请等待编辑任务完成')
    if bridge.pending is not None:
        raise ValueError('请等待当前世界操作完成')
    if target is None:
        target = ProjectionTarget(session)
    if action != 'project' and expected_dimension is None:
        expected_dimension = bridge.factory.CreateGame(bridge.level).GetCurrentDimension()
    job = ProjectionPreparation(bridge, target, action, include_air, expected_dimension)
    bridge.projection_preparation = job
    if action == 'project':
        bridge.projection_requested = True
    session.busy = True
    session.editor.message = '正在准备投影变换…'
    session.emit()
    job.advance()
    return target


def placement_target(bridge):
    """Use the published projection; refuse changed, ungenerated settings."""
    if bridge.projection_preparation is not None:
        raise ValueError('投影变换正在准备，请完成后再检查或写入世界')
    work = bridge.projection_work
    if (bridge.projection_requested and work is not None and
            not work.ready and not work.error):
        raise ValueError('投影正在更新，请完成后再检查或写入世界')
    target = bridge.projection_target
    if target is not None and bridge.session.projection_active:
        if target.source_key != current_key(bridge.session):
            raise ValueError('草稿、原点或变换已改变，请先更新投影再检查或写入世界')
        return target.frozen()
    return ProjectionTarget(bridge.session)
