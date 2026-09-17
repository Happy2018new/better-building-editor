# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Tool parameters, layer editing, library and survival projection panels."""
from __future__ import unicode_literals
from functools import partial
from ..pyreact import *
from .widgets import Theme, S, text, row, surface, icon, line, Action, Range, Segments, Input, Scroll
from .widgets import JellyButton as Button
from .catalog import BY_ID, MATERIALS
from .model import AIR


def material_name(value):
    return next((m[2] for m in MATERIALS if tuple(m[:2]) == value), value[0].split(':')[-1])


def material_color(value):
    code = next((m[3] for m in MATERIALS if tuple(m[:2]) == value), '9BA6B4')
    return Color(int(code + 'FF', 16))


@Component
def Coordinates(label='', value=(0, 0, 0), onChange=None):
    draft, set_draft = use_state(', '.join(str(v) for v in value))
    valid, set_valid = use_state(True)

    def sync():
        set_draft(', '.join(str(v) for v in value))
    use_effect(sync, [value])

    def change(raw):
        set_draft(raw)
        try:
            values = tuple(int(v.strip()) for v in raw.split(','))
            if len(values) != 3:
                raise ValueError('three coordinates required')
        except (ValueError, TypeError):
            set_valid(False)
            return
        set_valid(True)
        onChange(values)
    return Panel(style=S(gap=4, marginBottom=7), children=[
        text(label if valid else '格式：X, Y, Z · 整数', 10, Theme.muted if valid else Theme.red),
        Input(value=draft, onChange=change, style=S(width='100%', height=27))])


@Component
def MaterialPicker(session=None, revision=0):
    channel, set_channel = use_state('material')
    custom, set_custom = use_state('minecraft:stone')
    custom_aux, set_custom_aux = use_state('0')
    e = session.editor

    def choose(value):
        session.set_editor(channel, value)

    def custom_apply():
        from .model import block
        choose(block((custom.strip(), int(custom_aux))))
    current = getattr(e, channel)
    return Panel(style=S(gap=7), children=[
        Segments(items=[('material', '主材质'), ('secondary', '副材质'), ('source', '替换来源')],
                 value=channel, onChange=set_channel, width=216),
        row([Item(identifier=current[0], aux=current[1], style=S(width=30, height=30)),
             Panel(style=S(flex=1), children=[text(material_name(current), 12), text('方块附加值  %d' % current[1], 10, Theme.muted)])]),
        Panel(style=S(flexDirection=FlexDirection.row, flexWrap=FlexWrap.wrap, gap=5, height=159, flexShrink=0), children=[
            Button(key='mat%d' % i, onClick=partial(choose, tuple(m[:2])),
                   buttonBuilder=partial(material_background, tuple(m[:2]) == current),
                   style=S(width=49, height=36), children=Item(identifier=m[0], aux=m[1], style=S(width=25, height=25)))
            for i, m in enumerate(MATERIALS)]),
        text('自定义方块标识符 / 附加值', 10, Theme.muted),
        row([Input(value=custom, onChange=set_custom, style=S(flex=1, height=25)),
             Input(value=custom_aux, onChange=set_custom_aux, style=S(width=34, height=25))]),
        Action(label='使用自定义材质', onClick=partial(session.action, custom_apply), height=26, compact=True),
    ])


def material_background(selected, state):
    return Image(color=Theme.tint if selected or state != ButtonState.default else Theme.pale)


@Component
def Parameters(session=None, revision=0):
    e = session.editor
    tool = BY_ID[session.tool]
    return Scroll(style=S(width=230, flex=1), children=Panel(style=S(width=216, gap=6), children=[
        text('工具参数', 10, Theme.muted, marginTop=6),
        text(tool[2], 20),
        # Split help by sentence length into readable, deliberate lines.
        text(tool[3], 11, Theme.muted, width=216),
        line(), MaterialPicker(session=session, revision=session.ui_revision), line(),
        text('作用范围', 12),
        text('%d 格已选择 · %d 层已锁定' % (len(e.selection), len(e.locked_layers)), 10, Theme.muted),
        Segments(items=[('all', '全部'), ('solid', '实体'), ('air', '空气'), ('material', '来源')],
                 value=e.mask, onChange=partial(session.set_editor, 'mask'), width=216),
        Coordinates(label='起点  X, Y, Z', value=e.start, onChange=partial(session.set_editor, 'start')),
        Coordinates(label='终点  X, Y, Z', value=e.end, onChange=partial(session.set_editor, 'end')),
        Range(label='厚度', value=e.thickness, minimum=1, maximum=8, integer=True,
              onChange=partial(session.set_editor, 'thickness'), unit=' 格'),
        Range(label='步长 / 纹理间距', value=e.step, minimum=1, maximum=16, integer=True,
              onChange=partial(session.set_editor, 'step'), unit=' 格'),
        Range(label='副材质比例', value=e.ratio, minimum=0, maximum=1,
              onChange=partial(session.set_editor, 'ratio')),
        row([text('随机种子', 11, Theme.muted, flex=1),
             Action(label=str(e.seed), onClick=partial(session.set_editor, 'seed', e.seed + 1), width=72, height=26)]),
        text('点击种子切换可复现的随机图案', 10, Theme.muted),
        Panel(style=S(height=8)),
    ]))


