"""Use the carried survey wand through the engine's item-on-block path."""
import json
import sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.tool_items import SURVEY_WAND

f = api.GetEngineCompFactory()
p = api.GetPlayerList()[0]
s = api.GetSystem('ModernProjection', 'ModernProjectionServerSystem')
info = f.CreateBlockInfo(p)
positions = sys._p0_acceptance_positions
end = (positions[9][0] + 1, positions[9][1] + 1, positions[9][2])
WorldAdapter(p).write(end, ('minecraft:stone', 0))
f.CreateItem(p).SpawnItemToPlayerCarried(
    {'itemName': SURVEY_WAND.encode('utf8'), 'count': 1, 'auxValue': 0}, p)
sys._p0_selection_native_end = end
used = info.PlayerUseItemToPos(positions[0], api.GetMinecraftEnum().ItemPosType.CARRIED, 0, 1)
_result = json.dumps({'used': used, 'point': s.world_points.get(p), 'region': s.world_regions.get(p)})
