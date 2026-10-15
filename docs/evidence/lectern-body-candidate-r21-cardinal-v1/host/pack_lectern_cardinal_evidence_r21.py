"""Seal or replay the actual-cardinal40 lectern candidate, retaining failures."""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / '.runtime/lectern-body-candidate-r21'
PREFIX = 'behavior_pack/modern_projection/projection/'
SOURCES = ('render_context.py', 'lectern_body.py', 'geometry_palette.py', 'entity_render.py',
           'visible_actor.py', 'book_render_plan.py', 'book_preview.py', 'book_projection.py',
           'book_profile.py', 'projection_companions.py', 'bridge.py', 'world_projection.py',
           'occupancy.py', 'occupancy_shader.py', 'render_layout.py', 'model.py', 'codec.py',
           'semantic_wire.py', 'cell.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii')


def verify(package, replay=True):
    manifest = load(package / 'manifest.json')
    for name, row in manifest['files'].items():
        path = package / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    actual = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    assert actual == set(manifest['files']) | {'manifest.json'}
    report = load(package / 'valid/report.json')
    prepared = load(package / 'frozen/manifest.json')
    assert report['source_sha256'] == prepared['source_sha256']
    assert all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged'))
    assert report['planned_captures'] == len(report['captures']) == 40 and not report['cleanup_errors']
    assert report['host_sha256'] == prepared['host_sha256'] == sha(package / 'host/probe_holdout.py')
    assert report['config_sha256'] == prepared['config_sha256'] == sha(package / 'sources/.mcdev.json')
    for name, row in prepared['files'].items():
        target = package / ('host/' + Path(name).name if name.startswith('host/') else 'host/' + name)
        assert sha(target) == row['sha256']
    for path in (package / 'sources').rglob('*'):
        if path.is_file() and path.name != '.mcdev.json':
            name = path.relative_to(package / 'sources').as_posix()
            assert sha(path) == report['source_sha256'][name]
    observations = load(package / 'review/observations.json')
    assert observations['raw_report_sha256'] == sha(package / 'valid/report.json')
    assert observations['analysis_sha256'] == sha(package / 'review/analysis.json')
    assert observations['native_book_fixture']['book_oracle_validated'] is False
    assert observations['native_book_fixture']['product_book_pixel_failure_claimed'] is False
    assert observations['native_body_oracle']['south_empty_world_valid'] is False
    assert observations['hidden_boundary']['cyan_hidden_boundary_passed'] is False
    assert observations['production_qualified'] is False
    exits = load(package / 'lifecycle/exact-exit.json')
    assert exits['completed'] and all(row['state'] == 'exited' for row in exits['processes'].values())
    assert exits['processes']['game']['exit_code_hex'] == '0xC0000409'
    assert exits['processes']['mcdk']['exit_code_hex'] == '0x00000000'
    lifecycle = load(package / 'lifecycle/summary.json')
    assert lifecycle['force_used'] is False and lifecycle['finalize_state'] == 'stopped'
    if replay:
        spec = importlib.util.spec_from_file_location('sealed_cardinal_review', package / 'host/review_holdout.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='lectern-cardinal-replay-') as temp:
            output = Path(temp) / 'review'
            with contextlib.redirect_stdout(io.StringIO()):
                module.analyze(package / 'valid/report.json', output)
            for path in output.iterdir():
                assert sha(path) == sha(package / 'review' / path.name), path.name
    return {'files': len(manifest['files']), 'captures': 40, 'replayed': replay,
            'manifest_sha256': sha(package / 'manifest.json'),
            'report_sha256': sha(package / 'valid/report.json'), 'production_qualified': False}


def pack(output):
    assert not output.exists()
    frozen = HERE / 'holdout-prepare-v1'
    prepared = load(frozen / 'manifest.json')
    report = load(HERE / 'runtime-holdout-v1/report.json')
    assert report['source_sha256'] == prepared['source_sha256']
    project = Path(prepared['project'])
    assert all(sha(project / name) == expected for name, expected in report['source_sha256'].items())
    session = load(HERE / 'holdout-start-v1.json')
    finalized = load(HERE / 'holdout-finalize-v1.stdout.json')
    assert finalized['state'] == 'stopped'
    assert all(session[key] == report['session'][key] for key in report['session'])
    sources = {Path('host') / Path(__file__).name: Path(__file__),
        Path('host/review_holdout.py'): HERE / 'review_holdout.py',
        Path('review/observations.json'): HERE / 'holdout-review-observations-v1.json',
        Path('frozen/manifest.json'): frozen / 'manifest.json',
        Path('frozen/prelaunch.json'): HERE / 'holdout-prelaunch-v1.json',
        Path('lifecycle/exact-exit.json'): HERE / 'holdout-exit-observation-v1.json',
        Path('lifecycle/normal-stop.stderr.txt'): HERE / 'holdout-stop-v1.stderr.txt'}
    for name, row in prepared['files'].items():
        source = frozen / name
        assert sha(source) == row['sha256']
        destination = Path('host') / Path(name).name if name.startswith('host/') else Path('host') / name
        sources[destination] = source
    for name in SOURCES:
        sources[Path('sources') / PREFIX / name] = project / PREFIX / name
    for name in ('resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex',
                 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment',
                 'resource_pack/materials/terrain.material', '.mcdev.json'):
        sources[Path('sources') / name] = project / name
    for destination, directory in (('valid', 'runtime-holdout-v1'), ('review', 'runtime-holdout-v1-review')):
        for source in sorted((HERE / directory).iterdir()):
            if source.is_file():
                sources[Path(destination) / source.name] = source
    output.mkdir(parents=True)
    for relative, source in sources.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    launch = {key: session[key] for key in ('id', 'owner', 'project', 'created_at', 'game_pid',
                                          'game_identity', 'mcdk_pid', 'mcdk_identity')}
    launch['noactivation'] = {key: session['noactivation'][key] for key in
        ('requested', 'dll', 'mcdk', 'user_foreground_allowed', 'agent_activation_allowed')}
    save(output / 'lifecycle/launch.json', launch)
    save(output / 'lifecycle/summary.json', {'normal_stop_requested': True,
        'normal_stop_returncode': 1, 'force_used': False, 'exact_observer_started_after_ready': True,
        'finalize_returncode': 0, 'finalize_state': finalized['state'],
        'owned_game_identity_after_exit': None, 'owned_mcdk_identity_after_exit': None,
        'game_shutdown_qualified': False,
        'limit': 'Ordinary stop timed out; the retained handle later reported 0xC0000409. Cause is unclassified.'})
    (output / 'README.md').write_text('''# Native Lectern Actual-Cardinal40 Holdout

This is an isolated, unpowered candidate experiment, not a production admission.
Four actual source states south0/west1/north2/east3 use one fixed oblique camera.
Each independent 3x3x3 document contains one target and one cyan lower support.
Empty and real writable-book targets exercise world/full/missing/hidden; four
book cases add body_only. An independent two-cyan control contributes four
frames. All 40 raw PNGs and native capture receipts are retained unchanged.

Acquisition completed and restored the inventory, world, player/camera,
environment and session; cleanup errors are empty and all 3093 frozen sources
are unchanged. Runtime plus restoration took 252.795 seconds. All nine
native-pixel review sheets were opened. API replication and owner counts are
recorded separately from visible pixels.

## Preserved Failures and Limits

The first south_empty_world frame does not visibly contain the target or its
cyan support, although the offset stone reference is visible. This world
oracle is invalid. The other seven lectern world frames visibly contain their
native bodies. Four orientations of full/missing have complete visible top
boards without the former packed-context cutout. Four body_only controls show
no book. Active full/missing/body_only routes emit exactly one native target,
with no lectern leaked into packed neighbor context.

All eight lectern hidden frames preserve a lower cyan support with a visible
top face. The independent cyan_hidden control fails: the lower cyan side faces
remain, but its top face is absent and background shows through. The candidate
does not pass the independent hidden support boundary.

The four native world book cases contain blank writable_book items inserted
by actual inventory and PlayerUseItemToPos. Server NBT hasBook=1/Count1 and
totalPages=0. Client palette actor is empty; complete client book NBT was not
acquired. World books look absent while custom full/missing books are visible.
The native book oracle is unvalidated. This is neither book parity nor an
adjudicated product book pixel failure. A separate native authored-book oracle
is only offline prepared and is not part of this executed evidence package.

Ordinary stop returned 1. Exact retained process handles then observed game
0xC0000409 and MCDK 0; both identities were independently absent before a second
ordinary stop finalized the stopped registry state. No force stop was used.
Fixture restoration passed; normal game shutdown did not qualify.

## Replay

Run the bundled host/pack_lectern_cardinal_evidence_r21.py --verify PACKAGE.
Verification hashes every payload, checks exact source/host/receipt bindings,
and rebuilds all 40 unscaled crops and nine sheets from the archived raw PNGs.
Rebuilt analysis and PNGs must be byte-identical. Review/observations.json is
the explicit human review, separate from automatically verified acquisition.
No alignment, rescaling, recoloring, color mask or image fitting is applied.
No powered appearance, production support, book parity or lifecycle admission
is granted. Main business sources and admission gates remain unchanged.
''', encoding='ascii')
    manifest = {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
        'captures': 40, 'production_qualified': False, 'native_book_oracle_validated': False,
        'cyan_hidden_boundary_passed': False, 'normal_game_shutdown_qualified': False,
        'source_digest': prepared['source_digest'], 'files': {}}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            manifest['files'][path.relative_to(output).as_posix()] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    save(output / 'manifest.json', manifest)
    return verify(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.verify.resolve()) if args.verify else pack(args.output.resolve())))
