"""Freeze exact reviewed native item sources and owner capture dependencies."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from run_native_item_paper_doll import ROOT, ENTITIES, SESSION, ARTIFACTS, BUNDLE, load_probe, \
    PROBE_SHA256, PLAN_SHA256, GUARD_SHA256, HELPER_SHA256, EVIDENCE_PREFIX
from session_pack_stage import digest


def main():
    target = ARTIFACTS / (EVIDENCE_PREFIX + '.sources')
    index = ARTIFACTS / (EVIDENCE_PREFIX + '.sources.index.json')
    assert not target.exists() and not index.exists()
    probe, source = load_probe()
    bundle, plan = probe.verify_bundle(BUNDLE)
    pins = {
        ROOT / '.runtime/frame-baseline-plan-r11/run_native_item_paper_doll.py':
            '1390f778a20b5c0350b7cfebc40b4462a701fac16ce2240d2cecc50cb9399820',
        ROOT / '.runtime/frame-baseline-plan-r11/test_run_native_item_paper_doll.py':
            '16c90ae9611d4fb2f867fdeb509888ba0366a8acf720d88ea16f1feb28a25195',
        ROOT / '.runtime/frame-baseline-plan-r11/session_pack_stage.py': GUARD_SHA256,
        source: PROBE_SHA256,
        bundle / 'plan.json': PLAN_SHA256,
        ENTITIES / 'tests/test_native_item_paper_doll.py':
            '2ad2023e9f0e2bb08f9e0ea8f592ba81f0932dbb8696e80a4e8848902f0aae42',
        ENTITIES / 'docs/NATIVE_ITEM_PAPER_DOLL_DIAGNOSTIC_R12.md':
            'a1eb8cb230f4c1b845738eb45173dfd49fe186a8bb3c0c6f1fd62aab3708581f',
        ROOT / '.runtime/frame-baseline-plan-r11/read_native_screen_view.py':
            '51ce4af51ad4c8894c8b2b3cf497babc7ed3fba9a9baab79e84dd130f39c53f6',
        ARTIFACTS / 'native-item-paper-doll-r12.screen-view-readonly-v1.json':
            'd6320b2d4cba0cf65c7af9a92d552fc54c3940741a3026748be61fe01943dade',
    }
    for name, sha in HELPER_SHA256.items():
        for root in (ROOT, ENTITIES):
            pins[root / 'tools' / (name + '.py')] = sha
    for path, sha in pins.items():
        assert digest(path) == sha
    target.mkdir()
    shutil.copytree(bundle, target / 'bundle')
    copies = [
        (ROOT / '.runtime/frame-baseline-plan-r11' / name, 'frame/.runtime/frame-baseline-plan-r11/' + name)
        for name in ('run_native_item_paper_doll.py', 'test_run_native_item_paper_doll.py',
                     'session_pack_stage.py', 'run_frame_translation.py', 'freeze_native_item_paper_doll.py',
                     'read_native_screen_view.py')
    ]
    copies.extend([
        (source, 'entities/tools/probe_native_item_paper_doll.py'),
        (ENTITIES / 'tools/execute_frame_item_translation.py', 'entities/tools/execute_frame_item_translation.py'),
        (ENTITIES / 'tests/test_native_item_paper_doll.py', 'entities/tests/test_native_item_paper_doll.py'),
        (ENTITIES / 'docs/NATIVE_ITEM_PAPER_DOLL_DIAGNOSTIC_R12.md', 'entities/docs/NATIVE_ITEM_PAPER_DOLL_DIAGNOSTIC_R12.md'),
        (ENTITIES / 'behavior_pack/modern_projection/projection/entity_overlays.py',
         'entities/behavior_pack/modern_projection/projection/entity_overlays.py'),
        (ROOT / '.mcdev.json', 'frame/.mcdev.json'),
        (SESSION / 'session.json', 'ready-session.json'),
        (SESSION / '.mcdev.json', 'generated.mcdev.json'),
    ])
    copies.extend([
        (ROOT / 'tools' / name, 'frame/tools/' + name)
        for name in ('capture_native_window.py', 'capture_native_burst.py', 'verify_sign_visuals.py')
    ])
    copies.extend([
        (ROOT / '.agents/skills/pyreact-debugging/scripts' / name,
         'frame/.agents/skills/pyreact-debugging/scripts/' + name)
        for name in ('mcdk.py', '_session.py', '_window.py', '_game_bridge.py')
    ])
    copies.extend([
        (ARTIFACTS / name, 'plans/' + name)
        for name in ('frame-shader-staging-execution-plan-v1.json',
                     'frame-shader-staging-execution-plan-v4-physical-volume-amendment.json',
                     'frame-shader-staging-original-pack-v1.index.json',
                     'frame-item-translation-v2.world-restoration-supplement.json',
                     'frame-item-translation-v2.restored-reload-supplement.json',
                     'frame-item-translation-v2.post-restoration-health.json',
                     'native-item-paper-doll-r12.screen-view-readonly-v1.json')
    ])
    actual_helpers = {}
    for name in HELPER_SHA256:
        module_path = Path(sys.modules[name].__file__).resolve()
        actual_helpers[name] = {'path': str(module_path), 'sha256': digest(module_path)}
        for root, namespace in ((ROOT, 'frame'), (ENTITIES, 'entities')):
            copies.append((root / 'tools' / (name + '.py'), namespace + '/tools/' + name + '.py'))
    loaded_sources = set()
    for module in list(sys.modules.values()):
        module_file = getattr(module, '__file__', None)
        if module_file and Path(module_file).suffix == '.py':
            loaded_sources.add(Path(module_file).resolve())
    for path in sorted(loaded_sources):
        for root, namespace in ((ROOT, 'frame'), (ENTITIES, 'entities')):
            if path.is_relative_to(root):
                copies.append((path, namespace + '/' + path.relative_to(root).as_posix()))
                break
    copied = set()
    for source_path, relative in copies:
        if relative in copied:
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, destination)
        assert digest(source_path) == digest(destination)
        copied.add(relative)
    rows = [{'path': path.relative_to(target).as_posix(), 'bytes': path.stat().st_size,
             'sha256': digest(path)} for path in sorted(target.rglob('*')) if path.is_file()]
    with index.open('x', encoding='ascii') as output:
        json.dump({'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                   'directory': str(target), 'files': rows,
                   'reviewed_sources': {str(path): sha for path, sha in pins.items()},
                   'actual_pixel_helpers': actual_helpers,
                   'python': {'version': sys.version, 'path': sys.executable, 'sha256': digest(Path(sys.executable))},
                   'native_frames': 15, 'native_limit_seconds': 150, 'cleanup_reserve_seconds': 30,
                   'shader_or_pack_mutation_authorized': False}, output, ensure_ascii=True, indent=2)
        output.write('\n')
    for row in rows:
        assert digest(target / row['path']) == row['sha256']
    print(json.dumps({'files': len(rows), 'index_sha256': digest(index),
                      'owner_wrapper_sha256': pins[ROOT / '.runtime/frame-baseline-plan-r11/run_native_item_paper_doll.py']}))


if __name__ == '__main__':
    main()
