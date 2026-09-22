# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Paged creative-style inventory with localized search and retained modal motion."""
from __future__ import unicode_literals
from functools import partial
from ..pyreact import *
from .widgets import Theme, S, text, retained_text, row, surface, icon, Action, Input, use_theme
from .widgets import JellyButton as Button
from .panels import material_background, MaterialIcon
from .materials import CATEGORIES, search_blocks, with_aux
from .motion import DialogMotion


@Component
def AuxEditor(value=None, onChange=None, onValidityChange=None, opened=False):
    use_theme()
    draft, set_draft = use_state(str(value[1]))
    valid, set_valid = use_state(True)
    def sync():
        set_draft(str(value[1]))
        set_valid(True)
        onValidityChange(True)
    use_effect(sync, [value, opened])
    def change(raw):
        set_draft(raw)
        try:
            updated = with_aux(value, raw)
        except (ValueError, TypeError):
            set_valid(False)
            onValidityChange(False)
            return
        set_valid(True)
        onValidityChange(True)
        onChange(updated)
    def step(delta):
        updated = with_aux(value, max(0, min(32767, value[1]+delta)))
        set_draft(str(updated[1]))
        set_valid(True)
        onValidityChange(True)
        onChange(updated)
    air = value[0] == 'minecraft:air'
    return row([text('附加值' if valid else '请输入 0–32767', 11, Theme.muted if valid else Theme.red, width=92),
        Action(glyph='minus', width=28, height=28, enabled=value[1]>0, onClick=partial(step, -1)),
        Input(value=draft, onChange=change, style=S(width=68, height=28)),
        Action(glyph='plus', width=28, height=28, enabled=not air and value[1]<32767, onClick=partial(step, 1)),
        Action(label='归零', glyph='undo', compact=True, height=28, enabled=value[1]!=0 or not valid,
               onClick=partial(step, -32767))], gap=5)


