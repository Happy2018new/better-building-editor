# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""A small orientation widget driven by the viewport's actual camera pose."""
from __future__ import unicode_literals
import math
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from .camera import OrbitCamera
from .widgets import Theme, S, TEX, text, use_theme


@Component
def OrientationGizmo(session=None):
    use_theme()
    lines = [use_ref(None) for unused in range(3)]
    tips = [use_ref(None) for unused in range(3)]
    labels = [use_ref(None) for unused in range(3)]
    previous = use_ref(None)
    layers = use_ref([None, None, None])

    def tick(unused):
        if session.page not in ('workspace', 'projection') or session.view != '3d':
            return
        yaw, pitch, unused_zoom = session.camera_pose
        held_touch = session.camera_dragging and session.touch_mode
        signature = (yaw, pitch, Theme.scale, held_touch)
        if signature == previous.current or not all(r.current for r in lines + tips + labels):
            return
        previous.current = signature
        right, up, toward = OrbitCamera(yaw, pitch).basis()
        scale, center = Theme.scale, 30 * Theme.scale
        layer_update = None
        for axis in range(3):
            dx, dy = right[axis], -up[axis]
            length = math.hypot(dx, dy)
            line = lines[axis].current
            line.SetPosition((center, center))
            line.SetSize((max(.1, length * 18 * scale), 1.5 * scale))
            line.asImage().Rotate(-math.degrees(math.atan2(dy, dx)))
            line.SetVisible(length > .02, False)
            tip = tips[axis].current
            tip.SetPosition((center + dx * 18 * scale - 2 * scale,
                             center + dy * 18 * scale - 2 * scale))
            label = labels[axis].current
            label.SetPosition((center + dx * 26 * scale - 4 * scale,
                               center + dy * 26 * scale - 5 * scale))
            # The axis pointing toward the viewer wins overlaps in cardinal views.
            depth = int(round((toward[axis] + 1.) * 3))
            if not held_touch and layers.current[axis] != depth:
                layers.current[axis] = depth
                # Any native layer refresh (including next-frame refresh) drops
                # a held touch's move/up route. Positions rotate live; refresh
                # overlap ordering once the finger is released.
                tip.SetLayer(10 + depth, False, False)
                label.SetLayer(20 + depth, False, False)
                layer_update = (label, 20 + depth)
        if layer_update:
            layer_update[0].SetLayer(layer_update[1], False, True)

    use_animation_frame(tick)
    colors = [Theme.red, Theme.mint, Theme.blue]
    return Panel(style=S(position=Position.absolute, right=10, bottom=10, width=60, height=60, zIndex=12),
        children=[Image(ref=lines[i], key='line%d' % i, color=colors[i], rotatePivot=(0., 0.),
                        style=S(position=Position.absolute, width=1, height=1)) for i in range(3)] +
                 [Image(ref=tips[i], key='tip%d' % i, src=TEX + 'dot', color=colors[i],
                        style=S(position=Position.absolute, width=4, height=4)) for i in range(3)] +
                 [Panel(ref=labels[i], key='label%d' % i,
                        style=S(position=Position.absolute, width=8, height=10),
                        children=text('XYZ'[i], 9, colors[i], center=True)) for i in range(3)] +
                 [Image(src=TEX + 'dot', color=Theme.muted,
                        style=S(position=Position.absolute, left=28, top=28, width=4, height=4, zIndex=9))])
