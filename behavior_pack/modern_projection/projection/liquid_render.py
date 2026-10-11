"""Owned liquid renderer lifetimes; no shape inference or global event listeners."""
import math
from .liquid_transport import validate_uniforms
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

    def _submit(self, slot, group, pose):
        scale, rot_x, rot_y, rot_z = pose
        returned = self.dolls[slot].RenderSkeletonModel({
            'skeleton_model_name': group.model_name, 'scale': scale, 'render_depth': -50,
            'init_rot_x': rot_x, 'init_rot_y': rot_y, 'init_rot_z': rot_z})
        if not returned:
            self.error = 'Could not submit liquid skeleton model'
            return False
        self.groups[slot], self.poses[slot] = group, pose
        self.ids[slot] = None
        self.uniforms[slot].clear()
        return True

    def _payload(self, slot):
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
        for index, value in enumerate(self.groups[slot].uniforms, 1):
            if self.uniforms[slot].get(index) == value:
                continue
            if not self.model_component.SetExtraUniformValue(model_id, index, value):
                self.error = 'Could not update owned liquid skeleton uniforms'
                return False
            self.uniforms[slot][index] = value
        return True

    def _settle(self, group, pose, now):
        back = 1 - self.front
        if self.pending != group:
            self._show(back, False)
            self.pending = None
            return True
        self.frames += 1
        if self.frames < 2 and now - self.started < self.READY_TIMEOUT:
            return False
        if not self._payload(back):
            if not self.error and now - self.started < self.READY_TIMEOUT:
                return False
            self.error = self.error or 'Liquid skeleton model ID did not become ready'
            self._show(back, False)
            self.pending = None
            self.failed_request = (group, pose)
            return False
        if self.frames < 3 or now - self.started < self.SETTLE_SECONDS:
            return False
        previous, self.front = self.front, back
        self.pending = None
        self._show(self.front, True)
        self._show(previous, False)
        return True

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
        if self.failed_request == request:
            return False
        self.error, self.failed_request = None, None
        if self.pending is not None and not self._settle(group, pose, now):
            return False
        if self.groups[self.front] != group:
            back = 1 - self.front
            self._show(back, False)
            self.error = None
            if not self._submit(back, group, pose):
                self.failed_request = request
                return False
            self.pending, self.started, self.frames = group, now, 0
            return False
        if self.poses[self.front] != pose:
            self.error = None
            if not self._submit(self.front, group, pose):
                self.failed_request = request
                return False
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
    """Independent actor uniforms, bounded to two generations of owned groups."""
    ACTOR_DELAY = .2
    SETTLE_SECONDS = .075

    def __init__(self, bridge, max_groups):
        if isinstance(max_groups, bool) or not isinstance(max_groups, integer_types) or max_groups < 1:
            raise ValueError('Liquid renderer needs an explicit positive group budget')
        self.bridge, self.max_groups = bridge, max_groups
        self.active, self.staging = {}, {}
        self.wanted = None
        self.anchor = None
        self.visible = True
        self.closed = False
        self.error = None
        self.cleanup_errors = []

    @staticmethod
    def offset(anchor, origin):
        # Same centered native model/180-degree convention as OccupancyShader.
        return (anchor[0] - origin[0] - .5, origin[1] - anchor[1],
                anchor[2] - origin[2] - .5)

    def _destroy(self, records):
        for record in records:
            if record['attached'] and not record['render'].DeleteActorBlockGeometry(record['group'].model_name):
                self.cleanup_errors.append((record['entity'], record['group'].model_name))
            self.bridge.system.DestroyClientEntity(record['entity'])

    def _cancel(self):
        self._destroy(tuple(self.staging.values()))
        self.staging.clear()
        self.wanted = None

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
            _finite_tuple(group.origin, 3, 'world group origin')
            if group.key in keys or not group.model_name:
                raise ValueError('Invalid or duplicate liquid render group')
            keys.add(group.key)
        anchor = _finite_tuple(anchor, 3, 'world anchor')
        self._cancel()
        self.error = None
        if not self.follow(anchor):
            return False
        self.wanted = groups
        for group in groups:
            old = self.active.get(group.key)
            if old is not None and old['group'] == group:
                continue
            entity = self.bridge.system.CreateClientEntityByTypeStr(
                b'modern_projection:anchor', self.anchor, (0., 0.))
            if not entity:
                return self._fail('Could not create owned liquid actor')
            self.staging[group.key] = {
                'group': group, 'entity': entity,
                'render': self.bridge.factory.CreateActorRender(entity),
                'position': self.bridge.factory.CreatePos(entity),
                'anchor': self.anchor, 'attached': False,
                'ready_at': now + self.ACTOR_DELAY, 'bound_at': None, 'frames': 0}
        if not self.staging:
            return self._promote()
        return True

    def _bind(self, record, now):
        render, group = record['render'], record['group']
        if not render.SetNotRenderAtAll(True):
            return self._fail('Could not hide preparing liquid actor')
        if not render.AddActorBlockGeometry(group.model_name, self.offset(self.anchor, group.origin), (0., 180., 0.)):
            return self._fail('Could not attach liquid carrier')
        record['attached'] = True
        if not (render.EnableActorBlockGeometryTransparent(group.model_name, True)
                and render.SetActorBlockGeometryTransparency(group.model_name, 1.)):
            return self._fail('Could not configure liquid carrier transparency')
        for index, value in enumerate(group.uniforms, 1):
            if not render.SetEntityExtraUniforms(index, value):
                return self._fail('Could not update owned liquid actor uniforms')
        record['bound_at'], record['frames'] = now, 0
        return True

    def _promote(self):
        incoming = dict((group.key, self.staging.get(group.key) or self.active[group.key])
                        for group in self.wanted)
        for record in incoming.values():
            if not record['render'].SetNotRenderAtAll(not self.visible):
                return self._fail('Could not show ready liquid actor')
        retired = tuple(record for key, record in self.active.items()
                        if incoming.get(key) is not record)
        self.active, self.staging, self.wanted = incoming, {}, None
        self._destroy(retired)
        return True

    def advance(self, now):
        if self.closed:
            return False
        if not self.bridge.alive:
            self.close()
            return False
        if self.wanted is None:
            return self.error is None
        ready = True
        for record in tuple(self.staging.values()):
            if now < record['ready_at']:
                ready = False
                continue
            if record['bound_at'] is None:
                if not self._bind(record, now):
                    return False
                ready = False
                continue
            record['frames'] += 1
            if record['frames'] < 3 or now - record['bound_at'] < self.SETTLE_SECONDS:
                ready = False
        return self._promote() if ready else False

    def follow(self, anchor):
        if self.closed:
            return False
        anchor = _finite_tuple(anchor, 3, 'world anchor')
        for record in tuple(self.active.values()) + tuple(self.staging.values()):
            if record['anchor'] == anchor:
                continue
            if not record['position'].SetPosForClientEntity(anchor):
                self.error = 'Could not move owned liquid actor'
                return False
            if record['attached'] and not record['render'].SetActorBlockGeometryOffset(
                    record['group'].model_name, self.offset(anchor, record['group'].origin)):
                self.error = 'Could not compensate liquid actor position'
                return False
            record['anchor'] = anchor
        self.anchor = anchor
        return True

    def set_visible(self, visible):
        if self.closed or bool(visible) == self.visible:
            return not self.closed
        for record in self.active.values():
            if not record['render'].SetNotRenderAtAll(not visible):
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
        return not self.cleanup_errors
