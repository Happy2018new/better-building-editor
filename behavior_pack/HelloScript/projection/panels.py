# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Tool parameters, layer editing, library and survival projection panels."""
from __future__ import unicode_literals
from functools import partial
from ..pyreact import *
from .widgets import Theme, S, text, row, surface, icon, line, Action, Range, Segments, Input, Scroll
from .widgets import JellyButton as Button, use_theme, retained_text
from .catalog import BY_ID, MATERIALS, tool_parameters
from .model import AIR, MAX_AXES, bounds
from .coordinates import parse_coordinates
from .preparation import PreparedColumn


def material_name(value):
    from .materials import DISPLAY_NAMES
    return DISPLAY_NAMES.get(value, value[0].split(':')[-1])


def material_color(value):
    code = next((m[3] for m in MATERIALS if tuple(m[:2]) == value), '9BA6B4')
    return Color(int(code + 'FF', 16))


@Component
def Coordinates(label='', value=(0, 0, 0), onChange=None, onValidityChange=None):
    use_theme()
    draft, set_draft = use_state(', '.join(str(v) for v in value))
    valid, set_valid = use_state(True)

    def sync():
        try:
            if parse_coordinates(draft) == tuple(value):
                return
        except (ValueError, TypeError):
            pass
        set_draft(', '.join(str(v) for v in value))
        set_valid(True)
    use_effect(sync, [value])

    def change(raw):
        set_draft(raw)
        try:
            values = parse_coordinates(raw)
        except (ValueError, TypeError):
            set_valid(False)
            if onValidityChange:
                onValidityChange(False)
            return
        set_valid(True)
        if onValidityChange:
            onValidityChange(True)
        onChange(values)
    return Panel(style=S(gap=4, marginBottom=7), children=[
        text(label if valid else '格式：X, Y, Z，整数', 10, Theme.muted if valid else Theme.red),
        Input(value=draft, onChange=change, style=S(width='100%', height=27))])


@Component
def MaterialIcon(value=AIR, size=30):
    """Air has no inventory renderer; keep its outline separate from real items."""
    use_theme()
    last_item = use_ref(('minecraft:stone', 0))
    if value != AIR:
        last_item.current = value
    return Panel(style=S(width=size, height=size), children=[
        Panel(style=S(position=Position.absolute, visible=value == AIR), children=icon('box_outline', Theme.muted, size)),
        Item(identifier=last_item.current[0], aux=last_item.current[1],
             style=S(position=Position.absolute, width=size, height=size, visible=value != AIR))])


