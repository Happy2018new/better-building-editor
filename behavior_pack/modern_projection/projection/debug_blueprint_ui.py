# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Public test blueprint page with stable category and fixture identities."""
from __future__ import unicode_literals
from functools import partial
from ..pyreact import Component, Panel, use_effect, use_state
from .widgets import Theme, S, row, text, Action, Segments, Scroll, Input, use_theme, line
from .panels import MaterialIcon, material_name, use_material_names
from .preparation import PreparedColumn
from .debug_blueprints import CATEGORIES, entries, material, open_blueprint
from .debug_ordinary_blueprints import SECTIONS, CASES, search_text


def _matches(metadata, query):
    if not query or query in (metadata[2] + ' ' + search_text(metadata[0])).lower():
        return True
    return any(query in material_name(case['material']).lower()
               for case in CASES.get(metadata[0], ()))


@Component
def ManualBlueprints(session=None, width=736, height=335):
    use_theme()
    use_material_names(session)
    section, set_section = use_state('dynamic')
    query, set_query = use_state('')
    page, set_page = use_state(0)

    def load_names():
        if not session.catalogue_loading and not session.catalogue_ready:
            session.catalogue_loading = True
            session.bridge.request_catalogue()
    use_effect(load_names, [session])

    def change_section(value):
        set_section(value)
        set_page(0)

    def search(value):
        set_query(value)
        set_page(0)

    blueprints = tuple(row for row in entries('manual')
                       if row[0].startswith('test.ordinary.' + section + '.')
                       and _matches(row, query.strip().lower()))
    pages = max(1, (len(blueprints) + 7) // 8)
    current = min(page, pages - 1)
    cards = []
    for identity, unused, title, size, block in blueprints[current * 8:(current + 1) * 8]:
        cases = CASES.get(identity, ())
        detail = '%d × %d × %d' % size
        if cases:
            detail = '%d 个样本 · %s — %s' % (
                len(cases), material_name(cases[0]['material']), material_name(cases[-1]['material']))
        load = partial(open_blueprint, session, identity)
        cards.append(Panel(key=identity, style=S(width=width - 24, height=80, flexShrink=0), children=[
            row([Panel(style=S(flex=1, gap=5), children=[
                text(title, 14, width=width - 145),
                text(detail, 11, Theme.muted, width=width - 145)]),
                Action(label='载入', glyph='cube', accent=True, width=90, height=32,
                       enabled=not session.busy and session.edit_job is None and session.io_job is None,
                       onClick=partial(session.confirm, '载入将替换当前草稿，继续吗？', load))], gap=8),
            line()]))
    return Panel(style=S(width=width, height=height, gap=7), children=[
        Segments(items=SECTIONS, value=section, width=min(520, width), onChange=change_section),
        row([text('搜索名称 / ID', 11, Theme.muted),
             Input(value=query, onChange=search, style=S(flex=1, height=28)),
             text('%d 份' % len(blueprints), 11, Theme.muted)], gap=8, height=28),
        text('均待人工确认；每页从左到右、从前到后排列，4 列 × 6 行。', 11, Theme.muted),
        Scroll(style=S(width=width, height=max(40, height - 129)), resetKey=(section, query, current),
               children=Panel(style=S(width=width - 24, height=max(40, len(cards) * 84), gap=4),
                              children=cards or [text('没有匹配的蓝图', 12, Theme.muted)])),
        row([Action(label='上一页', glyph='arrow_left', width=90, height=27,
                    enabled=current > 0, onClick=partial(set_page, current - 1)),
             text('%d / %d' % (current + 1, pages), 12, Theme.muted, flex=1),
             Action(label='下一页', glyph='arrow_right', width=90, height=27,
                    enabled=current + 1 < pages, onClick=partial(set_page, current + 1))], gap=8)])


@Component
def TestBlueprints(session=None, revision=0, width=760, height=440):
    use_theme()
    category, set_category = use_state('manual')
    blueprints = entries(category)
    cards = []
    card_width = width - 48
    for identity, unused_category, title, size, block in (blueprints if category != 'manual' else ()):
        load = partial(open_blueprint, session, identity)
        cards.append(Panel(key=identity, style=S(width=card_width, height=90, flexShrink=0,
                                               gap=8, paddingVertical=9), children=[
            row([MaterialIcon(value=material(block), size=36),
                 Panel(style=S(flex=1, gap=6), children=[
                     text(title, 16, width=card_width - 162),
                     text('%d × %d × %d' % size, 11, Theme.muted)]),
                 Action(label='载入', glyph='cube', accent=True, width=90, height=32,
                        enabled=not session.busy and session.edit_job is None and session.io_job is None,
                        onClick=partial(session.confirm, '载入将替换当前草稿，继续吗？', load))], gap=12),
            line()]))
    return Panel(style=S(width=width, height=height, padding=12, gap=12), children=[
        row([text('测试蓝图', 21, flex=1), text('%d 份' % len(blueprints), 11, Theme.muted)], height=34),
        Segments(items=CATEGORIES, value=category, width=min(660, width - 24), onChange=set_category),
        ManualBlueprints(session=session, width=width - 24, height=height - 105) if category == 'manual' else
        Scroll(style=S(width=width - 24, height=height - 105), resetKey=category,
               children=PreparedColumn(session=session, urgent=lambda: session.page == 'testing',
                   style=S(width=card_width, gap=8, height=max(90, len(cards) * 98 - 8)),
                   initial=1, children=cards))])
