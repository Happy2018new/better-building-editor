# -*- coding: utf-8 -*-
"""Read the native input setting, including the developer touch-mode toggle."""
import mod.client.extraClientApi as clientApi


def current_mode():
    view = clientApi.GetEngineCompFactory().CreatePlayerView(clientApi.GetLevelId())
    return view.GetToggleOption(clientApi.GetMinecraftEnum().OptionId.INPUT_MODE)


def is_touch():
    # On Windows F11 changes the simulation flag immediately, while INPUT_MODE
    # retains the previous contact's type in both directions until another input.
    if clientApi.GetPlatform() == 0:
        return clientApi.IsTouchWithMouse()
    mode = current_mode()
    if mode != clientApi.GetMinecraftEnum().InputMode.Undefined:
        return mode == clientApi.GetMinecraftEnum().InputMode.Touch
    return clientApi.GetPlatform() in (1, 2)
