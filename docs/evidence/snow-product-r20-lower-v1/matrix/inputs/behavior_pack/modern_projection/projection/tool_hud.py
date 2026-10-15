# -*- coding: utf-8 -*-
"""Small touch-friendly world button for the hand-held editor terminal."""
from __future__ import unicode_literals
import mod.client.extraClientApi as clientApi
from .tool_items import SURVEY_WAND, TERMINAL, item_name
from .bridge import native
from .input_mode import is_touch
from ..pyreact import navigator

_OWNER = [None]
ScreenNode = clientApi.GetScreenNodeCls()
CONTENT = ('/variables_button_mappings_and_controls/safezone_screen_matrix'
           '/inner_matrix/safezone_screen_panel/root_screen_panel')


class TerminalHudScreen(ScreenNode):
    def Create(self):
        self.button = self.GetBaseUIControl(str(CONTENT + '/open_button'))
        self.clear_button = self.GetBaseUIControl(str(CONTENT + '/clear_button'))
        self.tip = self.GetBaseUIControl(str(CONTENT + '/tip_panel'))
        if self.button is not None:
            self.button.asButton().AddTouchEventParams({'isSwallow': True})
            self.button.asButton().SetButtonTouchUpCallback(self.open)
        if self.clear_button is not None:
            self.clear_button.asButton().AddTouchEventParams({'isSwallow': True})
            self.clear_button.asButton().SetButtonTouchUpCallback(self.clear)
        if self.tip is not None:
            self.tip.SetVisible(False, False)
        self.set_state(False, False, '')
        owner = _OWNER[0]
        if owner is not None and owner.hud is not None:
            owner.hud.shown = None
            owner.hud.tip_shown = None

    def open(self, unused=None):
        owner = _OWNER[0]
        if owner is not None:
            owner.tool_hud_action()

    def clear(self, unused=None):
        owner = _OWNER[0]
        if owner is not None:
            owner.tool_reset()

    def set_state(self, visible, clear_visible, caption):
        if self.button is not None:
            self.button.SetVisible(bool(visible), False)
            self.button.SetFullPosition('x', {'absoluteValue': -27 if clear_visible else 0})
            label = self.GetBaseUIControl(str(CONTENT + '/open_button/caption'))
            if label is not None:
                label.asLabel().SetText(caption.encode('utf8'))
        if self.clear_button is not None:
            self.clear_button.SetVisible(bool(clear_visible), False)
            self.clear_button.SetFullPosition('x', {'absoluteValue': 27 if visible else 0})
        self.UpdateScreen(False)

    def set_tip(self, message):
        if self.tip is None:
            return
        label = self.GetBaseUIControl(str(CONTENT + '/tip_panel/tip_text'))
        if label is not None:
            label.asLabel().SetText(native(message))
        self.tip.SetVisible(bool(message), False)
        self.UpdateScreen(False)


class TerminalHud(object):
    def __init__(self, owner):
        _OWNER[0] = owner
        self.owner = owner
        self.carried = None
        self.shown = None
        self.tip_sequence = 0
        self.tip_message = ''
        self.tip_shown = None
        self.tip_carried = None
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
        # Existing HUD instances survive development-time Python hot reload.
        if not hasattr(self, 'tip_message'):
            self.tip_message = ''
            self.tip_shown = None
            self.tip_carried = None
        if self.carried != self.tip_carried:
            self.tip_carried = self.carried
            self.tip_message = ''
            self.tip_sequence += 1
        visible = self.carried in (TERMINAL, SURVEY_WAND)
        visible = visible and not navigator.contains('modern_projection_workspace')
        caption = '投影工作台' if self.carried == TERMINAL else '导入选区'
        clear_visible = self.carried == SURVEY_WAND and visible
        state = (visible, clear_visible, caption)
        if state != self.shown and self.screen is not None:
            self.shown = state
            self.screen.set_state(*state)
        self.update_tip(visible)

    def update_tip(self, visible=None):
        if self.screen is None:
            return
        if visible is None:
            visible = self.carried in (TERMINAL, SURVEY_WAND) and not navigator.contains('modern_projection_workspace')
        hint = ''
        if visible and not is_touch():
            hint = ('右键选点 · 左键导入 · 潜行＋右键清除' if self.carried == SURVEY_WAND
                    else '右键或点击按钮打开工作台')
        message = '\n'.join(part for part in (self.tip_message, hint) if part) if visible else ''
        if message != self.tip_shown:
            self.tip_shown = message
            self.screen.set_tip(message)

    def show_tip(self, message):
        if self.screen is None:
            return
        self.tip_sequence += 1
        sequence = self.tip_sequence
        self.tip_message = message
        self.update_tip()

        def hide():
            if self.tip_sequence == sequence and self.screen is not None:
                self.tip_message = ''
                self.update_tip()
        self.owner.bridge.later(4., hide)

    def destroy(self):
        if _OWNER[0] is self.owner:
            _OWNER[0] = None
        self.tip_sequence += 1
        if self.screen is not None:
            self.screen.set_state(False, False, '')
