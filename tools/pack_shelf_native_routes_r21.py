"""Package the completed v3 shelf route evidence; replay without local clones."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RAW_HASHES = {'native.png': 'a4d980167311419956d8499b82c0f220afc9f1c2bd95145799ff80fbc1fa9fb9',
              'empty.png': '0563eec33420bd406f7417a2683176b5334a38cb717f4e873457da81a6bf61c6'}
BOUNDS = (912, 440, 1088, 455)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True)+'\n', encoding='ascii', newline='\n')


def sky_review(captures):
    for name, expected in RAW_HASHES.items():
        if digest(captures/name) != expected:
            raise ValueError('The reviewed raw route image changed: '+name)
    with Image.open(captures/'native.png').convert('RGB') as first, Image.open(captures/'empty.png').convert('RGB') as second:
        if first.size != (1994, 1105) or second.size != first.size:
            raise ValueError('The reviewed raw images changed dimensions')
        pixels = [(x, first.getpixel((x, y)), second.getpixel((x, y)))
                  for y in range(BOUNDS[1], BOUNDS[3]) for x in range(BOUNDS[0], BOUNDS[2])]
    marker = [row for row in pixels if row[0]//16 % 2 == 0]
    artwork = [row for row in pixels if row[0]//16 % 2 == 1]
    if len(marker) != 1200 or any(row[1] != (255, 255, 0) for row in marker):
        raise ValueError('The reviewed shelf-body yellow marker pixels changed')
    if any(row[2] != (171, 210, 255) for row in pixels):
        raise ValueError('The reviewed empty body ROI is no longer entirely sky')
    if len(artwork) != 1440 or any(row[1] == (255, 255, 0) for row in artwork):
        raise ValueError('The reviewed native artwork strips changed')
    return {'bounds': list(BOUNDS), 'pixels': len(pixels), 'empty_sky_pixels': len(pixels),
        'yellow_marker_pixels': len(marker), 'native_artwork_pixels': len(artwork),
        'native_artwork_unique_rgb': len(Counter(row[1] for row in artwork)),
        'cyan_pixels': sum(row[1] == (0, 255, 255) for row in pixels),
        'conclusion': 'Native oak shelf body, south and unpowered, selects terrain_base for this world draw.',
        'scope': 'Not other woods, states, UI or product appearance qualification.',
        'raw_report_route_qualified_remains_false': True}


def verify_package(output):
    index = json.loads((output/'index.json').read_bytes())
    present = {path.relative_to(output).as_posix() for path in output.rglob('*')
               if path.is_file() and path.name != 'index.json'}
    if present != set(index['sha256']):
        raise ValueError('The portable file set changed')
    for name, expected in index['sha256'].items():
        if digest(output/name) != expected:
            raise ValueError('Portable evidence bytes changed: '+name)
    report = json.loads((output/'capture/report.json').read_bytes())
    freeze = json.loads((output/'records/frozen-v3.json').read_bytes())
    if report['frozen_manifest_sha256'] != digest(output/'records/frozen-v3.json'):
        raise ValueError('Acquisition is not bound to the packaged freeze')
    if not all(report[key] for key in ('completed', 'restored', 'source_unchanged')) or report['cleanup_errors']:
        raise ValueError('Acquisition did not complete and restore')
    if report['native_route_qualified'] is not False:
        raise ValueError('The original unsegmented report was changed')
    if sky_review(output/'capture') != json.loads((output/'review/sky-roi.json').read_bytes()):
        raise ValueError('Portable shelf-body review changed')
    for relative in freeze['changed_paths']:
        after = output/'diffs/after'/relative
        row = next(item for item in freeze['files'] if item['path'] == relative)
        if digest(after) != row['sha256']:
            raise ValueError('The packaged changed resource differs from its frozen row')
    compiler = json.loads((output/'records/compile.json').read_bytes())
    if not compiler['passed'] or compiler['frozen_manifest_sha256'] != digest(output/'records/frozen-v3.json'):
        raise ValueError('Compiler results are not bound to this exact freeze')
    lifecycle = json.loads((output/'lifecycle/facts.json').read_bytes())
    exact = json.loads((output/'lifecycle/exact-exit.json').read_bytes())
    if not exact['completed'] or any(row['state'] != 'exited' for row in exact['processes'].values()):
        raise ValueError('Exact process exit observation is incomplete')
    if lifecycle['session_state'] != 'stopped':
        raise ValueError('The owned route session was not finalized')
    session = json.loads((output/'lifecycle/session-stopped-redacted.json').read_bytes())
    if session['state'] != 'stopped' or session['owner'] != exact['owner'] or session['id'] != exact['session']:
        raise ValueError('The stopped session does not match the exact exit observer')
    for key in ('game', 'mcdk'):
        if session[key+'_pid'] != exact['processes'][key]['pid'] or session[key+'_identity'] != exact['processes'][key]['identity']:
            raise ValueError('The stopped session identity does not match the observer')
    return {'verified': True, 'files': len(present), 'sky_roi_pixels': 2640,
        'programs': compiler['programs'], 'pixel_checks': compiler['pixel_checks'],
        'production_qualified': False, 'package_index_sha256': digest(output/'index.json')}


def pack(control, output, lifecycle_facts):
    from prepare_shelf_native_routes_r21 import verify
    frozen = verify(control/'frozen.json')
    if output.exists():
        raise ValueError('Choose a fresh portable package directory')
    facts = json.loads(lifecycle_facts.read_bytes())
    if facts['session_state'] != 'stopped':
        raise ValueError('A stopped-session lifecycle fact record is required')
    output.mkdir(parents=True)
    (output/'.gitattributes').write_text('** -text -diff whitespace=cr-at-eol\n', encoding='ascii', newline='\n')

    def copy(source, relative):
        destination = output/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    for name in ('native.png', 'empty.png', 'report.json'):
        copy(control/'captures/south-selection'/name, 'capture/'+name)
    copy(control/'frozen.json', 'records/frozen-v3.json')
    copy(Path(frozen['source_freeze']), 'records/frozen-v2.json')
    copy(Path(frozen['v2_capture_report']), 'records/v2-capture-report.json')
    copy(control/'compile.json', 'records/compile.json')
    copy(control/'RUN.md', 'records/prepared-run-plan.md')
    for path in (control/'diffs').rglob('*'):
        if path.is_file():
            copy(path, 'diffs/'+path.relative_to(control/'diffs').as_posix())
    for relative, expected in frozen['host_sources'].items():
        if digest(ROOT/relative) != expected:
            raise ValueError('Frozen host source changed')
        copy(ROOT/relative, 'host/'+relative)
    for relative in ('tools/verify_biome_shader.py', 'tests/test_shelf_native_routes_r21.py',
                     'tools/pack_shelf_native_routes_r21.py'):
        copy(ROOT/relative, 'host/'+relative)
    shaders = Path(next(name for name in frozen['native_sources'] if name.endswith('renderchunk.fragment'))).parent
    visited = set()

    def native_source(path, relative):
        if path in visited:
            return
        visited.add(path)
        copy(path, 'native/'+relative)
        if path.suffix in ('.vertex', '.fragment', '.h'):
            for name in re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf8'), re.M):
                native_source(shaders/name, 'shaders/glsl/'+name)

    for name, expected in frozen['native_sources'].items():
        path = Path(name)
        if digest(path) != expected:
            raise ValueError('Native source changed')
        native_source(path, path.relative_to(shaders.parents[1]).as_posix())
    for name in ('exact-exit.json', 'start-summary.json'):
        copy(control/'launch'/name, 'lifecycle/'+name)
    start = json.loads((control/'launch/start-summary.json').read_bytes())
    session_path = Path(start['session_file'])
    session = json.loads(session_path.read_bytes())
    if session['state'] != 'stopped':
        raise ValueError('The owned session is not stopped')
    session.pop('token', None)
    write(output/'lifecycle/session-stopped-redacted.json', session)
    write(output/'lifecycle/session-provenance.json', {'original_path': str(session_path),
        'original_sha256': digest(session_path), 'redacted_top_level_keys': ['token'],
        'scope': 'Stopped-session snapshot; stale local authentication token omitted from portable evidence.'})
    copy(lifecycle_facts, 'lifecycle/facts.json')
    (output/'review').mkdir()
    write(output/'review/sky-roi.json', sky_review(output/'capture'))
    index = {'schema_version': 1, 'kind': 'portable shelf route evidence only; no full BP/RP clone',
        'replay': 'python -B -X utf8 host/tools/pack_shelf_native_routes_r21.py verify --package .',
        'sha256': {path.relative_to(output).as_posix(): digest(path) for path in sorted(output.rglob('*')) if path.is_file()}}
    write(output/'index.json', index)
    verify(control/'frozen.json')
    return verify_package(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    package = subs.add_parser('pack')
    package.add_argument('--control', type=Path, required=True)
    package.add_argument('--output', type=Path, required=True)
    package.add_argument('--lifecycle-facts', type=Path, required=True)
    replay = subs.add_parser('verify')
    replay.add_argument('--package', type=Path, required=True)
    args = parser.parse_args()
    result = pack(args.control, args.output, args.lifecycle_facts) if args.action == 'pack' else verify_package(args.package)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
