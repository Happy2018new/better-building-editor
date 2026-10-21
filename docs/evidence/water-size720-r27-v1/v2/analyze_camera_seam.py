"""Read-only cause isolation of the failed cube silhouette; no gate adjustment."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent


def main():
    names = ('product-v2-camera-native-v1_tilted_shown.png',
             'product-v2-camera-native-v1_tilted_hidden.png',
             'product-v2-camera-native-v1_tilted_signal.png',
             'product-v2-camera-native-v1.json')
    source = {name: hashlib.sha256((WORK / name).read_bytes()).hexdigest() for name in names}
    shown, hidden, mask = [Image.open(WORK / name).convert('RGB' if index < 2 else 'L')
                           for index, name in enumerate(names[:3])]
    rows = []
    for y in range(333, 346):
        original = selected = contribution = 0
        for x in range(595, 686):
            pixel, control = shown.getpixel((x, y)), hidden.getpixel((x, y))
            changed = max(abs(a-b) for a, b in zip(pixel, control)) > 20
            neutral = max(pixel)-min(pixel) < 13 and pixel[0] > 50
            original += bool(changed and neutral)
            contribution += changed
            selected += bool(mask.getpixel((x, y)))
        rows.append({'y': y, 'neutral_and_difference_pixels': original,
                     'difference_pixels': contribution, 'retained_signal_pixels': selected,
                     'shown_rgb_at_x640': shown.getpixel((640, y))})
    report = json.loads((WORK / names[-1]).read_bytes())
    tilted = report['views'][2]
    result = {'schema': 1, 'diagnostic_only': True, 'source_sha256': source,
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'original_camera_passed': report['passed'], 'limits_unchanged': True,
              'original_fit': tilted['fit'], 'rows': rows,
              'observed': 'One full non-neutral raster row disconnects the visible top from the front; largest_component retains only the front.',
              'limitations': ['No causal claim about water callback gaps.',
                              'No correction of the original camera result.',
                              'No new same-session world-camera qualification.'],
              'editor_only_contract': {'path': 'tools/probe_product_water.py',
                  'sha256': hashlib.sha256((ROOT / 'tools/probe_product_water.py').read_bytes()).hexdigest(),
                  'camera_required_condition': "if set(routes) - {'editor'}",
                  'editor_burst_guard': 'same scene_capture_state before and after; native burst validates physical window geometry'},
              'manual_closures_added': 0}
    assert rows[6]['neutral_and_difference_pixels'] == 0
    assert rows[6]['difference_pixels'] > 0
    assert rows[5]['retained_signal_pixels'] == 0
    assert rows[7]['retained_signal_pixels'] > 0
    with (WORK / 'camera-seam-readonly-v2.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'diagnostic_only': True, 'row339_neutral_pixels': rows[6]['neutral_and_difference_pixels'],
                      'original_passed': report['passed']}))


if __name__ == '__main__':
    main()
