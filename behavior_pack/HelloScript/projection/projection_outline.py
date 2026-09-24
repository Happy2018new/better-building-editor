# -*- coding: utf-8 -*-
"""One client-only, GPU-animated wire box for the committed world projection."""
from __future__ import unicode_literals


class ProjectionOutline(object):
    def __init__(self, bridge):
        self.bridge = bridge
        self.entity = None
        self.bounds = None
        self.render_position = None
        self.style = None
        from .survey_effects import WireEffects
        self.effects = WireEffects(bridge)

    def clear(self):
        self.bounds = None
        self.hide()

    def hide(self):
        self.render_position = None
        # Hot-reload can call destruction on an instance created by the
        # previous module generation. Treat missing fields as an already
        # empty outline so closing the UI never leaks or raises.
        style = getattr(self, 'style', None)
        entity = getattr(self, 'entity', None)
        if style in (None, 'rainbow') and entity is not None:
            self.bridge.system.DestroyClientEntity(entity)
        effects = getattr(self, 'effects', None)
        if effects is not None:
            effects.clear()
        self.entity = None
        self.style = None

    def replace(self, origin, size):
        # Store the projection snapshot, not the currently edited draft or origin.
        self.hide()
        self.bounds = (tuple(origin), tuple(size))
        self.sync()

    def sync(self):
        b = self.bridge
        s = b.session
        if not b.alive or not s.projection_active or not s.projection_outline or self.bounds is None:
            self.hide()
            return
        origin, size = self.bounds
        style = s.outline_style
        if self.style != style:
            self.hide()
            self.style = style
        if style != 'rainbow':
            self.effects.configure_style(style, s.outline_options[style], s.reduced_motion)
            self.effects.replace(origin, size)
            self.entity = self.effects.layers[1]['id'] if len(self.effects.layers) > 1 else None
            return
        if self.entity is not None:
            self.configure(self.entity)
            return
        position = tuple(float(origin[i]) + size[i] * .5 for i in range(3))
        entity = b.system.CreateClientEntityByTypeStr('modern_projection:outline'.encode('ascii'), position, (0., 0.))
        if not entity:
            s.editor.message = '投影已生成，范围框创建失败，请重新开启范围框'
            return
        self.entity = entity
        self.configure(entity)
        # Entity renderers may become ready after the creation tick. Reapply once;
        # animation itself needs no timers, callbacks or geometry uploads.
        def ready():
            if self.entity == entity and not self.configure(entity):
                self.hide()
                s.editor.message = '投影已生成，范围框创建失败，请重新开启范围框'
                s.emit()
        b.later(.2, ready)

    def configure(self, entity):
        s = self.bridge.session
        self.bridge.factory.CreateModel(entity).SetEntityShadowShow(False)
        origin, size = self.bounds
        # Engine TIME wraps every 210 seconds. An integral number of cycles in
        # that interval prevents a color jump at the wrap; match editor speed / 6.
        options = s.outline_options['rainbow']
        cycles = int(options['speed'] * 35. + .5) if not s.reduced_motion else 0
        values = tuple(float(v) for v in size) + (cycles / 210.,)
        render = self.bridge.factory.CreateActorRender(entity)
        result = render.SetEntityExtraUniforms(1, values)
        render.SetEntityExtraUniforms(3, (options['brightness'], options['width'], 0., 0.))
        # EXTRA2 is consumed by the outline vertex shader when the actor is
        # camera-relative.  Keeping the correction in world units avoids any
        # camera-dependent scale or line-width changes.
        current = self.render_position
        if current is not None:
            centre = tuple(float(origin[i]) + size[i] * .5 for i in range(3))
            correction = tuple(centre[i] - current[i] for i in range(3)) + (1.,)
            render.SetEntityExtraUniforms(2, correction)
        return result

    def follow(self, position, camera=None):
        """Move only the native culling anchor; preserve the world-space box."""
        if self.style in ('golden', 'starry'):
            return self.effects.follow(position, camera)
        if self.entity is None or self.bounds is None:
            return True
        origin, size = self.bounds
        target = tuple(float(v) for v in position)
        current = self.render_position
        if target == current:
            return True
        if not self.bridge.factory.CreatePos(self.entity).SetPosForClientEntity(target):
            return False
        centre = tuple(float(origin[i]) + size[i] * .5 for i in range(3))
        correction = tuple(centre[i] - target[i] for i in range(3)) + (1.,)
        if not self.bridge.factory.CreateActorRender(self.entity).SetEntityExtraUniforms(2, correction):
            return False
        self.render_position = target
        return True
