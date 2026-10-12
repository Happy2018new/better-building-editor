# -*- coding: utf-8 -*-
"""Two persistent geometry buffers on ONE actor; no per-cell shader masks."""
import traceback
from .biomes import actor_uniform
from .large_preview import SurfacePalette


class OccupancyShader(object):
    def __init__(self, tracker):
        self.tracker = tracker
        old = getattr(tracker.bridge, 'projection_shader', None)
        if old is None and tracker.bridge.projection_occupancy is not None:
            old = tracker.bridge.projection_occupancy.shader
        self.pool = 1-old.pool if old is not None else 0
        self.names = tuple('modern_projection_buffer_%d_%d' % (self.pool, bank)
                           for bank in range(2))
        self.render = None
        self.uniforms = {}
        self.bank = 0
        self.empty = False
        self.updates = 0
        self.parts = [{}, {}]
        self.active_parts = [set(), set()]
        self.overlay_visibility = {}
        self.overlay_restore = False
        self.local = False
        self.anchor = None

    def write(self, slot, value):
        if self.uniforms.get(slot) == value:
            return
        if not self.render.SetEntityExtraUniforms(slot, value):
            raise ValueError('Could not update projection shader')
        self.uniforms[slot] = value
        self.updates += 1

    def control(self):
        self.restore_overlays()
        tracker = self.tracker
        tint = actor_uniform(tracker.document.biome)
        self.write(4, tint[:2]+(-1. if self.empty else float(self.bank+1),
                               tracker.bridge.session.opacity))
        if self.local:
            self.write(1, (0., 0., 0., 19490.))

    def configure(self, bank, anchor):
        b = self.tracker.bridge
        base = self.names[bank]
        registry = getattr(b, 'context_models', {})
        incoming = registry.get(base, ((base, (0, 0, 0), True),))
        active = set(part[0] for part in incoming)
        for name in self.parts[bank]:
            if name not in active and not self.render.SetActorBlockGeometryTransparency(name, 1.):
                raise ValueError('Could not retire projection context chunk')
            if name not in active and not self.parts[bank][name][1]:
                self.show_overlay(name, False)
        self.active_parts[bank] = active
        for name, origin, context in incoming:
            if name not in self.parts[bank] and not self.render.AddActorBlockGeometry(
                    name, self.offset(anchor, origin), (0., 180., 0.)):
                raise ValueError('Could not attach projection context chunk')
            self.parts[bank][name] = (origin, context)
            transparency = (.25 if context else .125) + .5 * bank
            if not (self.render.EnableActorBlockGeometryTransparent(name, True) and
                    self.render.SetActorBlockGeometryTransparency(name, transparency)):
                raise ValueError('Could not configure projection context chunk')
            if not context:
                self.show_overlay(name, bank == self.bank and not self.empty)

    def show_overlay(self, name, visible):
        if self.overlay_visibility.get(name) == visible:
            return
        if not self.render.SetActorBlockGeometryVisible(name, visible):
            raise ValueError('Could not update projection overlay visibility')
        self.overlay_visibility[name] = visible

    def bind(self, entity, model, anchor, attached=False):
        tracker, b = self.tracker, self.tracker.bridge
        self.render = b.factory.CreateActorRender(entity)
        self.bank = self.names.index(model)
        self.local = model in getattr(b, 'context_models', {})
        self.anchor = anchor
        self.control()
        # Both names remain attached for the lifetime of this actor. Replacing
        # the inactive native resource must not invalidate the actor renderer.
        spare = 1-self.bank
        seed = SurfacePalette(tracker.size)
        pos = next(iter(tracker.targets))
        seed.add(pos, tracker.document.blocks[pos])
        if not b.geometry(seed, name=self.names[spare], context_document=tracker.document,
                          render_origin=tracker.origin):
            raise ValueError('Could not prepare projection shader buffer')
        if attached and not self.local:
            self.parts[self.bank][model] = ((0, 0, 0), True)
        for bank in range(2):
            self.configure(bank, anchor)

    def offset(self, anchor, chunk=(0, 0, 0)):
        origin = self.tracker.origin
        return (anchor[0]-origin[0]-.5-chunk[0], origin[1]-anchor[1]+chunk[1],
                anchor[2]-origin[2]-.5-chunk[2])

    def follow(self, anchor, camera):
        try:
            self.restore_overlays()
        except (ValueError, TypeError, RuntimeError):
            traceback.print_exc()
            return False
        self.anchor = anchor
        return all(self.render.SetActorBlockGeometryOffset(name, self.offset(anchor, value[0]))
                   for parts in self.parts for name, value in parts.items())

    def commit(self, model):
        self.restore_overlays()
        empty = model is None
        bank = self.names.index(model) if model is not None else self.bank
        tint = actor_uniform(self.tracker.document.biome)
        try:
            if model is not None:
                self.configure(bank, self.anchor)
            self.update_overlays(bank, empty)
            # Publish the bank only after native overlays have accepted the switch.
            self.write(4, tint[:2]+(-1. if empty else float(bank+1),
                                   self.tracker.bridge.session.opacity))
        except (ValueError, TypeError, RuntimeError):
            self.overlay_restore = True
            try:
                self.restore_overlays()
            except (ValueError, TypeError, RuntimeError):
                traceback.print_exc()
            raise
        self.empty, self.bank = empty, bank

    def restore_overlays(self):
        if self.overlay_restore:
            self.update_overlays(self.bank, self.empty)
            self.overlay_restore = False

    def update_overlays(self, bank, empty):
        # Native actor materials need not inherit our bank shader. Keep their
        # attached resources, but hide every inactive or retired overlay.
        for selected in (bank, 1-bank):
            for name, value in self.parts[selected].items():
                if not value[1]:
                    self.show_overlay(name, not empty and selected == bank and
                                      name in self.active_parts[selected])
