"""Export static definitions through managed MCDK server execution, without NBT reads."""
import json
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry

factory = api.GetEngineCompFactory()
info = factory.CreateBlockInfo(api.GetLevelId())
rows = {}
for name in sorted(block_registry.BLOCKS):
    data = info.GetBlockBasicInfo(name.encode('utf8'))
    if data is not None:
        rows[name] = dict((key, data[key]) for key in
                          ('solid', 'renderLayer', 'tags') if key in data)
_result = json.dumps({'schema': 1, 'game_version': block_registry.source_version(),
                      'palette_sha256': block_registry.fingerprint(), 'blocks': rows},
                     sort_keys=True)