@Component
def MaterialPicker(session=None, revision=0, channels=None):
    use_theme()
    channel, set_channel = use_state('material')
    managing, set_managing = use_state(False)
    picked, set_picked = use_state(None)
    e = session.editor
    last_channels = use_ref(channels or [('material', '主材质'), ('secondary', '副材质'), ('source', '替换来源')])
    if channels:
        last_channels.current = channels
    channels = last_channels.current
    active = channel if channel in [pair[0] for pair in channels] else channels[0][0]

    def choose(value):
        if managing:
            set_picked(value)
        else:
            session.set_editor(active, value)
    current = getattr(e, active)
    current_name = next((item['name'] for item in session.block_catalogue if item['value'] == current), material_name(current))
    index = session.palette.index(picked) if picked in session.palette else -1
    cells = [Button(key='mat%d' % i, onClick=partial(choose, value),
                    buttonBuilder=partial(material_background, value == (picked if managing else current)),
                    style=S(width=49, height=36), children=MaterialIcon(value=value, size=25))
             for i, value in enumerate(session.palette)]
    cells.append(Button(key='add_material', onClick=partial(session.open_materials, active),
                        buttonBuilder=partial(material_background, False), style=S(width=49, height=36),
                        children=icon('plus', Theme.blue, 22)))
    return Panel(style=S(gap=7), children=[
        Segments(items=channels, value=active, onChange=set_channel, width=216),
        row([MaterialIcon(value=current, size=30),
             Panel(style=S(flex=1), children=[text(current_name, 12, width=175), text('方块附加值  %d' % current[1], 10, Theme.muted)])]),
        row([text('常用方块', 11, Theme.muted, flex=1),
             Action(label='完成' if managing else '整理', glyph='check' if managing else 'sliders', compact=True,
                    height=25, width=62, selected=managing, onClick=partial(set_managing, not managing))]),
        Panel(style=S(flexDirection=FlexDirection.row, flexWrap=FlexWrap.wrap, gap=5,
                      height=((len(cells)+3)//4)*41-5, flexShrink=0), children=cells),
        optional('palette_management', managing, [
            text('选中常用方块，再移动或移除', 10, Theme.muted),
            row([Action(label='前移', glyph='arrow_left', compact=True, width=66, height=27, enabled=index>0,
                        onClick=partial(session.edit_palette, picked, -1)),
                 Action(label='后移', glyph='arrow_right', compact=True, width=66, height=27,
                        enabled=0<=index<len(session.palette)-1, onClick=partial(session.edit_palette, picked, 1)),
                 Action(label='移除', glyph='trash', compact=True, danger=True, width=66, height=27, enabled=index>=0,
                        onClick=partial(session.edit_palette, picked))]),
            text('仅移除快捷入口，不改变建筑方块', 10, Theme.muted, width=216)], gap=9),
        text('点击 + 按分类或中文名称添加方块', 10, Theme.muted, width=216),
    ])


def material_background(selected, state):
    return Image(color=Theme.tint if selected or state != ButtonState.default else Theme.pale)


def optional(identity, visible, children, gap=7):
    return OptionalSection(key=identity, visible=visible, children=children, gap=gap)


@Component
def OptionalSection(visible=False, children=None, gap=7):
    cached = use_ref(None)
    if visible:
        cached.current = children
    return Panel(style=S(width='100%', gap=gap, display=Display.flex if visible else Display.none), children=cached.current)


@Component
def SelectionBounds(session=None, revision=0):
    use_theme()
    e = session.editor
    lo, hi = bounds(e.selection) if e.selection else (e.start, e.end)
    rows = [row([text('轴', 10, Theme.muted, width=16), text('下界', 10, Theme.muted, width=94, center=True),
                 text('上界', 10, Theme.muted, width=94, center=True)], gap=6)]
    for axis, name in enumerate('XYZ'):
        children = [text(name, 11, Theme.blue, width=16)]
        for side, point in enumerate((lo, hi)):
            children.append(row([
                Action(glyph='minus', width=25, height=25,
                       enabled=point[axis] > (0 if side == 0 else lo[axis]),
                       onClick=partial(session.adjust_boundary, axis, side, -1)),
                text(str(point[axis]), 10, width=36, center=True),
                Action(glyph='plus', width=25, height=25,
                       enabled=point[axis] < (hi[axis] if side == 0 else e.document.size[axis]-1),
                       onClick=partial(session.adjust_boundary, axis, side, 1))], gap=4))
        rows.append(row(children, gap=6))
    return Panel(cacheLayout=True, style=S(width=216, height=115.5, gap=9, marginTop=3, marginBottom=3), children=rows)


@Component
def PasteControls(session=None, revision=0):
    use_theme()
    precise, set_precise = use_state(False)
    from .pasting import paste_error
    e = session.editor
    clip = e.clipboard
    error = paste_error(e.document, clip, session.paste_origin)
    return Panel(style=S(gap=10), children=[
        line(), text('粘贴预览', 15),
        text('请先复制或剪切一个区域' if clip is None else '尺寸  %d × %d × %d' % tuple(clip['size']), 12, Theme.blue),
        Panel(style=S(gap=4), children=[
            text('点击模型或网格，固定粘贴起点', 10, Theme.muted, width=216),
            text('预览完整范围后，点击确认粘贴', 10, Theme.muted, width=216)]),
        row([text('粘贴起点', 12, flex=1),
             text('已固定起点' if session.paste_pinned else '随指针定位', 10, Theme.blue)]),
        Panel(style=S(gap=8), children=[row([
              text(axis, 11, Theme.blue, width=20),
              text(('左右', '高低', '前后')[i], 10, Theme.muted, flex=1),
              row([Action(glyph='minus', width=29,height=28, enabled=session.paste_origin[i]>0,
                     onClick=partial(session.move_paste, i, -1)),
                   text(str(session.paste_origin[i]), 12, width=42,center=True),
                   Action(glyph='plus', width=29,height=28, enabled=session.paste_origin[i]<e.document.size[i]-1,
                     onClick=partial(session.move_paste, i, 1))], gap=4)
              ]) for i,axis in enumerate('XYZ')]),
        row([Action(label='重新定位', glyph='pin', compact=True, width=104, height=28,
                    onClick=partial(session.set, 'paste_pinned', False)),
             Action(label='坐标输入', glyph='sliders', compact=True, width=104, height=28, selected=precise,
                    onClick=partial(set_precise, not precise))], gap=8),
        optional('paste_coordinates', precise,
                 Coordinates(label='粘贴起点  X, Y, Z', value=session.paste_origin, onChange=session.set_paste_origin)),
        text(error or ('包含空气，覆盖目标范围' if session.tool=='paste' else '跳过空气，保留目标原有方块'),
             10, Theme.red if error else Theme.muted, width=216),
        Action(label='退出粘贴', glyph='close', compact=True, height=28,
               onClick=partial(session.choose_mode, 'select')),
    ])


@Component
def Parameters(session=None, revision=0, height=330):
    use_theme()
    e = session.editor
    tool = BY_ID[session.tool]
    options = tool_parameters(session.tool)
    if session.view == '3d' and session.direct_mode != 'browse':
        from .scene import MODES, HINTS
        tool = ('direct', 'edit', dict(MODES)[session.direct_mode], HINTS[session.direct_mode])
        options = set(['material']) if session.direct_mode in ('place', 'paint', 'pick') else set()
    channels = [pair for pair in [('material', '主材质'), ('secondary', '副材质'), ('source', '替换来源')] if pair[0] in options]
    if e.mask == 'material':
        channels.append(('filter_material', '匹配材质'))
    return Scroll(resetKey=(session.tool, session.direct_mode), style=S(width=230, height=height), children=Panel(style=S(width=216, gap=6), children=[
        retained_text('视图操作' if tool[0] == 'direct' else '工具参数', 10, Theme.muted, width=216, slots=4, marginTop=6),
        retained_text(tool[2], 20, width=216, slots=16),
        # Split help by sentence length into readable, deliberate lines.
        retained_text(tool[3], 11, Theme.muted, width=216, slots=48, lines=2),
        optional('erase_scope', session.direct_mode == 'erase', [
            text('擦除范围', 12),
            Segments(items=[('single', '单格'), ('selection', '选区')], value=session.erase_scope,
                     onChange=partial(session.set, 'erase_scope'), width=216),
            text('点击方块擦除一格' if session.erase_scope == 'single' else
                 '保留选区范围，点击下方擦除选区', 10, Theme.muted)]),
        optional('paste_parameters', session.paste_active(), PasteControls(session=session, revision=revision)),
        optional('selection_parameters', not session.paste_active(), SelectionParameters(session=session,
            revision=session.content_revision, anchor=session.box_anchor, corners='start' in options or 'end' in options)),
        ModificationMask(session=session, revision=session.content_revision),
        line(), optional('materials', bool(channels), MaterialPicker(session=session, revision=session.content_revision, channels=channels)),
        optional('material_line', bool(channels), line()),
        optional('thickness', 'thickness' in options, Range(label='厚度', value=e.thickness, minimum=1, maximum=8, integer=True,
              onChange=partial(session.range_value, 'thickness'), unit=' 格')),
        optional('step', 'step' in options, Range(label='步长 / 纹理间距', value=e.step, minimum=1, maximum=16, integer=True,
              onChange=partial(session.range_value, 'step'), unit=' 格')),
        optional('ratio', 'ratio' in options, Range(label='副材质比例', value=e.ratio, minimum=0, maximum=1,
              onChange=partial(session.range_value, 'ratio'))),
        optional('seed', 'seed' in options, row([text('随机种子', 11, Theme.muted, flex=1),
             Action(label=str(e.seed), onClick=partial(session.set_editor, 'seed', e.seed + 1), width=72, height=26)])),
        optional('seed_help', 'seed' in options, text('点击种子切换可复现的随机图案', 10, Theme.muted)),
        Panel(style=S(height=8)),
    ]))


@Component
def SelectionParameters(session=None, revision=0, anchor=None, corners=False):
    use_theme()
    coordinates_open, set_coordinates_open = use_state(False)
    selection_tools, set_selection_tools = use_state(False)
    e = session.editor
    return Panel(style=S(width=216, gap=7), children=[line(), text('当前选区', 12),
        retained_text('%d 格已选择' % len(e.selection) + ('，%d 层已锁定' % len(e.locked_layers) if e.locked_layers else ''),
                      10, Theme.muted, width=216, slots=32),
        row([Action(label='全选', glyph='grid', compact=True, width=104, height=27,
                    onClick=partial(session.action, e.run, 'select_all')),
             Action(label='坐标设置', glyph='sliders', compact=True, width=108, height=27, selected=coordinates_open,
                    onClick=partial(set_coordinates_open, not coordinates_open))], gap=4),
        row([Action(label='选择当前层', glyph='layers', compact=True, width=104, height=27,
                    onClick=partial(session.action, e.run, 'select_layer')),
             Action(label='调整选区', glyph='select_box', compact=True, width=108, height=27, selected=selection_tools,
                    onClick=partial(set_selection_tools, not selection_tools))], gap=4),
        optional('selection_tools', selection_tools, [row([
            Action(label=BY_ID[identity][2], glyph=glyph, compact=True, width=104, height=27,
                   onClick=partial(session.action, e.run, identity)) for identity, glyph in pair], gap=8)
            for pair in ((('select_expand', 'expand'), ('select_contract', 'contract')),
                         (('select_invert', 'invert'), ('select_surface', 'surface')))]),
        SelectionBounds(session=session, revision=session.content_revision),
        optional('box_pending', session.box_anchor is not None, Panel(children=[
            text('起点已设置，请点击终点', 10, Theme.blue),
            Action(label='取消框选', glyph='close', compact=True, height=26, onClick=partial(session.choose_mode, 'browse'))])),
        optional('corners', coordinates_open or corners, [
            Coordinates(label='选区起点  X, Y, Z', value=e.start, onChange=partial(session.set_editor, 'start')),
            Coordinates(label='选区终点  X, Y, Z', value=e.end, onChange=partial(session.set_editor, 'end'))])])


@Component
def ModificationMask(session=None, revision=0):
    use_theme()
    e = session.editor
    return Panel(style=S(width=216, gap=7), children=[line(), text('方块修改条件', 12),
        Segments(items=[('all', '全部'), ('solid', '方块'), ('air', '空气'), ('material', '材质')],
                 value=e.mask, onChange=partial(session.set_editor, 'mask'), width=216),
        text({'all': '允许修改方块和空气格', 'solid': '只修改已有方块', 'air': '只在空格中生成方块',
              'material': '只修改指定材质的方块'}[e.mask], 10, Theme.muted)])


@Component
def Layers(session=None, revision=0):
    use_theme()
    e = session.editor
    page, set_page = use_state(e.layer // 16)
    def follow_layer():
        set_page(e.layer // 16)
    use_effect(follow_layer, [e.layer, e.document.size])
    page = min(page, (e.document.size[1] - 1) // 16)
    low, high = page * 16, min(e.document.size[1], (page + 1) * 16)
    return Scroll(style=S(width=230, flex=1), children=PreparedColumn(session=session,
        urgent=lambda: session.inspector == 'layers' and session.page == 'workspace', style=S(width=216, gap=7), children=[
        row([text('垂直图层', 18, flex=1), text('%d 层' % e.document.size[1], 11, Theme.muted)]),
        text('锁定保护编辑，隐藏仅影响预览', 10, Theme.muted),
        Range(label='场景亮度', value=session.brightness, minimum=.2, maximum=1.,
              onChange=partial(session.range_value, 'brightness', editor=False)),
        Range(label='炫彩流动速度', value=session.spectrum_speed, minimum=.25, maximum=6., unit=' 倍',
              onChange=partial(session.range_value, 'spectrum_speed', editor=False)),
        text('默认 3 倍，减少动态效果时保持静止', 10, Theme.muted, width=216),
        text('在场景上方选择完整 / 切面 / 单层', 10, Theme.muted),
        row([Action(glyph='minus', width=28, height=26, enabled=page > 0, onClick=partial(set_page, max(0, page - 1))),
             text('Y %d–%d' % (low, high - 1), 11, Theme.muted, flex=1, center=True),
             Action(glyph='plus', width=28, height=26, enabled=high < e.document.size[1], onClick=partial(set_page, page + 1))]),
        line(),
    ] + [surface(color=Theme.tint if y == e.layer else Theme.pale, width=216, height=39, padding=5, children=row([
        Action(label='Y %02d' % y, onClick=partial(session.layer, y), selected=y == e.layer, height=28, width=60),
        text('%d 格' % e.document.layer_count(y), 10, Theme.muted, flex=1),
        Action(glyph='lock' if y in e.locked_layers else 'unlock', width=27, height=27,
               selected=y in e.locked_layers, onClick=partial(session.toggle_layer, 'lock', y)),
        Action(glyph='eye', width=27, height=27, selected=y not in e.hidden_layers,
               onClick=partial(session.toggle_layer, 'hide', y)),
    ], gap=3)) for y in reversed(range(low, high))]))


@Component
def History(session=None, revision=0):
    use_theme()
    e = session.editor
    return Scroll(style=S(width=230, flex=1), children=PreparedColumn(session=session,
        urgent=lambda: session.inspector == 'history' and session.page == 'workspace', style=S(width=216, gap=8), children=[
        text('操作历史', 18), text('最多保留 50 步，修改可逐步撤销', 10, Theme.muted),
        row([Action(label='撤销', glyph='undo', onClick=partial(session.action, e.undo), enabled=bool(e.undo_stack)),
             Action(label='重做', glyph='redo', onClick=partial(session.action, e.redo), enabled=bool(e.redo_stack))]), line(),
    ] + ([text('还没有编辑记录', 12, Theme.muted)] if not e.undo_stack else [
        surface(color=Theme.pale, padding=10, children=[text(name, 12), text('%d 个方块发生变化' % len(delta), 10, Theme.muted)])
        for name, delta in reversed(e.undo_stack)
    ]) + [line(), text('材料清单', 16)] + [
        row([Item(identifier=b[0], aux=b[1], style=S(width=23, height=23)),
             text(material_name(b), 11, flex=1), text('%d' % count, 12, Theme.blue)])
        for b, count in e.document.materials()]))


@Component
def NewRegion(session=None, compact=False):
    """Dimension controls bypass native text entry and its word filtering."""
    use_theme()
    size, set_size = use_state(session.new_size)

    def change(axis, value):
        updated = list(session.new_size)
        updated[axis] = max(1, min(MAX_AXES[axis], int(round(value))))
        session.new_size = tuple(updated)
        session.new_size_valid = True
        set_size(session.new_size)

    def create():
        session.confirm('新建 %d × %d × %d 区域将替换当前草稿。\n请先保存需要保留的作品。' % session.new_size, session.empty)

    axes = [DimensionAxis(key=str(axis), axis=axis, label=label, value=size[axis], maximum=MAX_AXES[axis],
                          onChange=partial(change, axis), stacked=compact)
            for axis, label in enumerate(('X 宽度', 'Y 高度', 'Z 长度'))]
    if compact:
        return PreparedColumn(session=session, style=S(gap=10), initial=1,
            urgent=lambda: session.page == 'library', children=[text('新建空白区域', 15)] + axes + [
            Action(label='新建空白', glyph='plus', height=32, onClick=create)])
    return surface(padding=12, gap=8, children=[
        row([text('新建区域', 14, flex=1),
             text('%d × %d × %d' % size, 12, Theme.muted),
             Action(label='新建空白', glyph='plus', accent=True, height=30, width=110, onClick=create)], gap=10),
        row(axes, gap=12),
    ])


@Component
def DimensionAxis(axis=0, label='', value=1, maximum=64, onChange=None, stacked=False):
    use_theme()
    return row([
        Action(glyph='minus', width=27, height=30, enabled=value > 1, onClick=partial(onChange, value-1)),
        Panel(style=S(flex=1), children=Range(label=label, value=value, minimum=1, maximum=maximum,
                                            integer=True, unit=' / %d' % maximum, onChange=onChange)),
        Action(glyph='plus', width=27, height=30, enabled=value < maximum, onClick=partial(onChange, value+1)),
    ], flex=None if stacked else 1, gap=4)


@Component
def Library(session=None, revision=0, width=760, height=440):
    use_theme()
    unused, update = use_state(0)
    def subscribe():
        return session.subscribe(lambda: update(lambda value: value+1), ('library', 'name'))
    use_effect(subscribe, [session])
    list_width = width-294
    cards = []
    for entry in session.library:
        data = entry['data']
        identity = entry['id']
        cards.append(surface(key='building%d' % identity, width=list_width-12, padding=14, height=130, flexShrink=0, gap=12, children=[
            row([surface(color=Theme.tint, width=40, height=40, justifyContent=JustifyContent.center,
                         alignItems=AlignItems.center, children=icon('cube', Theme.blue, 24)),
                 Panel(style=S(flex=1, gap=5), children=[text(data['name'][:24], 15, width=list_width-94),
                     text('%d × %d × %d' % tuple(data['size']), 11, Theme.muted),
                     text('%d 方块' % data.get('blockCount', len(data.get('blocks', []))), 10, Theme.muted)])]),
            row([Action(label='载入', accent=True, onClick=partial(session.confirm, '载入将替换当前草稿，继续吗？', partial(session.load, identity))),
                 Action(label='重命名', onClick=partial(session.open_rename, identity)),
                 Action(label='分享', glyph='copy', onClick=partial(session.action, session.sharing.open_export, identity)),
                 Action(label='删除', danger=True, onClick=partial(session.confirm, '删除这份已保存的建筑配置？', partial(session.delete, identity)))])]))
    return row(width=width, height=height, gap=18, padding=12, alignItems=AlignItems.stretch, children=[
        Panel(style=S(width=list_width, height=height-24, gap=12), children=[
            row([text('我的建筑库', 21, flex=1), text('%d / 32 个配置' % len(session.library), 11, Theme.muted)], height=34),
            Scroll(style=S(width=list_width, height=height-70), children=PreparedColumn(session=session,
                urgent=lambda: session.page == 'library', initial=0, style=S(width=list_width-12, gap=12,
                height=max(170,len(cards)*142-12)), children=cards or [surface(width=list_width-12, height=170,
                    alignItems=AlignItems.center, justifyContent=JustifyContent.center, gap=10, children=[
                        icon('library', Theme.muted, 34), text('这里等待你的第一件作品', 18),
                        text('给当前草稿起个名字，然后保存配置。', 11, Theme.muted)])]))]),
        surface(width=252, height=height-24, padding=14, children=Scroll(style=S(width=236, height=height-52), children=
            PreparedColumn(session=session, urgent=lambda: session.page == 'library', style=S(width=224, gap=12), children=[
                text('保存当前草稿', 15),
                Input(value=session.name, onChange=partial(session.set, 'name'), style=S(width=224, height=32)),
                Action(label='另存为新配置', glyph='save', accent=True, height=32, onClick=partial(session.action, session.save)),
                Action(label='分享当前草稿', glyph='copy', height=32, onClick=partial(session.action, session.sharing.open_export)),
                Action(label='导入分享码', glyph='paste', height=32, onClick=partial(session.action, session.sharing.open_import)),
                line(), NewRegion(session=session, compact=True)])))])


@Component
def ProjectionSettings(session=None, revision=0, height=330):
    use_theme()
    tab, set_tab = use_state('display')
    e, stats = session.editor, session.progress
    display = [
        text('投影位置', 14),
        Coordinates(label='原点  X, Y, Z', value=session.origin, onChange=partial(session.set, 'origin')),
        Action(label='使用脚下坐标', glyph='pin', onClick=session.bridge.use_player_origin),
        line(), text('显示效果', 14),
        Range(label='投影不透明度', value=session.opacity, minimum=.1, maximum=.85,
              onChange=partial(session.range_value, 'opacity', editor=False)),
        Action(label='炫彩范围框', glyph='box_outline', selected=session.projection_outline,
               onClick=partial(session.set, 'projection_outline', not session.projection_outline)),
        Range(label='炫彩流动速度', value=session.spectrum_speed, minimum=.25, maximum=6., unit=' 倍',
              onChange=partial(session.range_value, 'spectrum_speed', editor=False)),
    ]
    assist = [
        text('建造辅助', 14),
        text('在场景上方选择完整、切面或单层，并调整 Y。', 10, Theme.muted, width=216),
        Action(label='仅显示缺失方块', selected=session.projection_missing,
               onClick=partial(session.action, session.bridge.toggle_missing), enabled=not session.busy),
        text('隐藏已完成方块，保留缺失和材质不符的位置。', 10, Theme.muted, width=216),
        text('搭建后点击更新投影，重新检查。', 10, Theme.muted, width=216),
        line(), text('建造进度', 14),
        Action(label='检查建造进度', glyph='check', onClick=partial(session.action, session.bridge.check_progress), enabled=not session.busy),
        text('%d / %d 已完成' % (stats['correct'], stats['total']) if stats else '尚未检查', 11, Theme.muted),
        text('缺失 %d，材质不符 %d' % (stats['missing'], stats['wrong']) if stats else '', 10, Theme.muted),
        line(), text('所需材料', 14),
    ] + [row([MaterialIcon(value=b, size=22), text(material_name(b), 11, flex=1),
              text('%d' % count, 11, Theme.blue)]) for b, count in e.document.materials()]
    world = [
        text('写入真实方块', 14),
        text('需要创造模式、操作员和建造权限。', 11, Theme.muted, width=216),
        line(),
        Action(label='同步空气', glyph='erase', selected=session.apply_air, danger=session.apply_air,
               onClick=partial(session.set, 'apply_air', not session.apply_air)),
        text('开启后会清除草稿中空气对应的位置。', 10, Theme.muted, width=216),
        Action(label='应用到世界', glyph='cube', accent=True, onClick=partial(session.confirm,
               '将草稿同步到世界？\n空气位置的已有方块也会被清除。\n此操作无法撤销。' if session.apply_air else
               '将草稿中的方块写入目标位置？\n此操作无法撤销。', session.bridge.apply_world), enabled=not session.busy),
        text('世界写入无法撤销，请确认原点和范围。', 10, Theme.muted, width=216),
    ]
    return Panel(style=S(width=230, height=height, gap=10), children=[
        text('投影与范围框仅本机可见', 10, Theme.mint),
        row([
            Action(label='更新投影' if session.projection_active else '生成投影', glyph='projection', accent=True, width=130,
                   onClick=partial(session.action, session.bridge.project), enabled=not session.busy),
            Action(label='关闭', glyph='close', width=78, onClick=partial(session.action, session.bridge.stop_projection),
                   enabled=session.projection_active or session.bridge.projection_requested),
        ], gap=8),
        Segments(items=[('display','显示'),('assist','辅助'),('world','写入')], value=tab, onChange=set_tab, width=216),
        Scroll(style=S(width=230, height=max(60,height-110)), resetKey=tab, children=
            Panel(style=S(width=216), children=[
                Panel(key=name, style=S(display=Display.flex if tab==name else Display.none), children=
                    PreparedColumn(session=session, style=S(width=216, gap=10), initial=2,
                        urgent=partial(projection_tab_active, session, tab, name), children=items))
                for name,items in (('display',display),('assist',assist),('world',world))]))])


def projection_tab_active(session, active, name):
    return session.page == 'projection' and active == name


@Component
def Guide(session=None, revision=0, width=760, height=440):
    use_theme()
    sections = [
        ('01', '先认识你的工作台', '拖动模型自由旋转，滚轮缩放。切换放置、换材质、擦除，直接点击三维方块。', 'orbit'),
        ('02', '从一个小范围开始', '框选依次点击两个角点。场景上方切换完整、切面或单层，调整 Y 查看内部。', 'cursor'),
        ('03', '选工具，再确认参数', '左侧找到工具，右侧选择材质、蒙版和尺寸，点击执行。', 'brush'),
        ('04', '放心试验，随时撤销', '撤销 / 重做保存你的探索。锁定图层，可以保护已经完成的部分。', 'undo'),
        ('05', '保存作品，带走灵感', '建筑库可以保存多个配置。载入后可以继续编辑，也可以生成投影。', 'library'),
        ('06', '在生存世界慢慢实现', '到目标位置生成半透明投影，逐层搭建，检查缺失和放错的方块。', 'projection'),
    ]
    return Scroll(style=S(width=width, height=height), children=PreparedColumn(session=session,
        urgent=lambda: session.page == 'guide', style=S(width=width - 20, padding=20, gap=12), children=[
        text('从第一块，到完整的建筑。', 26), text('不用一次学会所有工具。选一份示例，跟着这六步开始。', 13, Theme.muted),
        row([Action(label='载入庭院示例', glyph='cube', accent=True, width=160,
                    onClick=partial(session.confirm, '载入示例将替换当前草稿，继续吗？', session.demo)),
             Action(label='减少动态效果', selected=session.reduced_motion, width=160,
                    onClick=partial(session.set, 'reduced_motion', not session.reduced_motion))]), line(),
    ] + [surface(padding=15, children=row([
        text(number, 23, Theme.blue, width=45),
        Panel(style=S(flex=1, gap=5), children=[text(title, 16), text(hint, 11, Theme.muted)]),
        icon(glyph, Theme.blue, 24),
    ])) for number, title, hint, glyph in sections] + [
        text('快捷入口：P 打开工作台', 12, Theme.muted),
        text('范围上限：64 × 128 × 64 格。', 11, Theme.muted),
        text('配置保存在本机；箱子内容与实体数据不包含在建筑配置中。', 11, Theme.muted),
    ]))
