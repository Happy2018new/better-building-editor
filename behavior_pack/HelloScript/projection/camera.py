# -*- coding: utf-8 -*-
"""Y-up orbit camera and bounded voxel picking, independent of the game SDK."""
from __future__ import division
import math


def clamp(value, low, high):
    return max(low, min(high, value))


class OrbitCamera(object):
    def __init__(self, yaw=35., pitch=25., zoom=1.):
        self.yaw, self.pitch, self.zoom = yaw, pitch, zoom
        self.target = (yaw, pitch, zoom)
        self.velocity = (0., 0.)
        self.dragging = False
        self.pan = (0., 0.)
        self.pan_target = self.pan

    def aim(self, yaw, pitch, zoom):
        self.target = (self.yaw + (yaw - self.yaw + 180.) % 360. - 180.,
                       clamp(pitch, -85., 90.), max(.25, zoom))
        self.velocity = (0., 0.)

    def drag(self, dx, dy, dt):
        # Grab the model: a rightward pointer movement brings its front to the
        # right. Camera azimuth has the opposite sign; inertia uses this delta too.
        yaw = -dx * .42
        pitch = dy * .42
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

    def basis(self):
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        return ((cy, 0., -sy), (-sy * sp, cp, -cy * sp), (sy * cp, sp, cy * cp))

    def project(self, point, size, width, height, unit):
        right, up, unused = self.basis()
        delta = [point[i] - size[i] / 2. for i in range(3)]
        return (width * (.5 + self.pan[0]) + unit * sum(delta[i] * right[i] for i in range(3)),
                height * (.5 + self.pan[1]) - unit * sum(delta[i] * up[i] for i in range(3)))

    def ray(self, x, y, size, width, height, unit):
        right, up, toward = self.basis()
        u, v = (x - width * (.5 + self.pan[0])) / unit, (height * (.5 + self.pan[1]) - y) / unit
        distance = sum(size) + 4.
        origin = tuple(size[i] / 2. + u * right[i] + v * up[i] + distance * toward[i] for i in range(3))
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
