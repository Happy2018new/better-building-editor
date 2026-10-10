"""Observe frame rotation NBT and server palettes through documented native APIs."""
import json
import sys
import mod.server.extraServerApi as api
from modern_projection.projection.nbt_spatial import root_payload, scalar

saved = sys._p0_entity_appearances
factory = api.GetEngineCompFactory()
info = factory.CreateBlockInfo(saved['player'])
frames = factory.CreateBlockEntity(api.GetLevelId())
block = factory.CreateBlock(api.GetLevelId())
saved['frame_rotation_samples'] = samples = []
originals = []


def portable_palette(data):
    result = dict((key, value) for key, value in data.items()
                  if key not in ('common', 'extra', 'states', 'extraStates'))
    for field in ('common', 'extra', 'states', 'extraStates'):
        result[field] = [{'material': key, 'value': value}
                         for key, value in data.get(field, {}).items()]
    return result


try:
    for row in saved['rows']:
        if not row.get('fill_item'):
            continue
        pos = tuple(row['pos'])
        original = frames.GetFrameRotation(pos, saved['dimension'])
        assert original >= 0, ('Native frame rotation unavailable', row['case'])
        originals.append((pos, original))
        for angle in (0., 45., 90., 135., 180., 225., 270., 315.):
            placed = frames.SetFrameRotation(pos, saved['dimension'], angle)
            assert placed, ('Native frame angle rejected', row['case'], angle)
            data = info.GetBlockEntityData(saved['dimension'], pos)
            root = root_payload(data)
            palette = block.GetBlockPaletteBetweenPos(saved['dimension'], pos, pos, False)
            assert palette is not None, ('Native server frame palette unavailable', row['case'])
            samples.append({'case': row['case'], 'face': row['face'],
                            'api_requested_degrees': angle,
                            'api_observed_degrees': frames.GetFrameRotation(pos, saved['dimension']),
                            'nbt_item_rotation': root.get('ItemRotation'),
                            'observed_id': scalar(root, 'id'),
                            'server_palette': portable_palette(palette.SerializeBlockPalette())})
finally:
    prior_error = sys.exc_info()[0]
    errors = []
    for pos, original in originals:
        try:
            restored = frames.SetFrameRotation(pos, saved['dimension'], original)
            if not restored or frames.GetFrameRotation(pos, saved['dimension']) != original:
                errors.append(('frame_rotation', pos, original))
        except Exception as error:
            errors.append(('frame_rotation', pos, str(error)))
    saved['frame_rotation_cleanup_errors'] = errors
    if errors and prior_error is None:
        raise AssertionError(errors)
_result = json.dumps({'schema': 1, 'game_version': saved['game_version'],
                      'palette_sha256': saved['palette_sha256'], 'samples': samples,
                      'rotations_restored': not errors})
