# -*- coding: utf-8 -*-
"""Prepare retained panes in small, cancellable batches between interactions."""
import time
import mod.client.extraClientApi as clientApi
from ..pyreact import Component, Panel, use_state, use_effect, use_event
from ..pyreact.hooks import use_animation_frame


INTERACTIVE_ANIMATIONS = frozenset(('Action', 'JellyButton', 'Animated', 'PageMotion',
                                  'WorkspaceMotion', 'DialogMotion'))


class PreparationQueue(object):
    def __init__(self, session):
        self.session = session
        self.jobs = []
        self.ready = False
        self.paused_until = 0.
        self.next_batch_at = 0.
        self.inputs = {}

    def add(self, callback, urgent=None):
        job = [True, callback, urgent]
        self.jobs.append(job)
        return lambda: job.__setitem__(0, False)

    def pause(self, unused=None):
        self.paused_until = time.time()+.25

    def step(self, now):
        if not self.ready or not self.jobs or now < max(self.paused_until, self.next_batch_at):
            return
        s = self.session
        if (s.camera_dragging or getattr(s, 'preview_pending', False) or
                getattr(getattr(s, 'tiles', None), 'mounting', False) or
                s.edit_job or s.busy or s.material_browser or s.pending_rename or s.pending_confirm or
                getattr(getattr(s, 'sharing', None), 'opened', False)):
            return
        host = clientApi.GetTopScreen()
        if host is None or getattr(host, '_projection_click_contacts', None):
            return
        if now-getattr(host, '_projection_last_pointer_time', 0.) < .25:
            return
        # Button rebound lasts longer than the pointer cooldown. Do not resume
        # hidden mounts halfway through it, tab sliding or native hover fades.
        for slot in getattr(host, '_animation_frames', {}).values():
            fiber = slot.get('fiber')
            if (slot.get('active') and fiber is not None and fiber._mounted and
                    getattr(fiber.comp_type, '__name__', '') in INTERACTIVE_ANIMATIONS):
                return
        # Native tree creation can interrupt edit_box focus even when hidden.
        # Pause background work for the whole focus lifetime, including IME.
        paths = getattr(host, '_input_handlers', {})
        if set(paths) != set(self.inputs):
            self.inputs = dict((p, host.GetBaseUIControl(p+'/centering_panel/clipper_panel/display_text')) for p in paths)
        for control in self.inputs.values():
            if control and control.GetPropertyBag().get('#text_edit_selected'):
                return
        self.jobs[:] = [j for j in self.jobs if j[0]]
        if not self.jobs:
            return
        job = next((j for j in self.jobs if j[2] and j[2]()), self.jobs[0])
        self.jobs.remove(job)
        job[0] = False
        self.next_batch_at = now + 1./30.
        # Exactly one small mount per frame across all panes, not one per pane.
        job[1]()


@Component
def PreparationPump(queue=None):
    use_animation_frame(queue.step)
    use_event('OnKeyPressInGame', queue.pause)
    return None


@Component
def PreparedColumn(session=None, style=None, children=None, urgent=None, initial=2):
    items = children or []
    count, set_count = use_state(min(initial, len(items)))
    queue = getattr(session, '_ui_preparation', None)

    def prepare():
        if queue is not None and count < len(items):
            return queue.add(lambda: set_count(count+1), urgent)
    use_effect(prepare, [queue, count, len(items)])
    return Panel(style=style, children=items if queue is None else items[:count])
