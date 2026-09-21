# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Modern Projection professional workspace, entirely native Pyreact JsonUI."""
from __future__ import unicode_literals
import mod.client.extraClientApi as clientApi
from functools import partial
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from ..pyreact.native import get_screen_size
from .widgets import Theme, S, TEX, text, row, surface, icon, line, Action, Range, Segments, Doll, Scroll, Input, transparent
from .widgets import JellyButton as Button, PageMotion, use_theme, NativeText, retained_text
from .panels import Parameters, Layers, History, Library, ProjectionSettings, Guide, material_color, material_name
from .catalog import GROUPS, TOOLS, BY_ID, TOOL_ICONS
from .model import AIR
from .scene import Scene, MODES, HINTS
from .effects import ClickEffects
from .gizmo import OrientationGizmo
from .camera import zoom_label
from .material_browser import MaterialBrowser
from .motion import DialogMotion, WorkspaceMotion
from .preparation import PreparationQueue, PreparationPump


def use_session_fields(session, fields):
    unused, update = use_state(0)

    def refresh():
        update(lambda previous: previous + 1)

    def subscribe():
        return session.subscribe(refresh, fields)
    use_effect(subscribe, [session])


@Component
def RetainedPane(active=True, children=None, style=None, session=None):
    """Keep native controls and scroll position; refresh stale content on entry."""
    cached = use_ref(None)
    prepared, set_prepared = use_state(False)
    queue = getattr(session, '_ui_preparation', None)
    def prepare():
        if queue is not None and not active and cached.current is None:
            return queue.add(lambda: set_prepared(True))
    use_effect(prepare, [queue, active])
    if active or (prepared and cached.current is None):
        cached.current = children
    return Panel(cacheLayout=True, style=(style or Style()).merge(Style(visible=active)), children=cached.current)


@Component
def ToolList(session=None, revision=0, height=440):
    use_theme()
    use_session_fields(session, ('group', 'query', 'editing_mode'))
    settled_query, set_settled_query = use_state(session.query)
    serial = use_ref(0)

    def filter_after_typing():
        serial.current += 1
        current = serial.current
        value = session.query

        def settle():
            if serial.current == current:
                set_settled_query(value)
        session.bridge.later(.12, settle)

        def cancel():
            serial.current += 1
        return cancel
    use_effect(filter_after_typing, [session.query])
    query = settled_query.strip().lower()
    items = [t for t in TOOLS if (query in (t[0] + t[2] + t[3]).lower() if query else t[1] == session.group)]
    title = next(g[1] for g in GROUPS if g[0] == session.group)
    return surface(width=174, height=height, padding=12, children=[
        row([text('工具箱', 15, flex=1), text(str(len(TOOLS)), 10, Theme.blue)]),
        Input(value=session.query, onChange=partial(session.set, 'query'), style=S(width=150, height=27, marginTop=12)),
        retained_text('搜索工具 / 描述' if not query else '找到 %d 个工具' % len(items), 10, Theme.muted, width=150, marginTop=5, marginBottom=12),
        retained_text('搜索结果' if query else title + '工具', 10, Theme.muted, width=150, marginBottom=7),
        Panel(style=S(width=154, flex=1), children=
            ToolGroup(session=session, group=session.group, query=query, selected=session.tool)),
        Panel(style=S(height=8)),
        surface(color=Theme.pale, padding=9, gap=3, children=[text('草稿内编辑', 11, Theme.blue), text('试验后再保存或应用', 10, Theme.muted)]),
    ])


@Component
def ToolGroup(session=None, group=None, query='', selected=None):
    use_theme()
    items = [t for t in TOOLS if (query in (t[0] + t[2] + t[3]).lower() if query else t[1] == group)]
    # One stable native pool serves both categories and search. Removing a
    # result while typing can interrupt Bedrock's edit_box focus; hiding it
    # preserves focus without a duplicate pool for every category and search.
    pool = TOOLS
    identities = set(t[0] for t in items)
    return Scroll(resetKey=(group, query), style=S(width=154, height='100%'),
        children=Panel(style=S(width=144, gap=5), children=[
            Panel(key=t[0], cacheLayout=True, style=S(width=144, height=32, display=Display.flex if t[0] in identities else Display.none), children=
                Action(label=t[2], glyph=TOOL_ICONS[t[0]], leading=True, height=32,
                       selected=selected == t[0], onClick=partial(session.choose_tool, t[0]), compact=True))
            for t in pool] + [Panel(key='empty', style=S(display=Display.none if items else Display.flex),
                                   children=text('没有匹配的工具', 11, Theme.muted))]))


