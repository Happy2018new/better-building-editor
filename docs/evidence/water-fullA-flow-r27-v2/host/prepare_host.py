"""Prepare new lifecycle: reviewed seam host, single-stone guards and fixed cutoff."""
import ast
from datetime import datetime,timezone
import difflib
import hashlib
import json
from pathlib import Path

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[2]
OLD=WORK.with_name('water-merged-fullA-v1')
CANDIDATE=WORK.with_name('water-camera-extractor-seam-candidate-v1')
OWNER='water-r27-merged-fullA-v2'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def once(text,before,after):
    assert text.count(before)==1,before
    return text.replace(before,after)


def write(name,value):
    with (WORK/name).open('x',encoding='utf8',newline='\n') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')


def main():
    assert not (WORK/'final-source-binding-v1.json').exists()
    binding=json.loads((OLD/'final-source-binding-v1.json').read_bytes())
    old_hosts=json.loads((OLD/'prelaunch-host-binding-v1.json').read_bytes())
    patches=[]
    names=('guard_policy.py','modal_guard.py','launch_r25.py','start_assert_watch.py','watch_handles.py',
        'retire_helpers.py','scene_game.py','scene_policy.py','scene_restore.py','resize_adapter.py',
        'resize_background.py','observe_cold_default.py','flow_restore.py','run_group.py','run_flow.py',
        'run_camera.py','world_readback.py','verify_prelaunch.py')
    for name in names:
        original=(OLD/name).read_text('utf8')
        text=original.replace(binding['owner'],OWNER)
        if name in ('run_camera.py','run_flow.py'):
            text=once(text,'import ctypes\n','from datetime import datetime,timezone\nimport ctypes\n')
            text=text.replace('product-v2-camera-native-v1.json','product-v2-camera-seam-v1.json')
        if name=='run_camera.py':
            text=once(text,"    original_capture = capture_native_window.capture\n",
                "    from calibration_host import activate,fixture_valid,SINGLE_STONE_CODE\n"
                "    activation=activate()\n"
                "    receipt['versioned_calibration_host']=activation\n"
                "    fixture_observations=[]\n"
                "    receipt['single_stone_fixture_observations']=fixture_observations\n"
                "    active_check=[None]\n"
                "    def single_stone_sample(label):\n"
                "        assert active_check[0] is not None\n"
                "        state=original_run(active_check[0],SINGLE_STONE_CODE)\n"
                "        fixture_observations.append({'label':label,'state':state})\n"
                "        save()\n"
                "        assert fixture_valid(state),state\n"
                "    original_capture = capture_native_window.capture\n")
            text=once(text,"        label = Path(path).stem\n",
                "        assert datetime.now(timezone.utc)<datetime.fromisoformat('2026-10-21T23:25:00+00:00'),'07:25 capture cutoff'\n"
                "        label = Path(path).stem\n"
                "        single_stone_sample(label+'_before_wgc')\n")
            text=once(text,"        result = original_capture(session_arg, owner, path, executable)\n",
                "        result = original_capture(session_arg, owner, path, executable)\n"
                "        single_stone_sample(label+'_after_wgc')\n")
            text=once(text,'    def tracked_run(check, code):\n','    def tracked_run(check, code):\n        active_check[0]=check\n')
            text=once(text,"        tool = importlib.import_module('verify_camera_projection')\n",
                "        tool = importlib.import_module('verify_camera_projection')\n"
                "        original_write=tool.write_json\n"
                "        def versioned_write(path,evidence):\n"
                "            evidence['versioned_calibration_host']=activation\n"
                "            evidence['single_stone_fixture_observations']=fixture_observations\n"
                "            return original_write(path,evidence)\n"
                "        tool.write_json=versioned_write\n")
        elif name=='run_flow.py':
            text=once(text,"    arguments = [str(tool_path), '--session', str(SESSION), '--owner', OWNER,\n",
                "    from calibration_host import activate,validate_report\n"
                "    activation=activate()\n"
                "    receipt['versioned_calibration_host']=activation\n"
                "    receipt['new_calibration_source']=validate_report(WORK/'product-v2-camera-seam-v1.json',activation)\n"
                "    arguments = [str(tool_path), '--session', str(SESSION), '--owner', OWNER,\n")
            text=once(text,"    def tracked_capture(session, owner, output, executable):\n",
                "    def tracked_capture(session, owner, output, executable):\n"
                "        assert datetime.now(timezone.utc)<datetime.fromisoformat('2026-10-21T23:25:00+00:00'),'07:25 capture cutoff'\n")
            text=once(text,"        def tracked_burst(*args, **kwargs):\n",
                "        def tracked_burst(*args, **kwargs):\n"
                "            assert datetime.now(timezone.utc)<datetime.fromisoformat('2026-10-21T23:25:00+00:00'),'07:25 capture cutoff'\n")
        elif name=='run_group.py':
            text=once(text,"    assert datetime.now(timezone.utc)<datetime.fromisoformat('2026-10-21T23:30:00+00:00')\n",
                "    assert datetime.now(timezone.utc)<datetime.fromisoformat('2026-10-21T23:20:00+00:00'),'Insufficient time before 07:25 capture cutoff'\n")
        elif name=='verify_prelaunch.py':
            text=once(text,"    world=load('world_readback.py')\n",
                "    calibration=load('calibration_host.py')\n"
                "    assert sha(calibration.CANDIDATE)==calibration.EXPECTED\n"
                "    compiled=subprocess.run(['D:/Program/Python27/python.exe','-B','-c','import sys;compile(sys.stdin.read(),\"single-stone-observation\",\"exec\")'],input=calibration.SINGLE_STONE_CODE.encode('utf8'),capture_output=True)\n"
                "    assert compiled.returncode==0,compiled.stderr\n"
                "    camera=(WORK/'run_camera.py').read_text('utf8')\n"
                "    assert 'single_stone_sample(label' in camera and \"tool.write_json=versioned_write\" in camera\n"
                "    assert 'versioned_calibration_host' in camera and 'validate_report' in flow\n"
                "    assert '07:25 capture cutoff' in camera and '07:25 capture cutoff' in flow\n"
                "    world=load('world_readback.py')\n")
        (WORK/name).write_text(text,encoding='utf8',newline='\n')
        if text!=original:
            patches.extend(difflib.unified_diff(original.splitlines(True),text.splitlines(True),
                fromfile='failed-fullA-v1/'+name,tofile='versioned-fullA-v2/'+name))
    (WORK/'host-changes-v2.patch').write_text(''.join(patches),encoding='utf8',newline='\n')
    binding=dict(binding,owner=OWNER,guard_deadline_utc='2026-10-21T23:30:00+00:00',
        previous_failed_fullA_binding={'path':str(OLD/'final-source-binding-v1.json'),'sha256':sha(OLD/'final-source-binding-v1.json')})
    write('final-source-binding-v1.json',binding)
    write('product-v2-launch-inputs.json',{key:binding[key] for key in ('schema','project','owner','source_sha256','source_contract_sha256','archive')})
    external=dict(old_hosts['external_host_sha256'])
    for name in ('candidate_extractor.py','run_controls.py','replay_controls.py','extractor-changes-v1.patch','controls-v1/report.json'):
        external[(CANDIDATE/name).relative_to(ROOT).as_posix()]=sha(CANDIDATE/name)
    plan=json.loads((OLD/'plan-v1.json').read_bytes())
    plan.update(owner=OWNER,created_at_utc=datetime.now(timezone.utc).isoformat(),
        new_calibration_host={'path':str(WORK/'calibration_host.py'),'sha256':sha(WORK/'calibration_host.py'),
            'version':'single_stone_actual_one_pixel_antialias_seam_v1',
            'candidate_path':str(CANDIDATE/'candidate_extractor.py'),'candidate_sha256':sha(CANDIDATE/'candidate_extractor.py'),
            'report_filename':'product-v2-camera-seam-v1.json','previous_failed_camera_preserved':True,
            'actual_single_stone_observations_per_capture':2,'expected_total_observations':12,
            'original_final_metrics_and_color_thresholds_unchanged':True,
            'source_and_SDK_single_actor_geometry_scale_guard':True},
        no_new_capture_after_utc='2026-10-21T23:25:00+00:00',
        restoration_deadline_utc='2026-10-21T23:30:00+00:00',
        refuse_group_start_after_utc='2026-10-21T23:20:00+00:00',
        calibration_host_does_not_grant_source_release_qualification=True)
    write('plan-v1.json',plan)
    write('stage-r25.json',{'schema':1,'owner':OWNER,'plan_sha256':sha(WORK/'plan-v1.json'),'formal_A_accepted':False,'manual_closures_added':0})
    for path in WORK.glob('*.py'):ast.parse(path.read_bytes(),filename=str(path))
    inventory={'schema':1,'source_project':binding['project'],'source_contract_sha256':binding['source_contract_sha256'],
        'source_files':len(binding['source_sha256']),'auxiliary_files':len(binding['auxiliary_sha256']),
        'archive':binding['archive'],'host_sha256':{path.name:sha(path) for path in WORK.iterdir()
            if path.is_file() and path.suffix in ('.py','.patch','.json') and path.name!='final-source-binding-v1.json'},
        'external_host_sha256':external,'MC_started':False}
    write('dependency-inventory-v1.json',inventory)
    write('prelaunch-host-binding-v1.json',{'schema':1,'source_binding_sha256':sha(WORK/'final-source-binding-v1.json'),
        'host_sha256':{path.name:sha(path) for path in WORK.iterdir() if path.is_file() and path.suffix in ('.py','.patch','.json') and path.name!='final-source-binding-v1.json'},
        'external_host_sha256':external,'startup_contract_sha256':old_hosts['startup_contract_sha256'],
        'MC_started':False,'frozen_at_utc':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'prepared':True,'MC_started':False,'source_or_archive_copied':False,
        'plan_sha256':sha(WORK/'plan-v1.json'),'host_binding_sha256':sha(WORK/'prelaunch-host-binding-v1.json'),
        'dependency_inventory_sha256':sha(WORK/'dependency-inventory-v1.json')}))


if __name__=='__main__':
    main()
