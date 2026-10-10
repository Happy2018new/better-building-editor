"""Validate a complete native export and replace only its separately verified bed states."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry, block_groups
from generate_block_traits import WATER_PROBE_METHOD, _water_rows

BASE_METHOD = ('Native default seed + semantic states and supported paired fixtures '
               'before/after over water, isLegacy=True, updateNeighbors=False; v4')
BED_METHOD = 'native head-first exact-aux bed pair before/after over water'


def load(path):
    data = json.loads(path.read_text(encoding='utf8'))
    return json.loads(data) if isinstance(data, str) else data


def merge(base_path, bed_path, output):
    base, bed = load(base_path), load(bed_path)
    for data, method in ((base, BASE_METHOD), (bed, BED_METHOD)):
        if (data.get('schema') != 1 or data.get('method') != method or
                data.get('game_version') != block_registry.source_version() or
                data.get('palette_sha256') != block_registry.fingerprint()):
            raise ValueError('Native evidence does not match the current palette and probe method')
    expected = set(block_registry.aux_values('minecraft:bed'))
    rows = bed.get('readback_states', {}).get('minecraft:bed', {})
    if (bed.get('tested_states') != len(expected) or bed.get('verified_states') != len(expected) or
            set(int(aux) for aux in rows) != expected or set(bed.get('blocks', {})) != {'minecraft:bed'}):
        raise ValueError('Supplemental bed evidence is incomplete')
    accepted = []
    for aux in sorted(expected):
        row = rows[str(aux)]
        value = ('minecraft:bed', aux)
        partner = block_groups.group_partner(value)[1]
        for field, material in (('dry', value), ('dry_partner', partner),
                                ('wet', value), ('wet_partner', partner)):
            actual = row.get(field)
            if (not actual or actual.get('front', {}).get('name') != material[0] or
                    actual.get('states') != block_registry.states(material)):
                raise ValueError('Supplemental bed readback mismatch: %d %s' % (aux, field))
        liquid = row['wet'].get('liquid')
        if liquid and liquid.get('name') == 'minecraft:water':
            accepted.append(aux)
    if bed['blocks']['minecraft:bed'] != accepted:
        raise ValueError('Bed capability summary does not match its native readback evidence')
    mismatches = base.get('state_mismatches', [])
    if (any(row.get('name') != 'minecraft:bed' or row.get('aux') not in expected for row in mismatches) or
            len(set(row['aux'] for row in mismatches)) != len(mismatches) or
            base.get('verified_states', 0) + len(mismatches) != base.get('tested_states')):
        raise ValueError('Base export contains unverified non-bed states or inconsistent verification counts')
    result = dict(base)
    result['blocks'] = dict(base['blocks'])
    result['blocks']['minecraft:bed'] = True if set(accepted) == expected else accepted or False
    result['readback_states'] = dict(base['readback_states'])
    result['readback_states']['minecraft:bed'] = rows
    result.update(method=WATER_PROBE_METHOD, verified_states=base['tested_states'],
                  state_mismatches=[], failure=None)
    result['evidence_sources'] = [
        {'file': base_path.name, 'sha256': hashlib.sha256(base_path.read_bytes()).hexdigest(),
         'method': BASE_METHOD, 'replaced_names': ['minecraft:bed']},
        {'file': bed_path.name, 'sha256': hashlib.sha256(bed_path.read_bytes()).hexdigest(),
         'method': BED_METHOD, 'verified_states': len(expected), 'replacement_names': ['minecraft:bed']}]
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    palette = json.loads((ROOT / manifest['source_file']).read_text(encoding='utf8'))
    _water_rows(result, {'game_version': block_registry.source_version(),
                         'palette_sha256': block_registry.fingerprint()}, palette)
    output.write_text(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n',
                      encoding='utf8')
    print('%d verified native states; %d head-first bed states replaced' %
          (result['verified_states'], len(expected)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('beds', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    merge(args.base, args.beds, args.output)
