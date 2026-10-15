"""Freeze one terrain fragment readback after native shelf route selection."""
import argparse
from collections import Counter
import difflib
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

from freeze_intrinsic_glint_project_r21 import fingerprint
from generate_shelf_resources_r17 import write_json
from prepare_shelf_native_light_r21 import digest
from prepare_shelf_native_routes_r21 import ROOT, fragment_path, verify as verify_routes


OWNER = 'root-shelf-r20-terrain-inputs-v4'
FRAGMENT = fragment_path('terrain_base')
STRIPES = ('color_marker_yellow', 'varying_color_rgb', 'lightmap_marker_magenta',
           'native_texture1_uv1_or_white_when_always_lit', 'flags_marker_cyan',
           'flags_rgb', 'final_rgb_marker_white', 'original_final_rgb')
FLAG_CHANNELS = (('FANCY', 'FOG', 'ALWAYS_LIT', 'ALPHA_TEST'),
                 ('BLEND', 'SEASONS', 'SEASONS_FAR', 'ALLOW_FADE'),
                 ('TEXEL_AA', 'ATLAS_TEXTURE', 'TEXEL_AA_FEATURE', 'AS_ENTITY_RENDERER'))


def fragment(original):
    anchor = 'gl_FragColor = diffuse;'
    if original.count(anchor) != 1 or original.count('// __multiversion__') != 1:
        raise ValueError('The installed terrain output changed')
    flags = ['vec3 shelfTerrainFlags=vec3(0.0);']
    for channel, names in zip('rgb', FLAG_CHANNELS):
        for bit, name in enumerate(names):
            flags.append('#ifdef '+name+'\nshelfTerrainFlags.'+channel+'+='+str(1 << bit)+'.0/15.0;\n#endif')
    output = '''float shelfTerrainStripe=mod(floor(gl_FragCoord.x/16.0),8.0);
    vec3 shelfTerrainRgb=diffuse.rgb;
    vec3 shelfTerrainLight=vec3(1.0);
#if !defined(ALWAYS_LIT)
    shelfTerrainLight=texture2D(TEXTURE_1,uv1).rgb;
#endif
    %s
    if(shelfTerrainStripe<0.5) shelfTerrainRgb=vec3(1.0,1.0,0.0);
    else if(shelfTerrainStripe<1.5) shelfTerrainRgb=color.rgb;
    else if(shelfTerrainStripe<2.5) shelfTerrainRgb=vec3(1.0,0.0,1.0);
    else if(shelfTerrainStripe<3.5) shelfTerrainRgb=shelfTerrainLight;
    else if(shelfTerrainStripe<4.5) shelfTerrainRgb=vec3(0.0,1.0,1.0);
    else if(shelfTerrainStripe<5.5) shelfTerrainRgb=shelfTerrainFlags;
    else if(shelfTerrainStripe<6.5) shelfTerrainRgb=vec3(1.0);
    gl_FragColor=vec4(shelfTerrainRgb,diffuse.a);''' % '\n'.join(flags)
    return original.replace(anchor, output).replace('// __multiversion__',
        '// __multiversion__\nprecision highp float;\nprecision highp int;', 1)