@Component
def ViewNavigation(session=None, width=430, revision=0):
    use_theme()
    use_session_fields(session, ('view', 'camera_depth'))
    # These move the viewpoint, so the model moves in the opposite direction.
    controls = [Action(label=label, glyph=glyph, compact=True, width=54, height=27,
                       onClick=partial(session.pan_view, x, y)) for label, glyph, x, y in (
        ('左移', 'arrow_left', .12, 0.), ('右移', 'arrow_right', -.12, 0.),
        ('上移', 'arrow_up', 0., .12), ('下移', 'arrow_down', 0., -.12))]
    controls.extend([
        Action(label='前移', glyph='front_view', compact=True, width=54, height=27,
               onClick=partial(session.move_depth, 1)),
        Action(label='后移', glyph='undo', compact=True, width=54, height=27,
               enabled=session.camera_depth > 0., onClick=partial(session.move_depth, -1))])
    return Panel(style=S(gap=3), children=[row(controls[:4], gap=3), row(controls[4:], gap=3)] if width < 520
                 else [row(controls, gap=3)])


@Component
def LocateSelected(session=None):
    use_theme()
    use_session_fields(session, ('point_edit', 'view'))
    return Action(label='定位选中', glyph='pin', height=28, compact=True,
                  enabled=session.focused is not None, onClick=session.locate_selected)


@Component
def PreviewProgress(session=None, width=400):
    use_theme()
    container, label, fill, cancel = use_ref(None), use_ref(None), use_ref(None), use_ref(None)
    previous = use_ref(None)
    card_width = min(250, width-24)

    def tick(unused_now):
        job = session.edit_job
        visible = job is not None or (session.preview_pending and session.tiles.report_progress)
        done, total = (min(job.processed, job.total), job.total) if job else session.tiles.progress()
        signature = (visible, job is not None, done, total, Theme.scale, card_width)
        if signature == previous.current or not all(ref.current for ref in (container,label,fill,cancel)):
            return
        previous.current = signature
        container.current.SetVisible(visible, False)
        cancel.current.SetVisible(job is not None, False)
        if visible:
            message = ('正在修改方块' if job else '正在更新预览') + '，%d / %d' % (done,total)
            label.current.asLabel().SetText(message)
            fill.current.SetSize(((card_width-16)*Theme.scale*min(1.,done/float(max(1,total))),4*Theme.scale))
    use_animation_frame(tick)
    return Panel(ref=container, style=S(position=Position.absolute, top=42, left=12, width=card_width,
                         zIndex=410, visible=False), children=surface(padding=8, gap=6, children=[
        row([NativeText(ref=label, content='', fontSize=10*Theme.scale, color=Theme.muted,
                        textAlign=TextAlignment.left, shadow=False, style=S(flex=1,height=20)),
             Panel(ref=cancel, style=S(width=34,height=23), children=Action(label='取消', compact=True,
                   height=23, width=34, onClick=session.cancel_edit))]),
        Image(color=Theme.line, style=S(width='100%', height=4), children=
              Image(ref=fill, color=Theme.blue, style=S(width=0, height=4))),
    ]))


