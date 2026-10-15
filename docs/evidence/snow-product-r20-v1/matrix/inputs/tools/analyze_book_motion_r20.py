"""Measure white fragments enclosed by brown covers in an owned native burst.

This is a diagnostic for the R19 moving-cover failure, not product admission.
Normal page silhouettes and exterior white background are excluded by requiring
brown artwork on a ring around each bright, nearly neutral fragment.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_book_surface_r17 import cover_pixels, isolated_cover_pixels, MAX_ISOLATED_PIXELS, ENGINE_VERSION


def white_cover_fragments(pixels):
    pixels = np.asarray(pixels, dtype=np.int16)
    if min(pixels.shape[:2]) <= 2:
        raise ValueError('A cover diagnostic needs a nonempty neighborhood')
    center = pixels[1:-1, 1:-1]
    bright = (np.min(center, axis=2) >= 120) & (np.ptp(center, axis=2) <= 45)
    mask = np.zeros(pixels.shape[:2], dtype=bool)
    mask[1:-1, 1:-1] = bright & isolated_cover_pixels(pixels)
    return mask


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local(directory, name):
    result = (directory/name).resolve(strict=True)
    if not result.is_relative_to(directory.resolve()):
        raise ValueError('Burst frame path escapes its directory')
    return result


def analyze(source, output):
    report = json.loads(source.read_bytes())
    if len(report['routes']) != 1:
        raise ValueError('Expected one book motion route')
    label, route = next(iter(report['routes'].items()))
    capture = route['capture']
    directory = source.parent/label
    manifest_path = directory/'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    recorded = capture['native_manifest_file']
    if _digest(manifest_path) != recorded['sha256']:
        raise ValueError('Burst manifest differs from its source receipt')
    hashes = {Path(item['path']).name: item['sha256'] for item in capture['artifacts']}
    rows, crops, counts, isolated_counts, crop_hashes = [], [], [], [], []
    for frame in manifest['frames']:
        if not frame.get('capture_valid'):
            continue
        path = _local(directory, frame['png'])
        if _digest(path) != hashes[path.name]:
            raise ValueError('Burst pixels differ from their source receipt: '+path.name)
        with Image.open(path) as original:
            width, height = original.size
            bounds = (width//2-150, height//2-150, width//2+150, height//2+90)
            crop = original.convert('RGB').crop(bounds)
        pixels = np.asarray(crop, dtype=np.int16)
        mask = white_cover_fragments(pixels)
        cover = int(cover_pixels(pixels).sum())
        count = int(mask.sum())
        isolated = int(isolated_cover_pixels(pixels).sum())
        rows.append({'sequence': frame['sequence'], 'png': frame['png'],
                     'frame_qpc_100ns': frame['frame_qpc_100ns'],
                     'cover_pixels': cover, 'white_cover_fragments': count,
                     'isolated_cover_pixels': isolated})
        counts.append(count)
        isolated_counts.append(isolated)
        crop_hashes.append(hashlib.sha256(crop.tobytes()).hexdigest())
        crops.append((count, frame['sequence'], crop, mask))
    trace = route.get('trace', {})
    trace_rows = trace.get('rows', [])
    owner_states = {json.dumps(row[5], sort_keys=True) for row in trace_rows}
    camera_states = {json.dumps(row[1:3], sort_keys=True) for row in trace_rows}
    timestamps = [row['frame_qpc_100ns'] for row in rows]
    duration = (max(timestamps)-min(timestamps))/1e7 if timestamps else 0.
    source_unchanged = (report.get('source_unchanged') is True and
                        report.get('source_before') == report.get('source_after'))
    source_is_editor = label.startswith('editor_')
    checks = {
        'report_identity': report.get('schema_version') == 1 and report.get('engine') == ENGINE_VERSION,
        'completed': report.get('completed') is True,
        'restored': report.get('restored') is True and report.get('cleanup_errors') == [],
        'source_unchanged': source_unchanged,
        'alias_source_unchanged': not report.get('alias_sources') or
                                   (report.get('alias_source_unchanged') is True and
                                    report['alias_sources'] == report.get('alias_sources_after')),
        'native_capture': all(capture.get(key) is True for key in
                              ('capture_valid', 'temporal_complete', 'native_resolution')) and
                          capture.get('activation_fallback') is False,
        'manifest_frame_count': len(rows) == manifest['valid_frames'] and len(rows) >= 16,
        'timestamps_increase': all(b > a for a, b in zip(timestamps, timestamps[1:])),
        'visible_book_content': bool(rows) and min(row['cover_pixels'] for row in rows) >= 20 and
                                max(row['cover_pixels'] for row in rows) >= 500,
        'fixed_camera': route.get('fixed_camera') is True and
                        (not source_is_editor or len(camera_states) == 1),
        'stable_owner': not source_is_editor or
                        (len(owner_states) == 1 and bool(trace_rows) and not trace.get('overflow')),
        'motion_content_changes': route.get('frozen') is True or len(set(crop_hashes)) >= 16,
        'full_rotation': route.get('frozen') is True or duration >= 16.,
    }
    frozen_unchanged = len(set(crop_hashes)) == 1 if route.get('frozen') else None
    measured_gaps = ([timestamps[0]-manifest['request_qpc_100ns']]+
                     [b-a for a, b in zip(timestamps, timestamps[1:])]+
                     [manifest['planned_end_qpc_100ns']-timestamps[-1]]) if timestamps else []
    top = sorted(crops, key=lambda row: (-row[0], row[1]))[:12]
    sheet = Image.new('RGB', (300*4, 264*3), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, (count, sequence, crop, mask) in enumerate(top):
        x, y = (index % 4)*300, (index//4)*264
        sheet.paste(crop, (x, y+24))
        draw.text((x+4, y+5), 'frame %d: %d white fragments' % (sequence, count), fill='black')
        points = np.argwhere(mask)
        for py, px in points:
            draw.rectangle((x+int(px)-2, y+24+int(py)-2,
                            x+int(px)+2, y+24+int(py)+2), outline='magenta')
    sheet_path = output.with_suffix('.png')
    sheet.save(sheet_path)
    diagnostic_valid = all(checks.values())
    dense_passed = (diagnostic_valid and label == 'editor_active' and route.get('frozen') is False and
                    not report.get('alias_sources') and
                    manifest['planned_duration_ms'] >= 17000 and manifest['max_gap_ms'] <= 250 and
                    manifest['maximum_gap_100ns'] <= 2500000 and
                    bool(measured_gaps) and min(measured_gaps) >= 0 and max(measured_gaps) <= 2500000 and
                    max(isolated_counts, default=MAX_ISOLATED_PIXELS+1) <= MAX_ISOLATED_PIXELS)
    result = {'schema': 1, 'source': str(source.resolve()), 'source_sha256': _digest(source),
              'analyzer_sha256': _digest(Path(__file__)), 'product_qualified': False,
              'scope': 'White fragments enclosed by cover artwork; no pose, brightness or product acceptance.',
              'checks': checks, 'diagnostic_valid': diagnostic_valid,
              'dense_cover_motion_passed': dense_passed,
              'frame_count': len(rows), 'duration_seconds': duration,
              'maximum_measured_gap_ms': max(measured_gaps, default=0)/1e4,
              'maximum_white_cover_fragments': max(counts, default=0),
              'maximum_isolated_cover_pixels': max(isolated_counts, default=0),
              'maximum_allowed_isolated_pixels': MAX_ISOLATED_PIXELS,
              'frames_with_white_cover_fragments': sum(count > 0 for count in counts),
              'frozen_crop_unchanged': frozen_unchanged, 'distinct_crop_count': len(set(crop_hashes)),
              'contact_sheet': str(sheet_path.resolve()), 'rows': rows}
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii')
    print(json.dumps({key: value for key, value in result.items() if key not in
                      ('rows', 'scope', 'source', 'source_sha256', 'analyzer_sha256')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.source, args.output)
