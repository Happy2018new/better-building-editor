"""Verify the archived R18 bounds evidence without connecting to a game."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
PHASES = (
    'baseline', 'bounds_2', 'bounds_4', 'bounds_8', 'bounds_16',
    'bounds_32', 'bounds_64', 'large_bounds', 'entity_distance_1024',
    'player_near', 'player_far_return',
)
HELPER_SHA256 = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
SECRET_KEY = re.compile(r'(^|_)(token|password|secret|authorization|api_key)($|_)', re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def check_secret_keys(value, label):
    if isinstance(value, dict):
        for key, item in value.items():
            require(not SECRET_KEY.search(key), 'Sensitive field in ' + label)
            check_secret_keys(item, label)
    elif isinstance(value, list):
        for item in value:
            check_secret_keys(item, label)


def provenance(relative):
    if relative.startswith(('reports/', 'analysis/', 'captures/')):
        return {'kind': 'exact_copy', 'source_path': str(WORKSPACE / '.runtime' / Path(relative).name)}
    prefix = 'sources/cold_project/'
    if relative.startswith(prefix):
        return {'kind': 'exact_copy', 'source_path': 'D:/bbe-r18-water-production/' + relative[len(prefix):]}
    prefix = 'sources/host/'
    if relative.startswith(prefix):
        return {'kind': 'exact_copy', 'source_path': str(WORKSPACE / relative[len(prefix):])}
    return {'kind': 'authored_offline'}


def verify_report(version, launch, start):
    stem = 'liquid-r18-visibility-v%d' % version
    report_path = ROOT / 'reports' / (stem + '.json')
    report = load(report_path)
    analysis = load(ROOT / 'analysis' / (stem + '-analysis.json'))
    require(report['diagnostic_only'] and not report['product_admission_performed'], stem + ': scope')
    require(all(report[key] for key in ('completed', 'restored', 'source_unchanged')), stem + ': incomplete')
    require(report['cleanup_errors'] == [], stem + ': cleanup error')
    require(report['session_id'] == start['id'], stem + ': session identity')
    require(report['launch_contract_sha256'] == launch['source_contract_sha256'], stem + ': launch contract')
    source = 'cold_project' if version == 4 else 'host'
    tool = ROOT / 'sources' / source / 'tools' / 'diagnose_water_visibility_r18.py'
    require(report['tool_sha256'] == digest(tool), stem + ': diagnostic tool hash')
    require(analysis['source_report_sha256'] == digest(report_path), stem + ': analysis report hash')
    require(analysis['all_22_capture_receipts_verified'] is True, stem + ': previous receipt analysis')
    require(analysis['product_qualified'] is False, stem + ': product gate')
    require(set(report['phases']) == set(PHASES), stem + ': phase list')
    require(len(report['captures']) == 22, stem + ': capture count')
    baseline = report['phases']['baseline']
    require(baseline['projection_type'] == 'ProductLiquidProjection', stem + ': projection owner')
    require(baseline['renderer_type'] == 'ProductWorldLiquidRenderer', stem + ': renderer owner')
    require(baseline['default_bounding_box'] == [[-4.] * 3, [4.] * 3], stem + ': initial bounds')
    cleanup = report['owner_cleanup_restore']
    require(cleanup['closed'] and cleanup['renderer_closed'], stem + ': owner not closed')
    require(all(cleanup[key] == 0 for key in ('active', 'staging', 'retired')), stem + ': retained models')
    require(cleanup['cleanup_errors'] == [], stem + ': renderer cleanup error')
    for name, phase in report['phases'].items():
        require(phase['active_count'] == 8 and phase['staging_count'] == 0
                and phase['retired_count'] == 0, stem + ': model counts ' + name)
        if version == 5:
            require(phase['camera'] == baseline['camera'] and phase['rotation'] == baseline['rotation'],
                    stem + ': changed fixture camera ' + name)
            require(phase['after']['camera'] == baseline['camera']
                    and phase['after']['rotation'] == baseline['rotation'],
                    stem + ': changed camera during capture ' + name)
    for label, embedded in report['captures'].items():
        image_path = ROOT / 'captures' / ('v%d' % version) / (stem + '_' + label + '.png')
        receipt = load(image_path.with_suffix('.capture.json'))
        require(receipt == embedded, stem + ': receipt differs from report ' + label)
        for key in ('ok', 'reliable', 'native_resolution', 'guarded_no_activation',
                    'noactivation_requested', 'foreground_unchanged', 'background_safe'):
            require(receipt[key] is True, stem + ': ' + key + ' ' + label)
        require(receipt['agent_activation_allowed'] is False
                and receipt['activation_fallback'] is False, stem + ': activation ' + label)
        require(receipt['helper_returncode'] == 0, stem + ': helper failure ' + label)
        require(receipt['helper']['sha256'] == HELPER_SHA256, stem + ': helper identity ' + label)
        require(receipt['game_pid'] == start['game_pid']
                and receipt['game_identity'] == start['game_identity'], stem + ': game identity ' + label)
        require(receipt['owner'] == start['owner'], stem + ': owner identity ' + label)
        require(receipt['sha256'] == digest(image_path), stem + ': PNG hash ' + label)
        require(receipt['bytes'] == image_path.stat().st_size, stem + ': PNG size ' + label)
        png = image_path.read_bytes()
        require(png[:8] == b'\x89PNG\r\n\x1a\n', stem + ': PNG signature ' + label)
        require(struct.unpack('>II', png[16:24]) == (receipt['width'], receipt['height']),
                stem + ': native dimensions ' + label)
    return report, analysis


def verify_pixels(version, analysis):
    from PIL import Image, ImageChops
    stem = 'liquid-r18-visibility-v%d' % version
    metrics = []
    for phase in analysis['phases']:
        prefix = ROOT / 'captures' / ('v%d' % version) / (stem + '_' + phase['phase'])
        with Image.open(str(prefix) + '_wet.png') as wet, Image.open(str(prefix) + '_hidden.png') as hidden:
            difference = ImageChops.difference(wet.convert('RGB'), hidden.convert('RGB'))
            channels = difference.crop(tuple(analysis['metric_roi'])).split()
            maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
            histogram = maximum.histogram()
            count = sum(histogram[analysis['changed_pixel_threshold'] + 1:])
            require(count == phase['changed_pixels_roi'], stem + ': pixel metric ' + phase['phase'])
            if 'peak_delta_roi' in phase:
                require(max(index for index, amount in enumerate(histogram) if amount)
                        == phase['peak_delta_roi'], stem + ': peak metric ' + phase['phase'])
            metrics.append({'phase': phase['phase'], 'changed_pixels_roi': count})
    return metrics


def verify_manifest():
    manifest = load(ROOT / 'manifest.json')
    expected = set()
    for entry in manifest['files']:
        path = ROOT / entry['path']
        require(path.is_file(), 'Missing artifact ' + entry['path'])
        require(digest(path) == entry['sha256'] and path.stat().st_size == entry['bytes'],
                'Manifest mismatch ' + entry['path'])
        expected.add(entry['path'])
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*') if path.is_file()
              and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    require(actual == expected, 'Unlisted or removed artifacts')
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-manifest', action='store_true', help='Generate offline verification and hashes')
    parser.add_argument('--pixels', action='store_true', help='Recompute the declared ROI metrics; requires Pillow')
    args = parser.parse_args()
    launch = load(ROOT / 'reports' / 'liquid-r18-launch-inputs-v6.json')
    start = load(ROOT / 'reports' / 'liquid-r18-start-v4.json')
    contract = hashlib.sha256(json.dumps(launch['source_sha256'], sort_keys=True,
                              separators=(',', ':')).encode('ascii')).hexdigest()
    require(contract == launch['source_contract_sha256'], 'Launch contract digest')
    for path in (ROOT / 'sources' / 'cold_project').rglob('*.py'):
        name = path.relative_to(ROOT / 'sources' / 'cold_project').as_posix()
        require(digest(path) == launch['source_sha256'][name], 'Cold source differs: ' + name)
    gate = ROOT / 'sources/cold_project/behavior_pack/modern_projection/projection/liquid_product_qualification_data.py'
    require('PRODUCT_QUALIFIED = False' in gate.read_text(encoding='utf-8'), 'Archived gate changed')
    for path in ROOT.rglob('*.json'):
        require(path.name != 'session.json', 'Session credentials must not be archived')
        check_secret_keys(load(path), path.relative_to(ROOT).as_posix())
    summary = {'schema': 1, 'offline_only': True, 'product_qualified': False,
               'source_contract_sha256': contract, 'launch_input_count': len(launch['source_sha256']),
               'versions': []}
    for version in (4, 5):
        report, analysis = verify_report(version, launch, start)
        row = {'version': version, 'verified_captures': len(report['captures']),
               'completed': report['completed'], 'restored': report['restored'],
               'source_unchanged': report['source_unchanged'], 'owner_cleanup': report['owner_cleanup_restore'],
               'tool_sha256': report['tool_sha256']}
        if args.pixels:
            row['recomputed_roi_metrics'] = verify_pixels(version, analysis)
        summary['versions'].append(row)
    if args.refresh_manifest:
        (ROOT / 'verification.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='ascii')
        entries = []
        for path in sorted(ROOT.rglob('*')):
            if not path.is_file() or path.name == 'manifest.json' or '__pycache__' in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            entries.append(dict(path=relative, bytes=path.stat().st_size, sha256=digest(path), **provenance(relative)))
        manifest = {'schema': 1, 'product_qualified': False, 'source_contract_sha256': contract, 'files': entries}
        (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='ascii')
    summary['verified_manifest_files'] = verify_manifest()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
