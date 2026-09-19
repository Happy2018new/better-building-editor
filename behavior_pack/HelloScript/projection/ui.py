# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Modern Projection professional workspace, entirely native Pyreact JsonUI."""
from __future__ import unicode_literals
import time
from functools import partial
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from ..pyreact.native import get_screen_size
from .widgets import Theme, S, TEX, text, row, surface, icon, line, Action, Range, Segments, Doll, Scroll, Input, transparent
from .widgets import JellyButton as Button, PageMotion, use_theme
from .panels import Parameters, Layers, History, Library, ProjectionSettings, Guide, material_color, material_name
from .catalog import GROUPS, TOOLS, BY_ID, TOOL_ICONS
from .model import AIR
from .model import SMALL_VOLUME
from .scene import Scene, MODES, HINTS
from .effects import ClickEffects
from .gizmo import OrientationGizmo


def use_session_fields(session, fields):
    unused, update = use_state(0)

    def refresh():
        update(lambda previous: previous + 1)

    def subscribe():
        return session.subscribe(refresh, fields)
    use_effect(subscribe, [session])


@Component
def RetainedPane(active=True, children=None, style=None):
    """Keep native controls and scroll position; refresh stale content on entry."""
    cached = use_ref(children)
    if active:
        cached.current = children
    return Panel(style=(style or Style()).merge(Style(visible=active)), children=cached.current)


@Component
def ToolList(session=None, revision=0, height=440):
    use_theme()
    use_session_fields(session, ('group', 'query'))
    query = session.query.strip().lower()
    items = [t for t in TOOLS if (query in (t[0] + t[2] + t[3]).lower() if query else t[1] == session.group)]
    title = next(g[1] for g in GROUPS if g[0] == session.group)
    return surface(width=174, height=height, padding=12, children=[
        row([text('工具箱', 15, flex=1), text('64', 10, Theme.blue)]),
        Input(value=session.query, onChange=partial(session.set, 'query'), style=S(width=150, height=27, marginTop=12)),
        text('搜索工具 / 描述' if not query else '找到 %d 个工具' % len(items), 10, Theme.muted, marginTop=5, marginBottom=12),
        text('搜索结果' if query else title + '工具', 10, Theme.muted, marginBottom=7),
        Panel(style=S(width=154, flex=1), children=[
            RetainedPane(key=identity, active=not query and session.group == identity,
                style=S(position=Position.absolute, width='100%', height='100%'),
                children=ToolGroup(session=session, group=identity, selected=session.tool))
            for identity, unused_title, unused_icon in GROUPS] + [
            RetainedPane(key='search', active=bool(query),
                style=S(position=Position.absolute, width='100%', height='100%'),
                children=ToolGroup(session=session, query=query, selected=session.tool))]),
        Panel(style=S(height=8)),
        surface(color=Theme.pale, padding=9, gap=3, children=[text('草稿内编辑', 11, Theme.blue), text('试验后再保存或应用', 10, Theme.muted)]),
    ])


@Component
def ToolGroup(session=None, group=None, query='', selected=None):
    use_theme()
    items = [t for t in TOOLS if (query in (t[0] + t[2] + t[3]).lower() if query else t[1] == group)]
    return Scroll(resetKey=query, style=S(width=154, height='100%'),
        children=Panel(style=S(width=144, gap=5), children=[
            Action(key=t[0], label=t[2], glyph=TOOL_ICONS[t[0]], leading=True, height=32,
                   selected=selected == t[0], onClick=partial(session.choose_tool, t[0]), compact=True)
            for t in items] or [text('没有匹配的工具', 11, Theme.muted)]))


