"""Prepare reversible plant cross hypotheses; this does not accept their pixels."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from generate_static_plant_proxies import ROOT, SOURCE, validate
from generate_shulker_proxies import behavior


NAMES = ('poppy', 'crimson_roots', 'warped_roots', 'nether_sprouts',
         'short_grass', 'fern')
TARGET = (-47, 117, -70)
CLIP_REPORT = Path('C:/Users/Happy2018new/.pyreact-debug/instances/28978d1a387543aa8bc37951fd2ece18/artifacts/netease-offset-capability-r9-v3.json')
CLIP_REPORT_SHA256 = '35ff1a991bad3efa60ec53a96c3a29005990bf377f57f667921c6f8600018df5'
# These values are independent clip clues, not a recovered native mesh contract.
XZ_CLIP_HYPOTHESIS = (-7. / 60., -7. / 60.)
GRASS_Y_CLIP_HYPOTHESIS = -7. / 75.


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def candidates(source, originals, offset=True):
    """Use source texture/UV identities and declare geometry assumptions explicitly."""
    validate(source)
    blocks = deepcopy(originals['resource_pack/blocks.json'])
    atlas = deepcopy(originals['resource_pack/textures/terrain_texture.json'])
    data = originals['behavior_pack/modern_projection/projection/plant_proxy_data.py']
    files = {}
    for name in NAMES:
        identifier = 'modern_projection:preview_' + name
        model = deepcopy(source['template'])
        short = name in ('short_grass', 'fern')
        dx, dz = XZ_CLIP_HYPOTHESIS if offset else (0., 0.)
        dy = GRASS_Y_CLIP_HYPOTHESIS if short and offset else 0.
        for bone in model['netease:block_geometry']['bones']:
            bone['pivot'] = [-8. - dx * 16., 8. + dy * 16., 8. + dz * 16.]
            for cube in bone['cubes']:
                cube['origin'][0] -= dx * 16.
                cube['origin'][1] = dy * 16.
                cube['origin'][2] += dz * 16.
                cube['size'][1] = 16.
        if short:
            key = 'tallgrass' if name == 'short_grass' else 'fern'
            texture = 'textures/blocks/' + key
            sound = 'grass'
        else:
            record = source['plants'][name]
            key = 'modern_projection_static_' + name
            texture = record['texture_path'].rsplit('.', 1)[0]
            sound = record['definition'].get('sound', 'grass')
            data += '\nSTATIC_PLANT_PROXIES[(%r, 0)] = %r\n' % ('minecraft:' + name, identifier)
            data += 'STATIC_PLANT_MAX_Y[(%r, 0)] = %r\n' % (
                'minecraft:' + name, 1. - record['alpha_bounds'][1] / 16.)
        model['netease:block_geometry']['description'].update(
            identifier=identifier, textures=[key], item_texture=key)
        definition = behavior(identifier, 'alpha')
        definition['minecraft:block']['components'].update({
            'netease:water_source': {'value': True},
            'netease:water_flow_source': {'value': True}})
        if short:
            appearance = deepcopy(blocks[identifier])
        else:
            appearance = {'netease_model': identifier, 'sound': sound}
        blocks[identifier] = appearance
        atlas['texture_data'][key] = {'textures': texture}
        files['behavior_pack/netease_blocks/preview_' + name + '.json'] = definition
        files['resource_pack/models/netease_block/preview_' + name + '.json'] = model
    files.update({'resource_pack/blocks.json': blocks,
                  'resource_pack/textures/terrain_texture.json': atlas,
                  'behavior_pack/modern_projection/projection/plant_proxy_data.py': data})
    return {name: (value if isinstance(value, str) else
                  json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('utf8')
            for name, value in files.items()}


def apply(snapshot, offset):
    if snapshot.exists():
        raise ValueError('Experimental source snapshot must be fresh')
    if offset and digest(CLIP_REPORT.read_bytes()) != CLIP_REPORT_SHA256:
        raise ValueError('Independent native clip evidence changed')
    source = json.loads(SOURCE.read_bytes())
    names = ('resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json',
             'behavior_pack/modern_projection/projection/plant_proxy_data.py')
    originals = {name: ((ROOT/name).read_text(encoding='utf8') if name.endswith('.py')
                       else json.loads((ROOT/name).read_bytes())) for name in names}
    files = candidates(source, originals, offset)
    before = {name: (ROOT/name).read_bytes() if (ROOT/name).is_file() else None
              for name in files}
    record = {'schema': 1, 'project': str(ROOT), 'native_target': TARGET,
              'plants': NAMES, 'production_acceptance': False,
              'native_mesh_or_offset_contract_recovered': False,
              'geometry_hypothesis': 'Unit-height cross; unchanged XZ spans/UV; independent native fern clip translation applied only as a candidate',
              'clip_hypothesis_enabled': offset,
              'xz_clip_hypothesis': XZ_CLIP_HYPOTHESIS if offset else (0., 0.),
              'grass_y_clip_hypothesis': GRASS_Y_CLIP_HYPOTHESIS if offset else 0.,
              'clip_source_report': str(CLIP_REPORT) if offset else None,
              'clip_source_report_sha256': CLIP_REPORT_SHA256 if offset else None,
              'source_manifest_sha256': digest(SOURCE.read_bytes()),
              'before': {name: raw.hex() if raw is not None else None for name, raw in before.items()},
              'candidate_sha256': {name: digest(raw) for name, raw in files.items()}}
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps(record, ensure_ascii=True, indent=2) + '\n', encoding='utf8')
    for name, raw in files.items():
        (ROOT/name).write_bytes(raw)
    return record


def restore(snapshot):
    record = json.loads(snapshot.read_bytes())
    if record['schema'] != 1 or Path(record['project']).resolve() != ROOT.resolve():
        raise ValueError('Experimental snapshot belongs to another project')
    changed = [name for name, expected in record['candidate_sha256'].items()
               if not (ROOT/name).is_file() or digest((ROOT/name).read_bytes()) != expected]
    if changed:
        raise ValueError('Candidate bytes changed; refuse to overwrite: ' + ', '.join(changed))
    for name, raw in record['before'].items():
        if raw is None:
            (ROOT/name).unlink()
        else:
            (ROOT/name).write_bytes(bytes.fromhex(raw))
    return {'restored': True, 'snapshot': str(snapshot.resolve())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--centered', action='store_true')
    args = parser.parse_args()
    record = restore(args.snapshot) if args.restore else apply(args.snapshot, not args.centered)
    print(json.dumps({key: value for key, value in record.items() if key not in
                      ('before', 'candidate_sha256')}, ensure_ascii=True))


if __name__ == '__main__':
    main()