@Component
def Layers(session=None, revision=0):
    e = session.editor
    return Scroll(style=S(width=230, flex=1), children=Panel(style=S(width=216, gap=7), children=[
        row([text('垂直图层', 18, flex=1), text('%d 层' % e.document.size[1], 11, Theme.muted)]),
        text('锁定保护编辑 · 隐藏仅影响预览', 10, Theme.muted),
        Action(label='仅显示当前层' if not session.solo_layer else '显示全部图层', onClick=session.toggle_solo, selected=session.solo_layer),
        line(),
    ] + [surface(color=Theme.tint if y == e.layer else Theme.pale, height=39, padding=5, children=row([
        Action(label='Y %02d' % y, onClick=partial(session.layer, y), selected=y == e.layer, height=28, width=60),
        text('%d 格' % sum(1 for p in e.document.blocks if p[1] == y), 10, Theme.muted, flex=1),
        Action(glyph='lock' if y in e.locked_layers else 'unlock', width=27, height=27,
               selected=y in e.locked_layers, onClick=partial(session.toggle_layer, 'lock', y)),
        Action(glyph='eye', width=27, height=27, selected=y not in e.hidden_layers,
               onClick=partial(session.toggle_layer, 'hide', y)),
    ], gap=3)) for y in reversed(range(e.document.size[1]))]))


