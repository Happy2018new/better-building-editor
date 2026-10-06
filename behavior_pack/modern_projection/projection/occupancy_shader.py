# -*- coding: utf-8 -*-
"""Two persistent geometry buffers on ONE actor; no per-cell shader masks."""
from .biomes import actor_uniform
from .large_preview import SurfacePalette


class OccupancyShader(object):
    def __init__(self, tracker):
        self.tracker = tracker
        old = tracker.bridge.projection_occupancy
        self.pool = 1-old.shader.pool if old is not None else 0
        self.names = tuple('modern_projection_buffer_%d_%d' % (self.pool, bank)
                           for bank in range(2))
        self.render = None
        self.backdrop = None
        self.uniforms = {}
        self.bank = 0
        self.empty = False
        self.updates = 0

    def write(self, slot, value):
        if self.uniforms.get(slot) == value:
            return
        if not self.render.SetEntityExtraUniforms(slot, value):
            raise ValueError('Could not update projection shader')
        self.uniforms[slot] = value
        self.updates += 1

    def control(self):
        self.commit(None if self.empty else self.names[self.bank])

    def bind(self, entity, model, anchor, attached=False, backdrop=None):
        tracker, b = self.tracker, self.tracker.bridge
        self.render = b.factory.CreateActorRender(entity)
        self.bank = self.names.index(model)
        self.control()
        # Both names remain attached for the lifetime of this actor. Replacing
        # the inactive native resource must not invalidate the actor renderer.
        spare = 1-self.bank
        seed = SurfacePalette(tracker.size)
        pos = next(iter(tracker.targets))
        seed.add(pos, tracker.document.blocks[pos])
        if not b.geometry(seed, name=self.names[spare]):
            raise ValueError('Could not prepare projection shader buffer')
        for bank, name in enumerate(self.names):
            offset = self.offset(anchor)
            if (not attached or name != model) and not self.render.AddActorBlockGeometry(
                    name, offset, (0., 180., 0.)):
                raise ValueError('Could not attach projection shader buffer')
            if not (self.render.EnableActorBlockGeometryTransparent(name, True) and
                    self.render.SetActorBlockGeometryTransparency(name, .25+.5*bank)):
                raise ValueError('Could not configure projection shader buffer')
        if backdrop is not None:
            backdrop.bind(self.names, model, tracker.document.biome)
        self.backdrop = backdrop

    def offset(self, anchor):
        origin = self.tracker.origin
        return (anchor[0]-origin[0]-.5, origin[1]-anchor[1], anchor[2]-origin[2]-.5)

    def follow(self, anchor, camera):
        offset = self.offset(anchor)
        return all(self.render.SetActorBlockGeometryOffset(name, offset) for name in self.names)

    def commit(self, model):
        empty = model is None
        bank = self.names.index(model) if model is not None else self.bank
        tint = actor_uniform(self.tracker.document.biome)
        previous = dict(self.backdrop.visible) if self.backdrop is not None else None
        if self.backdrop is not None:
            self.backdrop.select(model)
        try:
            self.write(4, tint[:2]+(-1. if empty else float(bank+1),
                                   self.tracker.bridge.session.opacity))
        except (ValueError, TypeError, RuntimeError):
            if self.backdrop is not None:
                self.backdrop.restore_visibility(previous)
            raise
        self.empty, self.bank = empty, bank