def route_review(captures, output):
    report = json.loads((captures/'report.json').read_bytes())
    if not all(report.get(key) for key in ('completed', 'restored', 'source_unchanged')) or report['cleanup_errors']:
        raise ValueError('The native route acquisition did not complete and restore')
    if report.get('direction') != 'south':
        raise ValueError('This reviewed body-only ROI applies to south only')
    bounds = (912, 440, 1088, 455)
    with Image.open(captures/'native.png').convert('RGB') as first, Image.open(captures/'empty.png').convert('RGB') as second:
        if first.size != (1994, 1105) or first.size != second.size:
            raise ValueError('The reviewed raw route images changed dimensions')
        pixels = [(x, first.getpixel((x, y)), second.getpixel((x, y)))
                  for y in range(bounds[1], bounds[3]) for x in range(bounds[0], bounds[2])]
    marker = [row for row in pixels if row[0]//16 % 2 == 0]
    artwork = [row for row in pixels if row[0]//16 % 2 == 1]
    if any(row[2] != (171, 210, 255) for row in pixels):
        raise ValueError('The reviewed body-only empty ROI is not entirely sky')
    if len(marker) != 1200 or any(row[1] != (255, 255, 0) for row in marker):
        raise ValueError('The reviewed shelf body did not receive all yellow selector strips')
    if any(row[1] == (255, 255, 0) for row in artwork):
        raise ValueError('Native artwork strips unexpectedly became selector strips')
    result = {'schema_version': 1, 'actual_images_opened_by_shelf_agent': True,
        'scope': 'Oak shelf, south, unpowered, native world draw only; not other woods, states, UI or product qualification.',
        'conclusion': 'The visible native shelf body selects the terrain_base fragment override.',
        'body_only_bounds': bounds, 'empty_sky_rgb': (171, 210, 255),
        'empty_sky_pixels': len(pixels), 'yellow_marker_pixels': len(marker),
        'native_artwork_pixels': len(artwork), 'native_artwork_unique_rgb': len(Counter(row[1] for row in artwork)),
        'raw_acquisition_route_qualified_unchanged': report['native_route_qualified'],
        'raw_sha256': {name: digest(captures/name) for name in ('native.png', 'empty.png', 'report.json')},
        'frozen_manifest_sha256': report['frozen_manifest_sha256']}
    output.mkdir(parents=True)
    for name in result['raw_sha256']:
        shutil.copyfile(captures/name, output/name)
    write_json(output/'analysis.json', result)
    return result


def hosts():
    names = ['tools/prepare_shelf_terrain_inputs_r21.py', 'tools/verify_shelf_terrain_inputs_r21.py',
             'tools/probe_shelf_terrain_inputs_r21.py', '.runtime/shelf-terrain-inputs-r21-v4/run.py']
    return {name: digest(ROOT/name) for name in names}


def verify(manifest):
    data = json.loads(manifest.read_bytes())
    source = verify_routes(Path(data['source_freeze']))
    if digest(Path(data['source_freeze'])) != data['source_freeze_sha256'] or source['files'] != data['source_files']:
        raise RuntimeError('The frozen v3 route source changed')
    if fingerprint(Path(data['project'])) != data['files'] or hosts() != data['host_sources']:
        raise RuntimeError('A frozen v4 resource or host changed')
    for name, expected in data['evidence_sha256'].items():
        if digest(manifest.parent/name) != expected:
            raise RuntimeError('V4 evidence changed: '+name)
    return data


def prepare(source_freeze, captures, headers, project, output):
    occupied = output.exists() and any(path.name != 'run.py' for path in output.iterdir())
    if project.exists() or occupied:
        raise ValueError('Choose a fresh v4 clone and control directory')
    source = verify_routes(source_freeze)
    report = json.loads((captures/'report.json').read_bytes())
    if report['frozen_manifest_sha256'] != digest(source_freeze):
        raise ValueError('The route images are not bound to this exact v3 freeze')
    if digest(headers/'renderchunk.fragment') != source['native_sources'][str(headers/'renderchunk.fragment')]:
        raise ValueError('The native terrain fragment changed')
    output.mkdir(parents=True, exist_ok=True)
    review = route_review(captures, output/'route-evidence')
    for folder in ('behavior_pack', 'resource_pack'):
        shutil.copytree(Path(source['project'])/folder, project/folder)
    shutil.copyfile(Path(source['project'])/'.mcdev.json', project/'.mcdev.json')
    if fingerprint(project) != source['files']:
        raise ValueError('The v4 clone does not match its frozen v3 source')
    original = (project/FRAGMENT).read_bytes()
    incoming = fragment((headers/'renderchunk.fragment').read_text(encoding='utf8')).encode('ascii')
    (project/FRAGMENT).write_bytes(incoming)
    after = fingerprint(project)
    previous = {row['path']: row for row in source['files']}
    changed = [row['path'] for row in after if previous.get(row['path']) != row]
    if changed != [FRAGMENT]:
        raise ValueError('V4 must change exactly one terrain fragment resource')
    (output/'fragment-before.txt').write_bytes(original)
    (output/'fragment-after.txt').write_bytes(incoming)
    (output/'fragment.patch').write_text(''.join(difflib.unified_diff(original.decode('ascii').splitlines(True),
        incoming.decode('ascii').splitlines(True), fromfile='v3/'+FRAGMENT, tofile='v4/'+FRAGMENT)),
        encoding='ascii', newline='\n')
    paths = [path for path in output.rglob('*') if path.is_file() and path.name != 'run.py']
    frozen = {'schema_version': 1, 'owner': OWNER, 'project': str(project.resolve()),
        'source_freeze': str(source_freeze.resolve()), 'source_freeze_sha256': digest(source_freeze),
        'source_files': source['files'], 'files': after, 'changed_paths': changed,
        'files_sha256': hashlib.sha256(json.dumps(after, ensure_ascii=True).encode('ascii')).hexdigest(),
        'host_sources': hosts(), 'capture_exe': source['capture_exe'], 'capture_exe_sha256': source['capture_exe_sha256'],
        'evidence_sha256': {path.relative_to(output).as_posix(): digest(path) for path in paths},
        'route_review': review, 'stripe_width_pixels': 16, 'stripe_period_pixels': 128,
        'stripes': dict(enumerate(STRIPES)), 'flag_channels': FLAG_CHANNELS,
        'native_tile_status': 'No TILE_LIGHT_COLOR declaration or consumption in the original terrain pair; no uniform added.',
        'world_vertex_unchanged': True, 'native_discard_bypass_and_alpha_preserved': True,
        'game_launched': False, 'production_qualified': False, 'native_input_readback_qualified': False,
        'limits': ['Exactly south native/empty two-image acquisition; review before expansion.',
                   'Lightmap is texture1(uv1) when the native branch uses it; ALWAYS_LIT reports the effective white factor.',
                   'COLOR is the interpolated native varying, not an assumed geometric normal or actor light.']}
    write_json(output/'frozen.json', frozen)
    verify(output/'frozen.json')
    print(json.dumps({'prepared': True, 'files': len(after), 'changed_paths': changed,
                      'files_sha256': frozen['files_sha256'], 'game_launched': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-freeze', 'captures', 'headers', 'project', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source_freeze, args.captures, args.headers, args.project, args.output)