@Component
def Viewport(session=None, revision=0, width=430, height=440):
    use_theme()
    use_session_fields(session, ('view', 'preview', 'preview_visible'))
    navigation = use_ref(None)
    e = session.editor
    doc = e.document
    focus = session.focus_view
    area_h = max(130, height - (191 if focus else 203))
    viewport_children = []
    viewport_children.append(Scene(key='scene_model', session=session, revision=revision, width=width, height=area_h, navigation=navigation))
    if not session.model_name:
        viewport_children.append(Panel(key='empty_model', style=S(width='100%', height='100%', alignItems=AlignItems.center,
            justifyContent=JustifyContent.center, gap=10), children=[icon('cube', Theme.muted, 36),
                text(session.preview_error or ('正在构建方块预览…' if session.preview_pending else
                     '当前没有可见方块，点击网格放置'), 12, Theme.muted)]))
    viewport_children.extend([
        Panel(key='scene_status', style=S(position=Position.absolute, left=12, top=12, zIndex=400, visible=session.view == '3d'),
              children=surface(paddingHorizontal=9, height=24, justifyContent=JustifyContent.center,
                  children=SceneStatus(session=session))),
        Panel(key='scene_error', style=S(position=Position.absolute, left=12, bottom=12, zIndex=400, visible=bool(session.preview_error)),
              children=text(session.preview_error, 11, Theme.red, width=width-24)),
        Panel(key='orientation', style=S(position=Position.absolute, width='100%', height='100%', visible=session.view == '3d', zIndex=400),
              children=OrientationGizmo(session=session)),
        Panel(key='view_navigation', ref=navigation, style=S(position=Position.absolute, left=12, bottom=12, zIndex=400, visible=session.view == '3d'),
              children=ViewNavigation(session=session, width=width, revision=revision)),
        PreviewProgress(key='preview_progress', session=session, width=width),
    ])
    view_controls = [
        Action(glyph='minus', width=28, height=26, onClick=partial(session.camera_view, zoom=max(.25, session.zoom / 1.2))),
        text(zoom_label(session.zoom), 10, Theme.muted, width=44, center=True),
        Action(glyph='plus', width=28, height=26, onClick=partial(session.camera_view, zoom=session.zoom * 1.2)),
        Action(label='左转', height=26, compact=True, onClick=partial(turn_camera, session, -30)),
        Action(label='右转', height=26, compact=True, onClick=partial(turn_camera, session, 30)),
        Action(label='俯视', height=26, compact=True, onClick=partial(session.camera_view, yaw=0., pitch=90.)),
        Action(label='正视', height=26, compact=True, onClick=partial(session.camera_view, yaw=0., pitch=0.)),
        Panel(style=S(flex=1)),
        Action(label='网格', glyph='grid', compact=True, height=26, selected=session.grid, onClick=partial(session.set, 'grid', not session.grid)),
        Action(label='复位', glyph='home', compact=True, height=26, onClick=partial(reset_camera, session)),
    ]
    return surface(width=width, height=height, children=[
        row([Panel(style=S(flex=1, gap=3), children=[text('专注编辑' if focus else '场景视图', 14),
                text(('%d × %d × %d' % doc.size) + ('，' + material_name(e.material) if focus else ''), 10, Theme.muted)]),
             Panel(style=S(display=Display.flex if focus else Display.none, flexDirection=FlexDirection.row, gap=5), children=[
                 Action(glyph='undo', width=28, height=26, onClick=partial(session.action, e.undo), enabled=bool(e.undo_stack)),
                 Action(glyph='redo', width=28, height=26, onClick=partial(session.action, e.redo), enabled=bool(e.redo_stack)),
                 Action(label='材质与属性', height=27, compact=True, selected=session.focus_inspector,
                        onClick=partial(session.set, 'focus_inspector', not session.focus_inspector))]),
             LocateSelected(session=session),
             Action(label='还原视图' if focus else '展开视图', height=28, compact=True, accent=focus,
                    onClick=partial(session.set, 'focus_view', not focus))], paddingHorizontal=12, height=45 if focus else 57),
        Image(color=Theme.line, style=S(height=1, width='100%')),
        row([Segments(items=[('full', '完整'), ('section', '切面'), ('single', '单层')],
                      value=session.current_display_mode(), onChange=session.display_mode, width=178),
             Panel(style=S(flex=1)),
             text('Y', 11, Theme.blue),
             Action(glyph='minus', width=27, height=27, enabled=e.layer > 0, onClick=partial(session.layer, e.layer-1)),
             Input(value=str(e.layer), onChange=partial(set_view_layer, session), style=S(width=44, height=27)),
             Action(glyph='plus', width=27, height=27, enabled=e.layer < doc.size[1]-1,
                    onClick=partial(session.layer, e.layer+1))], paddingHorizontal=8, height=34, gap=4),
        Image(color=Color(0xF7F9FCFF), style=S(height=area_h, width='100%'), children=viewport_children),
        row(view_controls, paddingHorizontal=6 if width < 480 else 10,
            height=36, gap=1 if width < 480 else 3),
        ViewportModes(session=session, revision=revision, width=width)])


