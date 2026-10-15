"""Logical liquid batches share the editor's affine camera and depth plane."""
from collections import namedtuple

from .camera import render_bounds
from .cell import text_type
from .liquid_render import SkeletonLiquidRenderer
from .liquid_transport import RenderGroup, with_preview_distance
from .storage import integer_types

LiquidView = namedtuple('LiquidView', 'position size distance clipped')
_IMMUTABLE_TYPES = frozenset(integer_types + (float, str, text_type, type(None)))


def _immutable(value):
    if type(value) is tuple:
        return all(_immutable(item) for item in value)
    return type(value) in _IMMUTABLE_TYPES


def group_view(origin, camera, scene_origin, scene_size, viewport, unit):
    """A four-cube is centered on its resource origin plus two logical blocks."""
    width, height = viewport
    center = tuple(origin[axis] + 2. - scene_origin[axis] for axis in range(3))
    right, up, toward = camera.basis()
    x, y = camera.project(center, scene_size, width, height, unit)
    radius_x = unit * 2. * sum(abs(axis) for axis in right)
    radius_y = unit * 2. * sum(abs(axis) for axis in up)
    offscreen = x + radius_x < 0. or x - radius_x > width or y + radius_y < 0. or y - radius_y > height
    plane = camera.depth_plane(scene_size)
    limit = plane[1] if plane else sum(scene_size[axis] * max(0., toward[axis]) for axis in range(3)) + .5
    distance = sum(center[axis] * toward[axis] for axis in range(3)) - limit
    radius_depth = 2. * sum(abs(axis) for axis in toward)
    position, size = render_bounds(width, height, (x - width / 2., y - height / 2.))
    return LiquidView(position, size, distance, offscreen or distance - radius_depth >= 0.)


class LiquidControls(object):
    """Scene-owned controls; their containing components own native unmounting."""
    def __init__(self, registry, model_component, renderer_factory=SkeletonLiquidRenderer,
                 distance_adapter=with_preview_distance):
        self.registry, self.model_component = registry, model_component
        self.renderer_factory, self.distance_adapter = renderer_factory, distance_adapter
        self.pending = False
        self.error = None
        self.closed = False

    def _renderer(self, entry):
        renderer = entry.get('renderer')
        if renderer is not None:
            return renderer
        surfaces = entry['surfaces']
        def show(slot, visible):
            control = surfaces[slot].current
            if control is not None:
                return control.SetVisible(visible, False)
        renderer = self.renderer_factory(
            tuple(ref.current.asNeteasePaperDoll() for ref in entry['dolls']),
            self.model_component, show)
        entry['renderer'] = renderer
        return renderer

    def _displayed(self, entry, group, distance):
        cached = entry.get('distance_request')
        if (self.distance_adapter is with_preview_distance and cached is not None
                and cached[0] is group and type(cached[1]) is type(distance)
                and cached[1] == distance):
            return cached[2]
        entry.pop('distance_request', None)
        displayed = self.distance_adapter(group, distance)
        # Namedtuple fields can still contain mutable values supplied by callers.
        if (self.distance_adapter is with_preview_distance and type(group) is RenderGroup
                and _immutable(distance) and all(_immutable(value) for value in group)):
            entry['distance_request'] = group, distance, displayed
        return displayed

    def update(self, groups, view_at, pose_at, clip_offset, now):
        if self.closed:
            return False
        self.pending, self.error = any(key not in self.registry for key in groups), None
        for key, entry in tuple(self.registry.items()):
            dolls, surfaces = entry['dolls'], entry['surfaces']
            if not all(ref.current for ref in dolls + surfaces):
                entry.pop('distance_request', None)
                self.pending = True
                continue
            renderer = self._renderer(entry)
            if not renderer.restore_publication():
                self.pending = True
                self.error = self.error or renderer.error
                entry.pop('ready_request', None)
                entry.pop('distance_request', None)
                continue
            group = groups.get(key)
            if group is None:
                entry.pop('distance_request', None)
                renderer.update(None, None, now)
                entry.pop('ready_request', None)
                entry.pop('validation_error', None)
                continue
            failed = entry.get('validation_error')
            if failed is not None and failed[0] == group:
                self.pending = True
                self.error = self.error or failed[1]
                continue
            entry.pop('validation_error', None)
            try:
                view = view_at(group.origin)
                if view is None or view.clipped:
                    entry.pop('distance_request', None)
                    renderer.update(None, None, now)
                    entry.pop('ready_request', None)
                    continue
                displayed = self._displayed(entry, group, view.distance)
                pose = self.renderer_factory.validate(displayed, pose_at(view))
            except ValueError as error:
                entry.pop('distance_request', None)
                message = str(error) or 'Invalid liquid UI request'
                entry['validation_error'] = group, message
                self.pending = True
                self.error = self.error or message
                continue
            if entry.get('clip_offset') != clip_offset:
                for ref in surfaces:
                    ref.current.SetPosition(clip_offset)
                entry['clip_offset'] = clip_offset
            geometry = view.position, view.size
            if entry.get('geometry') != geometry:
                for ref in dolls:
                    ref.current.SetPosition(view.position)
                    ref.current.SetSize(view.size)
                entry['geometry'] = geometry
            request = displayed, pose
            if entry.get('ready_request') == request:
                continue
            if renderer.update(displayed, pose, now):
                entry['ready_request'] = request
            else:
                entry.pop('ready_request', None)
                self.pending = True
            if renderer.error and self.error is None:
                self.error = renderer.error
        return not self.pending

    def retry(self):
        self.error = None
        for entry in self.registry.values():
            renderer = entry.get('renderer')
            if renderer is not None:
                renderer.retry()
            entry.pop('ready_request', None)
            entry.pop('validation_error', None)
            entry.pop('distance_request', None)

    def invalidate(self):
        for entry in self.registry.values():
            renderer = entry.get('renderer')
            if renderer is not None:
                renderer.update(None, None, 0.)
            entry.pop('geometry', None)
            entry.pop('clip_offset', None)
            entry.pop('ready_request', None)
            entry.pop('validation_error', None)
            entry.pop('distance_request', None)

    def close(self):
        self.closed = True
        for entry in self.registry.values():
            entry.pop('distance_request', None)
            renderer = entry.get('renderer')
            if renderer is not None:
                renderer.close()
