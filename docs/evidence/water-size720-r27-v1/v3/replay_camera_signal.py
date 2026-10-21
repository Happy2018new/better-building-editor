"""Compare one contribution-supported seam repair on preserved native controls."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
import verify_camera_projection as camera


def candidate(shown, hidden):
    with Image.open(shown).convert('RGB') as image:
        red, green, blue = image.split()
        spread = camera.maximum(Image.merge('RGB', (ImageChops.difference(red, green),
            ImageChops.difference(red, blue), ImageChops.difference(green, blue))))
        mask = ImageChops.multiply(spread.point(lambda v: 255 if v < 13 else 0),
                                  red.point(lambda v: 255 if v > 50 else 0))
        center = Image.new('L', image.size)
        width, height = image.size
        ImageDraw.Draw(center).rectangle((width*.3, height*.25, width*.7, height*.75), fill=255)
        mask = ImageChops.multiply(mask, center)
    contribution = camera.maximum(camera.signal(shown, hidden)).point(lambda v: 255 if v > 20 else 0)
    seed = ImageChops.multiply(mask, contribution)
    closed = seed.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    # A joined pixel must actually differ from the hidden control; no analytical hull is used.
    joined = ImageChops.lighter(seed, ImageChops.multiply(closed, contribution))
    mask = camera.largest_component(joined)
    outline = camera.fill_enclosed_holes(mask).filter(ImageFilter.MedianFilter(3))
    outline = outline.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    assert ImageChops.multiply(outline, contribution).histogram()[255] >= 1000
    return outline


def main():
    files = [ROOT / '.runtime/round-20261022/water-size720-v2/product-v2-camera-native-v1.json',
             ROOT / '.runtime/round-20261021/trace-lifetime-v2/experiment-isolated-v1/product-v2-camera-native-v1.json']
    result = {'schema': 1, 'diagnostic_only': True, 'MC_started': False,
              'original_results_modified': False, 'world_qualification_granted': False,
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'cases': []}
    for path in files:
        report = json.loads(path.read_bytes())
        for row in report['views']:
            shown, hidden = Path(row['shown']['path']), Path(row['hidden']['path'])
            original = camera.stone_signal(shown, hidden)
            repaired = candidate(shown, hidden)
            original_fit = camera.fit_fov(original, row['pose'], report['vertical_fov'])
            repaired_fit = camera.fit_fov(repaired, row['pose'], report['vertical_fov'])
            fits = {}
            for label, fit in (('original', original_fit), ('candidate', repaired_fit)):
                fits[label] = {'fit': fit, 'passed_original_limits': fit['boundary_rms_pixels'] <= 2
                    and fit['mask_iou'] >= .95 and fit['outline_recall_2px'] >= .985
                    and fit['outline_precision_2px'] >= .985}
            result['cases'].append({'report_path': str(path), 'view': row['view'],
                'resolution': list(original.size), 'report_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'shown_sha256': hashlib.sha256(shown.read_bytes()).hexdigest(),
                'hidden_sha256': hashlib.sha256(hidden.read_bytes()).hexdigest(), **fits})
    # An unchanged screenshot cannot acquire a fabricated signal through closing.
    shown = Path(json.loads(files[0].read_bytes())['views'][0]['shown']['path'])
    try:
        candidate(shown, shown)
    except (AssertionError, ValueError) as error:
        result['unchanged_control_rejected'] = True
    else:
        raise AssertionError('Zero contribution control was fabricated')
    with (WORK / 'camera-signal-replay-v1.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'cases': len(result['cases']),
        'original_passed': sum(c['original']['passed_original_limits'] for c in result['cases']),
        'candidate_passed': sum(c['candidate']['passed_original_limits'] for c in result['cases']),
        'unchanged_control_rejected': result['unchanged_control_rejected']}))


if __name__ == '__main__':
    main()
