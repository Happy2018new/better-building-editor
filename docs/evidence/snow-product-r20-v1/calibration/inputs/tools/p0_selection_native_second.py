import json
import sys
import mod.server.extraServerApi as api
f = api.GetEngineCompFactory()
p = api.GetPlayerList()[0]
s = api.GetSystem('ModernProjection', 'ModernProjectionServerSystem')
used = f.CreateBlockInfo(p).PlayerUseItemToPos(
    sys._p0_selection_native_end, api.GetMinecraftEnum().ItemPosType.CARRIED, 0, 1)
_result = json.dumps({'used': used, 'point': s.world_points.get(p), 'region': s.world_regions.get(p)})
