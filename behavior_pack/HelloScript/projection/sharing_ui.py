# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Clipboard dialogs with the same motion as other application dialogs."""
from __future__ import unicode_literals
from functools import partial
from ..pyreact import *
from .widgets import Theme, S, text, row, surface, icon, Action, Segments, use_theme
from .sharing_codec import PART_SIZES
from .motion import DialogMotion


@Component
def SharingDialog(session=None, width=900, height=640):
    use_theme()
    share = session.sharing
    unused, refresh = use_state(0)
    retained = use_ref(None)
    def subscribe():
        return session.subscribe(lambda: refresh(lambda value: value+1), ('sharing', 'library'))
    use_effect(subscribe, [session])
    if share.opened:
        exporting = share.mode == 'export'
        card_width = min(480,width-48)
        content_width = card_width-48
        title = '分享建筑' if exporting else '导入建筑'
        children = [row([icon('copy' if exporting else 'paste', Theme.blue, 24), text(title, 20),
                         Panel(style=S(flex=1)), Action(glyph='close', width=28, onClick=share.close)]),
                    text(share.message, 11, Theme.red if share.error else Theme.muted, width=content_width)]
        if share.busy:
            done,total = share.progress
            children += [text('%d / %d' % (done,total), 10, Theme.muted),
                         Image(color=Theme.line, style=S(width=content_width,height=3), children=
                               Image(color=Theme.blue,style=S(width=content_width*min(1.,done/float(max(1,total))),height=3)))]
        if share.document:
            document = share.document
            children += [surface(color=Theme.tint, padding=12, gap=5, children=[
                text(document.name, 15, width=content_width-24),
                text('%d × %d × %d，%d 个方块' % (tuple(document.size)+(len(document.blocks),)), 11, Theme.muted)])]
        if exporting and share.text:
            children += [Action(label='复制完整编码', glyph='copy', accent=True, onClick=share.copy)]
            if share.parts:
                children += [text('分段发送，每段长度',11,Theme.muted),
                             Segments(items=[(size,'%d 字'%size) for size in PART_SIZES],value=share.part_size,
                                      onChange=share.set_part_size,width=content_width),
                             row([Action(glyph='arrow_left', width=30,onClick=partial(share.select_part,-1),enabled=share.part>0),
                                  text('第 %d / %d 段' % (share.part+1,len(share.parts)),11,Theme.muted,flex=1,center=True),
                                  Action(glyph='arrow_right',width=30,onClick=partial(share.select_part,1),enabled=share.part+1<len(share.parts)),
                                  Action(label='复制这一段',glyph='copy',onClick=partial(share.copy,True))])]
        elif not exporting:
            children += [row([Action(label='从剪贴板读取',glyph='paste',accent=True,onClick=share.paste,enabled=not share.busy),
                              Action(label='清空',glyph='erase',onClick=share.clear_parts,enabled=not share.busy and bool(share.inbox.parts))])]
            if share.document:
                children += [text('导入只添加本地配置，当前草稿和世界保持完整。',11,Theme.muted,width=content_width),
                             Action(label='确认加入建筑库',glyph='save',accent=True,onClick=share.accept,enabled=not share.busy and not share.saved)]
            elif share.inbox.parts:
                children += [text('绿色为已接收，浅灰为待接收',10,Theme.muted)]
                start = share.inbox_page*24+1
                for first in range(start,min(start+24,share.inbox.total+1),6):
                    children.append(row([surface(width=(content_width-30)/6.,height=24,padding=0,
                        color=Theme.tint if number not in share.inbox.parts else Color(0xE6F5EFFF),
                        justifyContent=JustifyContent.center,alignItems=AlignItems.center,children=
                        text(str(number),10,Theme.muted if number not in share.inbox.parts else Theme.mint))
                        for number in range(first,min(first+6,share.inbox.total+1))]))
                children += [row([Action(glyph='arrow_left',width=28,onClick=partial(share.inbox_move,-1),enabled=share.inbox_page>0),
                                  text('%d / %d 页'%(share.inbox_page+1,(share.inbox.total+23)//24),10,Theme.muted,flex=1,center=True),
                                  Action(glyph='arrow_right',width=28,onClick=partial(share.inbox_move,1),enabled=start+24<=share.inbox.total),
                                  Action(label='定位缺失',glyph='pin',onClick=share.first_missing)])]
        retained.current = surface(width=card_width,padding=24,gap=16,children=children)
    return DialogMotion(opened=share.opened, session=session, children=retained.current)
