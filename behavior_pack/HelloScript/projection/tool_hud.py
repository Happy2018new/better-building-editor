# -*- coding: utf-8 -*-
"""Small touch-friendly world button for the hand-held editor terminal."""
from __future__ import unicode_literals
import mod.client.extraClientApi as clientApi
from .tool_items import SURVEY_WAND, TERMINAL, item_name
from .input_mode import is_touch
from ..pyreact import navigator

_OWNER = [None]
ScreenNode = clientApi.GetScreenNodeCls()
CONTENT = ('/variables_button_mappings_and_controls/safezone_screen_matrix'
           '/inner_matrix/safezone_screen_panel/root_screen_panel')


class TerminalHudScreen(ScreenNode):
    def Create(self):
        self.button = self.GetBaseUIControl(str(CONTENT + '/open_button'))
        if self.button is not None:
            self.button.asButton().AddTouchEventParams({'isSwallow': True})
            self.button.asButton().SetButtonTouchUpCallback(self.open)
        self.set_state(False, '')

    def open(self, unused=None):
        owner = _OWNER[0]
        if owner is not None:
            owner.tool_hud_action()

    def set_state(self, visible, caption):
        if self.button is not None:
            self.button.SetVisible(bool(visible), False)
            label = self.GetBaseUIControl(str(CONTENT + '/open_button/caption'))
            if label is not None:
                label.asLabel().SetText(caption.encode('utf8'))
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
        corners = self.owner.bridge.corners
        visible = (self.carried == TERMINAL or
                   (self.carried == SURVEY_WAND and None not in corners and is_touch()))
        visible = visible and not navigator.contains('modern_projection_workspace')
        caption = '投影工作台' if self.carried == TERMINAL else '导入选区'
        state = (visible, caption)
        if state != self.shown and self.screen is not None:
            self.shown = state
            self.screen.set_state(*state)

    def destroy(self):
        if _OWNER[0] is self.owner:
            _OWNER[0] = None
        if self.screen is not None:
            self.screen.set_state(False, '')
