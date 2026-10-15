"""Publish owned liquid/item surfaces together with a single occupancy snapshot."""


class ProjectionCompanions(object):
    def __init__(self, companions):
        self.companions = tuple(companions)
        if not self.companions:
            raise ValueError('Projection companions need at least one owner')
        self.revision = 0
        self.candidates = ()
        self.reported_error = False
        self.closed = False
        # Legacy callers use owner.renderer for publication error and retirement.
        self.renderer = self

    @property
    def error(self):
        return next((owner.error or owner.renderer.error for owner in self.companions
                     if owner.error is not None or owner.renderer.error is not None), None)

    def request(self, targets=None, occupied=None, deferred=False):
        if self.closed:
            raise ValueError('Projection companions are closed')
        previous = self.candidates
        self.revision += 1
        self.reported_error = False
        requested = []
        try:
            for owner in self.companions:
                requested.append((owner, owner.request(targets, occupied, deferred)))
        except (ValueError, TypeError, RuntimeError):
            # Remaining owners may still hold the preceding request's candidate.
            owners = set(owner for owner, serial in requested)
            self.candidates = tuple(requested) + tuple((owner, serial) for owner, serial
                                                       in previous if owner not in owners)
            self.cancel_candidate(self.revision)
            raise
        self.candidates = tuple(requested)
        return self.revision

    def advance(self):
        ready = True
        for owner in self.companions:
            ready = owner.advance() and ready
        return ready

    def prepare(self, targets, occupied=None):
        self.request(targets, occupied, deferred=True)
        while not self.advance():
            if self.error is not None:
                raise self.error
            yield None

    def prepare_publication(self, revision):
        if (self.closed or revision != self.revision or
                len(self.candidates) != len(self.companions)):
            return False
        for owner, serial in self.candidates:
            if not owner.prepare_publication(serial):
                self.restore_publication()
                return False
        return True

    def restore_publication(self):
        restored = True
        for owner in reversed(self.companions):
            restored = owner.restore_publication() and restored
        return restored

    def finalize_publication(self, revision):
        if (self.closed or revision != self.revision or
                len(self.candidates) != len(self.companions) or
                any(serial != owner.revision or owner.renderer.publication is None
                    for owner, serial in self.candidates)):
            raise ValueError('Projection companion snapshot was superseded')
        for owner, serial in self.candidates:
            owner.finalize_publication(serial)
        self.candidates = ()

    def cancel_candidate(self, revision):
        if revision != self.revision:
            return True
        restored = True
        for owner, serial in self.candidates:
            restored = owner.cancel_candidate(serial) and restored
        if restored:
            self.candidates = ()
        return restored

    def set_biome(self, biome):
        if self.closed:
            return
        for owner in self.companions:
            owner.set_biome(biome)
        if self.candidates:
            self.revision += 1
            self.candidates = tuple((owner, owner.revision) for owner in self.companions)

    def retry_retired(self):
        restored = True
        for owner in self.companions:
            restored = owner.renderer.retry_retired() and restored
        return restored

    def close(self):
        self.closed = True
        released = True
        for owner in self.companions:
            released = owner.close() and released
        return released
