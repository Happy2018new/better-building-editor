# -*- coding: utf-8 -*-
"""Y-up orbit camera and bounded voxel picking, independent of the game SDK."""
from __future__ import division
import math


def clamp(value, low, high):
    return max(low, min(high, value))


def behind_plane(pos, plane):
    return plane is None or sum((pos[i] + .5) * plane[0][i] for i in range(3)) <= plane[1] + 1e-7


def render_bounds(width, height, pan):
    """Move the native centre without allowing its UI rectangle to be culled."""
    px, py = pan
    return ((px-abs(px), py-abs(py)), (width+2*abs(px), height+2*abs(py)))


def zoom_label(zoom):
    if zoom < 10:
        return '%d%%' % int(round(zoom * 100))
    if zoom < 100:
        return u'%.1f\u00d7' % zoom
    if zoom < 10000:
        return u'%.0f\u00d7' % zoom
    return u'%.0e\u00d7' % zoom


class PinchZoom(object):
    """Absolute two-contact zoom, anchored at their midpoint with no mesh work."""
    def __init__(self, camera, points, width, height, minimum_distance=2.):
        self.camera = camera
        self.width, self.height = max(1., width), max(1., height)
        self.minimum_distance = minimum_distance
        self.baseline = None
        self.rebase(points)

    def rebase(self, points):
        a, b = points
        distance = math.hypot(b[0]-a[0], b[1]-a[1])
        if distance >= self.minimum_distance:
            anchor = ((a[0]+b[0])/(2.*self.width)-.5, (a[1]+b[1])/(2.*self.height)-.5)
            self.baseline = (distance, self.camera.zoom, self.camera.pan, anchor)

    def move(self, points):
        if self.baseline is None:
            self.rebase(points)
            return
        distance, zoom, pan, anchor = self.baseline
        a, b = points
        requested = zoom * math.hypot(b[0]-a[0], b[1]-a[1]) / distance
        if math.isnan(requested) or math.isinf(requested):
            return
        camera = self.camera
        camera.zoom = max(.25, requested)
        midpoint = ((a[0]+b[0])/(2.*self.width)-.5, (a[1]+b[1])/(2.*self.height)-.5)
        camera.pan = camera.pan_target = tuple(midpoint[i]+(pan[i]-anchor[i])*camera.zoom/zoom for i in range(2))
        camera.target = (camera.yaw, camera.pitch, camera.zoom)
        camera.velocity = (0., 0.)


