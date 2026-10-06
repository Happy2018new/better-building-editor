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
    """Keep moving values in separate linear channels and static ID buckets."""
    entered, brightness, style, orbit = appearance
    entered = _code(entered, 254., 254)
    brightness = _code(brightness, 170., 255)
    density = _code(density - .3, 40., 60)
    orbit = _code(orbit, 85., 255)
    variables = {
        'ux': int(size[0] - 1) + int(size[1] - 1) * 64 if face is None else face,
        'uy': int(size[2] - 1) if face is None else 0,
        'red': int(style) * 64 + density,
        'green': brightness, 'blue': orbit, 'alpha': 1 + entered}
    return variables, (entered / 254., brightness / 170., style, orbit / 85.), .3 + density / 40.


def aura_packet(flags, velocity, layout, birth_base):
    """One linear channel per velocity and phase; CPU interpolation stays raw.

    A phase begins at birth or a tool switch. Its fixed birth progress lets
    one scalar drive both the initial fade and the layout transition, even
    when the tool changes before the initial fade has finished.
    """
    birth = _code(birth_base, 63., 63)
    switching = _code(layout[2], 254., 254)
    codes = tuple(31 + int(round(max(-7., min(7., v)) * 31. / 7.)) for v in velocity)
    seed_from, seed_to = int(layout[0]), int(layout[1])
    x, y, z = codes
    modes = int(flags[0]) + int(flags[1]) * 2 + int(flags[2]) * 4
    variables = {'ux': (seed_from % 64) * 256,
                 'uy': seed_from // 64 + seed_to * 4 + modes * 1024,
                 'red': (birth % 4) * 64 + x,
                 'green': ((birth // 4) % 4) * 64 + y,
                 'blue': (birth // 16) * 64 + z,
                 'alpha': 1 + switching}
    velocity = tuple((value - 31) * (7. / 31.) for value in codes)
    motion = velocity + (math.sqrt(sum(v * v for v in velocity)),)
    phase = switching / 254.
    entered = min(1., birth / 63. + phase * (.7 / .65))
    return (variables, (entered,) + tuple(flags), motion,
            (float(seed_from), float(seed_to), phase, layout[3]))


class NativeGlow(object):
    """One emitter per owner, with no frame listeners or per-particle SDK calls."""
    def __init__(self, bridge, kind):
        self.bridge = bridge
        self.kind = kind
        self.effect = _EFFECTS[kind]
        self.component = None
        self.eid = None
        self.position = None
        self.variables = {}
        self._clearing = False
        self._cleanup_pending = False
        self._generation = 0
        self._signature = None
        self._activation = 0
        self._activation_pending = False

    def _forget(self):
        self.eid = self.position = None
        self.variables.clear()
        self._clearing = self._cleanup_pending = False
        self._signature = None
        self._activation_pending = False
        self._generation += 1

    def _static_signature(self, variables):
        signature = (variables['ux'], variables['uy'], variables['red'] // 64)
        if self.kind == 'aura':
            signature += (variables['green'] // 64, variables['blue'] // 64)
        return signature

    def _activate_later(self):
        if self._activation_pending or self.variables.get('ready') == 1:
            return
        self._activation_pending = True
        self._activation += 1
        activation, generation, eid = self._activation, self._generation, self.eid
        def activate():
            if (not self._activation_pending or self._clearing
                    or self.eid != eid or self._generation != generation
                    or self._activation != activation):
                return
            self._activation_pending = False
            if self.component.SetVariable(eid, _VARIABLES['ready'], 1.):
                self.variables['ready'] = 1
            elif not self.component.Exist(eid):
                self._forget()
        # Native previous/current attributes must both contain the complete
        # static metadata before the alpha channel can expose this emitter.
        self.bridge.later(.10, activate)

    def update(self, position, variables):
        if self._clearing:
            return False
        signature = self._static_signature(variables)
        if self.eid is not None and signature != self._signature:
            if not self.clear():
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
            self._signature = signature
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
        if ok:
            self._activate_later()
        else:
            self._activation_pending = False
            self._activation += 1
            if not component.Exist(self.eid):
                self._forget()
        return ok

    def clear(self):
        if self.eid is None:
            return True
        self._clearing = True
        self._activation_pending = False
        self._activation += 1
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
