# -*- coding: utf-8 -*-
"""Small touch-friendly world button for the hand-held editor terminal."""
from __future__ import unicode_literals
import mod.client.extraClientApi as clientApi
from .tool_items import SURVEY_WAND, TERMINAL, item_name
from ..pyreact import navigator

_OWNER = [None]
ScreenNode = clientApi.GetScreenNodeCls()
CONTENT = ('/variables_button_mappings_and_controls/safezone_screen_matrix'
           '/inner_matrix/safezone_screen_panel/root_screen_panel')


class TerminalHudScreen(ScreenNode):
    def Create(self):
        self.button = self.GetBaseUIControl(str(CONTENT + '/open_button'))
        self.reset_button = self.GetBaseUIControl(str(CONTENT + '/reset_button'))
        if self.button is not None:
            self.button.asButton().AddTouchEventParams({'isSwallow': True})
            self.button.asButton().SetButtonTouchUpCallback(self.open)
        if self.reset_button is not None:
            self.reset_button.asButton().AddTouchEventParams({'isSwallow': True})
            self.reset_button.asButton().SetButtonTouchUpCallback(self.reset)
        self.set_state(False, '', False)

    def open(self, unused=None):
        owner = _OWNER[0]
        if owner is not None:
            owner.tool_hud_action()

    def reset(self, unused=None):
        owner = _OWNER[0]
        if owner is not None:
            owner.tool_reset()

    def set_state(self, visible, caption, reset):
        if self.button is not None:
            self.button.SetVisible(bool(visible), False)
            self.GetBaseUIControl(str(CONTENT + '/open_button/caption')).asLabel().SetText(caption.encode('utf8'))
            if self.reset_button is not None:
                self.reset_button.SetVisible(bool(reset and visible), False)
            self.UpdateScreen(False)


class TerminalHud(object):
    def __init__(self, owner):
        _OWNER[0] = owner
        self.owner = owner
        self.carried = None
        self.shown = None
        clientApi.RegisterUI(str('ModernProjectionTools'), str('TerminalHud'),
                             str(__name__ + '.TerminalHudScreen'), str('ModernProjectionTools.hudScreen'))
        self.screen = clientApi.CreateUI(str('ModernProjectionTools'), str('TerminalHud'), {'isHud': 1})
        self.refresh_carried()

    def refresh_carried(self, item=None):
        if item is None:
            player = clientApi.GetLocalPlayerId()
            item = clientApi.GetEngineCompFactory().CreateItem(player).GetPlayerItem(
                clientApi.GetMinecraftEnum().ItemPosType.CARRIED, 0)
        self.carried = item_name(item)
        self.update()

    def update(self):
        visible = self.carried in (SURVEY_WAND, TERMINAL) and not navigator.contains('modern_projection_workspace')
        corners = self.owner.bridge.corners
        caption = ('打开投影工作台' if self.carried == TERMINAL else '导入选区' if None not in corners else
                   '标记第二角点' if corners[0] is not None else '标记第一角点')
        reset = self.carried == SURVEY_WAND and corners[0] is not None
        state = (visible, caption, reset)
        if state != self.shown and self.screen is not None:
            self.shown = state
            self.screen.set_state(*state)

    def destroy(self):
        if _OWNER[0] is self.owner:
            _OWNER[0] = None
        if self.screen is not None:
            self.screen.set_state(False, '', False)
