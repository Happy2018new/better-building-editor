# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Controlled native block viewport: orbit, inertia, zoom and direct voxel editing."""
from __future__ import unicode_literals
import math
import time
import mod.client.extraClientApi as clientApi
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from .widgets import Theme, S, Doll, Pointer, transparent, use_theme
from .camera import OrbitCamera, raycast, layer_hit, behind_plane
from .model import bounds
from .preview import PreviewBuffer
from .diagnostics import inspect
from functools import partial
from .scene_lines import cuboid, grid_lines, clip_line


MODES = [('browse', '浏览'), ('select', '选取'), ('place', '放置'), ('paint', '换材质'),
         ('erase', '擦除'), ('pick', '吸管'), ('box', '框选')]
HINTS = {'browse': '拖动自由旋转 · 滚轮缩放 · 点击定位单格',
         'select': '点击选择单个方块 · 拖动仍可旋转',
         'place': '蓝框预览放置位置 · 红框不可放置 · 点击确认',
         'paint': '仅替换点击格的材质 · 保持方块位置',
         'erase': '单格点击擦除 · 框选后可擦除整个选区 · 支持撤销',
         'pick': '点击吸取材质 · 不改变建筑',
         'box': '点击两点框选 · 空白处选择当前 Y 层 · 拖动旋转'}


@Component
def PreviewTile(identity=None, registry=None):
    dolls = [use_ref(None), use_ref(None)]
    surfaces = [use_ref(None), use_ref(None)]
    buffer = use_ref(lambda: PreviewBuffer()).current
    def register():
        entry = (dolls, surfaces, buffer)
        registry[identity] = entry
        def cleanup():
            if registry.get(identity) is entry:
                registry.pop(identity, None)
        return cleanup
    use_effect(register, [identity])
    return Panel(style=Style(position=Position.absolute, width='100%', height='100%'), children=[
        Panel(ref=surfaces[i], key='surface%d' % i,
              style=Style(position=Position.absolute, width='100%', height='100%'), children=[
            Doll(ref=dolls[i], managed=True, renderType=PaperDollRenderType.block_geometry,
                 style=Style(position=Position.absolute, width='100%', height='100%', zIndex=50))]) for i in range(2)])