class OrbitCamera(object):
    def __init__(self, yaw=35., pitch=25., zoom=1.):
        self.yaw, self.pitch, self.zoom = yaw, pitch, zoom
        self.target = (yaw, pitch, zoom)
        self.velocity = (0., 0.)
        self.dragging = False
        self.pan = (0., 0.)
        self.pan_target = self.pan
        self.pivot = None
        self.depth = self.depth_target = 0.

    def center(self, size):
        return self.pivot if self.pivot is not None else tuple(v / 2. for v in size)

    def set_pivot(self, point, size, width, height, unit):
        """Rebase the orbit without moving any displayed point, even mid-zoom."""
        old = self.center(size)
        self.pivot = tuple(point) if point is not None else None
        new = self.center(size)
        right, up, unused = self.basis()
        delta = tuple(new[i] - old[i] for i in range(3))
        shift = (unit * sum(delta[i] * right[i] for i in range(3)) / width,
                 -unit * sum(delta[i] * up[i] for i in range(3)) / height)
        self.pan = tuple(self.pan[i] + shift[i] for i in range(2))
        self.pan_target = tuple(self.pan_target[i] + shift[i] * self.target[2] / self.zoom for i in range(2))

    def reset(self):
        self.yaw, self.pitch, self.zoom = 35., 25., 1.
        self.target = (35., 25., 1.)
        self.pan = self.pan_target = (0., 0.)
        self.pivot = None
        self.depth = self.depth_target = 0.
        self.velocity = (0., 0.)
        self.dragging = False

    def aim(self, yaw, pitch, zoom):
        self.target = (self.yaw + (yaw - self.yaw + 180.) % 360. - 180.,
                       clamp(pitch, -85., 90.), max(.25, zoom))
        self.velocity = (0., 0.)

    def zoom_at(self, zoom, x, y, width, height):
        """Keep the ray under the cursor fixed throughout smooth zooming."""
        zoom = max(.25, zoom)
        anchor = (x / width - .5, y / height - .5)
        ratio = zoom / self.zoom
        self.pan_target = tuple(anchor[i] + (self.pan[i] - anchor[i]) * ratio for i in range(2))
        self.aim(self.yaw, self.pitch, zoom)

    def centered_pan(self, point, size, width, height, unit):
        right, up, unused = self.basis()
        center = self.center(size)
        delta = [point[i] - center[i] for i in range(3)]
        return (-unit * sum(delta[i] * right[i] for i in range(3)) / width,
                unit * sum(delta[i] * up[i] for i in range(3)) / height)

    def drag(self, dx, dy, dt, sensitivity=1.):
        # Grab the model: a rightward pointer movement brings its front to the
        # right. Camera azimuth has the opposite sign; inertia uses this delta too.
        yaw = -dx * .42 * sensitivity
        pitch = dy * .42 * sensitivity
        self.yaw += yaw
        self.pitch = clamp(self.pitch + pitch, -85., 90.)
        self.target = (self.yaw, self.pitch, self.zoom)
        dt = max(.008, dt)
        self.velocity = (clamp(yaw / dt, -240., 240.), clamp(pitch / dt, -180., 180.))

    def advance(self, dt, motion=True):
        dt = clamp(dt, 0., .05)
        alpha = 1. - math.exp(-16. * dt) if motion else 1.
        self.pan = tuple(b if abs(b-a) < .00001 else a + (b-a)*alpha
                         for a, b in zip(self.pan, self.pan_target))
        self.depth = self.depth_target if abs(self.depth_target-self.depth) < .0001 else self.depth + (self.depth_target-self.depth)*alpha
        before = (self.yaw, self.pitch, self.zoom)
        if not self.dragging:
            if not motion:
                self.velocity = (0., 0.)
            decay = math.exp(-8. * dt) if motion else 0.
            vx, vy = self.velocity
            if abs(vx) + abs(vy) > .2:
                distance = (1. - decay) / 8.
                self.yaw += vx * distance
                self.pitch = clamp(self.pitch + vy * distance, -85., 90.)
                self.velocity = (vx * decay, vy * decay)
                self.target = (self.yaw, self.pitch, self.zoom)
            else:
                self.velocity = (0., 0.)
            alpha = 1. - math.exp(-16. * dt) if motion else 1.
            self.yaw += (self.target[0] - self.yaw) * alpha
            self.pitch += (self.target[1] - self.pitch) * alpha
            self.zoom += (self.target[2] - self.zoom) * alpha
            if max(abs(a - b) for a, b in zip((self.yaw, self.pitch, self.zoom), self.target)) < .0001:
                self.yaw, self.pitch, self.zoom = self.target
        return before != (self.yaw, self.pitch, self.zoom)

    def render_angles(self):
        # Netease 3.9 accepts floats but truncates native init_rot_* to integers.
        # Round once here, then use those exact angles for rendering and picking.
        # Keep the continuous pose/velocity for smooth drag and zoom integration.
        return (int(math.floor(self.yaw + .5)), int(math.floor(self.pitch + .5)))

    def basis(self):
        angles = self.render_angles()
        if getattr(self, '_basis_angles', None) == angles:
            return self._basis_value
        yaw, pitch = [math.radians(v) for v in angles]
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        self._basis_angles = angles
        self._basis_value = ((cy, 0., -sy), (-sy * sp, cp, -cy * sp), (sy * cp, sp, cy * cp))
        return self._basis_value

    def projection(self, size, width, height, unit):
        """Freeze affine coefficients once for a frame's tiles and line vertices."""
        key = (self.render_angles(), self.pan, self.pivot, size, width, height, unit)
        if getattr(self, '_projection_key', None) != key:
            right, up, unused = self.basis()
            center = self.center(size)
            self._projection_key = key
            self._projection_value = (tuple(unit*v for v in right), tuple(-unit*v for v in up),
                width*(.5+self.pan[0])-unit*sum(center[i]*right[i] for i in range(3)),
                height*(.5+self.pan[1])+unit*sum(center[i]*up[i] for i in range(3)))
        return self._projection_value

    def projector(self, size, width, height, unit):
        rx, uy, tx, ty = self.projection(size, width, height, unit)
        def project(point):
            return (tx+point[0]*rx[0]+point[1]*rx[1]+point[2]*rx[2],
                    ty+point[0]*uy[0]+point[1]*uy[1]+point[2]*uy[2])
        return project

    def project(self, point, size, width, height, unit):
        rx, uy, tx, ty = self.projection(size, width, height, unit)
        return (tx+point[0]*rx[0]+point[1]*rx[1]+point[2]*rx[2],
                ty+point[0]*uy[0]+point[1]*uy[1]+point[2]*uy[2])

    def depth_plane(self, size):
        if self.depth <= .0001:
            return None
        toward = self.basis()[2]
        far = sum(size[i] * max(0., toward[i]) for i in range(3)) + .5
        return toward, far - self.depth

    def ray(self, x, y, size, width, height, unit):
        right, up, toward = self.basis()
        u, v = (x - width * (.5 + self.pan[0])) / unit, (height * (.5 + self.pan[1]) - y) / unit
        distance = sum(size) + 4.
        center = self.center(size)
        origin = tuple(center[i] + u * right[i] + v * up[i] + distance * toward[i] for i in range(3))
        plane = self.depth_plane(size)
        if plane is not None:
            shift = sum(origin[i]*toward[i] for i in range(3))-plane[1]
            origin = tuple(origin[i]-max(0.,shift)*toward[i] for i in range(3))
        return origin, tuple(-a for a in toward)


