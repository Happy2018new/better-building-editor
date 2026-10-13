"""Freeze one native palette/direct visibility comparison from the current root baseline."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

PROJECT=Path(__file__).resolve().parents[1]
BASE=PROJECT/'.runtime/liquid-native-write-r13-v4b'
PREVIOUS=Path('D:/liquid-r12-followup/.runtime/liquid-native-write-r12-v12/plan.json')

def fingerprint(path):
    path=Path(path).resolve(strict=True)
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

if BASE.exists() or (PROJECT/'.mcdev.json').exists():
    raise ValueError('Fresh one-attempt plan and original configuration absence required')
previous=json.loads(PREVIOUS.read_bytes())
previous['binaries']['guard']=fingerprint('D:/bbe-r13-background/.runtime/native_focus_guard-r13-v1/native_focus_guard.dll')
assert previous['binaries']['guard']['sha256']=='04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
previous['limits'].update(ready_normal_seconds=240,ready_fixture_cleanup_seconds=270,ready_outer_seconds=300,end_to_end_from_exact_game_creation_seconds=480,ready_outer_formula='min(actual-world-ready+300, exact-game-creation+480)',insufficient_full150_reservation='read-only rejection before first fixture or WGC if full300 seconds unavailable',ready_budget_change_basis='R13V1 measured calibration89.7s and repeated native216snapshot cost; new complete36source neighborhoods preserve visibility scope')
BASE.mkdir()
shutil.copyfile(previous['configuration']['path'],BASE/'configuration.json')
pack,host={},{}
for scope in ('behavior_pack','resource_pack','tools','.agents/skills/pyreact-debugging/scripts'):
    rows=pack if scope.endswith('_pack') else host
    for path in sorted((PROJECT/scope).rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc','.pyo'):
            continue
        if rows is host and path.suffix not in ('.py','.ps1','.cpp','.h','.json','.cs'):
            continue
        relative=path.relative_to(PROJECT).as_posix()
        archive=BASE/'sources'/relative
        archive.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,archive)
        rows[relative]={'live':fingerprint(path),'archive':fingerprint(archive)}
for relative in ('.runtime/prepare_liquid_native_write_r13_v4b.py','.runtime/liquid_native_write_session_r13_v4b.py',
        '.runtime/liquid_passive_guard_r12_v8.py','.runtime/liquid_priority_guard_r12_v9.py',
        '.runtime/read_native_capacity_snapshot_r12.py','.runtime/runtime-health-r12/check_runtime_health.py',
        'tests/test_liquid_original_probe_state.py','tests/test_liquid_native_write_analysis.py'):
    archive=BASE/'sources'/relative
    archive.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(PROJECT/relative,archive)
    host[relative]={'live':fingerprint(PROJECT/relative),'archive':fingerprint(archive)}
plan={'schema':1,'project':str(PROJECT),'owner':'liquid-r13-native-write-v4b',
    'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=PROJECT).decode().strip(),
    'scope':'V3-established near +2 terrain visibility; same-session calibration and unchanged H/L NW palette/direct/full diagnostic',
    'runtime_pack_files':pack,'host_helper_files':host,'binaries':previous['binaries'],
    'configuration':fingerprint(BASE/'configuration.json'),
    'game_executable':json.loads((BASE/'configuration.json').read_bytes())['game_executable_path'],
    'capacity_baseline':fingerprint(PROJECT/'.runtime/native-capacity-readonly-r12-v1.json'),
    'capacity_policy':previous['capacity_policy'],
    'limits':previous['limits'],'calibration':previous['calibration'],
    'camera_settle':previous['camera_settle'],'actual_world_gate':previous['actual_world_gate'],
    'live_signal_cache':previous['live_signal_cache'],
    'probe_pending_fix':{'renderer_none_groups_empty':True,'strict_world_ready_retained':True,
        'offline_inactive_pending_published_error_replay':True,'V11_frozen_sources_edited':False},
    'capture_schedule':{'fixture_height_above_foot':2,'V3_native_positive_plan':'eeefd53faa05e0daf1dbc8410bdcc83ad0c7e32bd03a41f0e82c9817c9ab58db','preflight_png_count':1,'stone_png_count':6,'empty_native_png_count':1,
        'palette_native_png_count':2,'direct_native_png_count':2,'full_projection_png_count':2,
        'total_native_png_count':14,'sources':['water_depth_0_foreground','water_depth_3_foreground'],
        'view':'vnw','same_cells_camera_readbacks_required':True,'per_native_capture_complete_source_one_cell_neighbors':36,'initial_air_reservation_and_cleanup_cells':216,'minimum_low_side_pixels':24,
        'write_routes':['WorldAdapter.write palette','SetBlockNew isLegacy=True updateNeighbors=False'],
        'direct_only_front_stone_water_air_background_no_actor':True,
        'two_actual_render_events_after_each_write':True,'full_wait_reads_preserved':True,
        'two_actual_render_events_after_full_project':True},
    'native_write_visibility':{'source':'tools/analyze_liquid_native_write.py','limits':{'rgb_delta':12,'minimum_signal_pixels':80,'inset_pixels':3,'crosshair_half_extent':20,'hud_top_fraction':.12,'hud_bottom_fraction':.90},
        'source_driven_no_image_fitting':True,'shape_UV_alpha_animation_qualification':False},
    'prohibited':previous['prohibited'] if 'prohibited' in previous else [],
    'no_activation':True,'no_real_input':True,'no_resize':True,'maximum_launch_attempts':1,
    'production_qualified':False,'side_uv_qualified':False,'animation_qualified':False,'transparency_qualified':False}
(BASE/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='ascii')
print(json.dumps({'plan':fingerprint(BASE/'plan.json'),'runtime_files':len(pack),'host_files':len(host)}))
