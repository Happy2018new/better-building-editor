# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Paged creative-style inventory with localized search and retained modal motion."""
from __future__ import unicode_literals
import time
from functools import partial
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from ..pyreact.primitives import PanelPrimitive
from .widgets import Theme, S, text, retained_text, row, surface, icon, Action, Input, use_theme
from .widgets import JellyButton as Button
from .panels import material_background
from .materials import CATEGORIES, search_blocks


InventoryModal = PanelPrimitive()
InventoryModal.template_path = '/root/mp_inventory_modal_tmpl'


@Component
def BlockInventory(session=None, channel=None, width=750, height=500, revision=0):
    use_theme()
    group, set_group = use_state('all')
    query, set_query = use_state('')
    page, set_page = use_state(0)
    selected, set_selected = use_state(getattr(session.editor, channel or 'material'))
    grid_width = width-162
    columns = max(4, int(grid_width//64))
    rows = 4
    count = columns*rows
    matches = use_memo(lambda: search_blocks(session.block_catalogue, group, query),
                       [id(session.block_catalogue), len(session.block_catalogue), group, query])
    pages = max(1, (len(matches)+count-1)//count)
    current_page = min(page, pages-1)
    visible = matches[current_page*count:(current_page+1)*count]
    # Stable slots keep native item controls and captions alive across pages,
    # category changes and empty searches. Only their content/visibility changes.
    visible += [None] * (count-len(visible))
    selected_name = next((item['name'] for item in session.block_catalogue if item['value']==selected), '')
    cell_width = (grid_width-(columns-1)*5)/columns

    def change_group(value):
        set_group(value)
        set_page(0)

    def change_query(value):
        set_query(value)
        set_page(0)
        set_group('all')

    return surface(width=width, height=height, padding=18, gap=10, children=[
        row([icon('cube', Theme.blue, 24), text('方块目录', 20, flex=1),
             Action(glyph='close', width=30, height=30, onClick=partial(session.set, 'material_browser', None))]),
        text('按分类浏览 · 搜索中文方块名 · 添加到常用并使用', 11, Theme.muted),
        row([
            Panel(style=S(width=116, height=rows*63, gap=4), children=[
                Action(key=key, label=label, glyph=glyph, leading=True, compact=True, height=28,
                       selected=group==key, onClick=partial(change_group, key)) for key,label,glyph in CATEGORIES]),
            Panel(style=S(width=grid_width, height=rows*63), children=[
                Panel(style=S(width=grid_width, height=rows*63, flexDirection=FlexDirection.row, flexWrap=FlexWrap.wrap, gap=5),
                      children=[InventoryCell(key='slot%d' % i, item=item, selected=bool(item and item['value']==selected),
                                              onSelect=set_selected, width=cell_width) for i,item in enumerate(visible)]),
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
        row([Item(identifier=selected[0], aux=selected[1], style=S(width=28,height=28)),
             retained_text(selected_name or '请选择方块', 12, flex=1),
             Action(label='添加并使用', glyph='check',
                    accent=True, height=32, width=124, enabled=bool(selected_name), onClick=partial(session.add_material, selected))]),
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
    return Button(key='block', style=S(width=width, height=58, visible=item is not None),
        buttonBuilder=partial(material_background, selected), onClick=partial(onSelect, value['value']),
        children=Panel(style=S(width='100%', alignItems=AlignItems.center, gap=1), children=[
            Item(identifier=value['value'][0], aux=value['value'][1], style=S(width=30,height=30)),
            retained_text(value['name'], 8, width=width-3, center=True, slots=20, lines=2)]))


@Component
def MaterialBrowser(session=None, revision=0, width=980, height=640):
    use_theme()
    catalogue_revision, update = use_state(0)
    def subscribe():
        return session.subscribe(lambda: update(lambda n: n+1), ('block_catalogue',))
    use_effect(subscribe, [session])
    progress, set_progress = use_state(0.)
    motion = use_ref({'target': False, 'start': 0., 'from': 0.}).current
    channel = use_ref('material')
    opened = session.material_browser is not None
    if opened:
        channel.current = session.material_browser
    if motion['target'] != opened:
        motion.update(target=opened, start=time.time(), **{'from': progress})
    def tick(now):
        t = min(1., (now-motion['start'])/(.24 if opened else .16)) if Theme.motion else 1.
        set_progress(motion['from']+(float(opened)-motion['from'])*(1.-(1.-t)**3))
    use_animation_frame(tick, progress != float(opened))
    card = use_memo(lambda: BlockInventory(session=session, channel=channel.current,
                    width=min(750,width-36), height=min(500,height-32), revision=(revision,catalogue_revision)),
                    [opened, channel.current, width, height, revision, catalogue_revision, Theme.scale])
    if not opened and progress <= 0.:
        return None
    # A native modal input scope blocks the workspace without a full-screen
    # Button competing with edit_box selection on the same mouse press.
    return InventoryModal(style=S(position=Position.absolute, top=0, left=0,
                          width='100%', height='100%', zIndex=2000), children=[
        Image(color=Color(0x172B4D77), style=S(position=Position.absolute, width='100%', height='100%', opacity=progress)),
        Panel(style=S(position=Position.absolute, width='100%',height='100%', zIndex=2,
              alignItems=AlignItems.center, justifyContent=JustifyContent.center), children=
            Panel(style=S(opacity=progress,transform=[Translate(0,(1.-progress)*16*Theme.scale),Scale(.98+.02*progress)]), children=card))])
