# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Public test blueprint page with stable category and fixture identities."""
from __future__ import unicode_literals
from functools import partial
from ..pyreact import Component, Panel, use_state
from .widgets import Theme, S, row, text, Action, Segments, Scroll, use_theme, line
from .panels import MaterialIcon
from .preparation import PreparedColumn
from .debug_blueprints import CATEGORIES, entries, material, open_blueprint


@Component
def TestBlueprints(session=None, revision=0, width=760, height=440):
    use_theme()
    category, set_category = use_state('layers')
    blueprints = entries(category)
    cards = []
    card_width = width - 48
    for identity, unused_category, title, size, block in blueprints:
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
        Scroll(style=S(width=width - 24, height=height - 105), resetKey=category,
               children=PreparedColumn(session=session, urgent=lambda: session.page == 'testing',
                   style=S(width=card_width, gap=8, height=max(90, len(cards) * 98 - 8)),
                   initial=1, children=cards))])
