"""Freeze a new exact owner with the approved Win32 manifest-reader host only."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
OLD=WORK.with_name('water-anchor-calibration-v3')
OWNER='water-r27-anchor-calibration-v2'
WATCHER='.runtime/round-20261022/water-anchor-watcher-v5/watch_owned_disabled_skin_assert_r27_v5.py'
READER='.runtime/round-20261022/water-anchor-watcher-v5/windows_manifest_reader.py'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name,value):
    with (WORK/name).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def main():
    assert not (WORK/'plan-v1.json').exists()
    assert sha(ROOT/WATCHER)=='804aab25fa70ab91c63cffc3eb5db170dbd5800e3c4450da5b52c5a897e49565'
    assert sha(ROOT/READER)=='2ae4d46fc4fc63249b1b10d8cc6e7028009f4fa1941ea64f88452871a89eb28d'
    prior=json.loads((OLD/'prelaunch-host-binding-v1.json').read_bytes())
    names=('anchor_game.py','bootstrap_payload.py','candidate_bootstrap.py','guard_policy.py',
        'launch_r25.py','modal_guard.py','retire_bootstrap_marker.py','retire_helpers.py',
        'run_anchor_calibration.py','run_anchor_group.py','run_candidate_bootstrap.py',
        'start_assert_watch.py','watch_handles.py')
    originals={}
    for name in names:
        assert sha(OLD/name)==prior['host_sha256'][name],name
        text=(OLD/name).read_text('utf8');originals[name]=sha(OLD/name)
        if name!='candidate_bootstrap.py':text=text.replace('water-r27-anchor-calibration-v1',OWNER)
        if name=='start_assert_watch.py':
            text=text.replace("str(ROOT / 'tools/watch_owned_disabled_skin_assert_r20.py')","str(ROOT / "+repr(WATCHER)+")")
        if name=='launch_r25.py':
            text=text.replace("from _session import process_identity, registry_dir",'''from _session import process_identity, registry_dir
sys.path.insert(0,str(ROOT/'.runtime/round-20261022/water-anchor-watcher-v5'))
from windows_manifest_reader import native_read_json,bounded_manifest_read
from watch_owned_disabled_skin_assert_r27_v5 import native_load_session


def guarded_json(path,events):
    return bounded_manifest_read(lambda:native_read_json(path),events,str(path))''',1)
            text=text.replace("host_binding['external_host_sha256']['tools/watch_owned_disabled_skin_assert_r20.py']",
                "host_binding['external_host_sha256']["+repr(WATCHER)+"]")
            text=text.replace("    for manifest in registry_dir().glob('*/session.json'):\n        row = json.loads(manifest.read_bytes())",
                "    manifest_read_events=[]\n    for manifest in registry_dir().glob('*/session.json'):\n        row = guarded_json(manifest,manifest_read_events)",1)
            text=text.replace("'command': command, 'started_at': datetime.now(timezone.utc).isoformat(), 'samples': []}",
                "'command': command, 'started_at': datetime.now(timezone.utc).isoformat(), 'samples': [],\n              'manifest_read_events':manifest_read_events}",1)
            text=text.replace("row = json.loads(path.read_bytes())","row = guarded_json(path,manifest_read_events)",1)
            old="""                    row = json.loads(session_path.read_bytes())
                except (OSError, ValueError):
                    row = None"""
            new="""                    row = bounded_manifest_read(lambda:native_load_session(str(session_path),OWNER),
                        manifest_read_events,str(session_path))
                    assert Path(row['project']).resolve()==PROJECT.resolve()
                except (OSError, ValueError):
                    save()
                    raise"""
            assert old in text;text=text.replace(old,new,1)
        if name=='watch_handles.py':
            old='from _session import _kernel, _identity, process_identity, load_session'
            new='''from _session import _kernel, _identity, process_identity
sys.path.insert(0,str(ROOT/'.runtime/round-20261022/water-anchor-watcher-v5'))
from windows_manifest_reader import bounded_manifest_read
from watch_owned_disabled_skin_assert_r27_v5 import native_load_session


def load_starting_session(path,owner,events):
    return bounded_manifest_read(lambda:native_load_session(path,owner),events,str(path))'''
            assert old in text;text=text.replace(old,new,1)
            old="    session = load_session(launch['session_file'], binding['owner'], live=False)"
            new="    manifest_read_events=[]\n    session = load_starting_session(launch['session_file'],binding['owner'],manifest_read_events)"
            assert old in text;text=text.replace(old,new,1)
            text=text.replace("'stopped': False, 'completed': False}","'stopped': False, 'completed': False, 'manifest_read_events':manifest_read_events}",1)
        with (WORK/name).open('x',encoding='utf8',newline='\n') as stream:stream.write(text)
    binding=json.loads((OLD/'final-source-binding-v1.json').read_bytes())
    binding.update(owner=OWNER,bootstrap_receipt_marker='_water_r27_anchor_bootstrap_v2',
        previous_host_binding_sha256=sha(OLD/'prelaunch-host-binding-v1.json'),
        previous_failed_attempt_review_sha256=sha(OLD/'startup-failure-review-v1.json'),
        diagnostic_watcher={'path':WATCHER,'sha256':sha(ROOT/WATCHER),'reader_path':READER,'reader_sha256':sha(ROOT/READER)})
    write('final-source-binding-v1.json',binding)
    for name in ('diagnostic-source-v1.json',):
        with (WORK/name).open('xb') as stream:stream.write((OLD/name).read_bytes())
    inputs=json.loads((OLD/'product-v2-launch-inputs.json').read_bytes());inputs['owner']=OWNER
    write('product-v2-launch-inputs.json',inputs)
    plan=json.loads((OLD/'plan-v1.json').read_bytes())
    plan.update(schema=4,declared_at_utc=datetime.now(timezone.utc).isoformat(),owner=OWNER,
        previous_plan_sha256=sha(OLD/'plan-v1.json'),previous_attempt_outcome='Stopped before ready by watcher health gate; zero diagnostic images.',
        changed_condition='Root-reviewed private native Win32 manifest reader preserves GetLastError and retries only 5/32/33; old source/archive/pixel plan unchanged.',
        diagnostic_watcher=binding['diagnostic_watcher'])
    plan['host_code_sha256']={name:sha(WORK/name) for name in ('anchor_game.py','run_anchor_calibration.py')}
    write('plan-v1.json',plan)
    stage=json.loads((OLD/'stage-r25.json').read_bytes());stage.update(owner=OWNER,plan_sha256=sha(WORK/'plan-v1.json'))
    write('stage-r25.json',stage)
    sys.path.insert(0,str(WORK))
    import anchor_game
    from bootstrap_payload import dispatch_code
    payloads={name:getattr(anchor_game,name) for name in ('OPEN','CONFIGURE','STATUS','CLEAN','CLEAN_READY')}
    payloads['bootstrap']=dispatch_code((WORK/'candidate_bootstrap.py').read_text('utf8'),binding)
    compile_rows=[]
    for name,text in payloads.items():
        filename='dispatched-bootstrap-payload.py' if name=='bootstrap' else 'compile-'+name+'.py'
        if name=='CONFIGURE':text=text%({'mode':'empty','model':'modern_projection_r27_anchor_15','rect':[1,2,3,4],
            'position':[1,1,1],'unit':2.,'rotation':[0.,0.,0.],'offset':'zero','matrix':'WORLDVIEWPROJ'},)
        with (WORK/filename).open('x',encoding='utf8',newline='\n') as stream:stream.write(text)
        result=subprocess.run(['D:/Program/Python27/python.exe','-B','-c',
            'import sys;compile(open(sys.argv[1],"rb").read(),sys.argv[1],"exec")',str(WORK/filename)],capture_output=True,text=True)
        result.check_returncode();compile_rows.append({'name':filename,'exit_code':result.returncode,'sha256':sha(WORK/filename)})
    files=dict(binding['source_sha256'],**binding['auxiliary_sha256']);project=Path(binding['project'])
    assert all(sha(project/name)==expected for name,expected in files.items())
    archive=Path(binding['archive']['path']);assert sha(archive)==binding['archive']['sha256']
    with zipfile.ZipFile(archive) as stream:
        assert sorted(stream.namelist())==sorted(files)
        for name,expected in files.items():assert hashlib.sha256(stream.read(name)).hexdigest()==expected,name
    external=dict(prior['external_host_sha256']);external.pop('tools/watch_owned_disabled_skin_assert_r20.py')
    external.update({WATCHER:sha(ROOT/WATCHER),READER:sha(ROOT/READER)})
    assert all(sha(ROOT/name)==expected for name,expected in external.items())
    hosts={p.name:sha(p) for p in WORK.glob('*.py')}|{name:sha(WORK/name) for name in ('product-v2-launch-inputs.json','stage-r25.json','plan-v1.json')}
    for path in WORK.glob('*.py'):ast.parse(path.read_bytes(),filename=str(path))
    write('prelaunch-host-binding-v1.json',{'schema':4,'source_binding_sha256':sha(WORK/'final-source-binding-v1.json'),
        'host_sha256':hosts,'external_host_sha256':external,'MC_started':False,
        'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'previous_host_binding_sha256':sha(OLD/'prelaunch-host-binding-v1.json')})
    report={'schema':4,'MC_started':False,'source_unchanged':True,'archive_reused_without_rezip':True,
        'source_count':len(binding['source_sha256']),'auxiliary_count':len(binding['auxiliary_sha256']),
        'archive_entries_individually_reverified':len(files),'archive_sha256':sha(archive),
        'prior_host_source_sha256':originals,'plan_sha256':sha(WORK/'plan-v1.json'),
        'host_binding_sha256':sha(WORK/'prelaunch-host-binding-v1.json'),'host_files':len(hosts),'external_hosts':len(external),
        'true_python2_compile':compile_rows,'owner':OWNER,'unchanged_original_pixel_plan':True,
        'formal_A_accepted':False,'production_admission_performed':False,'manual_closures_added':0}
    write('v4-preparation-review-v1.json',report)
    print(json.dumps({k:report[k] for k in ('MC_started','plan_sha256','host_binding_sha256','host_files','external_hosts','archive_entries_individually_reverified','owner')}))


if __name__=='__main__':main()