@Component
def LayerCanvas(session=None, revision=0, width=380, height=300):
    use_theme()
    e = session.editor
    sx, unused_sy, sz = e.document.size
    ox, oz = min(session.canvas_x, sx - 1), min(session.canvas_z, sz - 1)
    nx, nz = min(12, sx - ox), min(12, sz - oz)
    cell = min((width - 36) / nx, (height - 48) / nz)
    left = (width - cell * nx) / 2.
    top = (height - cell * nz) / 2.
    controls = []
    for z in range(oz, oz + nz):
        for x in range(ox, ox + nx):
            pos = (x, e.layer, z)
            value = e.document.get(pos)
            color = material_color(value)
            if pos not in e.selection:
                color = color.lighten(.35)
            controls.append(Button(key='cell_%d_%d' % (x, z), buttonBuilder=partial(cell_bg, color),
                onClick=partial(session.paint, x, z), style=S(position=Position.absolute,
                    left=left + cell * (x - ox), top=top + cell * (z - oz), width=max(.5, cell - .7), height=max(.5, cell - .7))))
    controls.extend([text('Z', 11, Theme.muted, position=Position.absolute, left=max(2, left - 16), top=top),
                     text('X', 11, Theme.muted, position=Position.absolute, left=width - 20, top=height - 20)])
    return Image(color=Color(0xF7F9FCFF), style=S(position=Position.absolute, left=0, top=0, width=width, height=height, zIndex=5), children=controls)


def cell_bg(color, state):
    return Image(color=color if state == ButtonState.default else Theme.blue)


@Component
def ViewNavigation(session=None, width=430, revision=0):
    use_theme()
    # These move the viewpoint, so the model moves in the opposite direction.
    controls = [Action(label=label, glyph=glyph, compact=True, width=54, height=27,
                       onClick=partial(session.pan_view, x, y)) for label, glyph, x, y in (
        ('左移', 'arrow_left', .12, 0.), ('右移', 'arrow_right', -.12, 0.),
        ('上移', 'arrow_up', 0., .12), ('下移', 'arrow_down', 0., -.12))]
    controls.extend([
        Action(label='前移', glyph='front_view', compact=True, width=54, height=27,
               onClick=partial(session.move_depth, 1)),
        Action(label='后移', glyph='undo', compact=True, width=54, height=27,
               enabled=session.camera_depth > 0, onClick=partial(session.move_depth, -1)),
        Action(label='切面', glyph='layers', compact=True, width=54, height=27,
               selected=session.section, onClick=session.toggle_section)])
    return Panel(style=S(gap=3), children=[row(controls[:4], gap=3), row(controls[4:], gap=3)] if width < 520
                 else [row(controls, gap=3)])


