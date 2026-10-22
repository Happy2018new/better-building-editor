"""Narrow comparison of existing originals only; no launch or new pixel gate."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R28 = HERE.with_name('button-shift-lifecycle-v4') / 'check'
R27 = ROOT / '.runtime/round-20261022/transforms-lineage-runtime-v4/check'
ROI = (577, 242, 714, 452)  # Existing shift diagnostic's original ROI, unchanged.
BACKGROUND = (247, 249, 252)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


paths = {key: R28 / (name + '.png') for key, name in (
    ('combined', 'button_pair_full_baseline'), ('support_before', 'button_pair_support_before'),
    ('support_after', 'button_pair_support_after'), ('restored', 'button_pair_original_source_restored'))}
paths['old_single'] = R27 / 'pair_B_single_y3.png'
original_hashes = {key: sha(path) for key, path in paths.items()}
images = {key: Image.open(path).convert('RGB') for key, path in paths.items()}
assert all(image.size == (1280, 720) for image in images.values())
assert images['combined'].crop(ROI).tobytes() == images['restored'].crop(ROI).tobytes()
assert images['support_before'].crop(ROI).tobytes() == images['support_after'].crop(ROI).tobytes()
changed, high, silhouette = [], [], set()
for y in range(ROI[1], ROI[3]):
    for x in range(ROI[0], ROI[2]):
        point = (x, y)
        delta = max(abs(images['combined'].getpixel(point)[i] - images['support_before'].getpixel(point)[i]) for i in range(3))
        if delta:
            changed.append((point, delta))
        if delta > 12:
            high.append(point)
        if max(abs(images['old_single'].getpixel(point)[i] - BACKGROUND[i]) for i in range(3)) > 20:
            silhouette.add(point)


def bbox(points):
    return [min(point[0] for point in points), min(point[1] for point in points),
        max(point[0] for point in points) + 1, max(point[1] for point in points) + 1]


assert len(changed) == 264 and len(high) == 82
assert len(silhouette) == 758 and set(high) <= silhouette
report = json.loads((R27 / 'report.json').read_bytes())['button_pair']
native_inputs = []
for stage in report['stages']:
    native_inputs.append({'label': stage['label'], 'actual_button': stage['button'], 'actual_support': stage['support']})
assert all(row['actual_button']['native_volume'] == [16, 16, 10]
    and row['actual_button']['native_index'] == 827 and row['actual_button']['material'] == ['minecraft:stone_button', 0]
    for row in native_inputs)
result = {
    'scope': 'OFFLINE_NARROW_COMPARISON_OF_EXISTING_ORIGINALS',
    'source_commit_R28_shift': '2ab5a29a', 'ROI': list(ROI),
    'input_sha256': {str(paths[key].relative_to(ROOT)): digest for key, digest in original_hashes.items()},
    'combined_vs_support': {'nonzero_pixels': len(changed), 'pixels_gt12': len(high),
        'maximum_channel_difference': max(delta for point, delta in changed),
        'all_nonzero_bbox': bbox([point for point, delta in changed]),
        'all_gt12_inside_R27_single_silhouette': True,
        'R27_single_silhouette_pixels': len(silhouette), 'R27_single_silhouette_bbox': bbox(silhouette)},
    'repeatability_controls': {'combined_equals_original_restored_exact_ROI': True,
        'support_before_equals_support_after_exact_ROI': True,
        'restored_vs_after_has_identical_difference': True},
    'R27_actual_same_volume_and_indices': native_inputs,
    'conclusion': 'Combined rendering has a repeatable low-contrast contribution at the prior single-button silhouette. Complete absence of button output is not supported by these originals. Correct mounting, depth, thickness and expected vanilla appearance remain unqualified.',
    'not_a_new_acceptance_gate': True, 'manual_issues_closed': 0,
    'MC_started': False, 'native_mesh_qualified': False, 'native_attachment_qualified': False,
    'proposal_only': {
        'minimum_discriminating_input': 'Change support at native index1083 from minecraft:stone aux0 to fully opaque minecraft:white_concrete aux0; leave stone_button index827/aux0, volume(16,16,10), flags, native pose, slot, layout, source and original captures fixed.',
        'contrast_control': 'Compare combined versus support-only for each support material. The sole material axis is support color; original button data never changes. A clearer complete button against white weakens the visual-absence claim and isolates low contrast from continued combined-model depth/culling investigation.',
        'avoid_redundancy': 'Do not repeat same-volume button-only vs combined as a new discovery: R27 already submitted the same volume and button index in full/single/full. Do not repeat support-only shift as a button-rendered shift: R28 explicitly did not draw the button there.',
        'limits': 'Different native support material may also affect native lighting/culling. This is a bounded discriminator, not by itself proof of exact vanilla geometry. Root must review and grant any future MC run separately.'},
}
with (HERE / 'analysis.json').open('x', encoding='utf8') as output:
    json.dump(result, output, ensure_ascii=False, indent=2)
    output.write('\n')
crop = (606, 345, 685, 422)
contact = Image.new('RGB', (79 * 4 * 3, 77 * 4 + 45), 'white')
draw = ImageDraw.Draw(contact)
for index, (key, label) in enumerate((('combined', 'R28 COMBINED'), ('support_before', 'R28 SUPPORT ONLY'), ('old_single', 'R27 SINGLE BUTTON'))):
    draw.text((index * 316 + 6, 6), label, fill='black')
    draw.text((index * 316 + 6, 23), '4x nearest derivative; originals retained', fill='black')
    contact.paste(images[key].crop(crop).resize((316, 308), Image.Resampling.NEAREST), (index * 316, 45))
contact.save(HERE / 'comparison-4x-nearest-derivative.png')
assert all(sha(paths[key]) == digest for key, digest in original_hashes.items())
print(json.dumps({'nonzero': len(changed), 'gt12': len(high), 'all_gt12_inside_old_button': True,
    'analysis_sha256': sha(HERE / 'analysis.json'), 'new_MC_started': False}))
