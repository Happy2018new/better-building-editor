"""Standard-library offline verification of the bounded water experiment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import zlib

os.environ['OPENBLAS_NUM_THREADS'] = '1'
PHASES = ('skeleton_baseline', 'candidate', 'skeleton_restore', 'candidate_repeat', 'final_skeleton')
CONTRACT = 'dfe714e3b5b0807aed1b906f53095f7b26dd2f733d19552c7181457ce5b7c642'
SESSION = 'd88c93b78e304410b24e1c2feabc6010'
OWNER = 'water-r20-depth-cache-ab-v1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def png_roi(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, compressed, size, channels = 8, bytearray(), None, None
    ended = False
    while offset < len(data):
        length = struct.unpack_from('>I', data, offset)[0]
        kind, payload = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + length]
        crc = struct.unpack_from('>I', data, offset + 8 + length)[0]
        assert zlib.crc32(kind + payload) & 0xffffffff == crc
        if kind == b'IHDR':
            width, height, depth, color, comp, filt, interlace = struct.unpack('>IIBBBBB', payload)
            assert depth == 8 and color in (2, 6) and (comp, filt, interlace) == (0, 0, 0)
            size, channels = (width, height), 3 if color == 2 else 4
        elif kind == b'IDAT':
            compressed.extend(payload)
        offset += length + 12
        if kind == b'IEND':
            ended = True
            break
    assert ended and offset == len(data) and size == (1994, 1105)
    stride = size[0] * channels
    decoded = zlib.decompress(compressed)
    assert len(decoded) == (stride + 1) * size[1]
    previous, pixels = bytearray(stride), bytearray()
    for y in range(size[1]):
        start = y * (stride + 1)
        method, row = decoded[start], bytearray(decoded[start + 1:start + 1 + stride])
        assert method <= 4
        if method:
            for x in range(stride):
                a, b = row[x - channels] if x >= channels else 0, previous[x]
                c = previous[x - channels] if x >= channels else 0
                if method == 1:
                    predictor = a
                elif method == 2:
                    predictor = b
                elif method == 3:
                    predictor = (a + b) // 2
                else:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    predictor = a if pa <= pb and pa <= pc else b if pb <= pc else c
                row[x] = (row[x] + predictor) & 255
        if 354 <= y < 848:
            for x in range(470, 1540):
                pixels.extend(row[x * channels:x * channels + 3])
        previous = row
    return pixels


def changed(a, b):
    assert len(a) == len(b) == 1070 * 494 * 3
    return sum(max(abs(a[i + j] - b[i + j]) for j in range(3)) >= 8
               for i in range(0, len(a), 3))


def verify(package):
    manifest = load(package / 'manifest.json')
    paths = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    assert paths == set(manifest['files']) | {'manifest.json'}
    for name, expected in manifest['files'].items():
        data = (package / name).read_bytes()
        assert sha(data) == expected['sha256'] and len(data) == expected['bytes'], name
    ab = load(package / 'cache/ab-report-runtime-hashlib-retry-v1.json')
    ui = load(package / 'ui/result/report.json')
    for report in (ab, ui):
        assert all(report[k] for k in ('completed', 'restored', 'source_unchanged'))
        assert report['cleanup_errors'] == [] and report['window_actions'] == []
        assert report['source_contract_sha256'] == CONTRACT
        assert report['session_binding']['id'] == SESSION and report['session_binding']['owner'] == OWNER
        assert report['session_binding']['game_pid'] == 8756
        assert report['session_binding']['game_identity'] == '134365801198650139'
        assert report['production_qualified'] is False
    for name, error in (('cache/ab-report.json', 'sha256'), ('ui/failed/report.json', 'assertion_dialogs')):
        failed = load(package / name)
        assert not failed['completed'] and failed['restored'] and failed['source_unchanged']
        assert not failed['phases'] and not failed.get('captures')
        assert not failed['cleanup_errors'] and error in failed['error']
    baseline = (package / 'cache/baseline_viewport.py').read_bytes()
    assert ab['install']['baseline_source_readback'].encode('ascii') == baseline
    assert ab['baseline_transmission_sha256_host'] == sha(baseline)
    assert ab['game_sha_computed'] is False and ab['original_elapsed_failures_resolved'] is False
    assert sha((package / 'cache/retry/host.py').read_bytes()) == ab['host_sha256']
    retry = load(package / 'cache/retry/amendment.json')
    assert sha((package / 'cache/operational-amendment-v2.json').read_bytes()) == ab['operational_amendment_sha256']
    assert retry['operational_amendment_sha256'] == ab['operational_amendment_sha256']
    assert retry['retry_host_sha256'] == ab['host_sha256']
    assert retry['old_failure_report_sha256'] == sha((package / 'cache/ab-report.json').read_bytes())
    assert retry['frozen_host_sha256'] == sha((package / 'cache/frozen/host.py').read_bytes())
    assert retry['probe_source_readback_equal'] and retry['game_sha_computed'] is False
    assert not retry['hashlib_new_probe']['supported'] and retry['hashlib_new_probe']['digest'] is None
    assert 'unsupported hash type sha256' in retry['hashlib_new_probe']['error']
    frozen = load(package / 'cache/launch-inputs.json')
    assert frozen['source_contract_sha256'] == CONTRACT
    assert len(frozen['source_sha256']) == 3093
    assert sha(json.dumps(frozen['source_sha256'], sort_keys=True, separators=(',', ':')).encode('ascii')) == CONTRACT
    plan = load(package / 'cache/plan.json')
    assert load(package / 'cache/plan-receipt.json')['plan_sha256'] == sha((package / 'cache/plan.json').read_bytes())
    assert plan['source_contract_sha256'] == CONTRACT and plan['production_qualified'] is False
    assert plan['baseline_source_sha256'] == sha(baseline)
    assert plan['candidate_source_sha256'] == sha((package / 'source/frozen/liquid_viewport.py').read_bytes())
    assert plan['launch_inputs_sha256'] == sha((package / 'cache/launch-inputs.json').read_bytes())
    assert plan['launch_config_sha256'] == sha((package / 'cache/launch-mcdev.json').read_bytes())
    ready = load(package / 'cache/launch-ready.json')
    assert ready['id'] == SESSION and ready['owner'] == OWNER and ready['exact_process_handles_retained']
    assert ready['game_pid'] == 8756 and ready['game_identity'] == '134365801198650139'
    assert ready['mcdk_pid'] == 48772 and ready['mcdk_identity'] == '134365801196531006'
    for name in ('liquid_viewport.py', 'liquid_render.py', 'liquid_transport.py'):
        assert sha((package / 'source/frozen' / name).read_bytes()) == frozen['source_sha256']['behavior_pack/modern_projection/projection/' + name]
    config = load(package / 'source/frozen/.mcdev.json')
    assert all(config[k] is False for k in ('auto_hot_reload_materials', 'auto_hot_reload_mods', 'auto_hot_reload_shaders', 'auto_hot_reload_ui'))
    totals = {}
    for mode, expected in (('baseline', 240), ('candidate', 0)):
        phase = ab['phases'][mode]
        assert phase['done'] and len(phase['rows']) == 60 and len(phase['warmup_rows']) == 5
        assert phase['before'] == phase['after']
        assert all(not r['native_submissions'] and r['error'] is None and not r['pending'] for r in phase['rows'])
        totals[mode] = sum(r['source_validations'] for r in phase['rows'])
        assert totals[mode] == expected
    assert ab['phases']['baseline']['after'] == ab['phases']['candidate']['after']
    for left, right in zip(ab['phases']['baseline']['rows'], ab['phases']['candidate']['rows']):
        for key in ('view_callbacks', 'pose_callbacks', 'renderer_validations', 'publication_restores'):
            assert left[key] == right[key]
    assert all(ab['phases'][p]['done'] for p in ('depth', 'clip', 'unclip', 'invalid', 'retry'))
    assert ab['wrappers_restore']['restored'] and ab['workspace_restore'] and ab['close_restore']
    for entry in ab['capacity'] + ui['capacity']:
        state = entry['state']
        assert state['passed'] and state['effective_live_count'] <= 2
        assert state['commit']['commit_available_bytes'] >= 6 * 1024 ** 3
        if 'watcher' in entry:
            assert entry['watcher']['passed']
    assert ui['cache_ab_report_sha256'] == sha((package / 'cache/ab-report-runtime-hashlib-retry-v1.json').read_bytes())
    for name, key in (('candidate.py', 'candidate_sha256'), ('runtime.py', 'host_sha256'), ('runtime_engine.py', 'engine_sha256')):
        assert sha((package / 'ui/source' / name).read_bytes()) == ui[key]
    outer = ui['execution_outer_runner']
    assert sha((package / 'ui/source/receipt_retry_v2.py').read_bytes()) == outer['sha256']
    assert sha((package / 'ui/source/runtime-operational-amendment-v2.json').read_bytes()) == outer['receipt_sha256']
    assert ui['initial'] == ui['native_restore']['state'] and ui['native_restore']['restored']
    assert ui['native_restore_submissions']['restored'] and ui['workspace_restore']
    assert set(ui['phases']) == set(PHASES) and len(ui['captures']) == 11
    initial_ids = [e['actual_ids'][e['front']] for e in ui['initial']['entries']]
    assert len(initial_ids) == len(set(initial_ids)) == 8 and -1 not in initial_ids
    for label in PHASES:
        phase = ui['phases'][label]
        assert phase['ids']['ready'] and phase['ids']['ids'] == initial_ids
        actual = [identity for row in phase['ids']['state']['entries'] for identity in row['actual_ids'] if identity != -1]
        assert len(actual) == len(set(actual)) == 8
        assert all(r['returned'] and r['render_depth'] == -50 and r['mode'] == ('SE' if label.startswith('candidate') else 'S') for r in phase['submitted'])
        assert len(phase['submitted']) == 8
        for wet, hidden in zip(phase['wet_payload'], phase['hidden_payload']):
            assert wet['id'] == hidden['id'] and wet['tag'] == hidden['tag'] == 134
            assert not wet['hidden'] and hidden['hidden']
            assert len(wet['actual_uniforms']) == len(hidden['actual_uniforms']) == 4
            assert wet['actual_uniforms'][:3] == hidden['actual_uniforms'][:3]
            assert wet['actual_uniforms'][3][:3] == hidden['actual_uniforms'][3][:3]
            assert wet['actual_uniforms'][3][3] == 1 and hidden['actual_uniforms'][3][3] == 0
    assert ui['depth_step']['depth'] == ui['depth_step']['actual_depth'] == 1
    assert ui['depth_return']['depth'] == ui['depth_return']['actual_depth'] == 0
    assert ui['repair_accepted'] is False and ui['initial_construction_qualified'] is False
    assert ui['shared_depth_qualified'] is False and ui['cold_start_performed'] is False
    frames = {}
    for label, embedded in ui['captures'].items():
        receipt = load(package / 'ui/result' / (label + '.capture.json'))
        assert set(embedded) == set(receipt) | {'pool_before', 'pool_after'}
        assert all(embedded[k] == v for k, v in receipt.items())
        assert embedded['pool_before'] == embedded['pool_after']
        assert receipt['ok'] and receipt['reliable'] and receipt['native_resolution']
        assert receipt['backend'] == 'Windows.Graphics.Capture'
        assert receipt['owner'] == OWNER and receipt['game_pid'] == 8756
        assert receipt['game_identity'] == '134365801198650139'
        assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
        assert receipt['guarded_no_activation'] and receipt['noactivation_requested']
        assert receipt['foreground_unchanged'] and receipt['background_safe']
        assert (receipt['width'], receipt['height']) == (1994, 1105)
        png = package / 'ui/result' / (label + '.png')
        assert sha(png.read_bytes()) == receipt['sha256']
        frames[label] = png_roi(png)
    starts = [ui['captures'][p + '_wet']['started_at'] for p in PHASES]
    assert starts == sorted(starts)
    counts = {p: changed(frames[p + '_wet'], frames[p + '_hidden']) for p in PHASES}
    analysis = load(package / 'ui/result/analysis.json')
    assert counts == analysis['independent_water_changed_pixels'] == dict.fromkeys(PHASES, 96436)
    comparisons = (('candidate', 'candidate_repeat', 'candidate_repeat_wet_difference'),
                   ('skeleton_baseline', 'skeleton_restore', 'skeleton_restore_wet_difference'),
                   ('skeleton_baseline', 'final_skeleton', 'final_skeleton_wet_difference'))
    for a, b, key in comparisons:
        assert changed(frames[a + '_wet'], frames[b + '_wet']) == analysis[key] == 0
    assert analysis['assessment'] == 'inconclusive_for_invisible_state_repair_baseline_has_signal'
    assert analysis['repair_accepted'] is False and analysis['production_qualified'] is False
    exits = load(package / 'cache/process-exits.json')
    close = load(package / 'cache/retry/normal-close.json')
    assert exits['completed'] and exits['session'] == SESSION and exits['owner'] == OWNER
    assert exits['processes']['game']['state'] == exits['processes']['mcdk']['state'] == 'exited'
    assert exits['processes']['game']['identity'] == '134365801198650139'
    assert exits['processes']['mcdk']['identity'] == '134365801196531006'
    assert exits['processes']['game']['exit_code_hex'] == '0xC0000409'
    assert exits['processes']['mcdk']['exit_code'] == 0
    assert close['exact_exit_receipt'] == exits and close['exact_exits_observed'] and close['finalized']
    assert close['one_normal_close_only'] and close['force'] is False and close['window_activation'] is False
    assert 'Game has not closed' in close['normal_close_error']
    assert sha((package / 'cache/retry/normal_close.py').read_bytes()) == close['host_sha256']
    candidate_baseline_difference = changed(frames['skeleton_baseline_wet'], frames['candidate_wet'])
    return {'verified': True, 'files': len(manifest['files']), 'capture_count': 11,
            'source_count': len(frozen['source_sha256']), 'source_validations': totals,
            'native_submissions_both_steady_phases': 0, 'wet_hidden_pixels': counts,
            'candidate_baseline_wet_difference': candidate_baseline_difference,
            'repair_accepted': False, 'production_qualified': False, 'clean_shutdown': False,
            'game_exit': '0xC0000409', 'manifest_sha256': sha((package / 'manifest.json').read_bytes())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(verify(args.package.resolve()), sort_keys=True))