@Component
def ViewportModes(session=None, revision=0, width=430):
    use_theme()
    use_session_fields(session, ('editing_mode',))
    return Panel(style=S(paddingHorizontal=12, gap=4), children=[
        Segments(items=MODES, value=session.direct_mode, onChange=session.choose_mode, width=width-24),
        Panel(style=S(width='100%', height=36, marginTop=2),
              children=PlacementControls(session=session, revision=revision, width=width-24))])


@Component
def SceneStatus(session=None):
    use_theme()
    use_session_fields(session, ('view', 'point_edit', 'camera_depth'))
    label = 'X %d   Y %d   Z %d' % session.focused if session.focused else '三维，可直接编辑'
    if session.camera_depth > 0.:
        label += '，视线推进 %g 格' % session.camera_depth
    return text(label, 10, Theme.muted)


@Component
def PlacementControls(session=None, revision=0, width=400):
    use_theme()
    use_session_fields(session, ('input_mode', 'editing_mode'))
    hint = HINTS[session.direct_mode]
    if session.touch_mode:
        hint = '轻触操作，拖动旋转，下方按钮缩放与移动'
    if session.paste_active():
        hint = '点击固定粘贴起点，拖动旋转，确认后粘贴整个复制区域'
    return row([retained_text(hint, 10, Theme.muted, flex=1, slots=48, lines=2)], width=width, height=34)


def reset_camera(session):
    session.reset_camera()


def set_view_layer(session, value):
    try:
        layer = int(value)
    except (ValueError, TypeError):
        return
    session.layer(layer)


def turn_camera(session, amount):
    session.camera_view(yaw=session.camera_pose[0] + amount)


@Component
def Inspector(session=None, revision=0, height=440, page='workspace'):
    use_theme()
    use_session_fields(session, ('inspector', 'view', 'editing_mode'))
    projecting = page == 'projection'
    active = 'projection' if projecting else session.inspector
    panes = []
    for name, component in (('params', Parameters), ('layers', Layers), ('history', History), ('projection', ProjectionSettings)):
        content_revision = (session.content_revision, session.tool, session.direct_mode,
                            session.box_anchor, session.paste_origin, session.paste_pinned)
        if name == 'params' and session.direct_mode != 'browse':
            content_revision = (content_revision, session.view)
        panes.append(RetainedPane(key=name, active=active == name, session=session,
            style=S(position=Position.absolute, width=216, height=height-111),
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
                Action(label='取消编辑' if session.edit_job else '擦除选区' if erase_selection else '返回批量工具' if direct else
                       '确认粘贴' if session.paste_active() else '执行：' + BY_ID[session.tool][2],
                    glyph='close' if session.edit_job else 'erase' if erase_selection else 'play', accent=True, height=37, labelWidth=172,
                    onClick=session.cancel_edit if session.edit_job else session.erase_selection if erase_selection else
                            partial(session.choose_mode, 'browse') if direct else session.run,
                    enabled=not session.busy and (not session.paste_active() or (session.editor.clipboard is not None and session.paste_pinned)) and
                            (session.edit_job is not None or not erase_selection or
                            (bool(session.editor.selection) and session.box_anchor is None)))),
            Panel(style=S(position=Position.absolute, top=8, width='100%', visible=projecting), children=
                Action(label='返回工作台', glyph='brush', height=37, onClick=partial(session.set, 'page', 'workspace'))),
        ])]
    return surface(width=240, height=height, padding=12, children=children)


