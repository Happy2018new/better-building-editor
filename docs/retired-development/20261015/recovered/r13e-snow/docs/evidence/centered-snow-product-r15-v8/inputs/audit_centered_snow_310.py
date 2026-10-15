"""Read-only native resource audit; does not claim runtime or pixel support."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from generate_centered_plant_profiles import PROFILE, snapshot

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

native = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/resource_packs/vanilla')
original = json.loads(PROFILE.read_bytes())
candidate = snapshot(native)
rows = []
for name in sorted(original['plants']):
    old, new = original['plants'][name], candidate['plants'][name]
    rows.append({'plant': name, 'path': new['texture_path'],
                 'texture_sha256': new['texture_sha256'],
                 'texture_path_equal': old['texture_path'] == new['texture_path'],
                 'texture_bytes_equal': old['texture_sha256'] == new['texture_sha256'],
                 'definition_equal': old['definition'] == new['definition'],
                 'atlas_record_equal': old['atlas_record'] == new['atlas_record'],
                 'alpha_bounds_equal': old['alpha_bounds'] == new['alpha_bounds'],
                 'mesh_equal': old['mesh'] == new['mesh']})
report = {'schema': 1, 'resource_version': 'NEMC 3.10.0.420447',
          'registry_version_unchanged': original['game_version'],
          'registry_palette_sha256_unchanged': original['palette_sha256'],
          'original_profile_sha256': sha(PROFILE),
          'audit_tool_sha256': sha(Path(__file__)),
          'method': 'Read-only generator snapshot and field-by-field comparison; no dump, runtime or pixel calls',
          'actual_runtime_support_accepted': False, 'production_profile_updated': False,
          'candidate_source_sha256': candidate['source_sha256'],
          'whole_blocks_json_equal': original['source_sha256']['blocks'] == candidate['source_sha256']['blocks'],
          'whole_terrain_json_equal': original['source_sha256']['terrain'] == candidate['source_sha256']['terrain'],
          'rows': rows}
output = ROOT/'docs/evidence/centered-snow-resources-nemc-310.json'
output.write_text(json.dumps(report, ensure_ascii=True, indent=2)+'\n', encoding='ascii')
print(json.dumps({key: report[key] for key in ('resource_version','whole_blocks_json_equal','whole_terrain_json_equal')}))
print(json.dumps({'plants': len(rows), 'differing_fields': [row for row in rows if not all(row[key] for key in
      ('texture_path_equal','texture_bytes_equal','definition_equal','atlas_record_equal','alpha_bounds_equal','mesh_equal'))]}))
