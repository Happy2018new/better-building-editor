# -*- coding: utf-8 -*-
"""Read the native input setting, including the developer touch-mode toggle."""
import mod.client.extraClientApi as clientApi


def current_mode():
    view = clientApi.GetEngineCompFactory().CreatePlayerView(clientApi.GetLevelId())
    return view.GetToggleOption(clientApi.GetMinecraftEnum().OptionId.INPUT_MODE)


def is_touch():
    mode = current_mode()
    # F11 enables native mouse-as-touch before INPUT_MODE changes on the first
    # contact. Hide desktop hover and use touch gestures from UI entry onward.
    if clientApi.GetPlatform() == 0 and clientApi.IsTouchWithMouse():
        return True
    if mode != clientApi.GetMinecraftEnum().InputMode.Undefined:
        return mode == clientApi.GetMinecraftEnum().InputMode.Touch
    return clientApi.GetPlatform() in (1, 2)
