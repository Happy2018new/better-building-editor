# -*- coding: utf-8 -*-
"""Read the native input setting, including the developer touch-mode toggle."""
import mod.client.extraClientApi as clientApi


def current_mode():
    view = clientApi.GetEngineCompFactory().CreatePlayerView(clientApi.GetLevelId())
    return view.GetToggleOption(clientApi.GetMinecraftEnum().OptionId.INPUT_MODE)


def is_touch():
    mode = current_mode()
    if mode != clientApi.GetMinecraftEnum().InputMode.Undefined:
        return mode == clientApi.GetMinecraftEnum().InputMode.Touch
    return clientApi.GetPlatform() in (1, 2)
