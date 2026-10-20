"""Generate hidden neighbor-selected kelp meshes bound to the native atlas."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from configure_development_runtime import load_target
from generate_static_plant_proxies import centered_cross_model, TEMPLATE
from generate_shulker_proxies import behavior

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT/'tools/data/kelp_render_profiles_nemc_3.10.0.420447.json'
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.kelp_render import PROXIES
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(profile, native=None):
    if (profile.get('schema') != 1 or
            profile.get('registry_version') != registry.source_version() or
            profile.get('registry_sha256') != registry.fingerprint() or
            profile.get('resource_version') != load_target()['resource_version'] or
            profile.get('template_path') != TEMPLATE.relative_to(ROOT).as_posix() or
            profile.get('template_sha256') != digest(TEMPLATE) or
            profile.get('style') != 'fixed_centered_double_sided_native_atlas' or
            profile.get('native_mesh_authority') is not False or
            profile.get('native_cycle_qualified') is not False or
            profile.get('snow_qualified') is not False or
            set(profile.get('parts', {})) != set(PROXIES)):
        raise ValueError('Kelp source version, template or qualification changed')
    terrain = json.loads((ROOT/'resource_pack/textures/terrain_texture.json').read_bytes())['texture_data']
    flipbooks = json.loads((ROOT/'resource_pack/textures/flipbook_textures.json').read_bytes())
    for part, tile in (('stem', 'kelp_a'), ('top', 'kelp_top')):
        row = profile['parts'][part]
        expected_flipbook = {'atlas_tile':tile, 'flipbook_texture':'textures/blocks/'+tile,
                             'frames':list(range(20)), 'ticks_per_frame':4}
        if (row.get('identifier') != PROXIES[part] or row.get('atlas_tile') != tile or
                row.get('terrain_entry') != {'textures':'textures/blocks/'+tile} or
                row.get('texture_size') != [16, 320] or row.get('flipbook') != expected_flipbook or
                row.get('texture_path') != 'textures/blocks/'+tile+'.tga' or
                len(row.get('texture_sha256','')) != 64 or
                not set(row['texture_sha256']) <= set('0123456789abcdef') or
                PROXIES[part] not in INTERNAL_RENDER_BLOCKS):
            raise ValueError('Kelp native atlas binding or hidden identifier changed: '+part)
        if tile in terrain or [item for item in flipbooks if item.get('atlas_tile') == tile] != [expected_flipbook]:
            raise ValueError('Kelp inherited native atlas or project flipbook changed: '+part)
        if native is not None and digest(native/row['texture_path']) != row['texture_sha256']:
            raise ValueError('Installed kelp texture differs: '+part)
    if native is not None:
        native_terrain = json.loads((native/'textures/terrain_texture.json').read_bytes())['texture_data']
        native_flipbooks = json.loads((native/'textures/flipbook_textures.json').read_bytes())
        for row in profile['parts'].values():
            if (native_terrain.get(row['atlas_tile']) != row['terrain_entry'] or
                    [item for item in native_flipbooks if item.get('atlas_tile') == row['atlas_tile']] != [row['flipbook']]):
                raise ValueError('Installed native kelp atlas binding differs')


def outputs(profile):
    validate(profile)
    blocks_path = ROOT/'resource_pack/blocks.json'
    blocks = json.loads(blocks_path.read_bytes())
    template = {'template':json.loads(TEMPLATE.read_bytes())}
    result = {}
    for part, row in sorted(profile['parts'].items()):
        identifier = PROXIES[part]
        stem = identifier.split(':', 1)[1]
        definition = behavior(identifier, 'alpha')
        definition['minecraft:block']['components']['minecraft:block_light_absorption'] = {'value':0}
        result[ROOT/('behavior_pack/netease_blocks/'+stem+'.json')] = definition
        result[ROOT/('resource_pack/models/netease_block/'+stem+'.json')] = centered_cross_model(
            template, identifier, row['atlas_tile'])
        blocks[identifier] = {'netease_model':identifier,'sound':'grass'}
    result[blocks_path] = blocks
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--native-resources', type=Path)
    args = parser.parse_args()
    profile = json.loads(PROFILE.read_bytes())
    validate(profile, args.native_resources)
    files, stale = outputs(profile), []
    for path, value in files.items():
        if args.check:
            if not path.is_file() or json.loads(path.read_bytes()) != value:
                stale.append(path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(value,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    if stale:
        raise SystemExit('Stale kelp proxies: '+', '.join(stale))
    print(json.dumps({'checked':args.check,'files':len(files),'parts':len(PROXIES),
                      'native_mesh_authority':False,'native_cycle_qualified':False,'snow_qualified':False}))


if __name__ == '__main__':
    main()
