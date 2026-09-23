# -*- coding: utf-8 -*-
"""Read-only MCDK probe for custom tools and their HUD."""
import mod.client.extraClientApi as api
from HelloScript.projection.tool_items import SURVEY_WAND, TERMINAL
owner = api.GetSystem('ModernProjection', 'HelloClientSystem')
item = api.GetEngineCompFactory().CreateItem(api.GetLevelId())
hud = owner.hud
_result = {
    'session_ready': owner.session is not None,
    'wand': item.GetItemBasicInfo(SURVEY_WAND, 0),
    'terminal': item.GetItemBasicInfo(TERMINAL, 0),
    'hud_created': hud is not None and hud.screen is not None,
    'hud_button': hud is not None and hud.screen.button is not None,
    'hud_button_size': None if hud is None or hud.screen.button is None else hud.screen.button.GetSize(),
    'hud_button_visible': None if hud is None or hud.screen.button is None else hud.screen.button.GetVisible(),
    'hud_carried': None if hud is None else hud.carried,
    'hud_shown': None if hud is None else hud.shown,
}
