# -*- coding: utf-8 -*-
"""A bounded client-only magical aura; animation runs entirely in shaders."""
import time
import math
import random
from .tool_items import TERMINAL, SURVEY_WAND


class StaffAura(object):
    def __init__(self, bridge, player=None):
        self.bridge = bridge
        self.player = bridge.player if player is None else player
        self.entity = None
        self.started = 0.
        self.uniform = None
        self.motion_uniform = self.layout_uniform = None
        self.position = None
        self.retry_after = 0.
        self.last_tick = None
        self.last_target = None
        self.last_target_change = None
        self.samples = []
        self.stop_anchor = False
        self.velocity = (0., 0., 0.)
        self.carried = None
        self.layout_from = self.layout_to = random.random() * 1000.
        self.switch_started = 0.

    def _follow_sample(self, when):
        samples = self.samples
        if when <= samples[0][0]:
            return samples[0][1], (0., 0., 0.)
        for index in range(len(samples) - 1):
            t0, p0 = samples[index]
            t1, p1 = samples[index + 1]
            if when > t1:
                continue
            span = max(t1 - t0, .001)
            u = max(0., min(1., (when - t0) / span))
            before_t, before = samples[max(0, index - 1)]
            after_t, after = samples[min(len(samples) - 1, index + 2)]
            position, velocity = [], []
            for axis in range(3):
                slope = (p1[axis] - p0[axis]) / span
                m0 = (p1[axis] - before[axis]) / max(t1 - before_t, .001)
                m1 = (after[axis] - p0[axis]) / max(after_t - t0, .001)
                low, high = min(0., 3. * slope), max(0., 3. * slope)
                m0, m1 = max(low, min(high, m0)), max(low, min(high, m1))
                a = 2. * u * u * u - 3. * u * u + 1.
                b = u * u * u - 2. * u * u + u
                c = -2. * u * u * u + 3. * u * u
                d = u * u * u - u * u
                position.append(a * p0[axis] + b * span * m0 + c * p1[axis] + d * span * m1)
                velocity.append(((6. * u * u - 6. * u) * p0[axis]
                                 + (3. * u * u - 4. * u + 1.) * span * m0
                                 + (-6. * u * u + 6. * u) * p1[axis]
                                 + (3. * u * u - 2. * u) * span * m1) / span)
            return tuple(position), tuple(velocity)
        return samples[-1][1], (0., 0., 0.)

    def update(self, carried, visible=True):
        now = time.time()
        if not visible or carried not in (TERMINAL, SURVEY_WAND):
            self.clear()
            return
        # Feet position prevents camera bob and eye-height changes from moving
        # the magic circle. A single actor follows the player, never each mote.
        pos = self.bridge.factory.CreatePos(self.player).GetFootPos()
        if pos is None:
            self.clear()
            return
        pos = tuple(float(v) for v in pos)
        if self.carried is not None and carried != self.carried:
            self.layout_from = self.layout_to
            self.layout_to = random.random() * 1000.
            self.switch_started = now
        self.carried = carried
        if self.entity is None:
            if now < self.retry_after:
                return
            self.retry_after = now + 1.
            self.entity = self.bridge.system.CreateClientEntityByTypeStr(
                'modern_projection:staff_aura', pos, (0., 0.))
            if not self.entity:
                self.entity = None
                return
            self.started, self.position = now, pos
            self.last_tick, self.last_target = now, pos
            self.last_target_change = now
            self.samples = [(now, pos)]
            self.stop_anchor = False
            self.bridge.factory.CreateModel(self.entity).SetEntityShadowShow(False)
            # ActorRender registration is asynchronous; keep retrying only
            # this one uniform until accepted, also refresh after registration.
            entity = self.entity
            def ready():
                if self.entity == entity:
                    self.uniform = self.motion_uniform = self.layout_uniform = None
            self.bridge.later(.15, ready)
        dt = min(.1, max(.001, now - self.last_tick))
        delta = tuple(pos[i] - self.last_target[i] for i in range(3))
        if sum(v*v for v in delta) > 9.:
            self.position = pos
            self.velocity = (0., 0., 0.)
            self.samples = [(now, pos)]
            self.last_target_change = now
            self.stop_anchor = False
        else:
            if sum(v*v for v in delta) > 0.000001:
                if self.stop_anchor:
                    self.samples.append((now - min(.05, dt), self.last_target))
                self.samples.append((now, pos))
                self.last_target_change = now
                self.stop_anchor = False
            elif not self.stop_anchor and now - self.last_target_change >= .1:
                self.samples.append((now, pos))
                self.stop_anchor = True
            while len(self.samples) > 3 and self.samples[1][0] < now - .3:
                self.samples.pop(0)
            self.position, sample_velocity = self._follow_sample(now - .09)
            blend = 1. - math.exp(-dt / .06)
            self.velocity = tuple(self.velocity[i] + (sample_velocity[i] - self.velocity[i]) * blend
                                  for i in range(3))
        self.last_tick, self.last_target = now, pos
        self.bridge.factory.CreatePos(self.entity).SetPosForClientEntity(self.position)
        reduced = self.bridge.session.reduced_motion if self.bridge.session else False
        # Perspective belongs to the observer. A first-person observer still
        # sees other players' trails; only their own trails are hidden.
        first_person = False
        if self.player == self.bridge.player:
            first_person = self.bridge.factory.CreatePlayerView(self.bridge.player).GetPerspective() == 0
        value = (min(1., max(0., (now-self.started)/.65)),
                 1. if carried == TERMINAL else 0., 0. if reduced else 1.,
                 0. if first_person else 1.)
        if value != self.uniform:
            if self.bridge.factory.CreateActorRender(self.entity).SetEntityExtraUniforms(1, value):
                self.uniform = value
        speed = math.sqrt(sum(v*v for v in self.velocity))
        velocity = tuple(v * min(1., 7. / max(speed, .001)) for v in self.velocity)
        render = self.bridge.factory.CreateActorRender(self.entity)
        motion = velocity + (min(speed, 7.),)
        if motion != self.motion_uniform and render.SetEntityExtraUniforms(2, motion):
            self.motion_uniform = motion
        layout = (self.layout_from, self.layout_to,
                  min(1., max(0., (now - self.switch_started) / .7)), 1.)
        if layout != self.layout_uniform and render.SetEntityExtraUniforms(3, layout):
            self.layout_uniform = layout

    def clear(self):
        if self.entity is not None:
            self.bridge.system.DestroyClientEntity(self.entity)
        self.entity = None
        self.uniform = self.motion_uniform = self.layout_uniform = self.position = None
        self.retry_after = 0.
        self.last_tick = self.last_target = self.carried = None
        self.last_target_change = None
        self.samples = []
        self.stop_anchor = False
        self.velocity = (0., 0., 0.)


class NearbyStaffAuras(object):
    """Locally rendered aura actors for other players' server-reported tools."""
    def __init__(self, bridge):
        self.bridge = bridge
        self.auras = {}
        self.carried = {}

    def sync(self, carried):
        # Use the server's equipment snapshot instead of polling every
        # remote player's item component on each render tick.
        self.carried = dict((player, name) for player, name in carried.items()
                            if player != self.bridge.player and name in (TERMINAL, SURVEY_WAND))
        for player in list(self.auras):
            if player not in self.carried:
                self.auras.pop(player).clear()
        for player in self.carried:
            if player not in self.auras:
                self.auras[player] = StaffAura(self.bridge, player)

    def update(self):
        for player, aura in list(self.auras.items()):
            aura.update(self.carried[player])

    def clear(self):
        for aura in self.auras.values():
            aura.clear()
        self.auras.clear()
        self.carried.clear()