def raycast(document, origin, direction, visible=None):
    """Grid DDA returns the nearest visible voxel and its entered face normal."""
    near, far, normal = 0., float('inf'), (0, 0, 0)
    for axis in range(3):
        if abs(direction[axis]) < 1e-9:
            if not 0 <= origin[axis] < document.size[axis]:
                return None
            continue
        a = -origin[axis] / direction[axis]
        b = (document.size[axis] - origin[axis]) / direction[axis]
        entry, leave = min(a, b), max(a, b)
        if entry > near:
            near = entry
            normal = tuple((-1 if direction[axis] > 0 else 1) if i == axis else 0 for i in range(3))
        far = min(far, leave)
    if far < near:
        return None
    point = [origin[i] + (near + 1e-7) * direction[i] for i in range(3)]
    cell = [int(math.floor(v)) for v in point]
    step = [1 if d > 0 else -1 for d in direction]
    delta = [abs(1. / d) if abs(d) > 1e-9 else float('inf') for d in direction]
    crossing = [((cell[i] + (1 if step[i] > 0 else 0) - origin[i]) / direction[i]
                 if abs(direction[i]) > 1e-9 else float('inf')) for i in range(3)]
    for unused in range(sum(document.size) + 3):
        pos = tuple(cell)
        if not document.contains(pos):
            return None
        if pos in document.blocks and (visible is None or visible(pos)):
            return pos, normal
        axis = min(range(3), key=lambda i: crossing[i])
        if crossing[axis] > far + 1e-7:
            return None
        cell[axis] += step[axis]
        normal = tuple(-step[axis] if i == axis else 0 for i in range(3))
        crossing[axis] += delta[axis]
    return None


def layer_hit(document, origin, direction, layer):
    if abs(direction[1]) < 1e-8:
        return None
    distance = (layer - origin[1]) / direction[1]
    if distance < 0:
        return None
    point = tuple(int(math.floor(origin[i] + distance * direction[i])) for i in range(3))
    point = (point[0], layer, point[2])
    return point if document.contains(point) else None


def pick_target(document, origin, direction, visible=None, layer=None, grid=True):
    """Pick the nearest block or visible work-plane cell, including empty cells.

    A hidden grid keeps the old empty-space fallback. Existing blocks on the
    plane retain their entered face for placement; an empty plane cell stops
    clicks passing through to a tree/floor behind it.
    """
    hit = raycast(document, origin, direction, visible)
    pos = layer_hit(document, origin, direction, layer) if layer is not None else None
    if pos is None or (visible is not None and not visible(pos)):
        return hit
    if hit is None:
        return pos, (0, 0, 0)
    if not grid or hit[0] == pos:
        return hit
    axis = next((i for i in range(3) if hit[1][i]), None)
    distance = 0. if axis is None else (
        hit[0][axis] + int(hit[1][axis] > 0) - origin[axis]) / direction[axis]
    plane_distance = (layer - origin[1]) / direction[1]
    return (pos, (0, 0, 0)) if plane_distance <= distance + 1e-7 else hit
