# -*- coding: utf-8 -*-
"""Native billboard ownership and compact parameters shared with actor shaders."""
import math

_EFFECTS = dict((kind, 'modern_projection:' + kind + '_glow')
                for kind in ('survey', 'strike', 'aura'))
_VARIABLES = dict((key, 'variable.' + key)
                  for key in ('ux', 'uy', 'red', 'green', 'blue', 'alpha', 'ready'))


def _code(value, scale, maximum):
    return max(0, min(maximum, int(round(value * scale))))


def survey_packet(size, face, appearance, density):
    """Pack bounded sizes/settings; return the same decoded actor parameters."""
    entered, brightness, style, orbit = appearance
    entered = _code(entered, 63., 63)
    brightness = _code(brightness, 84., 126)
    density = _code(density, 70., 126)
    orbit = _code(orbit, 85., 255)
    variables = {
        'ux': int(size[0] - 1) + int(size[1] - 1) * 64 if face is None else face,
        'uy': int(size[2] - 1) if face is None else 0,
        'red': int(style) * 8 + (brightness % 16) * 16,
        'green': brightness // 16 + (density % 32) * 8,
        'blue': density // 32 + (orbit % 64) * 4,
        'alpha': orbit // 64 + entered * 4}
    return variables, (entered / 63., brightness / 84., style, orbit / 85.), density / 70.


def aura_packet(appearance, velocity, layout):
    """Quantize render uniforms only; the owner's CPU interpolation stays raw."""
    entered = _code(appearance[0], 127., 127)
    switching = _code(layout[2], 63., 63)
    codes = tuple(31 + int(round(max(-7., min(7., v)) * 31. / 7.)) for v in velocity)
    seed_from, seed_to = int(layout[0]), int(layout[1])
    x, y, z = codes
    variables = {'ux': (seed_from % 32) * 256,
                 'uy': seed_from // 32 + seed_to * 8 + (x % 4) * 2048,
                 'red': x // 4 + (y % 16) * 16,
                 'green': y // 16 + z * 4,
                 'blue': entered + (switching % 2) * 128,
                 'alpha': switching // 2 + int(appearance[1]) * 32
                          + int(appearance[2]) * 64 + int(appearance[3]) * 128}
    velocity = tuple((value - 31) * (7. / 31.) for value in codes)
    motion = velocity + (math.sqrt(sum(v * v for v in velocity)),)
    return (variables, (entered / 127.,) + appearance[1:], motion,
            (float(seed_from), float(seed_to), switching / 63., layout[3]))


class NativeGlow(object):
    """One emitter per owner, with no frame listeners or per-particle SDK calls."""
    def __init__(self, bridge, kind):
        self.bridge = bridge
        self.effect = _EFFECTS[kind]
        self.component = None
        self.eid = None
        self.position = None
        self.variables = {}
        self._clearing = False
        self._cleanup_pending = False
        self._generation = 0

    def _forget(self):
        self.eid = self.position = None
        self.variables.clear()
        self._clearing = self._cleanup_pending = False
        self._generation += 1

    def update(self, position, variables):
        if self._clearing:
            return False
        if self.component is None:
            self.component = self.bridge.factory.CreateParticleSystem(None)
            if self.component is None:
                return False
        component = self.component
        position = tuple(position)
        if self.eid is None:
            eid = component.Create(self.effect, position, (0., 0., 0.))
            if not eid:
                return False
            self.eid, self.position = eid, position
        ok = True
        if self.position != position:
            if component.SetPos(self.eid, position):
                self.position = position
            else:
                ok = False
        for key, value in variables.items():
            if self.variables.get(key) == value:
                continue
            if component.SetVariable(self.eid, _VARIABLES[key], float(value)):
                self.variables[key] = value
            else:
                ok = False
        # JSON starts hidden: partial native registration must never display
        # a carrier with uninitialized packet fields.
        if ok and self.variables.get('ready') != 1:
            ok = component.SetVariable(self.eid, _VARIABLES['ready'], 1.)
            if ok:
                self.variables['ready'] = 1
        if not ok and not component.Exist(self.eid):
            self._forget()
        return ok

    def clear(self):
        if self.eid is None:
            return True
        self._clearing = True
        if self.component.Remove(self.eid) or not self.component.Exist(self.eid):
            self._forget()
            return True
        # Retain the handle on failure, including after the owning record is
        # released. Its guarded retry cannot affect a later emitter instance.
        if self.component.SetVariable(self.eid, _VARIABLES['ready'], 0.):
            self.variables['ready'] = 0
        if not self._cleanup_pending:
            self._cleanup_pending = True
            generation = self._generation
            def retry():
                if self._clearing and self._generation == generation:
                    self._cleanup_pending = False
                    self.clear()
            self.bridge.later(.15, retry)
        return False