@Component
def RenameDialog(session=None, width=980, height=640):
    use_theme()
    use_session_fields(session, ('pending_rename',))
    opened = session.pending_rename is not None
    draft, set_draft = use_state('')
    visited = use_ref(False)
    if opened:
        visited.current = True
    def start():
        if opened:
            set_draft(session.pending_rename[1])
    use_effect(start, [session.pending_rename])
    def content():
        return surface(width=420, padding=24, gap=18, children=[
            row([icon('edit', Theme.blue, 24), text('重命名建筑配置', 21)]),
            text('建筑名称', 12, Theme.muted),
            Input(value=draft, onChange=set_draft, style=S(width=372, height=34)),
            text(session.rename_error or '请输入 1–64 字的建筑名称', 11,
                 Theme.red if session.rename_error else Theme.muted, width=372),
            row([Action(label='取消', enabled=opened, onClick=partial(session.set, 'pending_rename', None)),
                 Action(label='保存名称', glyph='check', enabled=opened and bool(draft.strip()), accent=True,
                        onClick=partial(session.accept_rename, draft))])])
    card = use_memo(lambda: content() if visited.current else None,
                    [draft, opened, session.rename_error, Theme.scale, visited.current])
    return DialogMotion(opened=opened, session=session, children=card)


@Component
def Confirmation(session=None, revision=0, height=640):
    use_theme()
    use_session_fields(session, ('pending_confirm',))
    message = use_ref('')
    opened = bool(session.pending_confirm)
    if opened:
        message.current = session.pending_confirm[0]

    def content():
        return surface(width=420, padding=24, gap=18, children=[
            icon('info', Theme.blue, 28), text('请确认这次操作', 21),
            text(message.current, 13, Theme.muted, width=372),
            row([Action(label='取消', enabled=opened, onClick=partial(session.set, 'pending_confirm', None)),
                 Action(label='确认继续', enabled=opened, accent=True, onClick=session.accept)])])
    card = use_memo(content, [message.current, opened, Theme.scale])
    return DialogMotion(opened=opened, session=session, children=card)


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
    return surface(width=64, height=height, paddingVertical=12, gap=13,
        alignItems=AlignItems.center, justifyContent=JustifyContent.center,
        display=Display.none if focus else Display.flex, children=[
        Panel(style=S(gap=4, alignItems=AlignItems.center), children=[
            Action(glyph=glyph, width=40, height=37, selected=session.group == identity and session.page == 'workspace',
                   onClick=partial(category, session, identity)),
            text(title, 10, Theme.blue if session.group == identity and session.page == 'workspace' else Theme.muted)])
        for identity, title, glyph in GROUPS])


