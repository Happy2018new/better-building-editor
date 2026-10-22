"""Offline measurements of immutable actual V3 frames and typed model inputs."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE / 'closeout-v1/analysis'
OUT.mkdir(parents=True, exist_ok=False)
ROI = (577, 242, 714, 452)
sys.path.insert(0, str(HERE.with_name('transforms-cache-lineage-v5')))
from lineage_host import decode


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    with (OUT / name).open('x', encoding='utf8') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def difference(a, b):
    raw = np.abs(np.asarray(images[a], dtype=np.int16) - np.asarray(images[b], dtype=np.int16))
    changed = np.any(raw, axis=2)
    ys, xs = np.where(changed)
    return {'changed_pixels': int(changed.sum()),
        'changed_bbox_in_original_image': [int(xs.min()) + ROI[0], int(ys.min()) + ROI[1],
            int(xs.max()) + ROI[0] + 1, int(ys.max()) + ROI[1] + 1] if len(xs) else None,
        'maximum_channel_delta': int(raw.max()), 'sum_absolute_channel_delta': int(raw.sum()),
        'mean_absolute_channel_delta_over_whole_ROI': float(raw.mean())}


report = json.loads((HERE / 'check/report.json').read_bytes())
pair = report['button_separate']
assert report['completed'] and report['restored'] and report['source_unchanged']
assert pair['completed'] and len(pair['stages']) == 6 and len(pair['creations']) == 4
images, originals = {}, {}
for label in ('full_baseline', 'a_combined_stone', 'a_support_stone', 'b_combined_white',
        'b_support_white', 'a2_combined_stone', 'a2_support_stone', 'original_source_restored'):
    path = HERE / ('check/button_pair_' + label + '.png')
    original = Image.open(path).convert('RGB')
    assert original.size == (1280, 720)
    images[label] = original.crop(ROI)
    originals[label] = {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size,
        'original_size': list(original.size), 'ROI': list(ROI)}
    images[label].resize((411, 630), Image.Resampling.NEAREST).save(OUT / (label + '-ROI-nearest3x.png'))
comparisons = [('a_combined_stone', 'a_support_stone'), ('b_combined_white', 'b_support_white'),
    ('a2_combined_stone', 'a2_support_stone'), ('a_combined_stone', 'b_combined_white'),
    ('a_support_stone', 'b_support_white'), ('a_combined_stone', 'a2_combined_stone'),
    ('a_support_stone', 'a2_support_stone'), ('full_baseline', 'original_source_restored'),
    ('full_baseline', 'a_combined_stone'), ('a2_combined_stone', 'original_source_restored')]
metrics = {a + '__vs__' + b: difference(a, b) for a, b in comparisons}
for a, b in comparisons[:3]:
    raw = np.any(np.asarray(images[a]) != np.asarray(images[b]), axis=2)
    mask = Image.fromarray((raw * 255).astype(np.uint8), mode='L').convert('RGB')
    mask.resize((411, 630), Image.Resampling.NEAREST).save(OUT / (a + '__minus__' + b + '-mask3x.png'))

decoded = {}
model_rows = []
for row in pair['creations']:
    expected, actual = decode(row['deserialize_input']), decode(row['native_serialized'])
    assert expected == actual and row['name'] == row['result'] and row['unsupported_mode'] == 0
    decoded[row['label']] = actual
    model_rows.append({'label': row['label'], 'name': row['name'], 'result': row['result'],
        'unsupported_mode': row['unsupported_mode'], 'Deserialize_input_equals_Serialize_result': True,
        'native_serialized_wire_sha256': hashlib.sha256(json.dumps(row['native_serialized'], sort_keys=True).encode()).hexdigest(),
        'common': [{'block': key[0].decode('ascii'), 'aux': key[1], 'indices': indices}
            for key, indices in sorted(actual[b'common'].items())],
        'states': [{'block': key[0].decode('ascii'), 'aux': key[1],
            'properties': {k.decode('ascii'): v for k, v in values.items()}}
            for key, values in sorted(actual[b'states'].items())],
        'volume': list(actual[b'volume']), 'eliminateAir': actual[b'eliminateAir'], 'void': actual[b'void']})
for material in ('stone', 'white'):
    combined, support = decoded['combined_' + material], decoded['support_' + material]
    remainder = dict(combined)
    remainder[b'common'] = dict(combined[b'common'])
    remainder[b'states'] = dict(combined[b'states'])
    assert remainder[b'common'].pop((b'minecraft:stone_button', 0)) == [827]
    assert remainder[b'states'].pop((b'minecraft:stone_button', 0)) == {
        b'button_pressed_bit': False, b'facing_direction': 0}
    assert remainder == support
assert len({row['name'] for row in pair['creations']}) == 4
stage_rows = []
for row in pair['stages']:
    label, state = row['label'], row['latest_state']
    assert row['capture']['sha256'] == originals[label]['sha256']
    assert state['settled_gate'] and state['frame_opportunities'] >= 6 and .25 <= state['age'] <= 2.
    assert state['surface_visibility'] == [True, False]
    drawing, = state['stage']['drawings']
    assert drawing['slot'] == 0 and drawing['result'] is True
    assert drawing['params']['block_geometry_model_name'] == next(
        m['name'] for m in model_rows if m['label'] == drawing['model_label'])
    stage_rows.append({'label': label, 'model_label': drawing['model_label'],
        'actual_RenderBlockGeometryModel_name': drawing['params']['block_geometry_model_name'],
        'draw_result': drawing['result'], 'draw_params': drawing['params'],
        'frame_opportunities_at_latest_state': state['frame_opportunities'],
        'age_at_latest_state_seconds': state['age'], 'settled_gate': state['settled_gate'],
        'surface_visibility': state['surface_visibility'],
        'source_tint_setter_value': state['source_tint_setter_value'],
        'native_tint_uniform_readback': False, 'native_mesh_vertices_readback': False,
        'original_screenshot_sha256': row['capture']['sha256']})
assert stage_rows[0]['draw_params'] == stage_rows[4]['draw_params']
assert stage_rows[1]['draw_params'] == stage_rows[5]['draw_params']
write('pixel-analysis.json', {'scope': 'OFFLINE_ACTUAL_MATCHED_STAGE_PIXEL_MEASUREMENTS',
    'ROI': list(ROI), 'ROI_provenance': 'Same declared V2 object ROI, before V3 stage analysis',
    'originals': originals, 'comparisons': metrics, 'models': model_rows, 'stages': stage_rows,
    'combined_vs_support_only_native_difference': 'stone_button aux0 at827; unpressed facing0 states',
    'A_vs_B_only_native_material_change': 'stone aux0 -> white_concrete aux0 at1083',
    'A2_reuses_original_A_names_and_parameters': True,
    'pixel_qualification_or_native_mesh_readback': False, 'manual_issues_closed': 0,
    'limitations': ['Difference isolates the net image contribution of adding the button under this one controlled view',
        'No native mesh vertices, face material IDs, UVs or GPU tint uniform were read back',
        'Does not establish correct button thickness, contact, all faces or all poses',
        'Gray-white pixels alone do not identify the native material or shader path',
        'No direct change to product rendering, rotations or mirrors is qualified by this diagnostic']})
print(json.dumps({'ROI': list(ROI), 'comparisons': metrics, 'models': len(model_rows),
    'stages': len(stage_rows), 'manual_issues_closed': 0}))
