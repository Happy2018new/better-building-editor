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
        select_pool = getattr(tracker.bridge, 'available_projection_pool', None)
        self.pool = select_pool() if select_pool is not None else (1-old.pool if old is not None else 0)
        if self.pool is None:
            raise ValueError('Projection geometry pools are still owned by previous actors')
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
        self.owned_parts = set()
        self.retirement_parts = None
        self.retirement_uniform_hidden = False
        self.local = False
        self.anchor = None
        self.offset_restore = []
        self._follow_anchor = None

    def write(self, slot, value):
        if self.uniforms.get(slot) == value:
            return
        if not self.render.SetEntityExtraUniforms(slot, value):
            raise ValueError('Could not update projection shader')
        self.uniforms[slot] = value
        self.updates += 1

    def control(self):
        if not self.restore_offsets():
            raise ValueError('Could not restore projection geometry offsets')
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
            # A failed native attachment may already have changed the renderer.
            self.owned_parts.add(name)
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
        own = getattr(b, 'own_projection_entity', None)
        if own is not None:
            own(entity, self)
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

    def retire(self):
        """Hide every attempted attachment; retain failed writes for destruction retries."""
        if self.render is None:
            return []
        self.overlay_restore = False
        if self.retirement_parts is None:
            self.retirement_parts = self.owned_parts.union(self.overlay_visibility)
            for parts in self.parts:
                self.retirement_parts.update(parts)
        errors = []
        if not self.retirement_uniform_hidden:
            hidden = actor_uniform(self.tracker.document.biome)[:2]+(-1., 0.)
            try:
                if not self.render.SetEntityExtraUniforms(4, hidden):
                    raise ValueError('Could not hide retired projection shader')
            except Exception as error:
                traceback.print_exc()
                errors.append(type('')(error))
            else:
                self.uniforms[4] = hidden
                self.updates += 1
                self.retirement_uniform_hidden = True
        for name in tuple(self.retirement_parts):
            try:
                if not self.render.SetActorBlockGeometryVisible(name, False):
                    raise ValueError('Could not hide retired projection geometry')
            except Exception as error:
                traceback.print_exc()
                errors.append(type('')(error))
            else:
                self.overlay_visibility[name] = False
                self.retirement_parts.remove(name)
        return errors

    def offset(self, anchor, chunk=(0, 0, 0)):
        origin = self.tracker.origin
        return (anchor[0]-origin[0]-.5-chunk[0], origin[1]-anchor[1]+chunk[1],
                anchor[2]-origin[2]-.5-chunk[2])

    def follow(self, anchor, camera):
        if not self.restore_offsets():
            return False
        if not self.prepare_follow(anchor, camera):
            self.restore_offsets()
            return False
        self.commit_follow()
        return True

    def prepare_follow(self, anchor, camera):
        if not self.restore_offsets():
            return False
        try:
            self.restore_overlays()
            for parts in self.parts:
                for name, value in parts.items():
                    # A native refusal may still change the offset. Journal
                    # the attempted write before crossing the SDK boundary.
                    self.offset_restore.append((name, self.offset(self.anchor, value[0])))
                    if not self.render.SetActorBlockGeometryOffset(name, self.offset(anchor, value[0])):
                        return False
        except (ValueError, TypeError, RuntimeError):
            traceback.print_exc()
            return False
        self._follow_anchor = anchor
        return True

    def commit_follow(self):
        if self._follow_anchor is not None:
            self.anchor = self._follow_anchor
        self._follow_anchor = None
        self.offset_restore = []

    def restore_offsets(self):
        remaining = []
        for name, offset in reversed(self.offset_restore):
            try:
                restored = self.render.SetActorBlockGeometryOffset(name, offset)
            except (ValueError, TypeError, RuntimeError):
                traceback.print_exc()
                restored = False
            if not restored:
                remaining.append((name, offset))
        self.offset_restore = list(reversed(remaining))
        self._follow_anchor = None
        return not self.offset_restore

    def commit(self, model):
        if not self.restore_offsets():
            raise ValueError('Could not restore projection geometry offsets')
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
