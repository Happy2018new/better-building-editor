# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Controlled native block viewport: orbit, inertia, zoom and direct voxel editing."""
from __future__ import unicode_literals
import math
import time
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from .widgets import Theme, S, Doll, Pointer, transparent, use_theme
from .camera import OrbitCamera, raycast, layer_hit
from .model import bounds
from .preview import PreviewBuffer


MODES = [('browse', '浏览'), ('select', '选取'), ('place', '放置'), ('paint', '涂装'),
         ('erase', '擦除'), ('pick', '吸管'), ('box', '框选')]
HINTS = {'browse': '拖动自由旋转 · 滚轮缩放 · 点击查看坐标',
         'select': '点击选择单个方块 · 拖动仍可旋转',
         'place': '点击方块表面向外放置 · 空白处放在当前 Y 层',
         'paint': '点击方块更换主材质 · 拖动旋转',
         'erase': '点击擦除可见方块 · 支持撤销',
         'pick': '点击吸取材质 · 不改变建筑',
         'box': '依次点击两个方块框选 · 拖动旋转'}


@Component
def Scene(session=None, revision=0, width=400, height=300):
    use_theme()
    unused, refresh = use_state(0)

    def subscribe():
        def changed():
            refresh(lambda previous: previous + 1)
        return session.subscribe(changed, ('page', 'view'))
    use_effect(subscribe, [session])
    dolls = [use_ref(None), use_ref(None)]
    surfaces = [use_ref(None), use_ref(None)]
    pointer, canvas = use_ref(None), use_ref(None)
    clipping = use_ref(None)
    clip_geometry = use_ref(None)
    preview = use_ref(lambda: PreviewBuffer()).current
    camera = use_ref(lambda: OrbitCamera(session.camera_yaw, session.camera_pitch, session.zoom)).current
    frame = use_ref(time.time())
    outline = use_ref(None)
    wheel_time = use_ref(None)
    drag = use_ref(None)
    hovering = use_ref(False)
    edge_refs = [use_ref(None) for unused in range(12)]
    active = session.view == '3d' and session.page in ('workspace', 'projection') and not session.pending_confirm

    def clip():
        if canvas.current:
            canvas.current.SetClipsChildren(True)
        if clipping.current:
            clipping.current.SetClipsChildren(True)
    use_effect(clip, [])

    def aim():
        camera.aim(session.camera_yaw, session.camera_pitch, session.zoom)
    use_effect(aim, [session.camera_yaw, session.camera_pitch, session.zoom, session.camera_revision])

    def unit():
        # Native PaperDoll is orthographic; calibrated against block face corners.
        return min(width, height) * Theme.scale * camera.zoom * .72 / max(session.scene_size)

    def tick(now):
        dt = now - frame.current
        frame.current = now
        if canvas.current and clipping.current and all(ref.current for ref in surfaces):
            x, y = canvas.current.GetGlobalPosition()
            cw, ch = canvas.current.GetSize()
            # The native scissor rounds fractional bottom/right edges differently
            # from JsonUI. Use integral UI bounds and preserve the model's origin.
            dx, dy = math.ceil(x) - x, math.ceil(y) - y
            geometry = (dx, dy, max(0., math.floor(x + cw) - math.ceil(x)),
                        max(0., math.floor(y + ch) - math.ceil(y)))
            if geometry != clip_geometry.current:
                clip_geometry.current = geometry
                clipping.current.SetPosition((dx, dy))
                clipping.current.SetSize(geometry[2:])
                for surface in surfaces:
                    surface.current.SetPosition((-dx, -dy))
        if not active or not all(ref.current for ref in dolls + surfaces):
            drag.current = None
            camera.dragging = False
            camera.velocity = (0., 0.)
            return
        camera.advance(dt, Theme.motion)
        session.camera_pose = (camera.yaw, camera.pitch, camera.zoom)
        if wheel_time.current is not None and now - wheel_time.current >= .18:
            wheel_time.current = None
            # A drag may have started since the last wheel event. Publish its
            # current pose too, so the delayed UI refresh cannot rewind it.
            session.camera_yaw, session.camera_pitch = camera.yaw, camera.pitch
            session.zoom = camera.target[2]
            session.emit()
        signature = (session.model_name, camera.yaw, camera.pitch, camera.zoom, width, height, Theme.scale)
        def draw(slot, name, pose):
            return dolls[slot].current.asNeteasePaperDoll().RenderBlockGeometryModel({
                'block_geometry_model_name': name, 'scale': pose[0],
                'init_rot_x': pose[1], 'init_rot_y': 0., 'init_rot_z': pose[2]})

        def show(slot, visible, front):
            # Warm the transparent renderer while the previous image remains
            # visible. Hidden renderers defer initialization until made visible.
            surfaces[slot].current.SetVisible(visible, False)

        preview.update(session.model_name, (unit() * session.scene_scale / 10., -90. + camera.pitch, camera.yaw), now, draw, show)
        focused = session.focused
        lo, hi = focused, tuple(v + 1 for v in focused) if focused is not None else None
        if focused is not None and session.direct_mode == 'box' and session.box_anchor is None:
            lo, upper = bounds([session.editor.start, session.editor.end])
            hi = tuple(v + 1 for v in upper)
        edge_signature = (signature, lo, hi, focused, active)
        if edge_signature == outline.current:
            return
        outline.current = edge_signature
        for index, ref in enumerate(edge_refs):
            if not ref.current:
                continue
            ref.current.SetVisible(focused is not None and session.editor.document.contains(focused))
            if focused is None:
                continue
            axis, corner = index // 4, index % 4
            other = [i for i in range(3) if i != axis]
            a = list(lo)
            a[other[0]] = (lo, hi)[corner // 2][other[0]]
            a[other[1]] = (lo, hi)[corner % 2][other[1]]
            b = list(a)
            b[axis] = hi[axis]
            a = tuple(a[i] - session.scene_origin[i] for i in range(3))
            b = tuple(b[i] - session.scene_origin[i] for i in range(3))
            sx, sy = camera.project(a, session.scene_size, width * Theme.scale, height * Theme.scale, unit())
            ex, ey = camera.project(b, session.scene_size, width * Theme.scale, height * Theme.scale, unit())
            # UI Y grows downward, while native positive rotation is counterclockwise.
            angle = -math.degrees(math.atan2(ey - sy, ex - sx))
            ref.current.SetPosition((sx, sy))
            ref.current.SetSize((max(.1, math.hypot(ex - sx, ey - sy)), max(.5, Theme.scale)))
            # Native Rotate assigns the absolute angle (it does not accumulate).
            ref.current.asImage().Rotate(angle)

    def down(args):
        if not active:
            return
        camera.velocity = (0., 0.)
        camera.target = (camera.yaw, camera.pitch, camera.zoom)
        camera.dragging = True
        drag.current = [args['TouchPosX'], args['TouchPosY'], args['TouchPosX'], args['TouchPosY'], time.time(), False]

    def move(args):
        if drag.current is None:
            return
        x, y, last_x, last_y, then, moved = drag.current
        now = time.time()
        nx, ny = args['TouchPosX'], args['TouchPosY']
        moved = moved or math.hypot(nx - x, ny - y) > 4 * Theme.scale
        if moved:
            camera.drag((nx - last_x) / Theme.scale, (ny - last_y) / Theme.scale, now - then)
        drag.current = [x, y, nx, ny, now, moved]

    def cancel(unused):
        drag.current = None
        camera.dragging = False
        camera.velocity = (0., 0.)

    def up(args):
        if drag.current is None:
            return
        x, y, unused_x, unused_y, then, moved = drag.current
        drag.current = None
        camera.dragging = False
        if moved:
            if time.time() - then > .08 or not Theme.motion:
                camera.velocity = (0., 0.)
            return
        camera.velocity = (0., 0.)
        if session.preview_pending or session.model_revision is None or not preview.ready(session.model_name):
            session.editor.message = '预览更新中，请稍后点击'
            session.emit()
            return
        px, py = pointer.current.GetGlobalPosition()
        x, y = args.get('TouchPosX', x) - px, args.get('TouchPosY', y) - py
        doc = session.editor.document
        origin, direction = camera.ray(x, y, session.scene_size, width * Theme.scale, height * Theme.scale, unit())
        origin = tuple(origin[i] + session.scene_origin[i] for i in range(3))

        def visible(pos):
            return (all(session.scene_origin[i] <= pos[i] < session.scene_origin[i] + session.scene_size[i] for i in range(3)) and
                    pos[1] not in session.editor.hidden_layers and (not session.solo_layer or pos[1] == session.editor.layer))
        hit = raycast(doc, origin, direction, visible)
        if hit:
            if session.scene_scale > 1:
                session.focus_preview(hit[0])
            else:
                session.point_action(hit[0], hit[1])
        elif session.direct_mode == 'place':
            pos = layer_hit(doc, origin, direction, session.editor.layer)
            if pos is not None:
                session.point_action(pos, (0, 0, 0))
        else:
            session.focused = None
            session.editor.message = '没有命中可见方块'
            session.emit()

    def enter(unused):
        hovering.current = True

    def leave(unused):
        hovering.current = False

    def wheel(args):
        if active and hovering.current:
            session.camera_yaw, session.camera_pitch = camera.yaw, camera.pitch
            session.zoom = max(.25, min(3., camera.target[2] * (1.12 if args['direction'] else 1. / 1.12)))
            camera.aim(camera.yaw, camera.pitch, session.zoom)
            wheel_time.current = time.time()

    use_event('MouseWheelClientEvent', wheel, active)
    use_animation_frame(tick)
    return Panel(ref=canvas, style=S(position=Position.absolute, width=width, height=height, zIndex=2), children=[
        Panel(ref=clipping, style=S(position=Position.absolute, width='100%', height='100%'), children=[
            Panel(ref=surfaces[i], key='surface%d' % i,
                  style=S(position=Position.absolute, width='100%', height='100%'), children=[
                Doll(ref=dolls[i], managed=True, renderType=PaperDollRenderType.block_geometry,
                     blockGeometryModelName=session.model_name, scale=unit() / 10.,
                     initRotX=-90. + camera.pitch, initRotY=0., initRotZ=camera.yaw,
                     style=S(position=Position.absolute, width='100%', height='100%', zIndex=1))])
            for i in range(2)]),
        Panel(style=S(position=Position.absolute, width='100%', height='100%', zIndex=4, visible=active), children=[
            Image(ref=ref, key='edge%d' % i, color=Theme.blue, rotatePivot=(0., 0.),
                  style=S(position=Position.absolute, width=1, height=1, visible=False))
            for i, ref in enumerate(edge_refs)]),
        Pointer(ref=pointer, onDown=down, onMove=move, onUp=up, onCancel=cancel, onEnter=enter, onLeave=leave,
                buttonBuilder=transparent, style=S(position=Position.absolute, width='100%', height='100%', zIndex=8, visible=active)),
    ])
