"""Archive the single startup failure without rewriting any earlier evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parents[1]
OUT = ROOT/'.runtime/alpha-single-failure-binding-r11-v3.json'
DIRECTORY = ROOT/'.runtime/alpha-single-failure-sources-r11-v3b'
SUPERVISOR = ROOT/'.runtime/alpha-single-supervisor-r11-v3.json'


def record(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    if OUT.exists() or DIRECTORY.exists():
        raise ValueError('Failure binding output must be fresh')
    report = json.loads(SUPERVISOR.read_bytes())
    assert report['launches'] == 1 and report['observation_completed'] is False
    assert report['owned_processes_dead'] and not report['cleanup_errors']
    assert report['marker_override_absent'] and report['native_texture_unchanged']
    assert all(row['restored'] for row in report['backup'])
    assert [phase['label'] for phase in report['phases']] == ['launch']
    launch = json.loads(report['phases'][0]['stdout'])
    assert launch['state'] == 'failed' and launch['ready'] is False
    DIRECTORY.mkdir()
    paths = [
        (SHARED/'.agents/skills/pyreact-debugging/scripts/instances.py','instances.py'),
        (SHARED/'.agents/skills/pyreact-debugging/scripts/mcdk.py','mcdk.py'),
        (SHARED/'.runtime/r11-native/.mcdev.json','private-flat-creative.mcdev.json'),
        (ROOT/'tools/verify_marked_native_plant.py','verify_marked_native_plant.py'),
        (ROOT/'tools/verify_camera_projection.py','verify_camera_projection.py'),
        (ROOT/'tools/capture_native_window.py','capture_native_window.py'),
        (ROOT/'.runtime/run_alpha_single_r11.py','run_alpha_single_r11.py'),
    ]
    sources = []
    for source, name in paths:
        original = record(source)
        frozen_source = source
        if name in ('instances.py', 'mcdk.py'):
            frozen_source = ROOT/'.agents/skills/pyreact-debugging/scripts'/name
        elif name == 'private-flat-creative.mcdev.json':
            frozen_source = ROOT/'.mcdev.json'
        assert original['sha256'] == report['frozen_sources'][str(frozen_source)], source
        target = DIRECTORY/name
        shutil.copyfile(source, target)
        assert record(target)['sha256'] == original['sha256']
        sources.append({'source': original, 'archive': record(target)})
    failed = DIRECTORY/'launch-failed-original.json'
    failed.write_bytes(report['phases'][0]['stdout'].encode('utf8'))
    session = Path(report['session']['session_file'])
    session_data = json.loads(session.read_bytes())
    sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
    from _session import process_identity
    dead = {kind: process_identity(session_data[kind+'_pid']) != session_data[kind+'_identity']
            for kind in ('game','mcdk')}
    assert all(dead.values())
    override = ROOT/'resource_pack/textures/blocks/flower_rose.png'
    assert not override.exists()
    binding = {'schema':1,'scope':'One bounded alpha-only startup failure, no native plant observation',
               'production_acceptance':False,'native_mesh_authority_recovered':False,
               'native_offset_formula_recovered':False,'marker_pixels_verified':False,
               'launches':1,'fixture_mutation_started':False,'timer_mutation_started':False,
               'camera_mutation_started':False,'native_capture_started':False,
               'holdout_pixels_acquired':False,'opaque_marker_installed':False,
               'supervisor':record(SUPERVISOR),'supervisor_source':record(ROOT/'.runtime/run_alpha_single_r11.py'),
               'original_failed_launch':record(failed),'stopped_session':record(session),
               'owner':session_data['owner'],'session_id':session_data['id'],
               'processes_dead':dead,'override_restored_absent':True,
               'original_config_and_scripts_restored':report['backup'],
               'native_texture_unchanged':True,'sources':sources,
               'alpha_snapshot':record(ROOT/'.runtime/poppy-alpha-marker-r11-v3.json'),
               'candidate':record(ROOT/'.runtime/poppy-alpha-marker-r11-v3_candidate.png'),
               'runtime_error':launch['error'],'normal_stop':report['normal_stop'],
               'identity_bound_force_stop_required':True,'total_elapsed_seconds':report['run_elapsed_seconds'],
               'accepted_scope_unchanged':{'positive_states':29,'height_observations':232,
                                         'negative_lower_half_states':8,
                                         'seed_name_false_rows_are_observed_negatives':False}}
    OUT.write_text(json.dumps(binding,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'binding':record(OUT),'dead':dead,'no_native_observation':True}))


if __name__=='__main__':
    main()
