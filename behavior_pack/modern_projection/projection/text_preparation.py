# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Give cold text atlases render frames while the workspace is still covered."""
from ..pyreact import Component, Panel, Style, Position, use_ref, use_effect
from ..pyreact.hooks import use_animation_frame
from ..pyreact import native


class TextPreparation(object):
    def __init__(self, prepared=None):
        self.prepared = prepared if prepared is not None else set()
        self.paths = set()
        self.pending = []
        self.frame = 0
        self.last_request = 0
        self.submit = None
        self.closed = False

    def request(self, path):
        if self.closed or path in self.prepared or path in self.paths:
            return
        self.paths.add(path)
        self.pending.append(path)
        self.last_request = self.frame

    def step(self, unused=None):
        if self.closed or self.submit is None:
            return
        self.frame += 1
        if self.pending:
            # One atlas per render frame, sharing the loading time with the
            # editor's staged native mounts instead of a burst on fade-in.
            self.submit(self.pending.pop(0))
            self.last_request = self.frame

    def settled(self):
        # SetSprite alone is not a GPU-ready signal. The SDK has no texture
        # completion callback; keep real, visible samples through render turns.
        return self.submit is not None and not self.pending and self.frame-self.last_request >= 2

    def seal(self):
        # New hidden panes must not trigger native clones during user gestures.
        if self.settled():
            self.prepared.update(self.paths)
        self.closed = True

    def dispose(self):
        self.closed = True
        self.pending[:] = []
        self.submit = None


@Component
def TextPreparationPump(preparation=None, host=None):
    control = use_ref(None)

    def bind():
        patches = []
        def submit(path):
            parent = control.current.GetPath()
            name = str('text_page_%d' % len(patches))
            native.clone(host, '/root/mp_type_tmpl', parent, name)
            patch = host.GetBaseUIControl(parent + '/' + name)
            image = patch.asImage()
            image.SetSprite(path)
            # Every generated text atlas has a transparent two-pixel border.
            # This draws a transparent pixel, not a hidden/zero-alpha image
            # which the renderer can cull before requesting its texture.
            image.SetSpriteUV((0., 0.))
            image.SetSpriteUVSize((1., 1.))
            patch.SetPosition((0., 0.))
            patch.SetSize((1., 1.))
            patch.SetVisible(True, False)
            patches.append(patch)
            host.UpdateScreen(False)
        preparation.submit = submit
        return preparation.dispose
    use_effect(bind, [preparation, host])
    use_animation_frame(preparation.step, not preparation.closed)
    return Panel(ref=control, style=Style(position=Position.absolute, left=0, top=0,
                                        width=1, height=1))
