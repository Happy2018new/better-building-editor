# -*- coding: utf-8 -*-
"""Read-only MCDK probe for registered custom items."""
import mod.server.extraServerApi as api
from modern_projection.projection.tool_items import SURVEY_WAND, TERMINAL
system = api.GetSystem('ModernProjection', 'ModernProjectionServerSystem')
item = api.GetEngineCompFactory().CreateItem(api.GetLevelId())
recipes = api.GetEngineCompFactory().CreateRecipe(api.GetLevelId())
_result = {
    'system_ready': system is not None,
    'wand': item.GetItemBasicInfo(SURVEY_WAND, 0),
    'terminal': item.GetItemBasicInfo(TERMINAL, 0),
    'wand_recipe': recipes.GetRecipesByResult(SURVEY_WAND.encode('utf8'), 'crafting_table'),
    'terminal_recipe': recipes.GetRecipesByResult(TERMINAL.encode('utf8'), 'crafting_table'),
    'vanilla_recipe': recipes.GetRecipesByResult('minecraft:compass', 'crafting_table'),
    'wand_by_id': recipes.GetRecipeByRecipeId(SURVEY_WAND.encode('utf8')),
    'terminal_by_id': recipes.GetRecipeByRecipeId(TERMINAL.encode('utf8')),
}
