"""Reproduce a failed sign mask offline without changing its acceptance result."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from verify_sign_visuals import colored_text, shape_match


def file_record(path):
    path = Path(path)
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def samples(case, scope):
    rows = case['samples']
    if scope == 'native':
        return rows['native_shown'], rows['native_blank']
    return rows[scope + '_shown']['screenshot'], rows[scope + '_blank']['screenshot']


def diagnose(case, scope, output):
    shown, blank = samples(case, scope)
    recorded = case[scope]
    crop = tuple(recorded['crop'])
    mask, repeated = colored_text(shown['path'], blank['path'], crop, recorded['color'],
                                 output / (scope + '_original_mask.png'),
                                 recorded['response'] == 'wood_composite')
    composite, composite_stats = colored_text(shown['path'], blank['path'], crop, recorded['color'],
                                             output / (scope + '_wood_composite_diagnostic.png'), True)
    absolute, absolute_stats = colored_text(shown['path'], blank['path'], crop, recorded['color'],
                                           output / (scope + '_absolute_delta_diagnostic.png'), False)
    with Image.open(shown['path']) as first, Image.open(blank['path']) as second:
        image = first.convert('RGB').crop(crop)
        baseline = second.convert('RGB').crop(crop)
    delta = ImageChops.difference(image, baseline)
    selected_index = 1 if recorded['color'] == 'green' else 0
    other_indices = [axis for axis in range(3) if axis != selected_index]
    colors = Counter()
    selected_dark_pairs = Counter()
    intensity = Counter()
    bright_rows = []
    for pixel, base, difference, selected in zip(image.getdata(), baseline.getdata(), delta.getdata(), mask.getdata()):
        if selected:
            colors[pixel] += 1
            intensity['0_to_64' if pixel[selected_index] <= 64 else
                      '65_to_128' if pixel[selected_index] <= 128 else '129_to_255'] += 1
            if pixel[selected_index] <= 64:
                selected_dark_pairs[(pixel, base)] += 1
        bright_rows.append(255 if max(difference) > 20 and pixel[selected_index] > 128 and
                           pixel[selected_index] - max(pixel[axis] for axis in other_indices) > 20 else 0)
    bright = Image.new('L', image.size)
    bright.putdata(bright_rows)
    bright.save(output / (scope + '_bright_glyph_diagnostic.png'))
    with Image.open(recorded['mask']) as saved:
        equal = saved.convert('L').size == mask.size and not ImageChops.difference(saved.convert('L'), mask).getbbox()
    result = {
        'recorded_pixels': recorded['pixels'], 'reproduced_pixels': repeated['pixels'],
        'recorded_bounds': recorded['bounds'], 'reproduced_bounds': repeated['bounds'],
        'original_mask_reproduced_exactly': equal,
        'original_mask_selected_channel_intensity': dict(intensity),
        'most_common_original_mask_shown_colors': [{'rgb': rgb, 'pixels': count}
                                                   for rgb, count in colors.most_common(12)],
        'most_common_original_mask_dark_shown_blank_pairs': [
            {'shown_rgb': pair[0], 'blank_rgb': pair[1], 'pixels': count}
            for pair, count in selected_dark_pairs.most_common(12)],
        'bright_diagnostic_pixels': bright.histogram()[255], 'bright_diagnostic_bounds': bright.getbbox(),
        'wood_composite_diagnostic': composite_stats,
        'absolute_delta_diagnostic': absolute_stats,
        'sources': [file_record(shown['path']), file_record(blank['path']), file_record(recorded['mask'])],
        'original_gate': recorded.get('native_comparison'),
        'original_layout': recorded.get('layout_comparison'),
    }
    return result, image, mask, bright, composite, baseline, absolute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    original = json.loads(args.report.read_text(encoding='utf-8'))
    assert len(original['cases']) == 1, 'Select a report containing one preserved failure'
    case = original['cases'][0]
    results = {scope: diagnose(case, scope, args.output) for scope in ('native', 'editor', 'projection')}
    report = {
        'schema': 1, 'read_only_game': True, 'source': file_record(args.report),
        'original_completed': original['completed'], 'original_passed': original['passed'],
        'visual_acceptance': False, 'case': case['id'], 'view': case['view'],
        'diagnostic_only': 'Bright selected channel >128 and selected-minus-other >20; original masks and .45 IoU gate unchanged.',
        'scopes': {scope: value[0] for scope, value in results.items()},
        'bright_diagnostic_normalized_iou': {
            scope: shape_match(results['native'][3], results[scope][3])['normalized_glyph_iou']
            for scope in ('editor', 'projection')},
        'wood_composite_diagnostic_comparison': {
            scope: shape_match(results['native'][4], results[scope][4])
            for scope in ('editor', 'projection')},
        'absolute_delta_diagnostic_comparison': {
            scope: shape_match(results['native'][6], results[scope][6])
            for scope in ('editor', 'projection')},
        'controls': {
            'native_shown_blank_player': [case['samples']['native_' + key]['near_player']
                                         for key in ('shown', 'blank')],
            'native_capture_pose_limit': 'native_sample waited for the same target-relative pose each time, but the original report did not save the native settled pose or a style snapshot for each capture.',
            'editor_shown_blank_camera': [case['samples']['editor_' + key]['screenshot']['actual_hidden_controls']
                                         for key in ('shown', 'blank')],
            'editor_shown_blank_renderer': [case['samples']['editor_' + key]['renderer']
                                           for key in ('shown', 'blank')],
            'projection_shown_blank_pose': [case['samples']['projection_' + key]['pose']
                                           for key in ('shown', 'blank')],
            'native_style': next(row for row in original['native']['rows'] if row['name'] == 'minecraft:oak_hanging_sign'),
            'daylight_saved_before_setup': original['daylight'],
            'daylight_during_capture_from_harness': 'Clear noon, daylight_cycle=False, weather_cycle=False.',
            'capture_options': original['capture_options'],
        },
    }
    native_extra = ImageChops.subtract(results['native'][2], results['native'][3])
    projected_at_native_extra = Counter(pixel for pixel, selected in
                                        zip(results['projection'][1].getdata(), native_extra.getdata()) if selected)
    report['projection_colors_at_native_dark_outline_pixels'] = [
        {'rgb': rgb, 'pixels': count} for rgb, count in projected_at_native_extra.most_common(12)]
    report['bright_native_projection_full_crop_mask_equal'] = not ImageChops.difference(
        results['native'][3], results['projection'][3]).getbbox()
    report['wood_composite_native_projection_full_crop_mask_equal'] = not ImageChops.difference(
        results['native'][4], results['projection'][4]).getbbox()
    report['manually_inspected_body_regions'] = {}
    body_regions = {'native': (831, 504, 1164, 742), 'editor': (851, 555, 1161, 776),
                    'projection': (831, 504, 1164, 742)}
    for scope, region in body_regions.items():
        result, image, mask, bright, composite, baseline, absolute = results[scope]
        crop = case[scope]['crop']
        local = tuple(value - crop[axis % 2] for axis, value in enumerate(region))
        excluded = (458, 213, 609, 306) if scope == 'editor' else (175, 209, 338, 310)
        values = []
        for y in range(local[1], local[3]):
            for x in range(local[0], local[2]):
                if excluded[0] - 2 <= x < excluded[2] + 2 and excluded[1] - 2 <= y < excluded[3] + 2:
                    continue
                values.append(max(abs(a - b) for a, b in zip(image.getpixel((x, y)), baseline.getpixel((x, y)))))
        report['manually_inspected_body_regions'][scope] = {
            'absolute_region': region, 'basis': 'Visible straight body edges in preserved full native-resolution frames; diagnostic only.',
            'excluded_local_text_rectangle_with_2px_margin': excluded,
            'outside_text_pixels': len(values), 'maximum_channel_difference': max(values),
            'changed_pixels_over_original_20_delta': sum(value > 20 for value in values)}
    report['manual_body_mask_diagnostic'] = {}
    for scope in ('native', 'editor', 'projection'):
        crop = case[scope]['crop']
        body = body_regions[scope]
        local = tuple(value - crop[axis % 2] for axis, value in enumerate(body))
        raw = results[scope][4]
        body_mask = Image.new('L', raw.size)
        body_mask.paste(raw.crop(local), local)
        outside = ImageChops.subtract(raw, body_mask)
        panel = case[scope]['panel_bounds']
        inside_panel = Image.new('L', raw.size)
        if panel:
            inside_panel.paste(outside.crop(tuple(panel)), tuple(panel))
        report['manual_body_mask_diagnostic'][scope] = {
            'manual_actual_body_absolute': body, 'reported_panel_local': panel,
            'inside_actual_body_pixels': body_mask.histogram()[255],
            'outside_actual_body_pixels': outside.histogram()[255],
            'outside_actual_body_inside_reported_panel_pixels': inside_panel.histogram()[255],
            'outside_actual_body_outside_reported_panel_pixels': outside.histogram()[255] - inside_panel.histogram()[255],
            'outside_actual_body_mask_bounds': outside.getbbox()}
        results[scope][0]['manual_body_wood_mask'] = body_mask
    report['manual_body_normalized_iou_diagnostic_only'] = {
        scope: shape_match(results['native'][0]['manual_body_wood_mask'],
                           results[scope][0]['manual_body_wood_mask'])['normalized_glyph_iou']
        for scope in ('editor', 'projection')}
    for scope in results:
        del results[scope][0]['manual_body_wood_mask']
    canvas = Image.new('RGB', (1080, 1050), (238, 238, 238))
    draw = ImageDraw.Draw(canvas)
    for index, (scope, (_, image, mask, bright, composite, _, _)) in enumerate(results.items()):
        x = index * 360
        draw.text((x + 8, 8), scope + ': frame / original / bright / wood-composite', fill=(0, 0, 0))
        for row, item in enumerate((image, mask, bright, composite)):
            if row:
                item = item.crop(item.getbbox())
                item = item.resize((324, 180), Image.Resampling.NEAREST)
            else:
                item = item.crop(tuple(case[scope]['bounds']))
                item = item.resize((324, 180), Image.Resampling.NEAREST)
            canvas.paste(item.convert('RGB'), (x + 18, 36 + row * 240))
    canvas.save(args.output / 'comparison.png')
    report['comparison'] = file_record(args.output / 'comparison.png')
    (args.output / 'analysis.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
