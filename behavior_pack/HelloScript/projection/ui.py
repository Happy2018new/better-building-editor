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
from .catalog import GROUPS, TOOLS, BY_ID
from .model import AIR
from .scene import Scene, MODES, HINTS
from .effects import ClickEffects


@Component
def ToolList(session=None, revision=0, height=440):
    use_theme()
    query = session.query.strip().lower()
    items = [t for t in TOOLS if (query in (t[0] + t[2] + t[3]).lower() if query else t[1] == session.group)]
    title = next(g[1] for g in GROUPS if g[0] == session.group)
    return surface(width=174, height=height, padding=12, children=[
        row([text('工具箱', 15, flex=1), text('64', 10, Theme.blue)]),
        Input(value=session.query, onChange=partial(session.set, 'query'), style=S(width=150, height=27, marginTop=12)),
        text('搜索工具 / 描述' if not query else '找到 %d 个工具' % len(items), 10, Theme.muted, marginTop=5, marginBottom=12),
        text('搜索结果' if query else title + '工具', 10, Theme.muted, marginBottom=7),
        Scroll(resetKey=(session.group, query), style=S(width=154, flex=1), children=Panel(style=S(width=144, gap=5), children=[
            Action(key=t[0], label=t[2], height=32, selected=session.tool == t[0],
                   onClick=partial(session.choose_tool, t[0]), compact=True)
            for t in items] or [text('没有匹配的工具', 11, Theme.muted)])),
        Panel(style=S(height=8)),
        surface(color=Theme.pale, padding=9, gap=3, children=[text('草稿内编辑', 11, Theme.blue), text('试验后再保存或应用', 10, Theme.muted)]),
    ])


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
def Viewport(session=None, revision=0, width=430, height=440):
    use_theme()
    e = session.editor
    doc = e.document
    focus = session.focus_view
    area_h = max(130, height - (136 if focus else 148))
    viewport_children = []
    if session.grid:
        viewport_children.append(Image(src=TEX + 'viewport_grid', style=S(width='100%', height='100%', opacity=.6)))
    viewport_children.append(Scene(key='scene_model', session=session, revision=revision, width=width, height=area_h))
    if not session.model_name:
        viewport_children.append(Panel(style=S(width='100%', height='100%', alignItems=AlignItems.center,
            justifyContent=JustifyContent.center, gap=10), children=[icon('cube', Theme.muted, 36),
                text(session.preview_error or '正在构建方块预览…', 12, Theme.muted)]))
    if session.view == 'layer':
        viewport_children.append(LayerCanvas(session=session, revision=session.ui_revision, width=width - 2, height=area_h))
    viewport_children.extend([
        surface(position=Position.absolute, left=12, top=12, paddingHorizontal=9, height=24,
                justifyContent=JustifyContent.center, color=Theme.white, children=text('Y %02d' % e.layer if session.view == 'layer' else
                    ('X %d · Y %d · Z %d' % session.focused if session.focused else '三维 · 可直接编辑'), 10, Theme.muted)),
        Image(src=TEX + 'axes', style=S(position=Position.absolute, right=13, bottom=13, width=50, height=50)),
    ])
    view_controls = [
        Action(glyph='minus', width=28, height=26, onClick=partial(session.camera_view, zoom=max(.25, session.zoom - .15))),
        text('%d%%' % int(round(session.zoom * 100)), 10, Theme.muted, width=35, center=True),
        Action(glyph='plus', width=28, height=26, onClick=partial(session.camera_view, zoom=min(3., session.zoom + .15))),
        Action(label='左转', height=26, compact=True, onClick=partial(turn_camera, session, -30)),
        Action(label='右转', height=26, compact=True, onClick=partial(turn_camera, session, 30)),
        Action(label='俯视', height=26, compact=True, onClick=partial(session.camera_view, yaw=0., pitch=90.)),
        Action(label='正视', height=26, compact=True, onClick=partial(session.camera_view, yaw=0., pitch=0.)),
        Panel(style=S(flex=1)),
        Action(glyph='grid', width=28, height=26, selected=session.grid, onClick=partial(session.set, 'grid', not session.grid)),
        Action(glyph='home', width=28, height=26, onClick=partial(reset_camera, session)),
    ]
    if session.view == 'layer':
        view_controls = [
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
             Action(label='还原视图' if focus else '展开视图', height=28, compact=True, accent=focus,
                    onClick=partial(session.set, 'focus_view', not focus))], paddingHorizontal=12, height=45 if focus else 57),
        Image(color=Theme.line, style=S(height=1, width='100%')),
        Image(color=Color(0xF7F9FCFF), style=S(height=area_h, width='100%'), children=viewport_children),
        row(view_controls, paddingHorizontal=12, height=36, gap=4),
        Panel(style=S(paddingHorizontal=12, gap=4), children=[
            (Segments(items=[('paint', '绘制'), ('erase', '擦除'), ('pick', '吸管'), ('start', '起点'), ('end', '终点')],
                      value=session.paint_mode, onChange=partial(session.set, 'paint_mode'), width=width - 24)
             if session.view == 'layer' else Segments(items=MODES, value=session.direct_mode,
                 onChange=session.choose_mode, width=width - 24)),
            text('点击格子编辑 · X / Z 为文档相对坐标' if session.view == 'layer' else HINTS[session.direct_mode], 10, Theme.muted, marginTop=2),
        ])])


