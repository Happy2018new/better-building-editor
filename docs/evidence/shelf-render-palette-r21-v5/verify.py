"""Archive/replay the three-image full-palette shelf diagnostic, without game calls."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT/'.runtime/shelf-render-palette-r21-v5-state-guard'
ORIGINAL = ROOT/'.runtime/shelf-render-palette-r21-v5'
HELPER = 'tools/shelf_render_palette_candidate_r21.py'
SOURCE = ('minecraft:oak_shelf', 0)
PROXY = ('modern_projection:preview_shelf_oak_unpowered_south_context_r21', 0)
CYAN = ('minecraft:cyan_concrete', 0)
LABELS = ('native', 'proxy_support', 'proxy_support_color')
REGIONS = {'upper_vertical': (920, 450, 1080, 490),
           'middle_vertical': (920, 500, 1080, 580),
           'lower_vertical': (920, 592, 1080, 630)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def require(value, message):
    if not value:
        raise ValueError(message)


def verify(package):
    index = load(package/'index.json')
    actual = {path.relative_to(package).as_posix() for path in package.rglob('*')
              if path.is_file() and path.name != 'index.json'}
    require(actual == set(index['files']), 'The indexed payload set changed')
    for name, row in index['files'].items():
        path = package/name
        require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'],
                'Payload bytes changed: '+name)
    original = load(package/'freeze/original.json')
    amended = load(package/'freeze/amended.json')
    base = load(package/'freeze/native-control.json')
    require(amended['files'] == original['files'], 'The amendment changed clone resources')
    require(sha(package/'freeze/original.json') == amended['amendment']['original_freeze_sha256'],
            'The original freeze provenance changed')
    require(sha(package/'freeze/native-control.json') == amended['source_freeze_sha256'],
            'The frozen native control provenance changed')
    delta = {name for name in amended['host_sources']
             if amended['host_sources'][name] != original['host_sources'].get(name)}
    require(delta == {HELPER}, 'The amendment changed more than its helper host')
    require(sha(package/'inputs/original_shelf_render_palette_candidate_r21.py') ==
            original['host_sources'][HELPER] == amended['amendment']['original_helper_sha256'],
            'The original helper bytes changed')
    for name, expected in amended['host_sources'].items():
        target = package/('inputs/run.py' if name.startswith('.runtime/') else 'inputs/'+name)
        require(sha(target) == expected, 'A frozen host changed: '+name)
    require(sha(package/'inputs/run.py') == sha(package/'inputs/amended_run.py'),
            'The amended runner differs from its original bytes')
    before = {row['path']: row['sha256'] for row in base['files']}
    after = {row['path']: row['sha256'] for row in amended['files']}
    changed = {name for name, digest in after.items() if before.get(name) != digest}
    require(changed == set(amended['changed_paths']) and len(changed) == 6,
            'The declared six-path resource overlay changed')
    require(not (set(before)-set(after)), 'The clone unexpectedly lost source files')
    for name in changed:
        require(sha(package/'overlay'/name) == after[name], 'An overlay resource changed: '+name)
    require(sha(package/'inputs/native-reference.json') == amended['reference_sha256'],
            'The model reference changed')
    model = load(package/'overlay/resource_pack/models/netease_block/preview_shelf_oak_unpowered_south_context_r21.json')
    require(model['netease:block_geometry']['description']['use_ao'] is True,
            'The declared use_ao model flag changed')
    config = load(package/'inputs/mcdev.json')
    require(all(config['auto_hot_reload_'+name] is False for name in ('mods', 'ui', 'materials', 'shaders')),
            'A reload flag is not disabled')
    compiler = load(package/'compile/amended.json')
    require(compiler['passed'] and compiler['programs'] == 16 and compiler['pixel_checks'] == 144,
            'The amended synthetic compiler result changed')
    require(compiler['frozen_manifest_sha256'] == sha(package/'freeze/amended.json'),
            'The compiler is not bound to the amended freeze')
    require(load(package/'compile/original.json')['frozen_manifest_sha256'] == sha(package/'freeze/original.json'),
            'The original compiler binding changed')
    report = load(package/'captures/report.json')
    require(all(report[key] for key in ('completed', 'restored', 'source_unchanged')) and
            not report['cleanup_errors'], 'The acquisition did not complete and restore')
    require(report['frozen_manifest_sha256'] == sha(package/'freeze/amended.json'),
            'The acquisition is not bound to the amended freeze')
    require(set(report['captures']) == set(LABELS), 'The raw acquisition has a different image set')
    raw_images = {path.name for path in (package/'captures').glob('*.png')}
    require(raw_images == {name+'.png' for name in LABELS}, 'Only the three new raw images may be included')
    camera = report['captures']['native']['before']
    require(all(row['before'] == camera and row['after'] == camera for row in report['captures'].values()),
            'The matched camera changed')
    palette = report['palette']
    require(palette['volume'] == [1, 1, 2] and
            ast.literal_eval(palette['source_common']) == {SOURCE: [1], CYAN: [0]} and
            ast.literal_eval(palette['common']) == {PROXY: [1], CYAN: [0]} and
            ast.literal_eval(palette['actor']) == {} and palette['support_inside_same_combine'] and
            not palette['independent_body_overlay'] and palette['source_unchanged'] and palette['prepared_unchanged'],
            'The full render-only palette ownership changed')
    air = [{'name': 'minecraft:air', 'aux': 0}] * 2
    require(report['empty_replication']['world'] == air and
            report['empty_replication']['replication']['cells'] == air,
            'Both real cells must replicate air before attaching the full geometry')
    minimum = min(row['commit_available_bytes'] for row in report['resource_samples'])
    require(minimum >= 6*1024**3, 'A capture boundary lacked canonical 6 GiB commit')
    counts = {}
    for label in LABELS:
        with Image.open(package/'captures'/(label+'.png')) as picture:
            require(picture.size == (1994, 1105), 'The raw image framing changed')
            if label == 'proxy_support_color':
                image = picture.convert('RGB')
                for name, bounds in REGIONS.items():
                    count = (bounds[2]-bounds[0])*(bounds[3]-bounds[1])
                    require(Counter(image.crop(bounds).getdata()) == {(204, 204, 204): count},
                            'The strict front COLOR ROI changed: '+name)
                    counts[name] = count
                require(all(image.getpixel(point) == (255, 255, 255)
                            for point in ((997, 439), (920, 585))), 'The upward COLOR controls changed')
    close = load(package/'lifecycle/normal-close-receipt.json')
    exited = load(package/'lifecycle/exact-exit.json')
    start = load(package/'lifecycle/start-summary.json')
    finalized = load(package/'lifecycle/finalized-session-readback.json')
    require(close['normal_close_calls'] == 1 and close['force'] is False and close['returncode'] == 1 and
            'Game has not closed' in close['stderr'], 'The one normal-close timeout receipt changed')
    require(exited['completed'] and exited['process_or_window_mutation'] is False,
            'The exact exit observer did not complete')
    for kind, code in (('game', 3221226505), ('mcdk', 0)):
        row = exited['processes'][kind]
        require(row['state'] == 'exited' and row['exit_code'] == code and
                (row['pid'], row['identity']) == (start[kind+'_pid'], start[kind+'_identity']) ==
                (finalized[kind+'_pid'], finalized[kind+'_identity']), 'The exact '+kind+' exit changed')
    require(finalized['id'] == report['session']['id'] == start['id'] == close['session'] == exited['session'] and
            finalized['owner'] == amended['owner'] == report['session']['owner'] == close['owner'] == exited['owner'] and
            finalized['state'] == 'stopped' and finalized['ready'] is False,
            'The finalized owner/session identity changed')
    watch = load(package/'lifecycle/assertion-watch-ready.json')
    require(any(row['id'] == finalized['id'] and row['owner'] == finalized['owner'] and
                row['game_pid'] == start['game_pid'] for row in watch['eligible_sessions']),
            'The owner-bound assertion watcher did not cover the ready session')
    review = load(package/'review.json')
    require(review['production_qualified'] is False and review['native_neighbor_ao_qualified'] is False and
            review['body_lighting_closed'] is False and amended['production_qualified'] is False,
            'The negative diagnostic must not become product qualification')
    require(review['color_regions'] == {name: {'bounds': list(REGIONS[name]), 'pixels': count,
                                              'rgb': [204, 204, 204]} for name, count in counts.items()},
            'The reviewed negative region counts changed')
    return {'verified': True, 'payload_files': len(index['files']), 'raw_images': 3,
            'color_pixels': sum(counts.values()), 'commit_minimum_bytes': minimum,
            'native_neighbor_ao_qualified': False, 'production_qualified': False,
            'game_exit_hex': exited['processes']['game']['exit_code_hex'], 'finalized': True}


def pack(package):
    require(not package.exists(), 'Choose a fresh package directory')
    import sys
    sys.path.insert(0, str(ROOT/'tools'))
    from prepare_shelf_render_palette_r21 import verify as verify_live
    frozen = verify_live(CONTROL/'frozen.json')
    files = {}
    def add(name, source):
        require(name not in files and source.is_file(), 'A package source is missing or duplicated: '+name)
        files[name] = source
    for name in (HELPER, 'tools/prepare_shelf_render_palette_r21.py', 'tools/probe_shelf_render_palette_r21.py',
                 'tools/verify_shelf_render_palette_r21.py', 'tests/test_shelf_render_palette_candidate_r21.py',
                 'tests/test_shelf_render_palette_guard_r21.py'):
        add('inputs/'+name, ROOT/name)
    for target, source in (
            ('verify.py', Path(__file__)), ('freeze/original.json', ORIGINAL/'frozen.json'),
            ('freeze/amended.json', CONTROL/'frozen.json'), ('freeze/native-control.json', Path(frozen['source_freeze'])),
            ('compile/original.json', ORIGINAL/'compile.json'), ('compile/amended.json', CONTROL/'compile.json'),
            ('inputs/run.py', ORIGINAL/'run.py'), ('inputs/amended_run.py', CONTROL/'run.py'),
            ('inputs/prepare-amendment.py', CONTROL/'prepare.py'), ('inputs/review-acquisition.py', CONTROL/'review.py'),
            ('inputs/original_shelf_render_palette_candidate_r21.py', CONTROL/'original_shelf_render_palette_candidate_r21.py'),
            ('inputs/mcdev.json', Path(frozen['project'])/'.mcdev.json'),
            ('inputs/native-reference.json', ROOT/'.runtime/shelf-skeleton-r21-v1/reference.json'),
            ('plan/original.md', ORIGINAL/'RUN.md'), ('plan/state-amendment.md', ORIGINAL/'STATE_AMENDMENT.md'),
            ('plan/guarded.md', CONTROL/'RUN.md'), ('review.json', CONTROL/'review.json')):
        add(target, source)
    for name in frozen['changed_paths']:
        add('overlay/'+name, Path(frozen['project'])/name)
    for name in ('report.json',)+tuple(label+'.png' for label in LABELS):
        add('captures/'+name, CONTROL/'captures/south-full-palette'/name)
    for name in ('start-summary.json', 'normal-close-receipt.json', 'exact-exit.json',
                 'finalized-session-readback.json', 'assertion-watch-ready.json', 'launch-attempt.json', 'frozen-project.json'):
        add('lifecycle/'+name, CONTROL/'launch'/name)
    package.mkdir(parents=True)
    for name, source in files.items():
        target = package/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (package/'.gitattributes').write_text('** -text -diff whitespace=cr-at-eol\n', encoding='ascii', newline='\n')
    (package/'README.md').write_text('''# Full-Palette Shelf Diagnostic V5

Exactly three new raw images: native shelf/support, one same-Combine proxy/support,
and its COLOR readback. No original V1/V4 image archive or game clone is included.
Frozen manifests and six overlay resources bind the source and amendment history.

The three front interior regions contain 25280 pixels, all byte204 gray; upward
controls are byte255. Including the cyan support in the same Combine did not
reproduce the previously measured native vertical COLOR gradient in this fixture.
This is a negative south/oak/unpowered diagnostic. Native AO, directional shading,
packed-context runtime and production qualification remain open. No scalar or
height fit is used.

The acquisition completed/restored with unchanged source and no cleanup errors.
One force=False normal close timed out; no retry or force followed. Exact handles
observed game35000 exit 0xC0000409 and MCDK6932 exit0 at 07:18:27 Asia/Shanghai.
Finalized registry readback is stopped/readyFalse. Finalize command exit0 is
transcript-attested; its stdout was not separately saved. Original receipts and
reports remain byte-exact. No session token or private-start-result is included.

Replay with Python 3 and Pillow, without Minecraft or access to the original clone:

```powershell
python -B -X utf8 verify.py verify --package .
```

The verifier recomputes all indexed bytes, both freeze/compiler bindings, the
single-helper amendment, six overlay resources, camera/palette/replication facts,
strict COLOR pixels, canonical memory boundaries and exact lifecycle identities.
The source native-control manifest is prerequisite metadata only; its older
runtime images are not copied here. Historical unrelated watcher entries are
preserved in the original ready snapshot and are not attributed to this owner.
''', encoding='ascii', newline='\n')
    rows = {path.relative_to(package).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
            for path in package.rglob('*') if path.is_file()}
    (package/'index.json').write_text(json.dumps({'schema_version': 1,
        'kind': 'shelf_same_combine_negative_r21_v5', 'raw_images': 3,
        'production_qualified': False, 'native_neighbor_ao_qualified': False, 'files': rows}, indent=2)+'\n',
        encoding='ascii', newline='\n')
    verify_live(CONTROL/'frozen.json')
    result = verify(package)
    result['index_sha256'] = sha(package/'index.json')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('pack', 'verify'))
    parser.add_argument('--package', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(pack(args.package) if args.action == 'pack' else verify(args.package)))


if __name__ == '__main__':
    main()
