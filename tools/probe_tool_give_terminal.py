# -*- coding: utf-8 -*-
"""Give the terminal to the isolated MCDK test player only."""
import mod.server.extraServerApi as api
from HelloScript.projection.tool_items import TERMINAL
player = api.GetPlayerList()[0]
item = api.GetEngineCompFactory().CreateItem(player)
created = item.SpawnItemToPlayerCarried({'itemName': TERMINAL.encode('utf8'), 'count': 1, 'auxValue': 0}, player)
_result = {'given': created, 'carried': item.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.CARRIED, 0)}
