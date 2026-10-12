"""Freeze the reviewed R13 owner, actual dependencies and loaded anchor resources."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from run_client_anchor_paper_doll import ROOT, ENTITIES, SESSION, ARTIFACTS, BUNDLE, load_probe, \
    PROBE_SHA256, PLAN_SHA256, GUARD_SHA256, HELPER_SHA256, EVIDENCE_PREFIX, verify_loaded_resources, \
    NORMAL_SECONDS, CLEANUP_SECONDS, OUTER_SECONDS, WGC_EXE, EXE_SHA256, WRAPPER_SHA256
from session_pack_stage import digest


WRAPPER_PIN = 'ff4218f7c9dd1a72436f1c4645ca1dbde4e100c111143d804cf3f6ef439e88de'
TESTS_PIN = 'f125620849ca9648a9b132c9fefc090206ac1498071c0f50cfbe20f96511d929'


def main():
    target = ARTIFACTS / (EVIDENCE_PREFIX + '.sources')
    index = ARTIFACTS / (EVIDENCE_PREFIX + '.sources.index.json')
    assert not target.exists() and not index.exists()
    probe, source = load_probe()
    bundle, plan = probe.verify_bundle(BUNDLE)
    resources = verify_loaded_resources(probe, bundle)
    executor = sys.modules['execute_frame_item_translation']
    pins = {
        ROOT / '.runtime/frame-baseline-plan-r11/run_client_anchor_paper_doll.py': WRAPPER_PIN,
        ROOT / '.runtime/frame-baseline-plan-r11/test_run_client_anchor_paper_doll.py': TESTS_PIN,
        ROOT / '.runtime/frame-baseline-plan-r11/session_pack_stage.py': GUARD_SHA256,
        source: PROBE_SHA256,
        bundle / 'plan.json': PLAN_SHA256,
        ENTITIES / 'tests/test_client_anchor_paper_doll.py':
            '14fdf5ca044adbe65493af204b0835885aa062c1e6b179a7a56307fdc4929b95',
        ENTITIES / 'docs/CLIENT_ANCHOR_PAPER_DOLL_DIAGNOSTIC_R13.md':
            '186e9fd7431355e7bf05e3bc207eb38b361a679403ae13c80e3171589c545324',
        Path(probe.base.__file__).resolve(): probe.BASE_SHA256,
        Path(executor.__file__).resolve(): probe.base.EXECUTOR_SHA256,
        ROOT / 'tools/capture_native_window.py': WRAPPER_SHA256,
        WGC_EXE: EXE_SHA256,
    }
    for name, expected in HELPER_SHA256.items():
        for root in (ROOT, ENTITIES):
            pins[root / 'tools' / (name + '.py')] = expected
    for row in resources['resources'].values():
        pins[Path(row['source'])] = row['sha256']
    for path, expected in pins.items():
        assert digest(path) == expected, path
    copies = [
        (ROOT / '.runtime/frame-baseline-plan-r11' / name,
         'frame/.runtime/frame-baseline-plan-r11/' + name)
        for name in ('run_client_anchor_paper_doll.py', 'test_run_client_anchor_paper_doll.py',
                     'freeze_client_anchor_paper_doll.py', 'session_pack_stage.py',
                     'run_frame_translation.py', 'run_native_item_paper_doll.py', 'check_runtime_health.py')
    ]
    copies.extend([
        (source, 'entities/tools/probe_client_anchor_paper_doll.py'),
        (ENTITIES / 'tests/test_client_anchor_paper_doll.py', 'entities/tests/test_client_anchor_paper_doll.py'),
        (ENTITIES / 'docs/CLIENT_ANCHOR_PAPER_DOLL_DIAGNOSTIC_R13.md',
         'entities/docs/CLIENT_ANCHOR_PAPER_DOLL_DIAGNOSTIC_R13.md'),
        (ROOT / '.mcdev.json', 'frame/.mcdev.json'),
        (SESSION / 'session.json', 'ready-session.json'),
        (SESSION / '.mcdev.json', 'generated.mcdev.json'),
    ])
    for pack, row in resources['packs'].items():
        copies.append((Path(row['source']) / 'manifest.json', 'loaded/' + pack + '/source-manifest.json'))
        copies.append((Path(row['world_manifest']), 'loaded/' + pack + '/world-manifest.json'))
        for location, path in row['lookup_roots'].items():
            copies.append((Path(path) / 'manifest.json', 'loaded/' + pack + '/' + location + '-manifest.json'))
    for name, row in resources['resources'].items():
        copies.append((Path(row['source']), 'loaded/resources/source/' + name))
        for location, lookup in row['lookups'].items():
            copies.append((Path(lookup['path']), 'loaded/resources/' + location + '/' + name))
    loaded_sources = set()
    actual_modules = {}
    for name, module in list(sys.modules.items()):
        module_file = getattr(module, '__file__', None)
        if not module_file or Path(module_file).suffix != '.py':
            continue
        path = Path(module_file).resolve()
        for root in (ROOT, ENTITIES):
            if path.is_relative_to(root):
                loaded_sources.add(path)
                actual_modules[name] = {'path': str(path), 'sha256': digest(path)}
                break
    for path in sorted(loaded_sources):
        for root, namespace in ((ROOT, 'frame'), (ENTITIES, 'entities')):
            if path.is_relative_to(root):
                copies.append((path, namespace + '/' + path.relative_to(root).as_posix()))
                break
    for name in HELPER_SHA256:
        for root, namespace in ((ROOT, 'frame'), (ENTITIES, 'entities')):
            copies.append((root / 'tools' / (name + '.py'), namespace + '/tools/' + name + '.py'))
    copies.extend([
        (ARTIFACTS / name, 'plans/' + name)
        for name in ('frame-shader-staging-execution-plan-v1.json',
                     'frame-shader-staging-execution-plan-v4-physical-volume-amendment.json',
                     'frame-shader-staging-original-pack-v1.index.json')
    ])
    target.mkdir()
    shutil.copytree(bundle, target / 'bundle')
    copied = set()
    for source_path, relative in copies:
        if relative in copied:
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination)
        assert digest(source_path) == digest(destination), source_path
        copied.add(relative)
    rows = [{'path': path.relative_to(target).as_posix(), 'bytes': path.stat().st_size,
             'sha256': digest(path)} for path in sorted(target.rglob('*')) if path.is_file()]
    with index.open('x', encoding='ascii') as output:
        json.dump({'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                   'directory': str(target), 'files': rows,
                   'reviewed_sources': {str(path): expected for path, expected in pins.items()},
                   'actual_local_imports': actual_modules, 'loaded_anchor_resources': resources,
                   'python': {'version': sys.version, 'path': sys.executable, 'sha256': digest(Path(sys.executable))},
                   'maximum_native_frames': 16, 'normal_limit_seconds': NORMAL_SECONDS,
                   'cleanup_deadline_seconds': CLEANUP_SECONDS, 'outer_limit_seconds': OUTER_SECONDS,
                   'shader_or_pack_mutation_authorized': False,
                   'world_or_inventory_mutation_authorized': False,
                   'player_position_mutation_authorized': False,
                   'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
                   'enchantment_glint_accepted': False}, output, ensure_ascii=True, indent=2)
        output.write('\n')
    for row in rows:
        assert digest(target / row['path']) == row['sha256']
    assert resources == verify_loaded_resources(probe, bundle)
    print(json.dumps({'files': len(rows), 'index_sha256': digest(index),
                      'owner_wrapper_sha256': WRAPPER_PIN, 'owner_tests_sha256': TESTS_PIN,
                      'actual_local_modules': len(actual_modules), 'anchor_resources': len(resources['resources'])}))


if __name__ == '__main__':
    main()
