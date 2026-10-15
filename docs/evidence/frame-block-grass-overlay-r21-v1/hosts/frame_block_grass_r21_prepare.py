"""Prepare a fresh grass-only project; no world, launch, or screenshot action."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.runtime/projects/frame-block-r21-light-holdout-v1'
PROJECT = ROOT / '.runtime/projects/frame-block-grass-overlay-r21-v1'
CONTROL = ROOT / '.runtime/frame-block-grass-overlay-r21-control-v1'
OVERLAY = ROOT / '.runtime/frame-block-grass-overlay-candidate-r21-v1'
sys.path[:0] = [str(BASE / 'tools'), str(ROOT / 'tools')]
from item_sprite_capture_contract import snapshot_sources, snapshot_digest
from archive_frame_block_evidence_r21 import import_closure


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def main():
    assert not PROJECT.exists() and not CONTROL.exists()
    before = snapshot_sources(BASE)
    assert snapshot_digest(before) == '7a9a00fd65e6f9ca88d143e71311371a90b63e65c1855bcc790e47247f62481f'
    overlay = json.loads((OVERLAY / 'candidate.json').read_bytes())
    assert overlay['affected_items'] == [['minecraft:grass_block', 0]]
    assert not any(overlay[key] for key in ('production_qualified', 'appearance_accepted', 'native_pixels_accepted'))
    PROJECT.mkdir(parents=True)
    CONTROL.mkdir(parents=True)
    for relative in before:
        destination = PROJECT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE / relative, destination)
    shutil.copy2(BASE / '.mcdev.json', PROJECT / '.mcdev.json')
    assert snapshot_sources(PROJECT) == before
    relative = overlay['changed_resource_paths'][0]
    assert sha(OVERLAY / 'override' / relative) == overlay['candidate_bitmap_sha256']
    shutil.copy2(OVERLAY / 'override' / relative, PROJECT / relative)
    profile_path = 'behavior_pack/modern_projection/projection/frame_block_item_data.py'
    values = runpy.run_path(str(PROJECT / profile_path))
    item = ('minecraft:grass_block', 0)
    selected = deepcopy(values['ITEMS'][item])
    selected['texture_sha256'] = overlay['candidate_bitmap_sha256']
    resource_files = {relative: sha(PROJECT / relative)}
    model = 'resource_pack/models/modern_projection/frame_block_items/' + overlay['resource_key'] + '_mesh.json'
    resource_files[model] = sha(PROJECT / model)
    for path in (PROJECT / 'resource_pack/shaders/glsl').glob('modern_projection_frame_block*'):
        resource_files[path.relative_to(PROJECT).as_posix()] = sha(path)
    contract = hashlib.sha256(b''.join(path.encode('ascii') + (PROJECT / path).read_bytes()
        for path in sorted(resource_files))).hexdigest()
    profile = {key: values[key] for key in ('SCHEMA_VERSION', 'LAYOUT_VERSION', 'ENGINE_VERSION', 'PALETTE_SHA256', 'POSE')}
    profile.update(RESOURCE_SHA256=contract, PRODUCTION_QUALIFIED=False,
        QUALIFICATION_SHA256=None, QUALIFICATION_RESOURCE_SHA256=None,
        QUALIFIED_MATERIALS=(), ITEMS={item: selected}, UNSUPPORTED={})
    assert profile['POSE']['scale_blocks'] == .25 and profile['POSE']['center_offset_blocks'] == [0., 0., .4375]
    (PROJECT / profile_path).write_bytes(('"""Grass-only overlay candidate; all native gates remain closed."""\n' +
        ''.join(key + ' = ' + repr(value) + '\n' for key, value in profile.items())).encode('ascii'))
    files = dict(resource_files)
    files[profile_path] = sha(PROJECT / profile_path)
    save(CONTROL / 'candidate.json', {'schema': 1, 'production_qualified': False,
        'appearance_accepted': False, 'native_pixels_accepted': False,
        'pose': profile['POSE'], 'items': [list(item)], 'base_light': .93,
        'base_light_general_acceptance': False, 'files': files,
        'mesh_sha256': {model: sha(PROJECT / model)}, 'resource_sha256': contract,
        'source_sha256': snapshot_digest(before), 'overlay_candidate_sha256': sha(OVERLAY / 'candidate.json'),
        'atlas_sha256': overlay['candidate_bitmap_sha256'],
        'limits': ['Only overlay alpha polarity changed relative to the captured baseline',
            'Existing empirical 0.93 remains unaccepted and unchanged', 'New pixels required for every view']})
    save(CONTROL / 'source-textures.json', {'minecraft:grass_block': {
        'atlas': relative, 'atlas_sha256': overlay['candidate_bitmap_sha256'],
        'original_atlas_sha256': overlay['original_bitmap_sha256'],
        'faces': overlay['resource']['faces'], 'rectangles': overlay['resource']['rectangles'],
        'overlay_recipe': 'bake_texture from corrected shared generator fd71754e',
        'appearance_accepted': False}})
    phases = []
    for identity, angle in (('front', 0), ('left75', -75), ('right75', 75)):
        matrix = {'schema': 1, 'production_qualified': False, 'cases': [{
            'id': 'grass_block.view' + str(angle), 'orientation': 'frame_f2_r0',
            'item': list(item), 'view_angle_degrees': angle, 'artificially_enchanted': False}]}
        save(CONTROL / (identity + '.json'), matrix)
        phases.append({'id': identity, 'angle': angle, 'time_of_day': 6000, 'cases': 1,
            'matrix': identity + '.json', 'matrix_sha256': sha(CONTROL / (identity + '.json')),
            'capture_output': str(ROOT / ('.runtime/frame-block-grass-overlay-r21-' + identity + '-v1')),
            'requires_first_image_review': identity != 'front'})
    external = CONTROL / 'external-host'
    host_files = {}
    for path in sorted(import_closure(ROOT, ['tools/watch_intrinsic_glint_exit_r21.py'])):
        destination = external / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, destination)
        host_files[path] = sha(destination)
    observer = external / 'tools/watch_intrinsic_glint_exit_r21.py'
    assert sha(observer) == 'aa436ee9a0f496554c69330d8456fa21b6bb551b63032f0b5a453ad9748646aa'
    after = snapshot_sources(PROJECT)
    changed = sorted(path for path in after if before.get(path) != after[path])
    assert changed == sorted([relative, profile_path])
    assert snapshot_sources(BASE) == before
    helpers = {'wgc': '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe',
        'mcdk': '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe',
        'guard': 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'}
    game = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/Minecraft.Windows.exe')
    plan = {'schema': 1, 'prepared': True, 'started': False, 'owner': 'item-r20',
        'project': str(PROJECT), 'source_sha256': snapshot_digest(after), 'sources': after,
        'base_source_sha256': snapshot_digest(before), 'base_source_unchanged': True,
        'changed_paths': changed, 'production_qualified': False, 'appearance_accepted': False,
        'candidate_sha256': sha(CONTROL / 'candidate.json'),
        'source_textures_sha256': sha(CONTROL / 'source-textures.json'),
        'configuration_sha256': sha(PROJECT / '.mcdev.json'),
        'launcher_sha256': sha(ROOT / '.runtime/frame_block_grass_r21_run.py'),
        'reviewer_sha256': sha(ROOT / '.runtime/frame_block_grass_r21_review.py'),
        'analysis_manifest_sha256': sha(ROOT / 'docs/evidence/frame-block-light-holdout-r21-v1/manifest.json'),
        'capture_host_sha256': sha(PROJECT / 'tools/frame_block_light_r21_host.py'),
        'external_host_files': host_files, 'helpers': helpers,
        'binaries': {path: sha(ROOT / path) for path in helpers.values()},
        'game_executable': str(game), 'game_executable_sha256': sha(game),
        'phases': phases, 'phase_policy': {'capture_admission_seconds': 150, 'target_wall_seconds': 180,
            'minimum_start_commit_gib': 9, 'runtime_commit_reserve_gib': 6, 'handle_limit': 200000},
        'calibration': 'Independent fresh three-view calibration in every single-case phase; no old PNG reuse',
        'scheduling': 'Front only initially; each oblique phase requires restored prior outcomes, bound front-review hash and explicit root inspected/scheduled flags',
        'fresh_world': True, 'world_copied': False,
        'observer_preflight': 'Exact external observer path plus entire static Python dependency closure verified before starting any game',
        'limits': ['No phase has been launched', 'No artificial enchantment probe for plain grass',
            'Empirical 0.93 retained unchanged; not universally accepted', 'No production catalog/profile/asset modifications']}
    save(CONTROL / 'plan.json', plan)
    print(json.dumps({key: plan[key] for key in ('prepared', 'started', 'source_sha256',
        'launcher_sha256', 'capture_host_sha256', 'changed_paths', 'phases')}))


if __name__ == '__main__':
    main()
