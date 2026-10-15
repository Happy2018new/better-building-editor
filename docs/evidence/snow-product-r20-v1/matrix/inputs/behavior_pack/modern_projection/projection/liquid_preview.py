"""Incremental editor liquid plans; native controls belong to the scene.

The provider/resource profile is injected by the version adapter. The previous
plan stays published while a new immutable document snapshot is prepared.
"""
import time

from .liquid_render_plan import iter_group_steps, render_steps
from .model import Document

_COMPLETE = object()


class LiquidPreview(object):
    BUILD_SECONDS = .0015

    def __init__(self, session, provider_factory, models, max_groups):
        self.session, self.provider_factory = session, provider_factory
        self.models, self.max_groups = dict(models), max_groups
        self.requested = self.published = None
        self.document = self.iterator = None
        self.preparing = {}
        self.groups = {}
        self.keys = ()
        self.error = None
        self.closed = False
        self.revision = 0

    def signature(self):
        session = self.session
        editor = session.editor
        return (id(editor), editor.revision, tuple(sorted(session.preview_hidden())),
                editor.layer if session.solo_layer else None, editor.document.biome)

    def _start(self, signature):
        source = self.session.editor.document
        snapshot = Document(source.size, biome=source.biome)
        snapshot.blocks = source.blocks.copy()
        hidden, layer = frozenset(signature[2]), signature[3]
        def visible(pos):
            return pos[1] not in hidden and (layer is None or pos[1] == layer)
        provider = self.provider_factory(snapshot)
        groups = iter_group_steps(snapshot, provider, visible=visible)
        self.document = snapshot
        self.iterator = render_steps(groups, self.models, 1., self.max_groups)
        self.preparing = {}

    def advance(self):
        if self.closed:
            return False
        signature = self.signature()
        try:
            if self.requested != signature:
                self.requested = signature
                self.error = None
                self._start(signature)
            if self.iterator is None:
                return self.error is None
            deadline = time.time() + self.BUILD_SECONDS
            for unused in range(64):
                result = next(self.iterator, _COMPLETE)
                if result is _COMPLETE:
                    keys = tuple(sorted(self.preparing, key=lambda key:
                                        (key[0], key[1][0], repr(key[1][1]), key[2])))
                    changed_keys = keys != self.keys
                    self.groups, self.keys = self.preparing, keys
                    self.preparing = {}
                    self.iterator = self.document = None
                    self.published = signature
                    self.revision += 1
                    if changed_keys:
                        self.session.emit('preview')
                    return True
                if result is not None:
                    self.preparing[result.key] = result
                if time.time() >= deadline:
                    return False
        except ValueError as error:
            self.error = error
            self.iterator = self.document = None
            self.preparing = {}
            self.session.emit('preview')
        return False

    def retry(self):
        self.requested = None

    def close(self):
        self.closed = True
        self.iterator = self.document = None
        self.preparing, self.groups, self.keys = {}, {}, ()