@Component
def Scene(session=None, revision=0, width=400, height=300, navigation=None):
    use_theme()
    unused, refresh = use_state(0)

    def subscribe():
        def changed():
            refresh(lambda previous: previous + 1)
        return session.subscribe(changed, ('page', 'view', 'preview'))
    use_effect(subscribe, [session])
    registry = use_ref({}).current
    pointer, canvas = use_ref(None), use_ref(None)
    clipping = use_ref(None)
    clip_geometry = use_ref(None)
    pan_geometry = use_ref(None)
    camera = use_ref(lambda: OrbitCamera(session.camera_yaw, session.camera_pitch, session.zoom)).current
    frame = use_ref(time.time())
    outline = use_ref(None)
    dimmer = use_ref(None)
    dim_alpha = use_ref(None)
    wheel_time = use_ref(None)
    drag = use_ref(None)
    hovering = use_ref(False)
    mouse = use_ref(lambda: clientApi.GetEngineCompFactory().CreateActorMotion(clientApi.GetLocalPlayerId())).current
    hover_preview = use_ref(None)
    placed_pointer = use_ref(None)
    depth_settled = use_ref((None, 0.))
    edge_refs = [use_ref(None) for unused in range(12)]
    grid_refs = [use_ref(None) for unused in range(52)]
    selected_bounds = use_ref((None, None))
    active = session.view == '3d' and session.page in ('workspace', 'projection') and not session.pending_confirm

    def reset_cursor():
        hover_preview.current = None
        placed_pointer.current = None
    use_effect(reset_cursor, [session.direct_mode, active])

    def clip():
        if canvas.current:
            canvas.current.SetClipsChildren(True)
        if clipping.current:
            clipping.current.SetClipsChildren(True)
    use_effect(clip, [])

    def restore_view():
        clip_geometry.current = None
        pan_geometry.current = None
        outline.current = None
        if active:
            for dolls, surfaces, preview in registry.values():
                preview.invalidate()
    use_effect(restore_view, [active, width, height, Theme.scale, session.page])

    def aim():
        camera.aim(session.camera_yaw, session.camera_pitch, session.zoom)
    use_effect(aim, [session.camera_yaw, session.camera_pitch, session.zoom, session.camera_revision])

    def unit():
        # Native PaperDoll is orthographic; calibrated against block face corners.
        return min(width, height) * Theme.scale * camera.zoom * .72 / max(session.scene_size)

    def hit_at(x, y):
        origin, direction = camera.ray(x, y, session.scene_size, width * Theme.scale, height * Theme.scale, unit())
        origin = tuple(origin[i] + session.scene_origin[i] for i in range(3))
        plane = session.depth_plane()
        def visible(pos):
            return (all(session.scene_origin[i] <= pos[i] < session.scene_origin[i] + session.scene_size[i] for i in range(3)) and
                    session.visible_layer(pos[1]) and behind_plane(pos, plane))
        hit = raycast(session.editor.document, origin, direction, visible)
        if hit:
            return hit
        if session.direct_mode in ('place', 'box', 'select'):
            pos = layer_hit(session.editor.document, origin, direction, session.editor.layer)
            if pos is not None and visible(pos):
                return pos, (0, 0, 0)
        return None

    def tick(now):
        dt = now - frame.current
        frame.current = now
        alpha = max(0., min(.8, 1.-session.brightness))
        if dimmer.current and dim_alpha.current != alpha:
            dimmer.current.SetAlpha(alpha)
            dim_alpha.current = alpha
        if canvas.current and clipping.current:
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
                for dolls, surfaces, preview in registry.values():
                    for surface in surfaces:
                        if surface.current:
                            surface.current.SetPosition((-dx, -dy))
        if not active:
            drag.current = None
            camera.dragging = False
            camera.velocity = (0., 0.)
            return
        camera.pan_target = session.camera_pan
        camera.advance(dt, Theme.motion)
        pan = (camera.pan[0] * width * Theme.scale, camera.pan[1] * height * Theme.scale)
        if pan != pan_geometry.current:
            pan_geometry.current = pan
            for dolls, surfaces, preview in registry.values():
                for ref in dolls:
                    if ref.current:
                        ref.current.SetPosition(pan)
        session.camera_pose = (camera.yaw, camera.pitch, camera.zoom)
        ray_origin, ray_direction = camera.ray(width*Theme.scale/2., height*Theme.scale/2., session.scene_size,
                                              width*Theme.scale, height*Theme.scale, unit())
        session.view_ray = (tuple(ray_origin[i]+session.scene_origin[i] for i in range(3)), ray_direction)
        if wheel_time.current is not None and now - wheel_time.current >= .18:
            wheel_time.current = None
            # A drag may have started since the last wheel event. Publish its
            # current pose too, so the delayed UI refresh cannot rewind it.
            session.camera_yaw, session.camera_pitch = camera.yaw, camera.pitch
            session.zoom = camera.target[2]
            session.emit()
        rendered_yaw, rendered_pitch = camera.render_angles()
        angles = (rendered_yaw, rendered_pitch)
        if angles != depth_settled.current[0]:
            depth_settled.current = (angles, now)
        elif not camera.dragging and now - depth_settled.current[1] > .2:
            session.settle_depth_direction(angles)
        signature = (session.model_name, rendered_yaw, rendered_pitch, camera.zoom, camera.pan, width, height, Theme.scale,
                     session.scene_origin, session.scene_size)
        pose = (unit() * session.scene_scale / 10., -90. + rendered_pitch, rendered_yaw)
        for key, controls in list(registry.items()):
            part = session.tiles.parts.get(key)
            dolls, surfaces, preview = controls
            if part is None or not all(ref.current for ref in dolls+surfaces):
                continue
            def draw(slot, name, pose):
                dx, dy = clip_geometry.current[:2] if clip_geometry.current else (0., 0.)
                surfaces[slot].current.SetPosition((-dx, -dy))
                dolls[slot].current.SetPosition(pan)
                result = dolls[slot].current.asNeteasePaperDoll().RenderBlockGeometryModel({
                    'block_geometry_model_name': name, 'scale': pose[0],
                    'init_rot_x': pose[1], 'init_rot_y': 0., 'init_rot_z': pose[2]})
                return result
            def show(slot, visible, front):
                if preview.visible[slot] != visible:
                    surfaces[slot].current.SetVisible(visible, False)
                    preview.visible[slot] = visible
                    if visible:
                        dolls[slot].current.SetLayer(50)
            preview.update(part['name'], pose, now, draw, show)
            if preview.ready(part['name']):
                part['pending'] = False
        e = session.editor
        selection_key = (id(e), e.selection_revision)
        if selected_bounds.current[0] != selection_key:
            selected_bounds.current = (selection_key, bounds(e.selection) if e.selection else None)
        preview_cell, preview_error = session.placement_proposal() if session.touch_mode else (None, None)
        if (active and not session.touch_mode and session.direct_mode == 'place' and hovering.current and
                (drag.current is None or not drag.current[-1])):
            point = mouse.GetMousePosition()
            if point is not None:
                # Keep the just-placed result under a stationary mouse. Otherwise
                # rebuilding the model immediately advances the cursor one cell.
                if placed_pointer.current is not None and tuple(point) != placed_pointer.current:
                    placed_pointer.current = None
                if placed_pointer.current is None:
                    key = (tuple(point), signature, e.revision, e.layer, e.material, e.mask,
                           e.filter_material, tuple(sorted(e.locked_layers)), session.preview_signature())
                    if hover_preview.current is None or hover_preview.current[0] != key:
                        px, py = pointer.current.GetGlobalPosition()
                        hit = hit_at(point[0] - px, point[1] - py)
                        target, error = session.placement_target(*hit) if hit else (None, None)
                        hover_preview.current = (key, target, error)
                    unused_key, preview_cell, preview_error = hover_preview.current
        edge_signature = (signature, selection_key, active, session.grid, e.layer, session.preview_pending,
                          session.model_revision, preview_cell, preview_error)
        if edge_signature == outline.current:
            return
        outline.current = edge_signature
        ready = True
        lines = []
        selected = selected_bounds.current[1]
        if preview_cell is not None:
            selected = (preview_cell, preview_cell)
        if selected:
            lo, upper = selected
            lines = list(cuboid(lo, tuple(v + 1 for v in upper)))

        def draw_lines(refs, segments, thickness, color=None):
            for index, ref in enumerate(refs):
                if not ref.current:
                    continue
                segment = segments[index] if ready and index < len(segments) else None
                if segment:
                    if color is not None:
                        ref.current.asImage().SetSpriteColor(color.to_rgb_tuple())
                    a, b = [tuple(p[i] - session.scene_origin[i] for i in range(3)) for p in segment]
                    a, b = [camera.project(p, session.scene_size, width * Theme.scale, height * Theme.scale, unit()) for p in (a, b)]
                    segment = clip_line(a, b, width * Theme.scale, height * Theme.scale)
                ref.current.SetVisible(bool(segment))
                if segment:
                    (sx, sy), (ex, ey) = segment
                    length = max(.001, math.hypot(ex - sx, ey - sy))
                    # Native JsonUI culls the unrotated rectangle first. Keep
                    # its centre inside the viewport, including vertical edges.
                    ref.current.SetPosition(((sx+ex-length)/2., (sy+ey-thickness)/2.))
                    ref.current.SetSize((length, thickness))
                    ref.current.asImage().Rotate(-math.degrees(math.atan2(ey - sy, ex - sx)))
        draw_lines(edge_refs, lines, max(.35, Theme.scale * .75), Theme.red if preview_error else Theme.blue)
        draw_lines(grid_refs, grid_lines(session.scene_origin, session.scene_size, e.layer) if session.grid else [], max(.22, Theme.scale * .4))

    def down(args):
        session.pointer_stats[0] += 1
        if not active:
            return
        if (args.get('pointerKind') == 'touch' or mouse.GetMousePosition() is None) and not session.touch_mode:
            session.set('touch_mode', True)
        camera.velocity = (0., 0.)
        camera.target = (camera.yaw, camera.pitch, camera.zoom)
        camera.dragging = True
        drag.current = [args['TouchPosX'], args['TouchPosY'], args['TouchPosX'], args['TouchPosY'], time.time(), False]

    def screen_hit(point):
        def contains(control):
            if control is None:
                return False
            x, y = control.GetGlobalPosition()
            w, h = control.GetSize()
            return x <= point[0] < x+w and y <= point[1] < y+h
        return active and contains(pointer.current) and not (navigation and contains(navigation.current))

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
        session.pointer_stats[1] += 1
        if drag.current is None:
            return
        x, y, unused_x, unused_y, then, moved = drag.current
        drag.current = None
        camera.dragging = False
        if moved:
            session.pointer_stats[2] += 1
            if time.time() - then > .08 or not Theme.motion:
                camera.velocity = (0., 0.)
            return
        camera.velocity = (0., 0.)
        signature = session.preview_signature()
        if session.tiles.context != signature[:1] + signature[2:] or session.preview_error:
            session.editor.message = '预览更新中，请稍后点击'
            session.emit()
            return
        px, py = pointer.current.GetGlobalPosition()
        x, y = args.get('TouchPosX', x) - px, args.get('TouchPosY', y) - py
        hit = hit_at(x, y)
        if hit:
            if session.touch_mode and session.direct_mode == 'place':
                session.propose_placement(hit[0], hit[1])
                return
            before_revision = session.editor.revision
            session.point_action(hit[0], hit[1])
            session.pointer_stats[3] += int(session.editor.revision != before_revision)
            point = mouse.GetMousePosition()
            placed_pointer.current = (tuple(point) if session.direct_mode == 'place' and point is not None and
                                      session.editor.revision != before_revision else None)
        else:
            session.focused = None
            session.editor.message = '没有命中可见方块'
            session.emit()

    def enter(unused):
        hovering.current = True

    def leave(unused):
        hovering.current = False
        hover_preview.current = None
        if not session.touch_mode:
            cancel(unused)

    def wheel(args):
        if active and hovering.current:
            session.camera_yaw, session.camera_pitch = camera.yaw, camera.pitch
            session.zoom = max(.25, camera.target[2] * (1.12 if args['direction'] else 1. / 1.12))
            camera.aim(camera.yaw, camera.pitch, session.zoom)
            wheel_time.current = time.time()

    use_event('MouseWheelClientEvent', wheel, active)
    use_animation_frame(tick)
    return Panel(ref=canvas, onDebug=partial(inspect, session), style=S(position=Position.absolute, width=width, height=height, zIndex=2), children=[
        Panel(style=S(position=Position.absolute, width='100%', height='100%', zIndex=-1, visible=active), children=[
            Image(ref=ref, key='grid%d' % i, color=Color(0x9BACCC88), rotatePivot=(.5, .5),
                  style=S(position=Position.absolute, width=1, height=1, visible=False)) for i, ref in enumerate(grid_refs)]),
        Panel(ref=clipping, style=S(position=Position.absolute, width='100%', height='100%'), children=[
            PreviewTile(key='tile_%d_%d_%d_%d' % ((id(session.editor),)+key), identity=key, registry=registry)
            for key in session.tiles.slots]),
        Panel(style=S(position=Position.absolute, width='100%', height='100%', zIndex=100, visible=active), children=[
            Image(ref=ref, key='edge%d' % i, color=Theme.blue, rotatePivot=(.5, .5),
                  style=S(position=Position.absolute, width=1, height=1, visible=False))
            for i, ref in enumerate(edge_refs)]),
        Image(ref=dimmer, color=Color(0x000000FF), style=S(position=Position.absolute, width='100%', height='100%',
              zIndex=75, opacity=max(0., 1.-session.brightness), visible=active)),
        Pointer(ref=pointer, enabled=active, globalCapture=True, screenHit=screen_hit, onDown=down, onMove=move, onUp=up, onCancel=cancel, onEnter=enter, onLeave=leave,
                buttonBuilder=transparent, style=S(position=Position.absolute, width='100%', height='100%', zIndex=110, visible=active)),
    ])