@Component
def EditorPane(session=None, revision=0, page='workspace', width=760, height=440, focus=False, entrance=None):
    use_theme()
    stage, set_stage = use_state(0)
    def prepare():
        alive = [True]
        if stage < 3:
            session.bridge.later(.015, lambda: set_stage(stage+1) if alive[0] else None)
        elif entrance is not None and entrance.current:
            entrance.current['ready']()
        return lambda: alive.__setitem__(0, False)
    use_effect(prepare, [stage])
    middle_width = width - 434
    if focus:
        middle_width = width - (250 if session.focus_inspector else 0)
    return row([
        Panel(style=S(width=174, height=height, display=Display.none if focus else Display.flex), children=[
            Panel(style=S(position=Position.absolute, visible=page != 'projection'),
                  children=ToolList(session=session, revision=(session.tool, Theme.scale), height=height) if stage>=2 else None),
            RetainedPane(active=page == 'projection', session=session,
                  style=S(position=Position.absolute, width=174, height=height),
                  children=ProjectionHelp(height=height)),
        ]),
        Panel(style=S(width=middle_width, height=height), children=
            Viewport(session=session, revision=revision, width=middle_width, height=height) if stage>=1 else None),
        Panel(style=S(display=Display.flex if not focus or session.focus_inspector else Display.none),
              children=Inspector(session=session, revision=revision, height=height, page=page) if stage>=3 else None),
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
def PageContent(session=None, revision=0, width=760, height=440, focus=False, entrance=None):
    use_theme()
    use_session_fields(session, ('page',))
    page = session.page
    editor_page = use_ref('workspace')
    if page in ('workspace', 'projection'):
        editor_page.current = page
    panes = [
        RetainedPane(key='editor', active=page in ('workspace', 'projection'), session=session,
            style=S(position=Position.absolute, width=width, height=height),
            children=EditorPane(session=session, revision=revision, page=editor_page.current,
                                width=width, height=height, focus=focus, entrance=entrance)),
        RetainedPane(key='library', active=page == 'library', session=session,
            style=S(position=Position.absolute, width=width, height=height),
            children=Library(session=session, revision=revision, width=width, height=height)),
        RetainedPane(key='guide', active=page == 'guide', session=session,
            style=S(position=Position.absolute, width=width, height=height),
            children=Guide(session=session, revision=session.reduced_motion, width=width, height=height)),
    ]
    return PageMotion(page=page, width=width, height=height, children=panes)


@Component
def Workspace(session=None, revision=0):
    revision, set_revision = use_state(0)
    screen, set_screen = use_state(get_screen_size())
    measured_screen = use_ref(screen)
    measured_pixels = use_ref(None)
    resize_pending = use_ref(False)
    entrance = use_ref(None)
    preparation = use_ref(None)
    if preparation.current is None:
        preparation.current = PreparationQueue(session)
    session._ui_preparation = preparation.current
    def release_preparation():
        def cleanup():
            preparation.current.ready = False
            preparation.current.jobs[:] = []
            preparation.current.inputs.clear()
            if getattr(session, '_ui_preparation', None) is preparation.current:
                del session._ui_preparation
        return cleanup
    use_effect(release_preparation, [session])

    def close():
        if entrance.current:
            entrance.current['close']()

    def refresh():
        set_revision(lambda previous: previous + 1)

    def subscribe():
        return session.subscribe(refresh, ())
    use_effect(subscribe, [session])

    def resized(unused):
        if resize_pending.current:
            return
        resize_pending.current = True

        def settle(final=False):
            if final:
                resize_pending.current = False
            current = get_screen_size()
            game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
            pixels = tuple(game.GetScreenViewInfo()[:2])
            pixels_changed = pixels != measured_pixels.current
            measured_pixels.current = pixels
            if current != measured_screen.current:
                measured_screen.current = current
                set_screen(current)
            elif pixels_changed:
                refresh()
            if not final:
                # The engine's physical viewport can settle after the logical
                # UI size. Recheck once so integer glyph scaling does not keep
                # a transient width from the native resize notification.
                session.bridge.later(.25, partial(settle, True))
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
            Action(glyph='close', width=32, height=32, onClick=close),
        ], height=48 if focus else 65, paddingHorizontal=18, gap=12)),
        PageNavigation(session=session, revision=session.content_revision, focus=focus),
        row([
            CategoryRail(session=session, height=main_h, focus=focus),
            PageContent(session=session, revision=session.content_revision, width=content_w, height=main_h, focus=focus, entrance=entrance),
        ], paddingHorizontal=12, gap=12, alignItems=AlignItems.stretch),
        row([
            text('工作层 Y', 11, Theme.blue, width=55),
            Action(glyph='minus', width=27, height=25, onClick=partial(session.layer, e.layer - 1)),
            text('%02d' % e.layer, 12, width=25, center=True),
            Action(glyph='plus', width=27, height=25, onClick=partial(session.layer, e.layer + 1)),
            text('网格高度' if not (session.solo_layer or session.section) else
                 '仅显示 Y 层' if session.solo_layer else '显示 Y 层和下方', 10, Theme.muted),
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
            text('P 打开，F6 / F7 两点选区', 9, Theme.muted),
        ], height=29, paddingHorizontal=20, gap=7)),
    ])
    return SafeArea(style=S(width='100%', height='100%'), children=[
        WorkspaceMotion(controller=entrance, awaitEditor=page in ('workspace', 'projection'),
                        width=width, preparation=preparation.current, children=main),
        Confirmation(session=session, revision=session.ui_revision, height=height),
        RenameDialog(session=session, width=width, height=height),
        MaterialBrowser(session=session, revision=session.ui_revision, width=width, height=height),
        ClickEffects(), PreparationPump(queue=preparation.current)])


@Component
def TaskStatus(session=None):
    use_theme()
    use_session_fields(session, ())
    message = ('处理中… ' if session.busy else '') + session.editor.message[:80]
    return text(message, 10, Theme.muted, flex=1)


def category(session, identity):
    session.set('page', 'workspace')
    session.choose_group(identity)
