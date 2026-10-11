"""Frame-budgeted world liquid plans over an immutable logical document."""
import time

from .liquid_render import WorldLiquidRenderer
from .liquid_render_plan import iter_group_steps, render_steps
from .model import Document

_COMPLETE = object()


class LiquidProjection(object):
    BUILD_SECONDS = .0015

    def __init__(self, bridge, document, origin, profile, dimension, hidden=(), layer=None):
        self.document = Document(document.size, biome=document.biome)
        self.document.blocks = document.blocks.copy()
        self.origin, self.profile = tuple(origin), profile
        self.hidden, self.layer = frozenset(hidden), layer
        self.renderer = WorldLiquidRenderer(bridge, profile.max_groups, dimension,
                                            profile.world_scale, profile.world_rotation)
        self.renderer.set_visible(False)
        self.iterator = None
        self.preparing = []
        self.occupied = None
        self.ready = self.closed = self.committed = False
        self.error = None
        self.reported_error = False

    def request(self, targets=None, occupied=None):
        if self.closed:
            return
        occupied = bytearray(occupied) if occupied is not None else None
        if occupied is not None and (len(occupied) != self.document.volume or
                                     any(state > 2 for state in occupied)):
            raise ValueError('Liquid occupancy must match the complete logical volume')
        self.occupied = occupied
        snapshot = Document(self.document.size, biome=self.document.biome)
        snapshot.blocks = self.document.blocks.copy()
        occupied, hidden, layer = self.occupied, self.hidden, self.layer
        sx, unused_sy, sz = snapshot.size
        def visible(pos):
            return (pos[1] not in hidden and (layer is None or pos[1] == layer)
                    and (occupied is None or occupied[(pos[1] * sx + pos[0]) * sz + pos[2]] != 2))
        provider = self.profile.provider_factory(snapshot)
        groups = iter_group_steps(snapshot, provider, targets=targets, visible=visible)
        self.iterator = render_steps(groups, self.profile.world_models,
                                     self.renderer.bridge.session.opacity, self.profile.max_groups)
        self.preparing = []
        self.ready, self.error = False, None
        self.reported_error = False

    def advance(self):
        if self.closed or self.error is not None:
            return False
        try:
            deadline = time.time() + self.BUILD_SECONDS
            for unused in range(64) if self.iterator is not None else ():
                group = next(self.iterator, _COMPLETE)
                if group is _COMPLETE:
                    self.iterator = None
                    if not self.renderer.begin(self.preparing, self.origin, time.time()):
                        raise ValueError(self.renderer.error or 'Could not prepare liquid projection')
                    self.preparing = []
                    break
                if group is not None:
                    self.preparing.append(group)
                if time.time() >= deadline:
                    return False
            if self.iterator is not None:
                return False
            self.ready = self.renderer.advance(time.time())
            if self.renderer.error:
                raise ValueError(self.renderer.error)
            return self.ready
        except ValueError as error:
            self.error = error
            self.iterator, self.preparing = None, []
            return False

    def prepare(self, targets, occupied=None):
        self.request(targets, occupied)
        while not self.advance():
            if self.error is not None:
                raise self.error
            yield None

    def publish(self):
        if not self.ready or self.error is not None:
            raise ValueError('Liquid projection is not ready for publication')
        if not self.renderer.set_visible(True):
            raise ValueError(self.renderer.error or 'Could not publish liquid projection')
        self.committed = True

    def set_biome(self, biome):
        if biome == self.document.biome or self.closed:
            return
        self.document.biome = biome
        self.request(occupied=self.occupied)

    def close(self):
        if self.closed:
            return self.renderer.retry_retired()
        self.closed = True
        self.iterator, self.preparing = None, []
        return self.renderer.close()