def reset_camera(session):
    session.camera_view(35., 25., 1.)


def turn_camera(session, amount):
    session.camera_view(yaw=session.camera_pose[0] + amount)


@Component
def Inspector(session=None, revision=0, height=440):
    use_theme()
    pane = (ProjectionSettings(session=session, revision=session.ui_revision) if session.page == 'projection' else
            Layers(session=session, revision=session.ui_revision) if session.inspector == 'layers' else
            History(session=session, revision=session.ui_revision) if session.inspector == 'history' else Parameters(session=session, revision=session.ui_revision))
    children = []
    if session.page != 'projection':
        children.extend([Segments(items=[('params', '参数'), ('layers', '图层'), ('history', '历史')],
                                   value=session.inspector, onChange=partial(session.set, 'inspector'), width=216),
                         Panel(style=S(height=10))])
    children.append(pane)
    if session.page != 'projection':
        direct = session.view == '3d' and session.direct_mode != 'browse'
        children.extend([Panel(style=S(height=8)), Action(label='返回批量工具' if direct else '执行 · ' + BY_ID[session.tool][2], glyph='play',
            accent=True, height=37, onClick=partial(session.choose_mode, 'browse') if direct else session.run, enabled=not session.busy)])
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
def Workspace(session=None, revision=0):
    revision, set_revision = use_state(0)
    screen, set_screen = use_state(get_screen_size())
    measured_screen = use_ref(screen)
    resize_pending = use_ref(False)

    def refresh():
        set_revision(lambda previous: previous + 1)

    def subscribe():
        return session.subscribe(refresh)
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
    page_names = [('workspace', '工作台'), ('library', '建筑库'), ('projection', '投影'), ('guide', '入门指南')]
    middle_width = content_w - 434 if page != 'projection' else content_w - 250
    if focus:
        middle_width = content_w - (250 if session.focus_inspector else 0)
    # Keep the native block-model renderer alive across tabs and layer mode.
    # Removing it while its render job is pending can terminate the game process.
    editor_body = row([
        Panel(style=S(display=Display.none if focus or page == 'projection' else Display.flex),
              children=ToolList(session=session, revision=(session.group, session.query, session.tool, Theme.scale), height=main_h)),
        Viewport(session=session, revision=session.ui_revision, width=middle_width, height=main_h),
        Panel(style=S(display=Display.flex if not focus or session.focus_inspector else Display.none),
              children=Inspector(session=session, revision=session.ui_revision, height=main_h)),
    ], gap=10, alignItems=AlignItems.stretch,
       display=Display.flex if page in ('workspace', 'projection') else Display.none)
    body = Panel(style=S(width=content_w, height=main_h), children=[editor_body,
        Panel(style=S(display=Display.flex if page == 'library' else Display.none),
              children=Library(session=session, revision=session.ui_revision if page == 'library' else None, width=content_w, height=main_h)),
        Panel(style=S(display=Display.flex if page == 'guide' else Display.none),
              children=Guide(session=session, revision=session.reduced_motion, width=content_w, height=main_h)),
    ])
    categories = []
    for identity, title, glyph in GROUPS:
        categories.append(Panel(style=S(gap=4, alignItems=AlignItems.center), children=[
            Action(glyph=glyph, width=40, height=37, selected=session.group == identity and page == 'workspace',
                   onClick=partial(category, session, identity)),
            text(title, 10, Theme.blue if session.group == identity and page == 'workspace' else Theme.muted)]))
    main = Image(color=Theme.bg, style=S(width='100%', height='100%'), children=[
        Image(color=Theme.white, style=S(width='100%', height=48 if focus else 65), children=row([
            Image(src=TEX + 'logo', style=S(width=29 if focus else 37, height=29 if focus else 37)),
            Panel(style=S(gap=1), children=[text('现代化投影', 16 if focus else 20),
                text('MODERN PROJECTION', 8, Theme.muted, display=Display.none if focus else Display.flex)]),
            Panel(style=S(flex=1)),
            Button(buttonBuilder=transparent, backgroundColor=Theme.green,
                   hoverColor=Color(0x178C7E2E), radius=7, style=S(height=32),
                   children=row([text('草稿已保存' if e.saved_revision == e.revision and session.library else '本地草稿',
                                      10, Theme.mint)], paddingHorizontal=12)),
            Action(label='保存配置', glyph='save', accent=True, width=115, height=32, onClick=partial(session.action, session.save)),
            Action(glyph='close', width=32, height=32, onClick=navigator.pop),
        ], height=48 if focus else 65, paddingHorizontal=18, gap=12)),
        row([
            Segments(items=page_names, value=page, onChange=partial(session.set, 'page'), width=340),
            Panel(style=S(flex=1)),
            text(e.document.name[:24], 11, Theme.muted),
            Action(glyph='undo', width=29, height=28, onClick=partial(session.action, e.undo), enabled=bool(e.undo_stack)),
            Action(glyph='redo', width=29, height=28, onClick=partial(session.action, e.redo), enabled=bool(e.redo_stack)),
            Action(label='读取选区', glyph='cursor', width=100, height=28, onClick=partial(session.confirm, '读取世界选区将替换当前草稿，继续吗？', session.bridge.capture), enabled=not session.busy),
        ], paddingHorizontal=18, height=49, gap=8, display=Display.none if focus else Display.flex),
        row([
            surface(width=64, height=main_h, paddingTop=12, gap=13, alignItems=AlignItems.center,
                    display=Display.none if focus else Display.flex, children=categories),
            PageMotion(page=page, width=content_w, height=main_h, children=body),
        ], paddingHorizontal=12, gap=12, alignItems=AlignItems.stretch),
        row([
            text('Y', 12, Theme.blue, width=20),
            Action(glyph='minus', width=27, height=25, onClick=partial(session.layer, e.layer - 1)),
            text('%02d' % e.layer, 12, width=25, center=True),
            Action(glyph='plus', width=27, height=25, onClick=partial(session.layer, e.layer + 1)),
            Action(label='隔离图层', selected=session.solo_layer, width=78, height=26, compact=True, onClick=session.toggle_solo),
            Panel(style=S(flex=1)),
            text('方块 %s' % format(len(e.document.blocks), ','), 10, Theme.muted),
            text('选区 %s' % format(len(e.selection), ','), 10, Theme.muted),
            text('材质 %d' % len(e.document.materials()), 10, Theme.muted),
        ], height=38, paddingHorizontal=22, gap=10),
        Image(color=Theme.white, style=S(width='100%', height=29), children=row([
            Image(src=TEX + 'dot', color=Theme.mint, style=S(width=5, height=5)),
            text(('处理中… ' if session.busy else '') + e.message[:80], 10, Theme.muted, flex=1),
            text('P 打开  ·  F6 / F7 两点选区', 9, Theme.muted),
        ], height=29, paddingHorizontal=20, gap=7)),
    ])
    return SafeArea(style=S(width='100%', height='100%'), children=[main,
        Confirmation(session=session, revision=session.ui_revision), ClickEffects()])


def category(session, identity):
    session.page = 'workspace'
    session.choose_group(identity)
