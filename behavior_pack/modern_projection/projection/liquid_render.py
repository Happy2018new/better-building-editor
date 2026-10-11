"""Owned liquid renderer lifetimes; no shape inference or global event listeners."""
import math
from .liquid_transport import PAYLOAD_TAG, validate_uniforms
from .storage import integer_types


def _finite_tuple(value, size, label):
    value = tuple(value)
    if len(value) != size or any(isinstance(item, bool)
            or not isinstance(item, integer_types + (float,))
            or math.isinf(item) or math.isnan(item) for item in value):
        raise ValueError('Invalid liquid ' + label)
    return value


class SkeletonLiquidRenderer(object):
    """Two caller-owned UI controls, with payloads applied before promotion.

    The containing component owns and unmounts the native PaperDolls. These
    model IDs must not be passed to RemoveFreeModel, which owns another API path.
    Call update once per existing animation frame; close before unmounting.
    """
    SETTLE_SECONDS = .075
    READY_TIMEOUT = 2.

    def __init__(self, dolls, model_component, show):
        if len(dolls) != 2:
            raise ValueError('Liquid UI renderer requires exactly two native PaperDolls')
        self.dolls, self.model_component, self.show = tuple(dolls), model_component, show
        self.front = 0
        self.groups = [None, None]
        self.poses = [None, None]
        self.ids = [None, None]
        self.uniforms = [{}, {}]
        self.visible = [None, None]
        self.pending = None
        self.started = 0.
        self.frames = 0
        self.closed = False
        self.error = None
        self.failed_request = None
        self._show(0, False)
        self._show(1, False)

    def _show(self, slot, value):
        if self.visible[slot] != value:
            self.show(slot, value)
            self.visible[slot] = value

    @staticmethod
    def _shape(group):
        return None if group is None else (group.model_name, group.uniforms[:3])

    def _render_pose(self, slot, group, pose):
        scale, rot_x, rot_y, rot_z = pose
        return self.dolls[slot].RenderSkeletonModel({
            'skeleton_model_name': group.model_name, 'scale': scale, 'render_depth': -50,
            'init_rot_x': rot_x, 'init_rot_y': rot_y, 'init_rot_z': rot_z})

    def _submit(self, slot, group, pose):
        # Hidden PaperDolls never allocate a native model ID. Mask the old
        # payload before making the preparing control drawable instead.
        old_id = self.dolls[slot].GetModelId()
        if old_id != -1:
            if old_id == self.ids[1 - slot]:
                self.error = 'Owned liquid skeleton models do not have independent IDs'
                return False
            masked = group.uniforms[3][:3] + (0.,)
            if not self.model_component.SetExtraUniformValue(old_id, 4, masked):
                self.error = 'Could not mask preparing liquid skeleton'
                return False
        self._show(slot, True)
        returned = self._render_pose(slot, group, pose)
        if not returned:
            self.error = 'Could not submit liquid skeleton model'
            self._show(slot, False)
            return False
        self.groups[slot], self.poses[slot] = group, pose
        self.ids[slot] = None
        self.uniforms[slot].clear()
        return True

    def _payload(self, slot, staging=False):
        model_id = self.dolls[slot].GetModelId()
        if model_id == -1:
            return False
        other = 1 - slot
        if self.groups[other] is not None and model_id == self.ids[other]:
            self.error = 'Owned liquid skeleton models do not have independent IDs'
            return False
        if model_id != self.ids[slot]:
            self.ids[slot] = model_id
            self.uniforms[slot].clear()
        payload = self.groups[slot].uniforms
        if staging:
            payload = payload[:3] + (payload[3][:3] + (0.,),)
        order = (4, 1, 2, 3) if staging else (1, 2, 3, 4)
        for index in order:
            value = payload[index - 1]
            if self.uniforms[slot].get(index) == value:
                continue
            if not self.model_component.SetExtraUniformValue(model_id, index, value):
                self.error = 'Could not update owned liquid skeleton uniforms'
                return False
            self.uniforms[slot][index] = value
        return True

    def _settle(self, group, pose, now):
        back = 1 - self.front
        if self._shape(self.pending[0]) != self._shape(group):
            self._show(back, False)
            self.pending = None
            return True
        self.groups[back] = group
        self.frames += 1
        if self.frames < 2 and now - self.started < self.READY_TIMEOUT:
            return False
        if not self._payload(back, staging=True):
            if not self.error and now - self.started < self.READY_TIMEOUT:
                return False
            self.error = self.error or 'Liquid skeleton model ID did not become ready'
            self._show(back, False)
            self.pending = None
            self.failed_request = (group, None)
            return False
        if self.frames < 3 or now - self.started < self.SETTLE_SECONDS:
            return False
        # Pose changes do not restart shape readiness. Apply the latest orbit
        # while the incoming bank is still masked before publishing it.
        if not self._update_pose(back, pose, staging=True):
            if not self.error and now - self.started < self.READY_TIMEOUT:
                return False
            self.error = self.error or 'Liquid skeleton pose ID did not become ready'
            self._show(back, False)
            self.pending = None
            self.failed_request = (group, None)
            return False
        if not self._payload(back):
            self._show(back, False)
            self.pending = None
            self.failed_request = (group, None)
            return False
        previous, self.front = self.front, back
        self.pending = None
        self._show(self.front, True)
        self._show(previous, False)
        return True

    def _update_pose(self, slot, pose, staging=False):
        if self.poses[slot] != pose:
            # Same-name submissions preserve IDs in the native orbit probe.
            # Reapply the payload if a replacement unexpectedly changes it.
            if not self._render_pose(slot, self.groups[slot], pose):
                self.error = 'Could not update liquid skeleton pose'
                return False
            self.poses[slot] = pose
        return self._payload(slot, staging=staging)

    def update(self, group, pose, now):
        if self.closed:
            return False
        if group is None:
            self.pending = None
            self.groups = [None, None]
            self.ids, self.poses = [None, None], [None, None]
            self.uniforms[0].clear()
            self.uniforms[1].clear()
            self.error, self.failed_request = None, None
            self._show(0, False)
            self._show(1, False)
            return True
        validate_uniforms(group.uniforms)
        pose = _finite_tuple(pose, 4, 'skeleton pose')
        if pose[0] <= 0.:
            raise ValueError('Liquid skeleton scale must be positive')
        request = (group, pose)
        failed = self.failed_request
        latched = failed in (request, (group, 'appearance')) or (failed is not None
            and failed[1] is None and self._shape(failed[0]) == self._shape(group))
        previous_error = self.error
        if not latched:
            self.error, self.failed_request = None, None
        if self.groups[self.front] is not None:
            previous_group = self.groups[self.front]
            self.groups[self.front] = (group if self._shape(previous_group) == self._shape(group)
                else previous_group._replace(uniforms=previous_group.uniforms[:3] + group.uniforms[3:]))
            if not self._update_pose(self.front, pose):
                self.groups[self.front] = previous_group
                if self.error:
                    self.failed_request = ((group, 'appearance') if 'uniforms' in self.error else request)
                return False
            if latched:
                self.error = previous_error
        if latched:
            return False
        if self.pending is not None and not self._settle(group, pose, now):
            return False
        if self._shape(self.groups[self.front]) != self._shape(group):
            back = 1 - self.front
            self._show(back, False)
            self.error = None
            if not self._submit(back, group, pose):
                self.failed_request = (group, None)
                return False
            self.pending, self.started, self.frames = request, now, 0
            return False
        ready = self._payload(self.front)
        if ready:
            self._show(self.front, True)
        elif self.error:
            self.failed_request = request
        return ready

    def retry(self):
        self.error, self.failed_request = None, None

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.pending = None
        self._show(0, False)
        self._show(1, False)
        self.groups, self.ids = [None, None], [None, None]
        self.uniforms[0].clear()
        self.uniforms[1].clear()