@Component
def Viewport(session=None, revision=0, width=430, height=440):
    use_theme()
    use_session_fields(session, ('view',))
    e = session.editor
    doc = e.document
    focus = session.focus_view
    area_h = max(130, height - (136 if focus else 148))
    viewport_children = []
    viewport_children.append(Scene(key='scene_model', session=session, revision=revision, width=width, height=area_h))
    if not session.model_name:
        viewport_children.append(Panel(style=S(width='100%', height='100%', alignItems=AlignItems.center,
            justifyContent=JustifyContent.center, gap=10), children=[icon('cube', Theme.muted, 36),
                text(session.preview_error or ('正在构建方块预览…' if session.preview_pending else
                     '当前深度没有方块 · 点击后移' if session.camera_depth else
                     '当前没有可见方块 · 点击网格放置'), 12, Theme.muted)]))
    viewport_children.append(RetainedPane(key='layer_canvas', active=session.view == 'layer',
        style=S(position=Position.absolute, width=width, height=area_h, zIndex=5),
        children=LayerCanvas(session=session, revision=session.content_revision, width=width - 2, height=area_h)))
    viewport_children.extend([
        Panel(style=S(position=Position.absolute, left=12, top=12, zIndex=200, visible=session.view == 'layer'),
              children=surface(paddingHorizontal=9, height=24, justifyContent=JustifyContent.center,
                               children=text('Y %02d' % e.layer, 10, Theme.muted))),
        Panel(style=S(position=Position.absolute, left=12, top=12, zIndex=200, visible=session.view == '3d'),
              children=surface(paddingHorizontal=9, height=24, justifyContent=JustifyContent.center,
                  children=text('正在构建方块预览…' if session.preview_pending else
                      '视线深入 %g 格' % session.camera_depth if session.camera_depth else
                      'X %d · Y %d · Z %d' % session.focused if session.focused else '三维 · 可直接编辑', 10, Theme.muted))),
        Panel(style=S(position=Position.absolute, left=12, bottom=12, zIndex=200, visible=bool(session.preview_error)),
              children=text(session.preview_error, 11, Theme.red, width=width-24)),
        Panel(style=S(position=Position.absolute, width='100%', height='100%', visible=session.view == '3d', zIndex=200),
              children=OrientationGizmo(session=session)),
        Panel(style=S(position=Position.absolute, left=12, bottom=12, zIndex=200, visible=session.view == '3d'),
              children=ViewNavigation(session=session, width=width, revision=revision)),
    ])
    view_controls = [
        Action(glyph='minus', width=28, height=26, onClick=partial(session.camera_view, zoom=max(.25, session.zoom / 1.2))),
        text(('%g×' % session.zoom) if session.zoom >= 10 else '%d%%' % int(round(session.zoom * 100)), 10, Theme.muted, width=40, center=True),
        Action(glyph='plus', width=28, height=26, onClick=partial(session.camera_view, zoom=session.zoom * 1.2)),
        Action(label='左转', height=26, compact=True, onClick=partial(turn_camera, session, -30)),
        Action(label='右转', height=26, compact=True, onClick=partial(turn_camera, session, 30)),
        Action(label='俯视', height=26, compact=True, onClick=partial(session.camera_view, yaw=0., pitch=90.)),
        Action(label='正视', height=26, compact=True, onClick=partial(session.camera_view, yaw=0., pitch=0.)),
        Panel(style=S(flex=1)),
        Action(label='网格', glyph='grid', compact=True, height=26, selected=session.grid, onClick=partial(session.set, 'grid', not session.grid)),
        Action(glyph='home', width=28, height=26, onClick=partial(reset_camera, session)),
    ]
    layer_controls = [
        Action(label='X−', width=34, height=26, onClick=partial(session.set, 'canvas_x', max(0, session.canvas_x - 12))),
        Action(label='X+', width=34, height=26, onClick=partial(session.set, 'canvas_x', min(((doc.size[0] - 1) // 12) * 12, session.canvas_x + 12))),
        Action(label='Z−', width=34, height=26, onClick=partial(session.set, 'canvas_z', max(0, session.canvas_z - 12))),
        Action(label='Z+', width=34, height=26, onClick=partial(session.set, 'canvas_z', min(((doc.size[2] - 1) // 12) * 12, session.canvas_z + 12))),
        text('X %d · Z %d' % (session.canvas_x, session.canvas_z), 10, Theme.muted),
    ]
    return surface(width=width, height=height, children=[
        row([Panel(style=S(flex=1, gap=3), children=[text('专注编辑' if focus else '场景视图', 14),
                text(('%d × %d × %d' % doc.size) + (' · ' + material_name(e.material) if focus else ''), 10, Theme.muted)]),
             Panel(style=S(display=Display.flex if focus else Display.none, flexDirection=FlexDirection.row, gap=5), children=[
                 Action(glyph='undo', width=28, height=26, onClick=partial(session.action, e.undo), enabled=bool(e.undo_stack)),
                 Action(glyph='redo', width=28, height=26, onClick=partial(session.action, e.redo), enabled=bool(e.redo_stack)),
                 Action(label='材质与属性', height=27, compact=True, selected=session.focus_inspector,
                        onClick=partial(session.set, 'focus_inspector', not session.focus_inspector))]),
             Segments(items=[('3d', '三维'), ('layer', '逐层')], value=session.view,
                      onChange=partial(session.set, 'view'), width=112),
             Panel(style=S(display=Display.flex if doc.volume > SMALL_VOLUME else Display.none), children=
                 Action(label='总览' if session.preview_detail else '精细', glyph='cube', width=62, height=28, compact=True,
                        onClick=session.toggle_preview_detail)),
             Action(label='还原视图' if focus else '展开视图', height=28, compact=True, accent=focus,
                    onClick=partial(session.set, 'focus_view', not focus))], paddingHorizontal=12, height=45 if focus else 57),
        Image(color=Theme.line, style=S(height=1, width='100%')),
        Image(color=Color(0xF7F9FCFF), style=S(height=area_h, width='100%'), children=viewport_children),
        Panel(style=S(width='100%', height=36), children=[
            Panel(style=S(position=Position.absolute, width='100%', height=36, visible=session.view == '3d'),
                  children=row(view_controls, paddingHorizontal=6 if width < 480 else 10,
                               height=36, gap=1 if width < 480 else 3)),
            Panel(style=S(position=Position.absolute, width='100%', height=36, visible=session.view == 'layer'),
                  children=row(layer_controls, paddingHorizontal=12, height=36, gap=4))]),
        Panel(style=S(paddingHorizontal=12, gap=4), children=[
            Panel(style=S(width='100%', height=32), children=[
                Panel(style=S(position=Position.absolute, width='100%', height=32, visible=session.view == 'layer'),
                      children=Segments(items=[('paint', '绘制'), ('erase', '擦除'), ('pick', '吸管'), ('start', '起点'), ('end', '终点')],
                          value=session.paint_mode, onChange=partial(session.set, 'paint_mode'), width=width - 24)),
                Panel(style=S(position=Position.absolute, width='100%', height=32, visible=session.view == '3d'),
                      children=Segments(items=MODES, value=session.direct_mode, onChange=session.choose_mode, width=width - 24))]),
            Panel(style=S(width='100%', height=15, marginTop=2), children=[
                Panel(style=S(position=Position.absolute, visible=session.view == 'layer'),
                      children=text('点击格子编辑 · X / Z 为文档相对坐标', 10, Theme.muted)),
                Panel(style=S(position=Position.absolute, visible=session.view == '3d'),
                      children=text(HINTS[session.direct_mode], 10, Theme.muted))]),
        ])])


def reset_camera(session):
    session.camera_pan = (0., 0.)
    session.camera_depth = 0.
    session.refresh_preview()
    session.camera_view(35., 25., 1.)


def turn_camera(session, amount):
    session.camera_view(yaw=session.camera_pose[0] + amount)


@Component
def Inspector(session=None, revision=0, height=440, page='workspace'):
    use_theme()
    use_session_fields(session, ('inspector', 'view'))
    projecting = page == 'projection'
    active = 'projection' if projecting else session.inspector
    panes = []
    for name, component in (('params', Parameters), ('layers', Layers), ('history', History), ('projection', ProjectionSettings)):
        content_revision = session.content_revision
        if name == 'params' and session.direct_mode != 'browse':
            content_revision = (content_revision, session.view)
        panes.append(RetainedPane(key=name, active=active == name,
            style=S(position=Position.absolute, width='100%', height='100%'),
            children=component(session=session, revision=content_revision)))
    direct = session.view == '3d' and session.direct_mode not in ('browse', 'box', 'select')
    erase_selection = direct and session.direct_mode == 'erase' and session.erase_scope == 'selection'
    children = [Panel(key='header', style=S(width='100%', height=42), children=[
        Panel(style=S(position=Position.absolute, visible=not projecting), children=
            Segments(items=[('params', '参数'), ('layers', '图层'), ('history', '历史')],
                     value=session.inspector, onChange=partial(session.set, 'inspector'), width=216)),
        Panel(style=S(position=Position.absolute, visible=projecting), children=text('世界坐标与显示', 12, Theme.muted)),
    ]), Panel(key='panes', style=S(width='100%', flex=1), children=panes),
        Panel(key='footer', style=S(width='100%', height=45), children=[
            Panel(style=S(position=Position.absolute, top=8, width='100%', visible=not projecting), children=
                Action(label='取消编辑' if session.edit_job else '擦除选区' if erase_selection else '返回批量工具' if direct else '执行 · ' + BY_ID[session.tool][2],
                    glyph='close' if session.edit_job else 'erase' if erase_selection else 'play', accent=True, height=37,
                    onClick=session.cancel_edit if session.edit_job else session.erase_selection if erase_selection else
                            partial(session.choose_mode, 'browse') if direct else session.run,
                    enabled=not session.busy and (session.edit_job is not None or not erase_selection or
                            (bool(session.editor.selection) and session.box_anchor is None)))),
            Panel(style=S(position=Position.absolute, top=8, width='100%', visible=projecting), children=
                Action(label='返回工作台', glyph='brush', height=37, onClick=partial(session.set, 'page', 'workspace'))),
        ])]
    return surface(width=240, height=height, padding=12, children=children)


@Component
def Confirmation(session=None, revision=0):
    use_theme()
    progress, set_progress = use_state(0.)
    motion = use_ref({'target': False, 'start': 0., 'from': 0.}).current
    message = use_ref('')
    opened = bool(session.pending_confirm)
    if opened:
        message.current = session.pending_confirm[0]
    if motion['target'] != opened:
        motion.update(target=opened, start=time.time(), **{'from': progress})

    def tick(now):
        fraction = min(1., (now - motion['start']) / (.28 if opened else .18)) if Theme.motion else 1.
        eased = 1. - (1. - fraction) ** 3
        set_progress(motion['from'] + (float(opened) - motion['from']) * eased)
    use_animation_frame(tick, progress != float(opened))

    def content():
        return surface(width=420, padding=24, gap=18, children=[
            icon('info', Theme.blue, 28), text('请确认这次操作', 21),
            text(message.current, 13, Theme.muted, width=372),
            row([Action(label='取消', enabled=opened, onClick=partial(session.set, 'pending_confirm', None)),
                 Action(label='确认继续', enabled=opened, accent=True, onClick=session.accept)])])
    card = use_memo(content, [message.current, opened, Theme.scale])
    # Retain the modal through exit; its scrim continues swallowing background input.
    return Modal(visible=opened or progress > 0., style=Style(zIndex=100), children=[
        Image(color=Color(0x172B4D77), style=S(position=Position.absolute, width='100%', height='100%', opacity=progress)),
        Panel(style=S(position=Position.absolute, width='100%', height='100%', zIndex=2,
              alignItems=AlignItems.center, justifyContent=JustifyContent.center), children=
            Panel(style=S(opacity=progress, transform=[Translate(0, (1. - progress) * 18 * Theme.scale),
                Scale(.97 + .03 * progress)]), children=card))])


@Component
def PageNavigation(session=None, revision=0, focus=False):
    use_theme()
    use_session_fields(session, ('page',))
    e = session.editor
    return row([
        Segments(items=[('workspace', '工作台'), ('library', '建筑库'), ('projection', '投影'), ('guide', '入门指南')],
                 value=session.page, onChange=partial(session.set, 'page'), width=340),
        Panel(style=S(flex=1)), text(e.document.name[:24], 11, Theme.muted),
        Action(glyph='undo', width=29, height=28, onClick=partial(session.action, e.undo), enabled=bool(e.undo_stack)),
        Action(glyph='redo', width=29, height=28, onClick=partial(session.action, e.redo), enabled=bool(e.redo_stack)),
        Action(label='读取选区', glyph='cursor', width=100, height=28,
               onClick=partial(session.confirm, '读取世界选区将替换当前草稿，继续吗？', session.bridge.capture), enabled=not session.busy),
    ], paddingHorizontal=18, height=49, gap=8, display=Display.none if focus else Display.flex)


@Component
def CategoryRail(session=None, height=440, focus=False):
    use_theme()
    use_session_fields(session, ('group', 'page'))
    return surface(width=64, height=height, paddingTop=12, gap=13, alignItems=AlignItems.center,
        display=Display.none if focus else Display.flex, children=[
        Panel(style=S(gap=4, alignItems=AlignItems.center), children=[
            Action(glyph=glyph, width=40, height=37, selected=session.group == identity and session.page == 'workspace',
                   onClick=partial(category, session, identity)),
            text(title, 10, Theme.blue if session.group == identity and session.page == 'workspace' else Theme.muted)])
        for identity, title, glyph in GROUPS])


@Component
def EditorPane(session=None, revision=0, page='workspace', width=760, height=440, focus=False):
    use_theme()
    middle_width = width - 434
    if focus:
        middle_width = width - (250 if session.focus_inspector else 0)
    return row([
        Panel(style=S(width=174, height=height, display=Display.none if focus else Display.flex), children=[
            Panel(style=S(position=Position.absolute, visible=page != 'projection'),
                  children=ToolList(session=session, revision=(session.tool, Theme.scale), height=height)),
            Panel(style=S(position=Position.absolute, visible=page == 'projection'),
                  children=ProjectionHelp(height=height)),
        ]),
        Viewport(session=session, revision=revision, width=middle_width, height=height),
        Panel(style=S(display=Display.flex if not focus or session.focus_inspector else Display.none),
              children=Inspector(session=session, revision=revision, height=height, page=page)),
    ], width=width, height=height, gap=10, alignItems=AlignItems.stretch)


@Component
def ProjectionHelp(height=440):
    use_theme()
    return surface(width=174, height=height, padding=12, gap=14, children=[
        text('投影工作流', 15),
        text('先预览，再逐层搭建', 10, Theme.muted),
        line(),
    ] + [Panel(style=S(gap=6), children=[
        row([icon(glyph, Theme.blue, 16), text(title, 12)]), text(hint, 11, Theme.muted, width=150)])
        for glyph, title, hint in [('cursor', '确定原点', '站到建造位置，将玩家脚下设为投影原点。'),
                                   ('layers', '准备材料', '根据右侧清单准备建材，投影不会消耗方块。'),
                                   ('cube', '逐层搭建', '对照半透明投影放置方块，随时检查完成进度。')]])


@Component
def PageContent(session=None, revision=0, width=760, height=440, focus=False):
    use_theme()
    use_session_fields(session, ('page',))
    page = session.page
    editor_page = use_ref('workspace')
    if page in ('workspace', 'projection'):
        editor_page.current = page
    panes = [
        RetainedPane(key='editor', active=page in ('workspace', 'projection'),
            style=S(position=Position.absolute, width=width, height=height),
            children=EditorPane(session=session, revision=revision, page=editor_page.current,
                                width=width, height=height, focus=focus)),
        RetainedPane(key='library', active=page == 'library',
            style=S(position=Position.absolute, width=width, height=height),
            children=Library(session=session, revision=revision, width=width, height=height)),
        RetainedPane(key='guide', active=page == 'guide',
            style=S(position=Position.absolute, width=width, height=height),
            children=Guide(session=session, revision=session.reduced_motion, width=width, height=height)),
    ]
    return PageMotion(page=page, width=width, height=height, children=panes)


@Component
def Workspace(session=None, revision=0):
    revision, set_revision = use_state(0)
    screen, set_screen = use_state(get_screen_size())
    measured_screen = use_ref(screen)
    resize_pending = use_ref(False)

    def refresh():
        set_revision(lambda previous: previous + 1)

    def subscribe():
        return session.subscribe(refresh, ())
    use_effect(subscribe, [session])

    def resized(unused):
        if resize_pending.current:
            return
        resize_pending.current = True

        def settle():
            resize_pending.current = False
            current = get_screen_size()
            if current != measured_screen.current:
                measured_screen.current = current
                set_screen(current)
        session.bridge.later(.05, settle)
    use_event('ScreenSizeChangedClientEvent', resized)
    Theme.configure(min(screen[1] / 640., screen[0] / 980.), not session.reduced_motion)
    width, height = screen[0] / Theme.scale, screen[1] / Theme.scale
    page = session.page
    focus = session.focus_view and page in ('workspace', 'projection')
    main_h = height - (115 if focus else 181)
    content_w = width - (24 if focus else 100)
    e = session.editor
    main = Image(color=Theme.bg, style=S(width='100%', height='100%'), children=[
        Image(color=Theme.white, style=S(width='100%', height=48 if focus else 65), children=row([
            Image(src=TEX + 'logo', style=S(width=29 if focus else 37, height=29 if focus else 37)),
            Panel(style=S(gap=1), children=[text('现代化投影', 16 if focus else 20),
                text('MODERN PROJECTION', 8, Theme.muted, display=Display.none if focus else Display.flex)]),
            Panel(style=S(flex=1)),
            Button(buttonBuilder=transparent, backgroundColor=Theme.green,
                   hoverColor=Color(0x178C7E2E), radius=7, style=S(height=32),
                   children=row([icon('check' if e.saved_revision == e.revision and session.library else 'draft', Theme.mint, 15),
                                 text('草稿已保存' if e.saved_revision == e.revision and session.library else '本地草稿',
                                      10, Theme.mint)], paddingHorizontal=12)),
            Action(label='保存配置', glyph='save', accent=True, width=115, height=32, onClick=partial(session.action, session.save)),
            Action(glyph='close', width=32, height=32, onClick=navigator.pop),
        ], height=48 if focus else 65, paddingHorizontal=18, gap=12)),
        PageNavigation(session=session, revision=session.content_revision, focus=focus),
        row([
            CategoryRail(session=session, height=main_h, focus=focus),
            PageContent(session=session, revision=session.content_revision, width=content_w, height=main_h, focus=focus),
        ], paddingHorizontal=12, gap=12, alignItems=AlignItems.stretch),
        row([
            text('工作层 Y', 11, Theme.blue, width=55),
            Action(glyph='minus', width=27, height=25, onClick=partial(session.layer, e.layer - 1)),
            text('%02d' % e.layer, 12, width=25, center=True),
            Action(glyph='plus', width=27, height=25, onClick=partial(session.layer, e.layer + 1)),
            Action(label='隔离图层', selected=session.solo_layer, width=92, height=26, compact=True, onClick=session.toggle_solo),
            Panel(style=S(flex=1)),
            text('方块 %s' % format(len(e.document.blocks), ','), 10, Theme.muted),
            text('选区 %s' % format(len(e.selection), ','), 10, Theme.muted),
            text('材质 %d' % len(e.document.materials()), 10, Theme.muted),
        ], height=38, paddingHorizontal=22, gap=10),
        Image(color=Theme.white, style=S(width='100%', height=29), children=row([
            Image(src=TEX + 'dot', color=Theme.mint, style=S(width=5, height=5)),
            TaskStatus(session=session),
            Panel(style=S(display=Display.flex if session.busy else Display.none), children=
                Action(label='取消', glyph='close', compact=True, height=22, onClick=session.bridge.cancel_world)),
            text('P 打开  ·  F6 / F7 两点选区', 9, Theme.muted),
        ], height=29, paddingHorizontal=20, gap=7)),
    ])
    return SafeArea(style=S(width='100%', height='100%'), children=[main,
        Confirmation(session=session, revision=session.ui_revision), ClickEffects()])


@Component
def TaskStatus(session=None):
    use_theme()
    use_session_fields(session, ('edit_progress',))
    return text(('处理中… ' if session.busy else '') + session.editor.message[:80], 10, Theme.muted, flex=1)


def category(session, identity):
    session.set('page', 'workspace')
    session.choose_group(identity)