@Component
def History(session=None, revision=0):
    e = session.editor
    return Scroll(style=S(width=230, flex=1), children=Panel(style=S(width=216, gap=8), children=[
        text('操作历史', 18), text('最多保留 50 步 · 修改可逐步撤销', 10, Theme.muted),
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
def Library(session=None, revision=0, width=760, height=440):
    e = session.editor
    cards = []
    for entry in session.library:
        data = entry['data']
        identity = entry['id']
        cards.append(surface(width=(width - 50) / 2., padding=16, height=160, children=[
            row([surface(color=Theme.tint, width=40, height=40, justifyContent=JustifyContent.center,
                         alignItems=AlignItems.center, children=icon('cube', Theme.blue, 24)),
                 Panel(style=S(flex=1, gap=4), children=[text(data['name'][:18], 15),
                     text('%d × %d × %d  ·  %d 方块' % tuple(data['size'] + [len(data['blocks'])]), 11, Theme.muted)])]),
            text('本机配置  #%03d' % identity, 10, Theme.muted, marginTop=12, marginBottom=12),
            row([Action(label='载入', accent=True, onClick=partial(session.confirm, '载入将替换当前草稿，继续吗？', partial(session.load, identity))),
                 Action(label='重命名', onClick=partial(session.action, session.rename, identity)),
                 Action(label='删除', danger=True, onClick=partial(session.confirm, '删除这份已保存的建筑配置？', partial(session.delete, identity)))])]))
    return Panel(style=S(width=width, height=height, gap=18, padding=18), children=[
        row([Panel(style=S(flex=1, gap=5), children=[text('把灵感，留给下一次建造。', 24),
             text('保存多个建筑配置，随时载入，在新的地点生成投影。', 12, Theme.muted)]), icon('library', Theme.blue, 32)]),
        surface(padding=14, children=row([
            Panel(style=S(flex=1, gap=5), children=[text('当前草稿名称 / 重命名内容', 10, Theme.muted),
                  Input(value=session.name, onChange=partial(session.set, 'name'), style=S(width='100%', height=30))]),
            Action(label='另存为新配置', glyph='save', accent=True, width=145, height=40, onClick=partial(session.action, session.save))
        ], gap=14)),
        row([text('我的建筑库', 17, flex=1), text('%d / 32 个配置' % len(session.library), 11, Theme.muted)]),
        row([Panel(style=S(flex=1), children=Coordinates(label='新建尺寸  X, Y, Z（每轴 1–64）', value=session.new_size,
                    onChange=partial(session.set, 'new_size'))),
             Action(label='新建空白', glyph='plus', width=120, onClick=partial(session.confirm,
                    '新建将替换当前草稿，请先保存需要保留的作品。', session.empty))]),
        Scroll(style=S(width='100%', flex=1), children=Panel(style=S(width=width - 36, flexDirection=FlexDirection.row,
            flexWrap=FlexWrap.wrap, gap=12, height=max(170, ((len(cards) + 1) // 2) * 172)), children=cards or [surface(width=width - 40, height=170,
                alignItems=AlignItems.center, justifyContent=JustifyContent.center, gap=10, children=[
                    icon('library', Theme.muted, 34), text('这里等待你的第一件作品', 18),
                    text('给当前草稿起个名字，然后保存配置。', 12, Theme.muted)])]))])


@Component
def ProjectionSettings(session=None, revision=0):
    e = session.editor
    stats = session.progress
    return Scroll(style=S(width=230, flex=1), children=Panel(style=S(width=216, gap=8), children=[
        text('投影设置', 20), text('在世界中照着半透明蓝图建造', 11, Theme.muted), line(),
        surface(color=Theme.green, padding=12, gap=5, children=[
            text('生存友好', 14, Theme.mint), text('投影不会放置方块或消耗物品', 10, Theme.mint)]),
        Coordinates(label='投影原点  X, Y, Z', value=session.origin, onChange=partial(session.set, 'origin')),
        Action(label='使用脚下坐标', glyph='pin', onClick=partial(session.bridge.use_player_origin)),
        Range(label='投影不透明度', value=session.opacity, minimum=.1, maximum=.85,
              onChange=partial(session.set, 'opacity')),
        Action(label='逐层投影' if not session.solo_layer else '显示全部层', selected=session.solo_layer, onClick=session.toggle_solo),
        Range(label='当前建造层', value=e.layer, minimum=0, maximum=max(1, e.document.size[1] - 1),
              integer=True, onChange=session.layer),
        Action(label='仅显示缺失方块', selected=session.projection_missing,
               onClick=partial(session.set, 'projection_missing', not session.projection_missing)),
        Action(label='更新 / 生成投影', glyph='projection', accent=True, onClick=partial(session.action, session.bridge.project)),
        Action(label='关闭投影', onClick=partial(session.action, session.bridge.stop_projection),
               enabled=session.projection_active or bool(session.bridge.preparing_entity)),
        Action(label='检查建造进度', glyph='check', onClick=partial(session.action, session.bridge.check_progress), enabled=not session.busy),
        text('进度：%d / %d 已完成' % (stats['correct'], stats['total']) if stats else '点击检查以获取真实建造进度', 11, Theme.muted),
        text('缺失 %d · 材质不符 %d' % (stats['missing'], stats['wrong']) if stats else '原点可在世界中重新定位', 10, Theme.muted),
        line(), text('创造模式', 14), text('应用前检查目标区域；可撤销最近一次写入。', 10, Theme.muted, width=216),
        Action(label='同步空气（会清除对应位置）', selected=session.apply_air, danger=session.apply_air,
               onClick=partial(session.set, 'apply_air', not session.apply_air), compact=True),
        Action(label='应用到世界', glyph='cube', onClick=partial(session.confirm,
               '将整个长方体同步到世界？草稿中的空气会清除对应位置的方块。' if session.apply_air else
               '将草稿中的实体方块写入目标位置？仅创造模式可用。', session.bridge.apply_world), enabled=not session.busy),
        Action(label='撤销世界写入', onClick=partial(session.confirm, '撤销最近一次世界写入？被他人修改的方块会保留。', session.bridge.undo_world), enabled=not session.busy),
        line(), text('所需材料', 15),
    ] + [row([Item(identifier=b[0], aux=b[1], style=S(width=22, height=22)),
              text(material_name(b), 11, flex=1), text('%d' % count, 11, Theme.blue)]) for b, count in e.document.materials()]))


@Component
def Guide(session=None, revision=0, width=760, height=440):
    sections = [
        ('01', '先认识你的工作台', '中间是实时三维模型。拖动旋转，用缩放按钮看清细节。', 'orbit'),
        ('02', '从一个小范围开始', '切换到逐层视图，用起点和终点框选。所有编辑只作用于选区。', 'cursor'),
        ('03', '选工具，再确认参数', '左侧找到工具，右侧选择材质、蒙版和尺寸，点击执行。', 'brush'),
        ('04', '放心试验，随时撤销', '撤销 / 重做保存你的探索。锁定图层，可以保护已经完成的部分。', 'undo'),
        ('05', '保存作品，带走灵感', '建筑库可以保存多个配置。载入后可以继续编辑，也可以生成投影。', 'library'),
        ('06', '在生存世界慢慢实现', '到目标位置生成半透明投影，逐层搭建，检查缺失和放错的方块。', 'projection'),
    ]
    return Scroll(style=S(width=width, height=height), children=Panel(style=S(width=width - 20, padding=20, gap=12), children=[
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
        text('快捷入口：P 打开工作台 · F6 / F7 标记脚下两点', 12, Theme.muted),
        text('当前范围：单轴最多 64 格，总体积最多 32768 格。', 11, Theme.muted),
        text('配置保存在本机；箱子内容与实体数据不包含在建筑配置中。', 11, Theme.muted),
    ]))
