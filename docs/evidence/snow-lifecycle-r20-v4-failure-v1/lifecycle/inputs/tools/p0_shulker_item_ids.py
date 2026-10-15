"""Read loaded native shulker item identities for fixture setup."""
import json
import mod.server.extraServerApi as api
items = api.GetEngineCompFactory().CreateItem(api.GetLevelId())
_result = json.dumps([name for name in items.GetLoadItems(True) if 'shulker' in name])
