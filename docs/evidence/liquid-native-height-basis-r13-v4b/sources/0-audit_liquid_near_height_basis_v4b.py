"""Audit saved rule inputs and numerical sensitivity without fitting water pixels."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_liquid_sides as oracle
import analyze_liquid_native_write as visibility

BASE = ROOT / 'docs/evidence/liquid-native-write-r13-v4b'
DEST = ROOT / 'docs/evidence/liquid-native-height-basis-r13-v4b'
assert not DEST.exists()
source = json.loads((BASE / 'original-priority.json').read_bytes())
geometry = json.loads((BASE / 'original-priority_geometry_plan.json').read_bytes())
declarations = {row['id']: row for row in geometry['declarations']}
rows = {}
for label, height in (('h_vnw', Fraction(44, 63)), ('l_vnw', Fraction(5, 36))):
    declaration = declarations['native_direct_' + label]
    projection = declaration['projection']
    origin = tuple(projection['origin'])
    expected = {tuple(origin[i] + pos[i] for i in range(3)): value for pos, value in declaration['source_cells']}
    checks = []
    for route in ('native_direct', 'native_palette'):
        state = source['states'][route + '_' + label]
        for point in ('before', 'after'):
            for side in ('client', 'server'):
                cells = state[point][side]['cells']
                actual = {tuple(cell['pos']): cell['foreground'] for cell in cells if cell['foreground'][0] != 'minecraft:air'}
                assert len(cells) == 36 and actual == expected
                assert all(cell['background'] == ['minecraft:air', 0] and not cell['actor'] for cell in cells)
                checks.append({'route': route, 'point': point, 'side': side, 'cells': 36,
                               'nonair': [cell for cell in cells if cell['foreground'][0] != 'minecraft:air'],
                               'exact_two_source_cells_background_air_no_actor': True})
    builtin = oracle.builtin_geometry(declaration['source_id'])
    code = int(height * 255 + Fraction(1, 2))
    assert builtin['surfaces'][0]['heights'] == [code] * 4
    points = [(3 + x, 3 + code / 255., 3 + z) for x, z in ((0, 0), (1, 0), (1, 1), (0, 1))]
    fixed_xy = oracle.project(points, projection)
    rational_xy = oracle.project([(x, 3 + float(height), z) for x, unused, z in points], projection)
    # These are already measured stone-calibration endpoints, not new fit results.
    endpoint_xy = oracle.project(points, dict(projection, vertical_fov=66.3))
    pairs = source['states']['full_' + label]['before']['groups']
    for group in pairs:
        assert group['uniforms'][1][:2] == [float(code * 257)] * 2
    rows[label] = {'neighborhood_checks': checks, 'candidate_height_rational': str(height),
                  'candidate_height_world': float(height), 'byte_code': code, 'payload_height_world': code / 255.,
                  'payload_world_error': abs(float(height) - code / 255.),
                  'height_quantization_max_top_corner_screen_error_pixels': float(abs(rational_xy - fixed_xy).max()),
                  'already_calibrated_66_3_vs_fixed_66_6_max_corner_screen_sensitivity_pixels': float(abs(endpoint_xy - fixed_xy).max()),
                  'full_published_uniforms_match_byte': True,
                  'native_mesh_height_independently_observed': False}
files = []
paths = [ROOT / '.runtime/audit_liquid_near_height_basis_v4b.py',
         ROOT / 'tools/analyze_liquid_sides.py', ROOT / 'behavior_pack/modern_projection/projection/liquid_shape.py',
         ROOT / 'behavior_pack/modern_projection/projection/liquid_shape_data.py',
         ROOT / 'tools/data/native_liquid_shape_candidate_nemc_3.9.0.401155.json',
         ROOT / 'tools/data/native_liquid_neighbor_shape_nemc_3.9.0.401155.json',
         Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/data/shaders/glsl/renderchunk_water_near.vertex'),
         Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/data/resource_packs/vanilla_netease/materials/terrain.material')]
for number, path in enumerate(paths):
    destination = DEST / 'sources' / (str(number) + '-' + path.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)
    files.append({'original_path': str(path), 'archive_path': destination.relative_to(DEST).as_posix(),
                  'bytes': destination.stat().st_size, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
result = {'schema': 1, 'scope': 'Post-capture saved-input rule/payload/sensitivity audit; no image fit or new acceptance',
          'original_archive_manifest': visibility.reference(BASE / 'archive-index.json'),
          'original_source': visibility.reference(BASE / 'original-priority.json'),
          'original_geometry': visibility.reference(BASE / 'original-priority_geometry_plan.json'),
          'cases': rows, 'source_files': files,
          'shader_wave_activity_proven': False, 'unique_boundary_cause_identified': False,
          'side_uv_qualified': False, 'animation_qualified': False,
          'transparency_qualified': False, 'production_qualified': False}
(DEST / 'audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
print(json.dumps({key: {field: value for field, value in row.items() if field != 'neighborhood_checks'} for key, row in rows.items()}))
