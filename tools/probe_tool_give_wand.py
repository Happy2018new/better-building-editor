# -*- coding: utf-8 -*-
"""Give the survey wand to the isolated MCDK test player only."""
import mod.server.extraServerApi as api
from HelloScript.projection.tool_items import SURVEY_WAND
player = api.GetPlayerList()[0]
item = api.GetEngineCompFactory().CreateItem(player)
created = item.SpawnItemToPlayerCarried({'itemName': SURVEY_WAND.encode('utf8'), 'count': 1, 'auxValue': 0}, player)
_result = {'given': created, 'carried': item.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED, 0)}