@Component
def BlockInventory(session=None, channel=None, width=750, height=500, revision=0, opened=False):
    use_theme()
    group, set_group = use_state('all')
    query, set_query = use_state('')
    page, set_page = use_state(0)
    selected, set_selected = use_state(getattr(session.editor, channel or 'material'))
    aux_valid, set_aux_valid = use_state(True)
    def sync_selection():
        if opened:
            set_selected(getattr(session.editor, channel or 'material'))
    use_effect(sync_selection, [opened, channel])
    grid_width = width-162
    columns = max(4, int(grid_width//64))
    rows = 4
    count = columns*rows
    prepared, set_prepared = use_state(0)
    def prepare():
        if prepared >= count:
            return
        queue = getattr(session, '_ui_preparation', None)
        # Opening the catalogue prioritizes its own cells. While hidden it
        # shares the same one-batch-per-frame budget as the other panes.
        if queue is not None and not opened:
            return queue.add(lambda: set_prepared(min(count, prepared+2)))
        alive = [True]
        session.bridge.later(.02, lambda: set_prepared(min(count, prepared+2)) if alive[0] else None)
        return lambda: alive.__setitem__(0, False)
    use_effect(prepare, [prepared, count, opened])
    matches = use_memo(lambda: search_blocks(session.block_catalogue, group, query),
                       [id(session.block_catalogue), len(session.block_catalogue), group, query])
    pages = max(1, (len(matches)+count-1)//count)
    current_page = min(page, pages-1)
    visible = matches[current_page*count:(current_page+1)*count]
    # Stable slots keep native item controls and captions alive across pages,
    # category changes and empty searches. Only their content/visibility changes.
    visible += [None] * (count-len(visible))
    selected_name = session.describe_material(selected)
    cell_width = (grid_width-(columns-1)*5)/columns

    def change_group(value):
        set_group(value)
        set_page(0)

    def change_query(value):
        set_query(value)
        set_page(0)
        set_group('all')

    return surface(width=width, height=height, padding=18, gap=8, children=[
        row([icon('cube', Theme.blue, 24), text('方块目录', 20, flex=1),
             Action(glyph='close', width=30, height=30, onClick=partial(session.set, 'material_browser', None))]),
        row([
            Panel(style=S(width=116, height=rows*63, gap=4), children=[
                Action(key=key, label=label, glyph=glyph, leading=True, compact=True, height=28,
                       selected=group==key, onClick=partial(change_group, key)) for key,label,glyph in CATEGORIES]),
            Panel(style=S(width=grid_width, height=rows*63), children=[
                Panel(style=S(width=grid_width, height=rows*63, flexDirection=FlexDirection.row, flexWrap=FlexWrap.wrap, gap=5),
                      children=[InventoryCell(key='slot%d' % i, item=item, selected=bool(item and item['value']==selected),
                                              onSelect=set_selected, width=cell_width) for i,item in enumerate(visible[:prepared])]),
                Panel(style=S(position=Position.absolute, top=30, width=grid_width, visible=not matches),
                      children=text('没有匹配的方块，试试其他名称', 12, Theme.muted, width=grid_width, center=True))])
        ], gap=10, alignItems=AlignItems.flex_start),
        row([retained_text('正在读取游戏方块…' if session.catalogue_loading else '%d 个方块' % len(matches), 10, Theme.muted, flex=1),
             Action(label='上一页', glyph='arrow_left', compact=True, height=25, enabled=current_page>0,
                    onClick=partial(set_page, current_page-1)),
             retained_text('%d / %d' % (current_page+1,pages), 10, width=52, center=True, slots=12),
             Action(label='下一页', glyph='arrow_right', compact=True, height=25, enabled=current_page+1<pages,
                    onClick=partial(set_page, current_page+1))]),
        row([icon('search', Theme.muted, 17), text('搜索方块', 11, Theme.muted),
             Input(value=query, onChange=change_query, style=S(flex=1,height=30)),
             Action(label='清空', glyph='close', compact=True, height=28, enabled=bool(query), onClick=partial(change_query, ''))]),
        row([MaterialIcon(value=selected, size=28),
             retained_text(selected_name, 12, flex=1),
             text('附加值可区分颜色、朝向等状态', 10, Theme.muted)]),
        row([AuxEditor(value=selected, onChange=set_selected, onValidityChange=set_aux_valid, opened=opened),
             Panel(style=S(flex=1)),
             Action(label='添加并使用', glyph='check',
                    accent=True, height=32, width=124, enabled=aux_valid, onClick=partial(session.add_material, selected))]),
    ])


@Component
def InventoryCell(item=None, selected=False, onSelect=None, width=60):
    use_theme()
    # Empty slots retain the last icon: hiding/revealing them is cheaper than
    # replacing every native Item with air and then restoring it.
    cached = use_ref({'value': ('minecraft:stone', 0), 'name': ''})
    if item is not None:
        cached.current = item
    value = cached.current
    return Button(key='block', cacheLayout=True, style=S(width=width, height=58, visible=item is not None),
        buttonBuilder=partial(material_background, selected), onClick=partial(onSelect, value['value']),
        children=Panel(style=S(width='100%', height=58, alignItems=AlignItems.center, gap=1), children=[
            MaterialIcon(value=value['value'], size=30),
            retained_text(value['name'], 8, width=width-3, center=True, slots=20, lines=2)]))


@Component
def MaterialBrowser(session=None, revision=0, width=980, height=640):
    use_theme()
    catalogue_revision, update = use_state(0)
    def subscribe():
        return session.subscribe(lambda: update(lambda n: n+1), ('block_catalogue', 'material_browser'))
    use_effect(subscribe, [session])
    prepared, set_prepared = use_state(False)
    def prepare():
        queue = getattr(session, '_ui_preparation', None)
        if queue is not None:
            return queue.add(lambda: set_prepared(True))
        alive = [True]
        session.bridge.later(.45, lambda: set_prepared(True) if alive[0] else None)
        return lambda: alive.__setitem__(0, False)
    use_effect(prepare, [])
    channel = use_ref('material')
    opened = session.material_browser is not None
    if opened:
        channel.current = session.material_browser
    card = use_memo(lambda: BlockInventory(session=session, channel=channel.current,
                    width=min(750,width-36), height=min(550,height-32), revision=(revision,catalogue_revision), opened=opened),
                    [opened, channel.current, width, height, revision, catalogue_revision, Theme.scale])
    return DialogMotion(opened=opened, session=session, zIndex=2000,
                        children=card if prepared or opened else None)
