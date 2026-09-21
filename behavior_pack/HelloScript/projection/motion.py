# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Retained entrance/exit motion without fading every descendant control."""
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


def use_presence(opened):
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
        duration = OPEN_DURATION if opened else CLOSE_DURATION
        t = max(0., min(1., (now-motion['start'])/duration)) if Theme.motion else 1.
        set_progress(motion['from']+(float(opened)-motion['from'])*(1.-(1.-t)**3))
    use_animation_frame(tick, progress != float(opened))
    return progress


@Component
def DialogMotion(opened=False, height=640, cardHeight=300, zIndex=2100, children=None):
    use_theme()
    progress = use_presence(opened)
    # All dialogs use the same input scope, scrim, easing, and duration. Keep
    # children mounted, including native edit_box focus and inventory slots.
    return ModalScope(style=S(position=Position.absolute, top=0, left=0,
                      width='100%', height='100%', zIndex=zIndex, visible=opened or progress>0.), children=[
        Image(color=Color(0x172B4D77), style=S(position=Position.absolute,
              width='100%', height='100%', opacity=progress)),
        Panel(style=S(position=Position.absolute, width='100%', height='100%', zIndex=2,
              alignItems=AlignItems.center, justifyContent=JustifyContent.center), children=
            Panel(key='moving', style=S(transform=[Translate(0,(1.-progress)*(height+cardHeight)*.5*Theme.scale)]),
                  children=children))])


@Component
def WorkspaceMotion(controller=None, awaitEditor=True, height=640, children=None):
    use_theme()
    ready, set_ready = use_state(not awaitEditor)
    closing, set_closing = use_state(False)
    popped = use_ref(False)
    progress = use_presence(ready and not closing)
    controller.current = {'ready': lambda: set_ready(True), 'close': lambda: set_closing(True)}

    def finish():
        if closing and progress == 0. and not popped.current:
            popped.current = True
            entry = navigator.top
            if entry is not None and entry.key == 'modern_projection_workspace':
                navigator.pop()
    use_effect(finish, [closing, progress])

    return Panel(style=S(width='100%', height='100%'), children=[
        Image(color=Color(0x172B4D77), style=S(position=Position.absolute,
              width='100%', height='100%', opacity=progress)),
        Panel(key='moving', style=S(width='100%', height='100%',
              transform=[Translate(0,(1.-progress)*height*Theme.scale)]), children=children),
        # Prevent edits during motion and keep native modal input blocking until
        # the last exit frame. There is no background Button to steal IME focus.
        ModalScope(style=S(position=Position.absolute, top=0, left=0,
                   width='100%', height='100%', zIndex=2900, visible=closing or progress<1.)),
    ])
