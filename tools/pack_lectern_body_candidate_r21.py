"""Seal or independently verify the isolated plain24 lectern body experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / '.runtime/lectern-body-candidate-r21'
EVIDENCE = ROOT / 'docs/evidence/lectern-body-candidate-r21-offline-v1'
PREFIX = 'behavior_pack/modern_projection/projection/'
HOSTS = ('probe_runtime.py', 'probe_runtime_v2.py', 'probe_runtime_v3.py',
         'review_plain.py', 'prepare_cold_launch.py', 'prelaunch-v1.json')
DEPENDENCIES = ('probe_liquid_pose_channel.py', 'probe_product_water.py',
                'capture_native_window.py', 'verify_debug_blueprints.py',
                'context_test_environment.py', 'verify_biome_shader.py',
                'watch_intrinsic_glint_exit_r21.py')
SOURCES = ('render_context.py', 'lectern_body.py', 'geometry_palette.py',
           'entity_render.py', 'visible_actor.py', 'book_render_plan.py',
           'book_preview.py', 'book_projection.py', 'book_profile.py',
           'projection_companions.py', 'bridge.py', 'world_projection.py',
           'occupancy.py', 'occupancy_shader.py', 'render_layout.py',
           'model.py', 'codec.py', 'semantic_wire.py', 'cell.py')
PHASES = ('body_only', 'full', 'missing', 'excluded', 'present')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def verify(package):
    manifest = load(package / 'manifest.json')
    for name, expected in manifest['files'].items():
        source = package / name
        if sha(source) != expected['sha256'] or source.stat().st_size != expected['bytes']:
            raise ValueError('Sealed payload changed: ' + name)
    actual = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    if actual != set(manifest['files']) | {'manifest.json'}:
        raise ValueError('Package contains missing or unlisted files')
    report = load(package / 'valid/report.json')
    if any(report.get(key) is not True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('The plain24 experiment did not complete and restore unchanged sources')
    if report.get('cleanup_errors') or len(report['captures']) != 24 or set(report['scenes']) != {'plain'}:
        raise ValueError('Expected restored plain24 only')
    scene = report['scenes']['plain']
    if (scene['source']['native_input_equal_for_empty_and_book'] is not True or
            scene['source']['native_render_actor_empty'] is not True):
        raise ValueError('Native lectern body inputs differ')
    for phase in PHASES:
        row = scene[phase]
        count = 0 if phase in ('excluded', 'present') else 2
        books = int(phase in ('full', 'missing'))
        if (row['target_body_count'] != count or row['state']['book_models'] != books or
                row['state']['logical_source_unchanged'] is not True):
            raise ValueError('Unexpected native body or book ownership: ' + phase)
    for label, capture in report['captures'].items():
        receipt = capture['receipt']
        if (receipt['reliable'] is not True or receipt['agent_activation_allowed'] is not False or
                receipt['activation_fallback'] is not False or
                capture['before'] != capture['after'] or
                sha(package / 'valid' / Path(receipt['path']).name) != receipt['sha256']):
            raise ValueError('Changed or unreliable native frame: ' + label)
    exits = load(package / 'lifecycle/exit-observation.json')
    if exits['completed'] is not True or any(row['state'] != 'exited' for row in exits['processes'].values()):
        raise ValueError('Exact exit observation is incomplete')
    return dict(files=len(manifest['files']), captures=24,
                manifest_sha256=sha(package / 'manifest.json'),
                report_sha256=sha(package / 'valid/report.json'),
                game_exit_code_hex=exits['processes']['game']['exit_code_hex'])


def pack(args):
    if args.output.exists():
        raise ValueError('Choose a fresh package output')
    prelaunch = load(HERE / 'prelaunch-v1.json')
    project = Path(prelaunch['project'])
    report = load(HERE / 'runtime-plain-v3/report.json')
    if report['source_sha256'] != prelaunch['source_sha256']:
        raise ValueError('Runtime source snapshot differs from cold prelaunch')
    if not sha(project / '.mcdev.json') == report['config_sha256'] == prelaunch['config_sha256']:
        raise ValueError('Cold-launch configuration changed')
    for name, expected in prelaunch['source_sha256'].items():
        if sha(project / name) != expected:
            raise ValueError('Cold candidate source changed: ' + name)
    if sha(HERE / 'probe_runtime.py') != prelaunch['host_sha256']:
        raise ValueError('The sealed base runtime host changed')
    if sha(HERE / 'probe_runtime_v3.py') != report['host_sha256']:
        raise ValueError('The executed v3 host changed')
    for name, expected in report['host_dependencies'].items():
        if sha(ROOT / 'tools' / name) != expected:
            raise ValueError('Executed shared host dependency changed: ' + name)
    if sha(EVIDENCE / 'manifest.json') != prelaunch['offline_evidence_manifest_sha256']:
        raise ValueError('The admitted offline candidate evidence changed')
    session = load(args.session)
    if any(session[key] != report['session'][key] for key in report['session']):
        raise ValueError('Launch and capture sessions differ')
    sources = {Path('host') / name: HERE / name for name in HOSTS}
    sources.update({Path('host/dependencies') / name: ROOT / 'tools' / name for name in DEPENDENCIES})
    sources[Path('host') / Path(__file__).name] = Path(__file__)
    sources[Path('offline/manifest.json')] = EVIDENCE / 'manifest.json'
    for destination, directory in (('failed-v1', 'runtime-plain-v1'),
                                   ('failed-v2', 'runtime-plain-v2'), ('valid', 'runtime-plain-v3'),
                                   ('review', 'runtime-plain-v3-review')):
        for source in sorted((HERE / directory).iterdir()):
            if source.is_file():
                sources[Path(destination) / source.name] = source
    for name in SOURCES:
        source = project / PREFIX / name
        if sha(source) != report['source_sha256'][PREFIX + name]:
            raise ValueError('A captured business source changed: ' + name)
        sources[Path('sources') / PREFIX / name] = source
    for name in ('resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex',
                 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment',
                 'resource_pack/materials/terrain.material', '.mcdev.json'):
        sources[Path('sources') / name] = project / name
    sources[Path('lifecycle/exit-observation.json')] = HERE / 'exit-observation-v1.json'
    args.output.mkdir(parents=True)
    for relative, source in sources.items():
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    launch = {key: session[key] for key in ('id', 'owner', 'project', 'created_at',
        'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'noactivation')}
    launch['noactivation'] = {key: launch['noactivation'][key] for key in (
        'requested', 'dll', 'mcdk', 'user_foreground_allowed', 'agent_activation_allowed')}
    lifecycle = dict(normal_stop_requested=True, normal_stop_returncode=1,
        normal_stop_message='Game has not closed; inspect it or explicitly use stop --force',
        force_stop_used=False, exact_exit_handles_opened_before_ready=True,
        first_ready_only_watcher_rejected_starting_without_opening_handles=True,
        startup_watcher_reads_owner_bound_session_with_live_false=True,
        watcher_still_checks_exact_handle_identity_and_executable=True,
        game_shutdown_passed=False,
        limit='The game exited with 0xC0000409 after ordinary stop; cause is unclassified.')
    (args.output / 'lifecycle/launch.json').write_text(json.dumps(launch, indent=2) + '\n', encoding='ascii')
    (args.output / 'lifecycle/stop.json').write_text(json.dumps(lifecycle, indent=2) + '\n', encoding='ascii')
    readme = '''# Native Lectern Body: Isolated Plain24 Candidate

This package records one real west-facing lectern state (`aux=1`, not powered),
seen from four fixed cameras. It does not establish four block directions.
Main business sources and admission gates have not changed.

## Native Result and Remaining Limits

The world contains an empty lectern and a genuinely item-used book lectern,
each on a cyan support. Native material/actor inputs are equal; both rendered
actors are `{}`. Full logical NBT remains in the document for the book owner.

All 24 v3 captures completed and restored unchanged sources, with zero cleanup
errors. Body-only, full and missing phases generate two target-only native
bodies outside packed context. Full/missing generate one custom book group;
body-only generates none. Hidden and already-present targets generate no
candidate body or book. The complete candidate top boards are visible from
south, north, east and west. The earlier packed-context notch is absent.

All four native-resolution review sheets were opened and inspected. The two
bodies overlap from east/west. Body-only shows no native duplicate book; full
and missing show a single custom book. This count does not prove book pixels:
the native world/present reference has no visible book from south/east while
the custom owner is visible there. Preserve that directional discrepancy.

The independent cyan-only clipping control, strict pixel boundary checks,
upper/side neighbors and separate cardinal block states remain open. There
is no whole-image IoU admission, no powered appearance admission and no main
candidate gate change. This is evidence for the isolated clipping candidate.

## Retained Host Failures

`failed-v1` has zero captures. Its host asserted a no-op air-to-air native write.
It restored world, inventory, camera, environment and Session successfully.
`failed-v2` retains four world captures. Its direct in-memory `to_data` /
`from_data` call hit Python 2 numeric scalar wire validation. It also restored
successfully. V3 adds the ordinary JSON encode/decode boundary. V2 also makes
air clearing idempotent and verifies actual block readback. The sealed base
host and business sources are unchanged; all three host files are retained.

## Shutdown and Reproduction

The ordinary managed stop returned 1. Exact retained process handles observed
game exit `0xC0000409` and MCDK exit `0`. No force stop was used. Scene restoration
passed; game shutdown is not a passed lifecycle check. Its cause is unclassified.

`lifecycle/launch.json` omits routing tokens and unrelated foreground details.
The existing handle watcher was used during startup with readiness checking
disabled only for reading the owner-bound session. It still validated each
retained native process handle's creation identity and executable before waiting.

`host/prelaunch-v1.json` binds all 3093 cold sources, configuration, the base
host and the earlier offline evidence manifest. `sources` freezes the scoped
business and shared shader inputs. `valid/report.json` records native palette
receipts, fixed camera states, WGC hashes and source hashes. No image alignment,
rescaling or recoloring is used for the individual review crops.

Run `python tools/pack_lectern_body_candidate_r21.py --verify <package>` to check
the self-contained payload, acquisition hashes, object counts and exit evidence.
Rebuild review crops using `host/review_plain.py valid/report.json --output
<fresh-review-directory>`. The JSON and PNG evidence also remain usable after
the original `.runtime` directory is removed.
'''
    (args.output / 'README.md').write_text(readme, encoding='ascii')
    manifest = dict(schema=1, created_at=datetime.now(timezone.utc).isoformat(),
        stage='isolated_native_lectern_plain24', product_qualified=False,
        four_block_directions_qualified=False, book_pixel_parity_qualified=False,
        lifecycle_qualified=False, offline_commit='e269225f', captures=24, files={})
    for source in sorted(args.output.rglob('*')):
        if source.is_file():
            manifest['files'][source.relative_to(args.output).as_posix()] = dict(
                sha256=sha(source), bytes=source.stat().st_size)
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='ascii')
    return verify(args.output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        result = verify(args.verify)
    else:
        if not args.session or not args.output:
            parser.error('Packaging requires --session and --output')
        result = pack(args)
    print(json.dumps(result))
