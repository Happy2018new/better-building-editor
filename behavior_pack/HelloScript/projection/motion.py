# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Retained workspace slides and compact, shared dialog transitions."""
from __future__ import unicode_literals
import time
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from ..pyreact.primitives import PanelPrimitive
from .widgets import Theme, S, use_theme


ModalScope = PanelPrimitive()
ModalScope.template_path = '/root/mp_inventory_modal_tmpl'
OPEN_DURATION = .30
CLOSE_DURATION = .20
DIALOG_OFFSET = 18.
WORKSPACE_OFFSET = 12.


class FadePrimitive(PanelPrimitive):
    """Native alpha inheritance, one setter regardless of descendant count."""
    template_path = '/root/mp_motion_group_tmpl'

    def props_affect_layout(self, prev_props, next_props, style):
        return False

    def apply_props(self, host, fiber, control, prev_props, next_props):
        if prev_props is None:
            control.SetAlpha(next_props['fade'].current)
            control.SetVisible(next_props['fade'].current > 0., False)

    def apply_layout(self, host, node):
        # A resize/full layout writes the ordinary Style alpha first.
        alpha = node.fiber.props['fade'].current
        control = host.GetBaseUIControl(node.fiber.native_path)
        control.SetAlpha(alpha)
        # Custom model renderers still draw at zero inherited image alpha.
        # Hide the group at the endpoint so no opaque model survives the fade.
        control.SetVisible(alpha > 0., False)
        node.fiber.primitive_state['motion_alpha'] = alpha


Fade = FadePrimitive()


def use_presence(opened, open_duration=OPEN_DURATION, close_duration=CLOSE_DURATION):
    progress, set_progress = use_state(0.)
    motion = use_ref({'start': 0., 'from': 0.}).current

    def start():
        # Start after native mounting/layout: creating a dialog must not consume
        # its animation before the first frame. Reversals continue from here.
        motion.update(start=time.time(), **{'from': progress})
        if not Theme.motion:
            set_progress(float(opened))
    use_effect(start, [opened, Theme.motion])

    def tick(now):
        duration = open_duration if opened else close_duration
        t = max(0., min(1., (now-motion['start'])/duration)) if Theme.motion else 1.
        set_progress(motion['from']+(float(opened)-motion['from'])*(1.-(1.-t)**3))
    use_animation_frame(tick, progress != float(opened))
    return progress


@Component
def DialogMotion(opened=False, zIndex=2100, session=None, children=None):
    use_theme()
    progress = use_presence(opened)
    # A stable reference keeps alpha out of prop diffs (which would request a
    # full native UpdateScreen). Transform's visual pass applies this alpha.
    fade = use_ref(0.)
    fade.current = progress
    queue = getattr(session, '_ui_preparation', None)
    # Keep deferred native mounts away from the entire closing transition too.
    if queue is not None and (opened or progress > 0.):
        queue.pause()
    # The card appears near its final position. Keep its scale constant so the
    # native input font remains at an integer physical magnification throughout.
    return ModalScope(style=S(position=Position.absolute, top=0, left=0,
                      width='100%', height='100%', zIndex=zIndex, visible=opened or progress>0.), children=[
        Image(color=Color(0x172B4D77), style=S(position=Position.absolute,
              width='100%', height='100%', opacity=progress)),
        SafeArea(style=S(position=Position.absolute, width='100%', height='100%', zIndex=2,
              alignItems=AlignItems.center, justifyContent=JustifyContent.center), children=
            Fade(key='moving', fade=fade, style=S(
                  transform=[Translate(0,(1.-progress)*DIALOG_OFFSET*Theme.scale)]),
                  children=children))])


@Component
def WorkspaceMotion(controller=None, awaitEditor=True, width=980, preparation=None, children=None):
    use_theme()
    ready, set_ready = use_state(not awaitEditor)
    closing, set_closing = use_state(False)
    popped = use_ref(False)
    progress = use_presence(ready and not closing, open_duration=.28)
    fade = use_ref(0.)
    fade.current = progress
    controller.current = {'ready': lambda: set_ready(True), 'close': lambda: set_closing(True)}

    def finish():
        if preparation is not None:
            preparation.ready = progress == 1. and not closing
        if closing and progress == 0. and not popped.current:
            popped.current = True
            entry = navigator.top
            if entry is not None and entry.key == 'modern_projection_workspace':
                navigator.pop()
    use_effect(finish, [closing, progress])

    return Panel(style=S(width='100%', height='100%'), children=[
        Image(color=Color(0x172B4D77), style=S(position=Position.absolute,
              width='100%', height='100%', opacity=progress)),
        Fade(key='moving', fade=fade, style=S(width='100%', height='100%',
              transform=[Translate((1.-progress)*WORKSPACE_OFFSET*Theme.scale,0)]), children=children),
        # Prevent edits during motion and keep native modal input blocking until
        # the last exit frame. There is no background Button to steal IME focus.
        ModalScope(style=S(position=Position.absolute, top=0, left=0,
                   width='100%', height='100%', zIndex=2900, visible=closing or progress<1.)),
    ])
