"""Frame-budgeted world liquid plans over an immutable logical document."""
import time
import traceback

from .liquid_render import WorldLiquidRenderer
from .liquid_render_plan import iter_group_steps, render_steps
from .model import Document

_COMPLETE = object()


def _copy_targets(targets):
    if not isinstance(targets, dict):
        raise ValueError('Liquid targets need a native palette mapping')
    result = {'volume': tuple(targets.get('volume', ())), 'common': {}, 'extra': {}}
    for name in ('common', 'extra'):
        values = targets.get(name, {})
        if not isinstance(values, dict):
            raise ValueError('Liquid targets need complete common and extra mappings')
        result[name] = dict((value, tuple(indices)) for value, indices in values.items())
    return result


class LiquidProjection(object):
    BUILD_SECONDS = .0015

    def __init__(self, bridge, document, origin, profile, dimension, hidden=(), layer=None,
                 renderer_factory=WorldLiquidRenderer, plan_factory=None):
        self.document = Document(document.size, biome=document.biome)
        self.document.blocks = document.blocks.copy()
        self.origin, self.profile = tuple(origin), profile
        self.hidden, self.layer = frozenset(hidden), layer
        self.renderer = renderer_factory(bridge, profile.max_groups, dimension,
                                         profile.world_scale, profile.world_rotation)
        self.plan_factory = plan_factory
        self.renderer.set_visible(False)
        self.iterator = None
        self.preparing = []
        self.targets = self.occupied = None
        self.opacity = None
        self.ready = self.closed = self.committed = False
        self.error = None
        self.reported_error = False
        self.deferred = False
        self.revision = 0
        self.candidate = None

    def request(self, targets=None, occupied=None, deferred=False):
        return self._request(targets, occupied, self.document.biome, deferred)

    def _request(self, targets, occupied, biome, deferred=False):
        if self.closed:
            return
        occupied = bytearray(occupied) if occupied is not None else None
        if occupied is not None and (len(occupied) != self.document.volume or
                                     any(state > 2 for state in occupied)):
            raise ValueError('Liquid occupancy must match the complete logical volume')
        targets = _copy_targets(targets) if targets is not None else None
        snapshot = Document(self.document.size, biome=biome)
        snapshot.blocks = self.document.blocks.copy()
        hidden, layer = self.hidden, self.layer
        sx, unused_sy, sz = snapshot.size
        def visible(pos):
            return (pos[1] not in hidden and (layer is None or pos[1] == layer)
                    and (occupied is None or occupied[(pos[1] * sx + pos[0]) * sz + pos[2]] != 2))
        if self.plan_factory is None:
            provider = self.profile.provider_factory(snapshot)
            groups = iter_group_steps(snapshot, provider, targets=targets, visible=visible)
            iterator = render_steps(groups, self.profile.world_models,
                                    self.renderer.bridge.session.opacity, self.profile.max_groups)
        else:
            iterator = self.plan_factory(snapshot, self.profile, targets, visible,
                                         self.renderer.bridge.session.opacity)
        # A rejected provider must leave the previous request and biome retryable.
        if not self.renderer.cancel_preparation():
            raise ValueError('Liquid publication restoration is still pending')
        self.revision += 1
        self.deferred = bool(deferred)
        self.candidate = (targets, occupied, biome)
        if not self.deferred:
            self.targets, self.occupied = targets, occupied
            self.document.biome = biome
        self.iterator = iterator
        self.preparing = []
        self.ready, self.error = False, None
        self.reported_error = False
        return self.revision

    def advance(self):
        if self.closed or self.error is not None:
            return False
        try:
            opacity = self.renderer.bridge.session.opacity
            if opacity != self.opacity:
                if not self.renderer.set_opacity(opacity):
                    raise ValueError(self.renderer.error or 'Could not update liquid projection opacity')
                self.opacity = opacity
            deadline = time.time() + self.BUILD_SECONDS
            for unused in range(64) if self.iterator is not None else ():
                group = next(self.iterator, _COMPLETE)
                if group is _COMPLETE:
                    self.iterator = None
                    groups = tuple(group._replace(uniforms=group.uniforms[:3] +
                        (group.uniforms[3][:3] + (opacity,),)) for group in self.preparing)
                    if not self.renderer.begin(groups, self.origin, time.time(), self.deferred):
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
        except (ValueError, TypeError, KeyError, RuntimeError) as error:
            traceback.print_exc()
            self.error = error
            self.iterator, self.preparing = None, []
            self.renderer.cancel_preparation()
            return False

    def prepare(self, targets, occupied=None):
        self.request(targets, occupied, deferred=True)
        while not self.advance():
            if self.error is not None:
                raise self.error
            yield None

    def publish(self):
        if not self.ready or self.error is not None:
            raise ValueError('Liquid projection is not ready for publication')
        if self.deferred:
            if not self.prepare_publication(self.revision):
                self.restore_publication()
                raise ValueError(self.renderer.error or 'Could not publish liquid projection')
            self.finalize_publication(self.revision)
            self.renderer.retry_retired()
        elif not self.renderer.set_visible(True):
            raise ValueError(self.renderer.error or 'Could not publish liquid projection')
        self.committed = True

    def prepare_publication(self, revision):
        return (not self.closed and self.ready and self.error is None and
                revision == self.revision and self.deferred and
                self.renderer.prepare_publication(True))

    def restore_publication(self):
        return self.renderer.restore_publication()

    def finalize_publication(self, revision):
        if revision != self.revision or self.renderer.publication is None:
            raise ValueError('Liquid publication candidate was superseded')
        self.targets, self.occupied, self.document.biome = self.candidate
        self.candidate = None
        self.renderer.finalize_publication()
        self.deferred = False
        self.committed = True

    def cancel_candidate(self, revision):
        if revision != self.revision:
            return True
        if not self.renderer.cancel_preparation():
            return False
        self.iterator, self.preparing, self.candidate = None, [], None
        self.deferred = False
        self.ready = False
        return True

    def set_biome(self, biome):
        if biome == self.document.biome or self.closed:
            return
        targets, occupied = self.targets, self.occupied
        if self.candidate is not None:
            targets, occupied, unused = self.candidate
        self._request(targets, occupied, biome, self.deferred)

    def close(self):
        if self.closed:
            return self.renderer.retry_retired()
        self.closed = True
        self.revision += 1
        self.candidate = None
        self.iterator, self.preparing = None, []
        return self.renderer.close()
