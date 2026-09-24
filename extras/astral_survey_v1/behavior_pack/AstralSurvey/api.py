# -*- coding: utf-8 -*-
"""ModSDK client adapter. No editor, UI framework or server dependency."""
from __future__ import unicode_literals
import mod.client.extraClientApi as clientApi
from .effects import SurveyEffects


class AstralSurvey(object):
    def __init__(self, client_system):
        self.system = client_system
        self.factory = clientApi.GetEngineCompFactory()
        self.level = clientApi.GetLevelId()
        self.alive = True
        self.effects = SurveyEffects(self)

    def later(self, delay, callback):
        def invoke():
            if self.alive:
                callback()
        return self.factory.CreateGame(self.level).AddTimer(delay, invoke)

    def show_box(self, origin, size):
        """Origin is the minimum block corner; size is a positive XYZ extent."""
        if not self.alive:
            raise ValueError('AstralSurvey has been destroyed')
        if len(origin) != 3 or len(size) != 3 or any(v <= 0 for v in size):
            raise ValueError('Expected a three-dimensional positive box')
        self.effects.replace(tuple(origin), tuple(size))

    def select(self, first, second):
        """Inclusive Minecraft block positions, including reversed corners."""
        lo = tuple(min(first[i], second[i]) for i in range(3))
        size = tuple(abs(first[i]-second[i])+1 for i in range(3))
        self.show_box(lo, size)

    def strike(self, block_position):
        if self.alive:
            self.effects.strike(block_position)

    def update(self, unused=None):
        """Call from the client's frame event, even while the player stands still."""
        if not self.alive or not self.effects.active():
            return
        camera = self.factory.CreateCamera(self.level)
        pos, forward = camera.GetPosition(), camera.GetForward()
        anchor = tuple(float(pos[i])+4.*forward[i] for i in range(3))
        self.effects.follow(anchor, tuple(pos))

    def clear(self):
        self.effects.clear()

    def destroy(self):
        self.alive = False
        self.clear()
