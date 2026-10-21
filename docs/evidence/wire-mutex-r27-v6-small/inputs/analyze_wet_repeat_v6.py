"""Read-only actual two-phase wet failure analysis; no game or new captures."""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import zlib

from PIL import Image, ImageFilter
import analyze_actual_native_v2 as native
import phase_transport_v5 as transport
import trial_capture_v6 as host

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FOLDER = HERE / 'negative-wet-wire-actual-v6'
OUT = HERE / 'wet-repeat-v6-readonly-analysis.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox(points):
    return None if not points else [min(x for x, y in points), min(y for x, y in points),
                                   max(x for x, y in points) + 1, max(y for x, y in points) + 1]


def main():
    assert not OUT.exists()
    report = json.loads((FOLDER / 'report.json').read_bytes())
    gate = json.loads((FOLDER / 'gate.json').read_bytes())
    assert report['completed'] is False and report['restored'] is True
    assert report['error'] == 'AssertionError: Wire contribution changed: opaque_top_repeat'
    assert report['cleanup_errors'] == [] and report['independent_audit']['restored']
    assert len(report['samples']) == 2 and [s['mode'] for s in report['samples']] == ['base', 'repeat']
    assert report['samples'][0]['helper_selection']['helper_ids'] == report['samples'][1]['helper_selection']['helper_ids']
    assert report['read_events'] == []
    phase_snapshots, exported, total_chunks = [], [], 0
    chunks, metadata, releases = {}, {}, {}
    for row in gate['RPCs']:
        path = FOLDER / ('rpc-%04d.py' % row['number'])
        assert sha(path) == row['sha256'] and row['acknowledged']
        result = json.loads((FOLDER / ('rpc-%04d-result.json' % row['number'])).read_bytes())
        if isinstance(result, dict):
            schema = result.get('schema')
            if schema == 'wire-complete-phase-byte-export-v5-crc32':
                metadata[result['phase_key']] = result
            elif schema == 'wire-complete-phase-chunk-v5-crc32':
                identity = result['phase_key'], result['index']
                assert identity not in chunks
                chunks[identity] = result
            elif result.get('released') is True:
                releases[result['phase_key']] = result
    for number in (1, 2):
        receipt = json.loads((FOLDER / ('phase-%02d-transport.json' % number)).read_bytes())
        meta = receipt['metadata']
        assert metadata[meta['phase_key']] == meta
        collector = transport.Collector(meta)
        for index in range(meta['chunks']):
            collector.add(chunks[(meta['phase_key'], index)])
        raw, snapshot = collector.finish()
        assert raw == (FOLDER / receipt['original_json_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == receipt['host_original_json_sha256']
        assert receipt['chunks'] == collector.receipts and releases[meta['phase_key']] == receipt['release']
        expected = copy.deepcopy(snapshot)
        host.host_wires(expected)
        saved = json.loads((FOLDER / ('phase-%02d-native.json' % number)).read_bytes())
        assert saved == expected
        phase_snapshots.append(saved)
        exported.append({'phase': number, 'phase_key': meta['phase_key'], 'records': len(saved['records']),
            'chunks': meta['chunks'], 'original_bytes': len(raw), 'CRC32': meta['crc32'],
            'host_derived_SHA256': hashlib.sha256(raw).hexdigest()})
        total_chunks += meta['chunks']
    assert total_chunks == len(chunks) and len(metadata) == len(releases) == 2
    maps = [native.phase_maps(snapshot) for snapshot in phase_snapshots]
    assert maps[0] == maps[1]
    assert sum(len(snapshot['records']) for snapshot in phase_snapshots) == report['observer_retirement']['record_count'] == 12
    assert report['observer_retirement']['phase_count'] == 2
    assert phase_snapshots[0]['logical_document'] == phase_snapshots[1]['logical_document']
    assert phase_snapshots[0]['work_document'] == phase_snapshots[1]['work_document']

    samples = report['samples']
    box = samples[0]['wire']['box']
    assert box == samples[1]['wire']['box']
    images = []
    for sample in samples:
        group = {}
        for label in ('shown', 'hidden'):
            path = Path(sample[label]['path'])
            assert sha(path) == sample[label]['sha256']
            with Image.open(path) as image:
                group[label] = image.convert('RGB').crop(tuple(box))
        images.append(group)
    with Image.open(samples[0]['wire']['mask']['path']) as image:
        mask = image.convert('L')
    with Image.open(samples[1]['wire']['mask']['path']) as image:
        assert image.convert('L').tobytes() == mask.tobytes()
    core = mask.filter(ImageFilter.MinFilter(3))
    core5 = mask.filter(ImageFilter.MinFilter(5))
    width, height = mask.size
    bits, core_bits, deep_bits = list(mask.getdata()), list(core.getdata()), list(core5.getdata())
    assert sum(bool(bit) for bit in bits) == 1998
    shown0, shown1 = list(images[0]['shown'].getdata()), list(images[1]['shown'].getdata())
    hidden0, hidden1 = list(images[0]['hidden'].getdata()), list(images[1]['hidden'].getdata())
    changed = []
    background_temporal = []
    all_temporal = []
    for index, (a, b, c, d) in enumerate(zip(shown0, shown1, hidden0, hidden1)):
        x, y = box[0] + index % width, box[1] + index // width
        shown_delta = [b[i] - a[i] for i in range(3)]
        hidden_delta = [d[i] - c[i] for i in range(3)]
        if a != b:
            all_temporal.append((x, y))
            if bits[index]:
                changed.append({'x': x, 'y': y, 'base_shown': a, 'repeat_shown': b,
                    'base_hidden': c, 'repeat_hidden': d, 'shown_delta': shown_delta,
                    'hidden_delta': hidden_delta, 'max_channel_delta': max(abs(v) for v in shown_delta),
                    'core_3x3': bool(core_bits[index]), 'core_5x5': bool(deep_bits[index])})
        if c != d:
            background_temporal.append((x, y))
    deltas = sorted(row['max_channel_delta'] for row in changed)
    summary = {'strict_wire_pixels': 1998, 'mask_and_box_exactly_equal': True,
        'one_pixel_eroded_core_pixels': sum(bool(bit) for bit in core_bits),
        'two_pixel_eroded_core_pixels': sum(bool(bit) for bit in deep_bits),
        'wire_mask_shown_RGB_changed_pixels': len(changed),
        'changed_one_pixel_core': sum(row['core_3x3'] for row in changed),
        'changed_edge_only_1px': sum(not row['core_3x3'] for row in changed),
        'changed_two_pixel_core': sum(row['core_5x5'] for row in changed),
        'changed_bbox_global_pixels': bbox([(row['x'], row['y']) for row in changed]),
        'wire_changed_with_hidden_temporal_change_at_same_pixel': sum(row['base_hidden'] != row['repeat_hidden'] for row in changed),
        'wire_change_max_RGB_delta_p50': deltas[len(deltas) // 2],
        'wire_change_max_RGB_delta_p95': deltas[int(len(deltas) * .95)],
        'wire_change_max_RGB_delta_max': max(deltas),
        'wire_change_more_than_12': sum(value > 12 for value in deltas),
        'entire_wire_ROI_shown_temporal_changed_pixels': len(all_temporal),
        'entire_wire_ROI_hidden_temporal_changed_pixels': len(background_temporal),
        'hidden_temporal_bbox_global_pixels': bbox(background_temporal),
        'thresholds_unchanged': True, 'ROI_global': box}
    state_differences = {key: [samples[0]['state'].get(key), samples[1]['state'].get(key)]
        for key in set(samples[0]['state']) | set(samples[1]['state'])
        if samples[0]['state'].get(key) != samples[1]['state'].get(key)}
    assert set(state_differences) == {'actor', 'serial'}
    assert samples[0]['screen'] == samples[1]['screen']
    timeline = []
    for sample in samples:
        for label in ('shown', 'hidden'):
            capture = sample[label]['capture']
            timeline.append({'phase': sample['mode'], 'capture': label, 'started_at': capture['started_at'],
                'finished_at': capture['finished_at'], 'frame_qpc_100ns': capture['frame']['frame_qpc_100ns'],
                'request_qpc_100ns': capture['frame']['request_qpc_100ns'],
                'foreground_unchanged': capture['foreground_unchanged'], 'helper_sha256': capture['helper']['sha256']})
    shown_separation = (datetime.fromisoformat(timeline[2]['started_at']) - datetime.fromisoformat(timeline[0]['started_at'])).total_seconds()
    shader = ROOT / '.runtime/projects/wire-r27-crc32-mutex-v10/resource_pack/shaders/glsl/modern_projection_liquid_product_still_water_grey.fragment'
    shader_source = shader.read_text('utf8')
    assert 'TOTAL_REAL_WORLD_TIME*20.0/TICKS_PER_FRAME' in shader_source
    assert 'fract(clock)' in shader_source and 'STYLE_DEFAULT_OPACITY = 0.45' in shader_source
    resource_sources = [{'path': shader.relative_to(ROOT).as_posix(), 'sha256': sha(shader)}]
    for name in ('liquid_product_profile.py', 'liquid_product_projection.py', 'liquid_product_render.py',
                 'liquid_render.py', 'liquid_projection.py', 'liquid_product_plan.py'):
        path = ROOT / '.runtime/projects/wire-r27-crc32-mutex-v10/behavior_pack/modern_projection/projection' / name
        resource_sources.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)})
    result = {'schema': 'wire-r27-wet-base-repeat-readonly-analysis-v6', 'report_sha256': sha(FOLDER / 'report.json'),
        'fixture_completed': False, 'fixture_restored': True, 'candidate_phase_reached': False,
        'failure': report['error'], 'actual_native_boundaries_equal': True,
        'native_groups_per_phase': len(maps[0]), 'native_records_per_phase': [6, 6],
        'all_actual_RPC_chunks_reconstructed': True, 'exported_phases': exported,
        'native_coverage_limit': 'Actual original palette Create/Deserialize/Serialize/Combine only; custom liquid FreeModel construction/uniform updates were not intercepted.',
        'same_original_helpers': True, 'logical_document_equal': True, 'work_document_equal': True,
        'state_differences_expected_fresh_phase_identity_only': state_differences,
        'camera_rotation_player_origin_opacity_and_screen_exactly_equal': True,
        'product_water_profile': report['profile'],
        'actual_custom_water_uniforms_captured': False,
        'actual_shader_clock_uniform_captured': False,
        'uniform_limit': 'Profile identity, owned names, logical layers and source bytes were recorded; actual active FreeModel group payloads/SetExtraUniformValue arguments and TOTAL_REAL_WORLD_TIME were not captured, so their equality or exact animation frames cannot be asserted.',
        'water_animation_evidence': {'source_uses_real_world_clock': True, 'frames': 32, 'ticks_per_frame': 2,
            'interpolates_fractional_frames': True, 'style_default_opacity': .45,
            'shown_separation_seconds': shown_separation, 'source_only_shader_clock_not_actual_uniform_receipt': True,
            'four_original_images_opened_for_review': True,
            'hidden_captures_still_show_animated_custom_water': True,
            'inference': 'Temporal custom-water contribution is strongly supported by unchanged wire silhouette/native palette inputs and moving water in both original hidden captures. Exact attribution of every changed wire RGB pixel remains unproven without the missing actual water uniforms/phase capture.'},
        'pixel_summary': summary, 'all_changed_wire_RGB_pixels_global_coordinates': changed,
        'capture_timeline': timeline, 'water_source_inputs': resource_sources,
        'cleanup_errors': [], 'independent_runtime_restored': True, 'runtime_and_host_unchanged': True,
        'runtime_calls_in_this_analysis': 0, 'new_captures': 0, 'MC_started': False,
        'candidate_promoted': False, 'manual_closures': 0}
    host.write(OUT, result)
    print(json.dumps({'analysis_sha256': sha(OUT), 'pixel_summary': summary,
        'native_boundaries_equal': True, 'phases': 2, 'transport_chunks': total_chunks,
        'actual_custom_water_uniforms_captured': False, 'runtime_calls': 0}))


if __name__ == '__main__':
    main()
