# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Controlled native block viewport: orbit, inertia, zoom and direct voxel editing."""
from __future__ import unicode_literals
import math
import time
import mod.client.extraClientApi as clientApi
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from .widgets import Theme, S, Doll, Pointer, TypeImage, transparent, use_theme
from .camera import OrbitCamera, pick_target, behind_plane, render_bounds
from .model import bounds, MAX_AXES
from .preview import PreviewBuffer
from .diagnostics import inspect
from functools import partial
from .scene_lines import cuboid, grid_lines, clip_line, clip_depth, outline_targets, cursor_hue, cursor_uv, segment_fractions
from .chunks import painter_order
from .input_mode import is_touch


MODES = [('browse', '浏览'), ('select', '选取'), ('place', '放置'), ('paint', '换材质'),
         ('erase', '擦除'), ('pick', '吸管'), ('box', '框选')]
HINTS = {'browse': '拖动自由旋转，滚轮缩放，点击定位单格',
         'select': '点击选择单个方块，拖动仍可旋转',
         'place': '彩框预览放置位置，红框不可放置，点击放置',
         'paint': '仅替换点击格的材质，保持方块位置',
         'erase': '单格点击擦除，框选后可擦除整个选区，支持撤销',
         'pick': '点击吸取材质，不改变建筑',
         'box': '点击两点框选，空白处选择当前 Y 层，拖动旋转'}


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
        return session.subscribe(changed, ('page', 'view', 'preview', 'editing_mode', 'material_browser', 'pending_rename', 'pending_confirm'))
    use_effect(subscribe, [session])
    use_effect(session.bridge.attach_frame_pump, [session])
    registry = use_ref({}).current
    models_signature = use_ref(None)
    models_pending = use_ref(True)
    order_cache = use_ref(None)
    pointer, canvas = use_ref(None), use_ref(None)
    clipping = use_ref(None)
    clip_geometry = use_ref(None)
    def create_camera():
        result = OrbitCamera(*session.camera_pose)
        result.depth, result.depth_target = session.camera_depth_pose, session.camera_depth
        result.pivot = session.camera_pivot
        result.pan = result.pan_target = session.camera_pan
        return result
    camera = use_ref(create_camera).current
    reset_revision = use_ref(session.camera_reset_revision)
    input_check = use_ref(0.)
    frame = use_ref(time.time())
    outline = use_ref(None)
    cursor_outline = use_ref(None)
    grid_outline = use_ref(None)
    cursor_color = use_ref(None)
    spectrum_time = use_ref(0.)
    cursor_ranges = use_ref([])
    dimmer = use_ref(None)
    dim_alpha = use_ref(None)
    wheel_time = use_ref(None)
    drag = use_ref(None)
    mouse = use_ref(lambda: clientApi.GetEngineCompFactory().CreateActorMotion(clientApi.GetLocalPlayerId())).current
    hover_preview = use_ref(None)
    placed_pointer = use_ref(None)
    edge_refs = [use_ref(None) for unused in range(12)]
    cursor_refs = [use_ref(None) for unused in range(12)]
    grid_refs = [use_ref(None) for unused in range(MAX_AXES[0]+MAX_AXES[2]+2)]
    selected_bounds = use_ref((None, None))
    active = session.view == '3d' and session.page in ('workspace', 'projection') and not session.pending_confirm and not session.material_browser and not session.pending_rename

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
        models_signature.current = None
        outline.current = None
        cursor_outline.current = None
        grid_outline.current = None
        cursor_color.current = None
        if active:
            for dolls, surfaces, preview in registry.values():
                preview.invalidate()
    use_effect(restore_view, [active, width, height, Theme.scale, session.page])

    def aim():
        if reset_revision.current != session.camera_reset_revision:
            return
        if (abs(session.zoom - camera.target[2]) > .00001 and session.camera_focus_request is None
                and session.camera_pan == camera.pan_target):
            camera.zoom_at(session.zoom, width / 2., height / 2., width, height)
            session.camera_pan = camera.pan_target
        camera.aim(session.camera_yaw, session.camera_pitch, session.zoom)
    use_effect(aim, [session.camera_yaw, session.camera_pitch, session.zoom, session.camera_revision])

    def unit():
        # Native PaperDoll is orthographic; calibrated against block face corners.
        return min(width, height) * Theme.scale * camera.zoom * .72 / max(session.scene_size)

    def hit_at(x, y):
        origin, direction = camera.ray(x, y, session.scene_size, width * Theme.scale, height * Theme.scale, unit())
        origin = tuple(origin[i] + session.scene_origin[i] for i in range(3))
        def visible(pos):
            return (all(session.scene_origin[i] <= pos[i] < session.scene_origin[i] + session.scene_size[i] for i in range(3)) and
                    session.visible_layer(pos[1]))
        layer = session.editor.layer if session.direct_mode in ('place', 'box', 'select', 'browse') else None
        return pick_target(session.editor.document, origin, direction, visible, layer, session.grid)

    def orbit_anchor(x, y):
        hit = hit_at(x, y)
        if hit is None:
            return
        origin, direction = camera.ray(x, y, session.scene_size, width*Theme.scale, height*Theme.scale, unit())
        pos, normal = hit
        axis = next((i for i in range(3) if normal[i]), 1)
        if abs(direction[axis]) < 1e-8:
            return
        face = pos[axis] + int(normal[axis] > 0)
        distance = (face-origin[axis]) / direction[axis]
        point = tuple(origin[i]+distance*direction[i] for i in range(3))
        camera.set_pivot(point, session.scene_size, width*Theme.scale, height*Theme.scale, unit())
        session.camera_pivot = camera.pivot
        session.camera_pan = camera.pan_target

    def tick(now):
        session.bridge.pump_frame()
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
            session.cursor_cell = None
            drag.current = None
            camera.dragging = False
            session.camera_dragging = False
            camera.velocity = (0., 0.)
            return
        if now >= input_check.current and drag.current is None:
            input_check.current = now + .25
            touch = is_touch()
            if session.touch_mode != touch:
                session.touch_mode = touch
                hover_preview.current = None
                session.emit('input_mode')
        if reset_revision.current != session.camera_reset_revision:
            reset_revision.current = session.camera_reset_revision
            if session.camera_reset_animated and Theme.motion:
                camera.set_pivot(None, session.scene_size, width*Theme.scale, height*Theme.scale, unit())
                camera.dragging = False
                camera.velocity = (0., 0.)
                camera.pan_target = (0., 0.)
            else:
                camera.reset()
            camera.aim(session.camera_yaw, session.camera_pitch, session.zoom)
            drag.current = None
            session.camera_dragging = False
            wheel_time.current = None
            placed_pointer.current = None
            hover_preview.current = None
            outline.current = None
        if session.camera_focus_request is not None:
            point = tuple(session.camera_focus_request[i] - session.scene_origin[i] for i in range(3))
            session.camera_focus_request = None
            # A selected voxel has the same useful editing size in a small
            # draft and a maximum-size building; retain the complete mesh.
            camera.set_pivot(point, session.scene_size, width*Theme.scale, height*Theme.scale, unit())
            session.camera_pivot = camera.pivot
            session.zoom = 20. * max(session.scene_size) / (min(width, height) * .72)
            camera.aim(camera.yaw, camera.pitch, session.zoom)
            session.camera_yaw, session.camera_pitch = camera.yaw, camera.pitch
            session.camera_pan = (0., 0.)
            session.emit('view')
        camera.pan_target = session.camera_pan
        camera.depth_target = session.camera_depth
        camera.advance(dt, Theme.motion)
        session.camera_depth_pose = camera.depth
        session.camera_pose = (camera.yaw, camera.pitch, camera.zoom)
        if wheel_time.current is not None and now - wheel_time.current >= .18:
            wheel_time.current = None
            # A drag may have started since the last wheel event. Publish its
            # current pose too, so the delayed UI refresh cannot rewind it.
            session.camera_yaw, session.camera_pitch = camera.yaw, camera.pitch
            session.zoom = camera.target[2]
            session.emit('view')
        rendered_yaw, rendered_pitch = camera.render_angles()
        signature = (session.model_name, rendered_yaw, rendered_pitch, camera.zoom, camera.pan, width, height, Theme.scale,
                     session.scene_origin, session.scene_size, camera.pivot, camera.depth)
        pose = (unit() * session.scene_scale / 10., -90. + rendered_pitch, rendered_yaw)
        toward = camera.basis()[2]
        order_key = (session.tiles.slots, tuple(v >= 0 for v in toward))
        if order_cache.current is None or order_cache.current[0] != order_key:
            order_cache.current = (order_key, painter_order(session.tiles.slots, toward))
        order = order_cache.current[1]
        plane = camera.depth_plane(session.scene_size)
        layer_updates = []
        held_touch = camera.dragging and session.touch_mode
        model_key = (signature, session.tiles.publication, len(registry), held_touch)
        update_models = model_key != models_signature.current or models_pending.current
        models_signature.current = model_key
        for index, controls in list(registry.items()) if update_models else ():
            dolls, surfaces, preview = controls
            if not all(ref.current for ref in dolls+surfaces):
                continue
            key = session.tiles.slots[index] if index < len(session.tiles.slots) else None
            part = session.tiles.parts.get(key)
            if part is None:
                if not getattr(preview, 'suspended', False):
                    preview.suspended = True
                    for slot, surface in enumerate(surfaces):
                        surface.current.SetVisible(False, False)
                        preview.visible[slot] = False
                    preview.invalidate()
                continue
            if getattr(preview, 'suspended', False):
                preview.suspended = False
                preview.invalidate()
            if not part['name'] and preview.initialized and not any(preview.names):
                part['pending'] = False
                continue
            center = tuple(part['origin'][i]+part['size'][i]/2.-session.scene_origin[i] for i in range(3))
            distance = sum(center[i]*toward[i] for i in range(3))-plane[1] if plane else -1000.
            radius = sum(part['size'][i]*abs(toward[i]) for i in range(3))/2.
            clipped = distance-radius >= 0.
            tile_layer = 240 + int(math.floor(distance*4.+.5)) if plane and distance+radius > 0. and not clipped else 50+order[key]
            if clipped != getattr(preview, 'depth_hidden', False):
                preview.depth_hidden = clipped
                for slot, surface in enumerate(surfaces):
                    shown = not clipped and bool(preview.names[slot]) and (slot == preview.front or preview.pending is not None)
                    surface.current.SetVisible(shown, False)
                    preview.visible[slot] = shown
            if (getattr(preview, 'scene_signature', None) == signature and not preview.restore and
                    preview.ready(part['name']) and preview.poses[preview.front] == pose and
                    getattr(preview, 'layer', None) == tile_layer):
                part['pending'] = False
                continue
            preview.scene_signature = signature
            center = tuple(part['origin'][i]+part['size'][i]/2.-session.scene_origin[i] for i in range(3))
            tx, ty = camera.project(center, session.scene_size, width*Theme.scale, height*Theme.scale, unit())
            native_position, native_size = render_bounds(width*Theme.scale, height*Theme.scale,
                (tx-width*Theme.scale/2., ty-height*Theme.scale/2.))
            geometry = (native_position, native_size)
            if getattr(preview, 'geometry', None) != geometry:
                preview.geometry = geometry
                for ref in dolls:
                    ref.current.SetPosition(native_position)
                    ref.current.SetSize(native_size)
            if not held_touch and getattr(preview, 'layer', None) != tile_layer:
                preview.layer = tile_layer
                for slot, ref in enumerate(dolls):
                    if not preview.visible[slot]:
                        continue
                    # Suppress both immediate and per-call deferred refresh;
                    # schedule one refresh after all tile changes below.
                    ref.current.SetLayer(tile_layer, False, False)
                    layer_updates.append((ref.current, tile_layer))
            def draw(slot, name, pose):
                dx, dy = clip_geometry.current[:2] if clip_geometry.current else (0., 0.)
                surfaces[slot].current.SetPosition((-dx, -dy))
                dolls[slot].current.SetPosition(native_position)
                dolls[slot].current.SetSize(native_size)
                result = dolls[slot].current.asNeteasePaperDoll().RenderBlockGeometryModel({
                    'block_geometry_model_name': name, 'scale': pose[0],
                    'init_rot_x': pose[1], 'init_rot_y': 0., 'init_rot_z': pose[2]})
                return result
            def show(slot, visible, front):
                visible = visible and not clipped
                if preview.visible[slot] != visible:
                    surfaces[slot].current.SetVisible(visible, False)
                    preview.visible[slot] = visible
                    if visible and not held_touch:
                        dolls[slot].current.SetLayer(tile_layer, False, False)
                        layer_updates.append((dolls[slot].current, tile_layer))
            preview.update(part['name'], pose, now, draw, show)
            if preview.ready(part['name']):
                part['pending'] = False
        if update_models:
            models_pending.current = any(part['pending'] for part in session.tiles.parts.values())
        if layer_updates:
            control, layer = layer_updates[-1]
            # Even changing native layers without a forced refresh may disturb
            # touch routing. Defer both assignment and refresh until release.
            control.SetLayer(layer, False, True)
        e = session.editor
        selection_key = (id(e), e.selection_revision)
        if selected_bounds.current[0] != selection_key:
            selected_bounds.current = (selection_key, bounds(e.selection) if e.selection else None)
        preview_cell, preview_error = (None, None)
        if session.touch_mode and drag.current is not None and not drag.current[-1]:
            px, py = pointer.current.GetGlobalPosition()
            hit = hit_at(drag.current[2]-px, drag.current[3]-py)
            if hit:
                preview_cell, preview_error = session.cursor_target(*hit)
        if not session.touch_mode and (drag.current is None or not drag.current[-1]):
            point = mouse.GetMousePosition()
            # Native hover-enter may be missing when the UI opens beneath the
            # mouse. Use the same viewport/navigation hit test as actual clicks.
            if point is not None and screen_hit(point):
                # Keep the just-placed result under a stationary mouse. Otherwise
                # rebuilding the model immediately advances the cursor one cell.
                if placed_pointer.current is not None and tuple(point) != placed_pointer.current:
                    placed_pointer.current = None
                if placed_pointer.current is None:
                    key = (tuple(point), signature, e.revision, e.layer, e.material, e.mask,
                           e.filter_material, tuple(sorted(e.locked_layers)), session.preview_signature(), session.direct_mode)
                    if hover_preview.current is None or hover_preview.current[0] != key:
                        px, py = pointer.current.GetGlobalPosition()
                        hit = hit_at(point[0] - px, point[1] - py)
                        target, error = session.cursor_target(*hit) if hit else (None, None)
                        hover_preview.current = (key, target, error)
                    unused_key, preview_cell, preview_error = hover_preview.current
                else:
                    preview_cell = session.focused
        session.cursor_cell = preview_cell
        selected, hovered = outline_targets(selected_bounds.current[1], session.direct_mode,
                                             session.box_anchor, preview_cell, session.touch_mode)
        pasting = session.paste_active()
        if pasting:
            from .pasting import paste_bounds, paste_error
            origin = session.paste_origin
            if not session.paste_pinned and not session.touch_mode and preview_cell is not None:
                origin = preview_cell
            selected, hovered = None, paste_bounds(e.clipboard, origin)
            preview_error = paste_error(e.document, e.clipboard, origin)

        def box_lines(target):
            return list(cuboid(target[0], tuple(v + 1 for v in target[1]))) if target else []

        def draw_lines(refs, segments, thickness, gradient_bounds=None):
            ranges = []
            gradient_size = tuple(gradient_bounds[1][i] - gradient_bounds[0][i] + 1 for i in range(3)) if gradient_bounds else None
            for index, ref in enumerate(refs):
                ranges.append(None)
                if not ref.current:
                    continue
                segment = segments[index] if index < len(segments) else None
                if segment:
                    segment = clip_depth(segment[0], segment[1], plane)
                if segment:
                    hues = [cursor_hue(p, gradient_bounds[0], gradient_size) for p in segment] if gradient_bounds is not None else None
                    a, b = [tuple(p[i] - session.scene_origin[i] for i in range(3)) for p in segment]
                    a, b = [camera.project(p, session.scene_size, width * Theme.scale, height * Theme.scale, unit()) for p in (a, b)]
                    segment = clip_line(a, b, width * Theme.scale, height * Theme.scale)
                    if segment and hues is not None:
                        ranges[index] = tuple(hues[0] + (hues[1]-hues[0])*t for t in segment_fractions(a, b, segment))
                ref.current.SetVisible(bool(segment), False)
                if segment:
                    (sx, sy), (ex, ey) = segment
                    length = max(.001, math.hypot(ex - sx, ey - sy))
                    # Native JsonUI culls the unrotated rectangle first. Keep
                    # its centre inside the viewport, including vertical edges.
                    ref.current.SetPosition(((sx+ex-length)/2., (sy+ey-thickness)/2.))
                    ref.current.SetSize((length, thickness))
                    ref.current.asImage().Rotate(-math.degrees(math.atan2(ey - sy, ex - sx)))
            return ranges
        thickness = max(.3, Theme.scale * .65)
        edge_signature = (signature, selected)
        if edge_signature != outline.current:
            outline.current = edge_signature
            draw_lines(edge_refs, box_lines(selected), thickness)
        cursor_signature = (signature, hovered)
        if cursor_signature != cursor_outline.current:
            cursor_outline.current = cursor_signature
            cursor_ranges.current = draw_lines(cursor_refs, box_lines(hovered), thickness, hovered)
            cursor_color.current = None
        grid_signature = (signature, session.grid, e.layer)
        if grid_signature != grid_outline.current:
            grid_outline.current = grid_signature
            draw_lines(grid_refs, grid_lines(session.scene_origin, session.scene_size, e.layer) if session.grid else [], max(.22, Theme.scale * .4))
        # Sliding twelve UV windows preserves a continuous gradient on each edge
        # and at every corner. No projection, layout, grid or mesh work here.
        if hovered is not None:
            if Theme.motion:
                spectrum_time.current += dt * session.spectrum_speed
            invalid = bool(preview_error) and (pasting or (not session.touch_mode and session.box_anchor is None))
            color_key = (int(now * 30) if Theme.motion and not invalid else 0, invalid)
            if color_key != cursor_color.current:
                resized = cursor_color.current is None
                cursor_color.current = color_key
                for ref, hues in zip(cursor_refs, cursor_ranges.current):
                    if ref.current and hues is not None:
                        uv, uv_size = cursor_uv(hues[0], hues[1], spectrum_time.current, Theme.motion, invalid)
                        ref.current.asImage().SetSpriteUV(uv)
                        if resized:
                            ref.current.asImage().SetSpriteUVSize(uv_size)

    def down(args):
        if not screen_hit((args['TouchPosX'], args['TouchPosY'])):
            return
        session.pointer_stats[0] += 1
        session.touch_mode = args.get('pointerKind') == 'touch' or is_touch()
        # Taking hold of the scene stops pending wheel/pan motion at its actual
        # pose, before rebasing the orbit. Otherwise an old zoom target can
        # continue translating the new pivot after the finger has stopped.
        camera.velocity = (0., 0.)
        camera.target = (camera.yaw, camera.pitch, camera.zoom)
        camera.pan_target = camera.pan
        session.camera_pan = camera.pan
        session.camera_yaw, session.camera_pitch, session.zoom = camera.target
        wheel_time.current = None
        # At close range rotate about the surface under the hand. The full
        # building remains rendered; rebasing preserves every screen position.
        if camera.zoom > 1.2:
            px, py = pointer.current.GetGlobalPosition()
            orbit_anchor(args['TouchPosX']-px, args['TouchPosY']-py)
        camera.dragging = True
        session.camera_dragging = True
        drag.current = [args['TouchPosX'], args['TouchPosY'], args['TouchPosX'], args['TouchPosY'], time.time(), False]

    def contains(control, point):
        if control is None:
            return False
        x, y = control.GetGlobalPosition()
        w, h = control.GetSize()
        return x <= point[0] < x+w and y <= point[1] < y+h

    def screen_hit(point):
        return active and contains(pointer.current, point) and not (navigation and contains(navigation.current, point))

    def move(args):
        if drag.current is None:
            return
        x, y, last_x, last_y, then, moved = drag.current
        now = time.time()
        nx, ny = args['TouchPosX'], args['TouchPosY']
        moved = moved or math.hypot(nx - x, ny - y) > 4 * Theme.scale
        if moved:
            sensitivity = min(1., math.sqrt(12.*Theme.scale/max(12.*Theme.scale, unit())))
            camera.drag((nx - last_x) / Theme.scale, (ny - last_y) / Theme.scale, now - then, sensitivity)
        drag.current = [x, y, nx, ny, now, moved]

    def cancel(unused):
        drag.current = None
        camera.dragging = False
        session.camera_dragging = False
        camera.velocity = (0., 0.)

    def up(args):
        if drag.current is None:
            return
        session.pointer_stats[1] += 1
        # A dropped native move must never turn a displaced release into an edit.
        if ('TouchPosX' in args and 'TouchPosY' in args and
                (args['TouchPosX'], args['TouchPosY']) != tuple(drag.current[2:4])):
            move(args)
        x, y, unused_x, unused_y, then, moved = drag.current
        drag.current = None
        camera.dragging = False
        session.camera_dragging = False
        if moved:
            session.pointer_stats[2] += 1
            if time.time() - then > .08 or not Theme.motion:
                camera.velocity = (0., 0.)
            session.camera_yaw, session.camera_pitch = camera.yaw, camera.pitch
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

    def leave(unused):
        hover_preview.current = None
        if not session.touch_mode:
            cancel(unused)

    def wheel(args):
        point = mouse.GetMousePosition() if not session.touch_mode else None
        if point is not None and screen_hit(point):
            session.camera_yaw, session.camera_pitch = camera.yaw, camera.pitch
            session.zoom = max(.25, camera.target[2] * (1.12 if args['direction'] else 1. / 1.12))
            if point is not None and pointer.current:
                px, py = pointer.current.GetGlobalPosition()
                camera.zoom_at(session.zoom, point[0] - px, point[1] - py, width * Theme.scale, height * Theme.scale)
                session.camera_pan = camera.pan_target
            else:
                camera.aim(camera.yaw, camera.pitch, session.zoom)
            wheel_time.current = time.time()

    use_event('MouseWheelClientEvent', wheel, active)
    use_animation_frame(tick)
    return Panel(ref=canvas, cacheLayout=True, onDebug=partial(inspect, session), style=S(position=Position.absolute, width=width, height=height, zIndex=2), children=[
        Panel(style=S(position=Position.absolute, width='100%', height='100%', zIndex=-1, visible=active), children=[
            Image(ref=ref, key='grid%d' % i, color=Color(0x9BACCC88), rotatePivot=(.5, .5),
                  style=S(position=Position.absolute, width=1, height=1, visible=False)) for i, ref in enumerate(grid_refs)]),
        Panel(ref=clipping, style=S(position=Position.absolute, width='100%', height='100%'), children=[
            # Seed the geometry shader's CURRENT_COLOR with this viewport's
            # inherited alpha. The preceding grid draws with its own .53 alpha;
            # without a draw at layer 49 the models inherit that stale value.
            # Reuse the transparent texture: no visible mark, one pixel draw,
            # and no per-frame geometry submissions for workspace fades.
            Image(src='textures/modern_projection/transparent',
                  style=S(position=Position.absolute, width=1, height=1, zIndex=49)),
        ] + [
            PreviewTile(key='tile_pool_%d' % index, identity=index, registry=registry)
            for index in range(session.tiles.pool_size)]),
        Panel(style=S(position=Position.absolute, width='100%', height='100%', zIndex=370, visible=active), children=[
            Image(ref=ref, key='edge%d' % i, color=Theme.blue, rotatePivot=(.5, .5),
                  style=S(position=Position.absolute, width=1, height=1, visible=False))
            for i, ref in enumerate(edge_refs)]),
        Panel(style=S(position=Position.absolute, width='100%', height='100%', zIndex=371, visible=active), children=[
            TypeImage(ref=ref, key='cursor%d' % i, src='textures/modern_projection/cursor_spectrum', color=Theme.white, rotatePivot=(.5, .5),
                  style=S(position=Position.absolute, width=1, height=1, visible=False))
            for i, ref in enumerate(cursor_refs)]),
        Image(ref=dimmer, color=Color(0x000000FF), style=S(position=Position.absolute, width='100%', height='100%',
              zIndex=360, opacity=max(0., 1.-session.brightness), visible=active)),
        Pointer(ref=pointer, enabled=active, globalCapture=True, screenHit=screen_hit, onDown=down, onMove=move, onUp=up, onCancel=cancel, onLeave=leave,
                buttonBuilder=transparent, style=S(position=Position.absolute, width='100%', height='100%', zIndex=380, visible=active)),
    ])