class WorldLiquidRenderer(object):
    """Free skeleton models, bounded to two generations of owned groups.

    Scale and rotation are explicit version-profile inputs. PaperDoll model IDs
    never enter this owner, and block-geometry attachment APIs are not used.
    """
    SETTLE_SECONDS = .075
    CREATIONS_PER_FRAME = 8

    def __init__(self, bridge, max_groups, dimension, scale, rotation):
        if isinstance(max_groups, bool) or not isinstance(max_groups, integer_types) or max_groups < 1:
            raise ValueError('Liquid renderer needs an explicit positive group budget')
        if isinstance(dimension, bool) or not isinstance(dimension, integer_types) or dimension < 0:
            raise ValueError('Liquid models require an explicit world dimension')
        self.scale = _finite_tuple(scale, 3, 'world scale')
        self.rotation = _finite_tuple(rotation, 3, 'world rotation')
        if any(axis <= 0. for axis in self.scale):
            raise ValueError('Liquid world scale must be positive')
        self.bridge, self.max_groups = bridge, max_groups
        self.dimension = dimension
        self.model = bridge.factory.CreateModel(bridge.level)
        self.active, self.staging = {}, {}
        self.retired = {}
        self.wanted = self.queue = None
        self.anchor = None
        self.visible = True
        self.closed = False
        self.error = None
        self.cleanup_errors = []

    @staticmethod
    def center(anchor, origin):
        return tuple(anchor[axis] + origin[axis] + 2. for axis in range(3))

    def _destroy(self, records):
        self.retired.update((record['model_id'], record) for record in records)
        for record in records:
            model_id = record['model_id']
            if not self._show(record, False):
                self.cleanup_errors.append((model_id, 'hide'))
            if not self.model.RemoveFreeModel(model_id):
                self.cleanup_errors.append((model_id, 'remove'))
                continue
            self.retired.pop(model_id, None)

    def retry_retired(self):
        self.cleanup_errors = []
        self._destroy(tuple(self.retired.values()))
        return not self.retired

    def _show(self, record, visible):
        if record['visible'] == visible:
            return True
        value = record['group'].uniforms[3]
        if not visible:
            value = value[:3] + (0.,)
        if not self.model.SetExtraUniformValue(record['model_id'], 4, value):
            return False
        record['visible'] = visible
        return True

    def _publish_visibility(self, records, visible):
        previous = []
        for record in records:
            old = record['visible']
            if not self._show(record, visible):
                for restored, was_visible in reversed(previous):
                    if not self._show(restored, was_visible):
                        self.cleanup_errors.append((restored['model_id'], 'visibility_rollback'))
                return False
            previous.append((record, old))
        return True

    def _cancel(self):
        self._destroy(tuple(self.staging.values()))
        self.staging.clear()
        self.wanted = self.queue = None

    def _fail(self, message):
        self.error = message
        self._cancel()
        return False

    def begin(self, groups, anchor, now):
        if self.closed or not self.bridge.alive:
            return False
        groups = tuple(groups)
        if len(groups) > self.max_groups:
            raise ValueError('Liquid render plan exceeds its owned group budget')
        keys = set()
        for group in groups:
            validate_uniforms(group.uniforms)
            if group.uniforms[3][0] != PAYLOAD_TAG:
                raise ValueError('World liquid models cannot receive a UI depth packet')
            _finite_tuple(group.origin, 3, 'world group origin')
            if group.key in keys or not group.model_name:
                raise ValueError('Invalid or duplicate liquid render group')
            keys.add(group.key)
        anchor = _finite_tuple(anchor, 3, 'world anchor')
        self._cancel()
        self.retry_retired()
        created = sum(self.active.get(group.key, {}).get('group') != group for group in groups)
        if len(self.active) + len(self.retired) + created > self.max_groups * 2:
            self.error = 'Retired liquid models still consume the owned group budget'
            return False
        self.error = None
        if not self.follow(anchor):
            return False
        self.wanted = groups
        pending = tuple(group for group in groups if self.active.get(group.key, {}).get('group') != group)
        self.queue = iter(pending) if pending else None
        if self.queue is None:
            return self._promote()
        return True

    def _create(self, group, now):
        model_id = self.model.CreateFreeModel(group.model_name, self.dimension)
        if not model_id:
            return self._fail('Could not create owned liquid model')
        if (model_id in self.retired or any(record['model_id'] == model_id for record in
                tuple(self.active.values()) + tuple(self.staging.values()))):
            return self._fail('Owned liquid models do not have independent IDs')
        record = {'group': group, 'model_id': model_id, 'anchor': self.anchor,
                  'visible': None, 'bound_at': now, 'frames': 0}
        self.staging[group.key] = record
        if not self._show(record, False):
            return self._fail('Could not mask preparing liquid model')
        # Native free models otherwise use a one-block culling box, although
        # decoded vertices can fill this complete four-block logical batch.
        if not self.model.SetFreeModelBoundingBox(model_id, (-2.,) * 3, (2.,) * 3):
            return self._fail('Could not bound preparing liquid model')
        if not (self.model.SetFreeModelScale(model_id, *self.scale) and
                self.model.SetFreeModelRot(model_id, *self.rotation) and
                self.model.SetFreeModelPos(model_id, *self.center(self.anchor, group.origin))):
            return self._fail('Could not position preparing liquid model')
        for index, value in enumerate(group.uniforms[:3], 1):
            if not self.model.SetExtraUniformValue(model_id, index, value):
                return self._fail('Could not update owned liquid model uniforms')
        return True

    def _promote(self):
        incoming = dict((group.key, self.staging.get(group.key) or self.active[group.key])
                        for group in self.wanted)
        if not self._publish_visibility(tuple(incoming.values()), self.visible):
            return self._fail('Could not show ready liquid model')
        retired = tuple(record for key, record in self.active.items()
                        if incoming.get(key) is not record)
        self.active, self.staging, self.wanted = incoming, {}, None
        self._destroy(retired)
        return True

    def advance(self, now):
        if self.closed:
            return self.retry_retired()
        if not self.bridge.alive:
            self.close()
            return False
        self.retry_retired()
        if self.wanted is None:
            return self.error is None
        for unused in range(self.CREATIONS_PER_FRAME) if self.queue is not None else ():
            group = next(self.queue, None)
            if group is None:
                self.queue = None
                break
            if not self._create(group, now):
                return False
        ready = self.queue is None
        for record in tuple(self.staging.values()):
            record['frames'] += 1
            if record['frames'] < 3 or now - record['bound_at'] < self.SETTLE_SECONDS:
                ready = False
        return self._promote() if ready else False

    def follow(self, anchor):
        if self.closed:
            return False
        anchor = _finite_tuple(anchor, 3, 'world anchor')
        moved = []
        for record in tuple(self.active.values()) + tuple(self.staging.values()):
            if record['anchor'] == anchor:
                continue
            old = record['anchor']
            if not self.model.SetFreeModelPos(record['model_id'], *self.center(anchor, record['group'].origin)):
                for restored, previous in reversed(moved):
                    if self.model.SetFreeModelPos(restored['model_id'],
                                                 *self.center(previous, restored['group'].origin)):
                        restored['anchor'] = previous
                    else:
                        self.cleanup_errors.append((restored['model_id'], 'position_rollback'))
                self.error = 'Could not move owned liquid model'
                return False
            record['anchor'] = anchor
            moved.append((record, old))
        self.anchor = anchor
        return True

    def set_visible(self, visible):
        if self.closed or bool(visible) == self.visible:
            return not self.closed
        if not self._publish_visibility(tuple(self.active.values()), bool(visible)):
            self.error = 'Could not update owned liquid visibility'
            return False
        self.visible = bool(visible)
        return True

    def close(self):
        if not self.closed:
            self.closed = True
            self._cancel()
            self._destroy(tuple(self.active.values()))
            self.active.clear()
        return not self.retired
