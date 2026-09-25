# -*- coding: utf-8 -*-
"""A bounded client-only magical aura; animation runs entirely in shaders."""
import time
from .tool_items import TERMINAL, SURVEY_WAND


class StaffAura(object):
    def __init__(self, bridge):
        self.bridge = bridge
        self.entity = None
        self.started = 0.
        self.uniform = None
        self.position = None
        self.retry_after = 0.

    def update(self, carried, visible=True):
        now = time.time()
        if not visible or carried not in (TERMINAL, SURVEY_WAND):
            self.clear()
            return
        # Feet position prevents camera bob and eye-height changes from moving
        # the magic circle. A single actor follows the player, never each mote.
        pos = self.bridge.factory.CreatePos(self.bridge.player).GetFootPos()
        if pos is None:
            self.clear()
            return
        pos = tuple(float(v) for v in pos)
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
            self.bridge.factory.CreateModel(self.entity).SetEntityShadowShow(False)
            # ActorRender registration is asynchronous; keep retrying only
            # this one uniform until accepted, also refresh after registration.
            entity = self.entity
            def ready():
                if self.entity == entity:
                    self.uniform = None
            self.bridge.later(.15, ready)
        if self.position != pos:
            if self.bridge.factory.CreatePos(self.entity).SetPosForClientEntity(pos):
                self.position = pos
        reduced = self.bridge.session.reduced_motion if self.bridge.session else False
        value = (min(1., max(0., (now-self.started)/.65)),
                 1. if carried == TERMINAL else 0., 0. if reduced else 1., 1.)
        if value != self.uniform:
            if self.bridge.factory.CreateActorRender(self.entity).SetEntityExtraUniforms(1, value):
                self.uniform = value

    def clear(self):
        if self.entity is not None:
            self.bridge.system.DestroyClientEntity(self.entity)
        self.entity = None
        self.uniform = self.position = None
        self.retry_after = 0.
