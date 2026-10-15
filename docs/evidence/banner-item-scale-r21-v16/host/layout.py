"""Estimate scale-one screen bounds from existing native pixels; no runtime calls."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PRIOR = ROOT / '.runtime/banner-pose-v14b-amendment-r21-v1'


def colored_bbox(image, box):
    points = []
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            rgb = image.getpixel((x, y))[:3]
            if max(rgb) - min(rgb) > 25 and max(rgb) > 70:
                points.append((x, y))
    assert points
    return [min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points) + 1, max(point[1] for point in points) + 1]


def estimate():
    image = Image.open(PRIOR / 'runtime-images/03-bound-yaw90.png').convert('RGB')
    source = json.loads((PRIOR / 'runtime-receipts/003-banner-client-mount.json').read_bytes())['result']
    # Zero-pose host copies have x centers .5, 2.5, 4.5, 6.5 and y center .5.
    body = Image.open(PRIOR / 'runtime-images/01-unbound-negative.png').convert('RGB')
    first = colored_bbox(body, (510, 640, 555, 690))
    second = colored_bbox(body, (630, 640, 680, 690))
    centers = [(first[0] + first[2] - 1) / 2., (second[0] + second[2] - 1) / 2.]
    pixels_per_unit = (centers[1] - centers[0]) / 2.
    root = [centers[0] - .5 * pixels_per_unit,
            (first[1] + first[3] - 1) / 2. + .5 * pixels_per_unit]
    rows = []
    for label, box, delta in (('plain', (490, 680, 550, 710), 0.),
                              ('patterned', (1450, 680, 1520, 710), 966.)):
        bounds = colored_bbox(image, box)
        pivot = [root[0] + delta, root[1]]
        enlarged = [pivot[index % 2] + 16. * (value - pivot[index % 2])
                    for index, value in enumerate(bounds)]
        # A two-pixel pivot uncertainty is amplified by fifteen in this extrapolation.
        margin = 32.
        conservative = [enlarged[0] - margin, enlarged[1] - margin,
                        enlarged[2] + margin, enlarged[3] + margin]
        rows.append({'label': label, 'old_bbox_pixels': bounds, 'estimated_root_pixels': pivot,
            'scale_one_estimated_bbox_pixels': enlarged,
            'scale_one_conservative_bbox_pixels': conservative,
            'inside_screen_conservatively': conservative[0] >= 0 and conservative[1] >= 0 and
                conservative[2] <= image.width and conservative[3] <= image.height})
    selected = [rows[1]['scale_one_conservative_bbox_pixels'][0] - 966.,
                rows[1]['scale_one_conservative_bbox_pixels'][1],
                rows[1]['scale_one_conservative_bbox_pixels'][2] - 966.,
                rows[1]['scale_one_conservative_bbox_pixels'][3]]
    return {'offline_only': True, 'native_size': list(image.size), 'old_layout': source,
        'host_first_bbox': first, 'host_second_bbox': second, 'pixels_per_model_unit': pixels_per_unit,
        'estimated_root_left_slot': root, 'scale_ratio': 16., 'rows': rows,
        'selected_slot': 'existing left slot, patterned item only',
        'selected_conservative_bbox_pixels': selected,
        'selected_inside_screen_conservatively': selected[0] >= 0 and selected[1] >= 0 and
            selected[2] <= image.width and selected[3] <= image.height,
        'approximate_left_doll_box_pixels': [32., 354., 974., 1064.],
        'selected_can_exceed_doll_control_right_edge': selected[2] > 974.,
        'single_patterned_reuses_left_slot_geometry': True,
        'left_slot_estimate_uses_plain_geometry_and_same_sized_patterned_native_item': True,
        'native_internal_item_root_assumed_invariant_under_uniform_scale': True,
        'prediction_is_not_runtime_fit_or_actual_pixel_acceptance': True,
        'paper_doll_template': 'PyreactBase.paperDoll', 'screen_scale': 1.,
        'explicit_enable_scissor_test': False,
        'no_runtime_claim_about_implicit_native_clipping': True}


if __name__ == '__main__':
    print(json.dumps(estimate(), indent=2))
