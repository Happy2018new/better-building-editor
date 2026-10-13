"""Freeze one priority native side/alpha diagnostic with bounded restoration."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PROJECT = Path(__file__).resolve().parents[1]
BASE = PROJECT / '.runtime/liquid-priority-r12-v11'
PREVIOUS = PROJECT / '.runtime/liquid-alpha-r12-v8/plan.json'


def fingerprint(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii')


if BASE.exists() or (PROJECT / '.mcdev.json').exists():
    raise ValueError('Fresh plan and original configuration absence required')
previous = json.loads(PREVIOUS.read_bytes())
BASE.mkdir()
shutil.copyfile(previous['configuration']['path'], BASE / 'configuration.json')
pack, host = {}, {}
for scope in ('behavior_pack', 'resource_pack', 'tools', '.agents/skills/pyreact-debugging/scripts'):
    rows = pack if scope.endswith('_pack') else host
    for path in sorted((PROJECT / scope).rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo'):
            continue
        if rows is host and path.suffix not in ('.py', '.ps1', '.cpp', '.h', '.json', '.cs'):
            continue
        relative = path.relative_to(PROJECT).as_posix()
        archive = BASE / 'sources' / relative
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, archive)
        rows[relative] = {'live': fingerprint(path), 'archive': fingerprint(archive)}
for relative in ('.runtime/prepare_liquid_priority_r12_v11.py', '.runtime/liquid_priority_session_r12_v11.py',
        '.runtime/probe_liquid_original_sides_r12_v11.py', '.runtime/liquid_passive_guard_r12_v8.py',
        '.runtime/liquid_priority_guard_r12_v9.py',
        '.runtime/read_native_capacity_snapshot_r12.py', '.runtime/runtime-health-r12/check_runtime_health.py',
        'tests/test_camera_projection_tool.py', 'tests/test_liquid_physical_readiness.py',
        '.runtime/test_liquid_priority_readiness_v11.py'):
    path = PROJECT / relative
    archive = BASE / 'sources' / relative
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, archive)
    host[relative] = {'live': fingerprint(path), 'archive': fingerprint(archive)}
plan = {'schema': 1, 'project': str(PROJECT), 'owner': 'liquid-r12-priority-v11',
    'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT).decode().strip(),
    'scope': 'Original-world8 then alpha6 native diagnostic only, all acceptance false',
    'runtime_pack_files': pack, 'host_helper_files': host, 'binaries': previous['binaries'],
    'configuration': fingerprint(BASE / 'configuration.json'),
    'game_executable': json.loads((BASE / 'configuration.json').read_bytes())['game_executable_path'],
    'previous_failure': fingerprint(PROJECT / '.runtime/liquid-alpha-r12-v8/calibrate-passive-health.json'),
    'previous_restoration': fingerprint(PROJECT / '.runtime/liquid-alpha-r12-v8/complete-restoration.json'),
    'previous_v9c_failed_readiness': fingerprint(PROJECT / '.runtime/liquid-priority-r12-v9c/physical-readiness.json'),
    'previous_v9c_cleanup': fingerprint(PROJECT / '.runtime/liquid-priority-r12-v9c/run.json'),
    'previous_v9d_deadline_failure': fingerprint(PROJECT / '.runtime/liquid-priority-r12-v9d/run.json'),
    'previous_v9d_calibration': fingerprint(PROJECT / '.runtime/liquid-priority-r12-v9d/camera-calibration.json'),
    'previous_v10_stale_camera_failure': fingerprint(PROJECT / '.runtime/liquid-priority-r12-v10/original-priority.json'),
    'previous_v10_restoration': fingerprint(PROJECT / '.runtime/liquid-priority-r12-v10/run.json'),
    'capacity_baseline': fingerprint(PROJECT / '.runtime/native-capacity-readonly-r12-v1.json'),
    'capacity_policy': {'root_authorized': True, 'active_limit': 5, 'owned_active_limit': 1,
        'baseline_exact_unchanged20_residuals_only': True, 'new_or_changed_or_uncertain_rows_count_active': True,
        'snapshot_before_single_launch': True, 'maximum_snapshot_age_seconds': 60,
        'residual_max_working_set_bytes_each': 65536, 'residual_max_private_bytes_each': 98304,
        'zero_threads_handles_virtual_cpu_required': True, 'OS_object_exit_or_destruction_proven': False},
    'fit_equivalence': fingerprint(PROJECT / '.runtime/calibration-fit-equivalence-v9.json'),
    'fit_source_pin': fingerprint(PROJECT / '.runtime/calibration-fit-equivalence-v9-source-pin.json'),
    'calibration': {'views': ['front', 'right', 'skyward_tilted'], 'fixture_lift_y': 30,
        'native_png_count': 6, 'fit_candidate_count': 1001, 'thresholds_relaxed': False,
        'each_view_fit_once': True, 'same_session_runtime_FOV_viewport_required': True,
        'raw_capture_and_per_view_signal_persisted': True, 'fitted_outline_deferred_to_final_analysis': True},
    'live_signal_cache': {'same_live_computed_masks_only': True,
        'ordered_key': ['view', 'shown_original_sha256', 'hidden_original_sha256'],
        'length_pair_order_mode_viewport_mismatch_rejected': True,
        'each_original_png_sha256_reverified_before_analysis': True,
        'replay_without_cache_recomputes_signals': True, 'thresholds_or_fit_changed': False},
    'camera_settle': {'predeclared_sdk_yaw_adjustments': [180., 0.],
        'actual_render_events_after_request_minimum': 2, 'stable_readbacks_required': 2,
        'actual_GetForward_to_target_cosine_exclusive_minimum': .99,
        'declaration_uses_settled_actual_camera': True,
        'capture_reapplies_pose_and_requires_same_frozen_actual_camera': True,
        'failed_capture_before_state_persisted_before_assert': True,
        'observer_removed_in_cleanup': True, 'position_geometry_pixel_thresholds_changed': False},
    'capture_schedule': {'preflight_png_count': 1, 'original_world_png_count': 8, 'alpha_png_count': 6,
        'total_native_png_count': 21,
        'original_sources': ['water_depth_0_foreground', 'water_depth_3_foreground'],
        'views': ['vnw', 'vse'], 'routes': ['native', 'full'], 'side_faces': ['north', 'west', 'south', 'east'],
        'whole8_geometry_preflight_before_first_water_png': True, 'minimum_low_side_pixels': 24,
        'native_server_client_before_after_readback': True, 'flow_frozen': True,
        'alpha_source': 'test.layers.water fence_rear supported_positive',
        'alpha_routes': ['scene', 'full', 'missing'], 'alpha_values': [0., 1.],
        'alpha_scope': 'Appearance/disappearance only; half transparency is NOT_TESTED',
        'alpha_source_body_layout_pose_ids_and_other_uniforms_fixed': True},
    'actual_world_gate': {'transport_ready_is_only_prerequisite': True,
        'manual_initialization_or_position_mutation': False,
        'business_requirements': ['owner', 'session', 'bridge', 'session.ready', 'bridge.session identity', 'hud'],
        'read_only_cheap_feet_poll_interval_seconds': .5, 'required_stable_samples': 3,
        'minimum_stable_seconds': 1., 'maximum_foot_delta': .05, 'same_floor_position_required': True,
        'single_player_client_server_agreement_required': True, 'dimension': 0,
        '216_cell_scan_once_after_stable_feet': True, 'full_reserve_failure_terminal': True,
        'existing_fresh_single_snapshot_before_fixture_retained': True,
        'first_actual_world_wgc_before_health_or_fixture': True,
        'whole_budget_reservation_required_before_world_fixture': True},
    'limits': {'startup_seconds': 180, 'launch_work_seconds': 180,
        'startup_phase_guard_outer_seconds': 240,
        'end_to_end_from_exact_game_creation_seconds': 300, 'pre_creation_fallback_end_to_end_seconds': 240,
        'ready_budget_origin': 'full actual UiInit + stable feet + reserved-area gate completion',
        'ready_outer_formula': 'min(actual-world-ready+150, exact-game-creation+300)',
        'insufficient_full150_reservation': 'read-only rejection before first fixture or WGC',
        'budget_change_basis': 'V9d measured signal times 8.157/7.936/7.407s plus repeated extraction; repeated live extraction now removed',
        'ready_normal_seconds': 120, 'ready_fixture_cleanup_seconds': 132, 'ready_outer_seconds': 150,
        'priority_rpc_seconds': 3, 'normal_owner_stop_seconds': 6, 'exact_force_wait_seconds_each': 1,
        'native_capture_helper_seconds': 15, 'single_cold_launch': True,
        'absolute_handles_cap': 100000, 'passive_interval_seconds': 5,
        'post_ready_growth_stop_minimum_delta': 2500, 'post_ready_growth_intervals': 3,
        'startup_and_actual_world_wait_growth_observation_only': True,
        'growth_stop_enabled_after_actual_world_gate': True},
    'guard_change': 'Startup180 with240 cleanup cap retained; post-actual normal120/fixture132/outer150 capped by exactcreation300; child waits≤1+1s, ordinaryclose≤6s, exactforce each≤1s; absolute100k throughout.',
    'candidate_profile': 'candidate_profile(frozen=True)', 'flowing_top_qualified': False,
    'restoration': ['world216air', 'flow unfreeze', 'camera/visual/document/profile/environment',
        'exact binding ordinary stop then authorized force fallback', 'process_identity gate', 'original config absence'],
    'real_input': False, 'activation': False, 'resize': False, 'hot_reload': False, 'background_only': True,
    'production_qualified': False, 'side_uv_qualified': False, 'animation_qualified': False,
    'transparency_qualified': False,
    'exclusions': ['Original Scene/missing H/L side holdouts', 'sloped/falling C/F holdouts',
        'occupied neighbor', 'structural marker UV oracle', 'alpha0.45 translucent pixels',
        'independent animation', 'flowing top direction', 'production memory/performance acceptance']}
for row in plan['binaries'].values():
    if fingerprint(row['path'])['sha256'] != row['sha256']:
        raise ValueError('Reviewed binary changed')
write(BASE / 'plan.json', plan)
print(json.dumps({'plan': fingerprint(BASE / 'plan.json'), 'runtime_files': len(pack), 'host_files': len(host)}))
