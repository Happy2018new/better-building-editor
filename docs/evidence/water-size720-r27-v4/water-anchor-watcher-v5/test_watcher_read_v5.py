"""Real Windows share-lock controls plus explicit synthetic registry/dialog IO."""
import ctypes
from ctypes import wintypes
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
TARGET=WORK/'watch_owned_disabled_skin_assert_r27_v5.py'
sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
from _session import load_session,process_identity


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.name=='nt'
    output=WORK/'windows-lock-controls-v1.json'
    assert not output.exists()
    spec=importlib.util.spec_from_file_location('water_private_assert_watcher_v5',TARGET)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fixture=WORK/'windows-lock-fixture-v1';fixture.mkdir(exist_ok=False)
    registry=fixture/'registry';registry.mkdir()
    instance=registry/'fixture-session';instance.mkdir()
    path=instance/'session.json'
    owner='water-r27-lock-control-only'
    identity=process_identity(os.getpid());assert identity
    base={'schema':1,'id':'fixture-session','owner':owner,'state':'starting',
        'project':str(ROOT/'.runtime/projects/water-lock-control-no-game'),
        'session_file':str(path.resolve()),'game_pid':os.getpid(),'game_identity':identity,
        'mcdk_pid':os.getpid(),'mcdk_identity':identity}
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,
                                wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    invalid=ctypes.c_void_p(-1).value
    results=[]

    def reset(data=None,raw=None):
        path.write_bytes(raw if raw is not None else json.dumps(base if data is None else data).encode('utf8'))

    def lock():
        handle=kernel.CreateFileW(str(path.resolve()),0x80000000,0,None,3,0,None)
        assert handle and handle!=invalid,ctypes.get_last_error()
        return handle

    def delayed_unlock(handle,seconds=.08):
        result={}
        def close():
            time.sleep(seconds)
            result['closed']=bool(kernel.CloseHandle(handle))
        thread=threading.Thread(target=close);thread.start()
        return thread,result

    def read(events,loader=module.native_load_session):return module.read_assigned_session(path,[owner],events,loader=loader)

    reset();events=[];data=read(events)
    assert data==base and not events
    assert module.eligible(data,[owner],ROOT/'.runtime/projects')
    results.append({'name':'normal_valid_schema_owner_actual_creation_identity','passed':True})

    loader_comparisons=[]
    for label,value,expected_owner,live in [
        ('valid',base,owner,False),
        ('valid_live',base,owner,True),
        ('schema_mismatch',dict(base,schema=2),owner,False),
        ('path_mismatch',dict(base,session_file=str(path.with_name('other.json'))),owner,False),
        ('owner_mismatch',base,'other-owner',False),
        ('not_ready_live',base,owner,True),
        ('wrong_identity_live',dict(base,state='ready',game_identity=str(int(identity)+1)),owner,True),
        ('ready_live',dict(base,state='ready'),owner,True)]:
        reset(value)
        outcomes=[]
        for loader in (load_session,module.native_load_session):
            try:result=loader(str(path),expected_owner,live=live)
            except Exception as error:outcomes.append({'error_type':type(error).__name__,'message':str(error)})
            else:outcomes.append({'data':result})
        assert outcomes[0]==outcomes[1],(label,outcomes)
        loader_comparisons.append({'case':label,'equal':True,'error_type':outcomes[0].get('error_type')})
    results.append({'name':'native_loader_matches_original_load_session_eight_input_controls',
                    'passed':True,'comparisons':loader_comparisons})

    events=[];missing=path.with_name('missing.json')
    try:module.bounded_manifest_read(lambda:module.native_read_json(missing),events,str(missing))
    except OSError as error:assert error.winerror==2
    else:raise AssertionError('Missing file accepted')
    assert not events
    results.append({'name':'real_native_missing_file_winerror2_not_retried','passed':True})

    reset();events=[];handle=lock();thread,closed=delayed_unlock(handle)
    data=read(events);thread.join()
    assert closed['closed'] and data==base and events[0]['recovered'] and not events[0]['exhausted']
    assert events[0]['successful_attempt']<=5
    assert all(item['winerror'] in (5,32,33) for item in events[0]['failures'])
    results.append({'name':'real_CreateFile_share0_temporary_first_read','passed':True,'events':events})

    reset();events=[];second={'calls':0,'thread':None,'closed':None}
    def lock_on_second_read(manifest,expected_owner):
        second['calls']+=1
        if second['calls']==1:
            handle=lock();second['thread'],second['closed']=delayed_unlock(handle)
        return module.native_load_session(manifest,expected_owner)
    data=read(events,lock_on_second_read);second['thread'].join()
    assert second['closed']['closed'] and second['calls']==2 and data==base
    assert len(events)==1 and events[0]['recovered']
    results.append({'name':'real_CreateFile_share0_temporary_second_read_whole_double_read_retried',
                    'passed':True,'loader_calls':second['calls'],'events':events})

    reset();events=[];handle=lock();started=time.monotonic()
    try:
        try:read(events)
        except PermissionError as error:
            observed={'type':type(error).__name__,'winerror':error.winerror,'errno':error.errno}
        else:raise AssertionError('Persistent lock was accepted')
    finally:assert kernel.CloseHandle(handle)
    elapsed=time.monotonic()-started
    assert events[0]['exhausted'] and not events[0]['recovered'] and len(events[0]['failures'])==5
    assert .70<=elapsed<3.
    results.append({'name':'real_CreateFile_share0_persistent_exhausts_five_attempts','passed':True,
                    'error':observed,'elapsed_seconds':elapsed,'events':events})

    reset(raw=b'{');events=[]
    try:read(events)
    except json.JSONDecodeError:pass
    else:raise AssertionError('Malformed JSON accepted')
    assert not events
    results.append({'name':'malformed_JSON_not_retried_or_accepted','passed':True})

    reset(dict(base,schema=2));events=[]
    try:read(events)
    except ValueError:pass
    else:raise AssertionError('Malformed schema accepted')
    assert not events
    results.append({'name':'invalid_schema_not_retried_or_accepted','passed':True})

    reset();events=[];calls=[]
    def changed_owner(manifest,expected_owner):
        calls.append(expected_owner);reset(dict(base,owner='other-owner'))
        return module.native_load_session(manifest,expected_owner)
    try:read(events,changed_owner)
    except ValueError:pass
    else:raise AssertionError('Owner changed between reads accepted')
    assert calls==[owner] and not events
    results.append({'name':'owner_change_between_reads_not_retried_or_accepted','passed':True})

    reset(dict(base,game_identity=str(int(identity)+1)));events=[];data=read(events)
    assert not module.eligible(data,[owner],ROOT/'.runtime/projects')
    assert not events
    results.append({'name':'wrong_expected_creation_identity_rejected_against_actual_Win32_process',
                    'passed':True,'PID_reuse_simulated':False})

    reset(dict(base,owner='other-owner'));events=[];loader_calls=[]
    data=read(events,lambda *args:loader_calls.append(args))
    assert data is None and not loader_calls and not events
    results.append({'name':'unassigned_owner_never_loaded_or_eligible','passed':True})

    reset();events=[];calls=[]
    def unrelated_permission(manifest,expected_owner):
        calls.append(1);error=PermissionError(13,'synthetic non-retry winerror');error.winerror=1314;raise error
    try:read(events,unrelated_permission)
    except PermissionError as error:assert error.winerror==1314
    else:raise AssertionError('Non-retry PermissionError accepted')
    assert calls==[1] and not events
    results.append({'name':'other_winerror_not_retried','passed':True,'IO':'explicit synthetic exception'})

    original_argv=sys.argv[:]
    module.registry_dir=lambda:registry
    module.assertion_dialogs=lambda:[]
    def run_once(label):
        folder=fixture/label
        sys.argv=[str(TARGET),'--owner',owner,'--until',
            (datetime.now(timezone.utc)+timedelta(seconds=15)).isoformat(),'--output',str(folder),'--once']
        try:result=module.main()
        finally:sys.argv=original_argv[:]
        return result,json.loads((folder/'status.json').read_bytes())

    reset();handle=lock();thread,closed=delayed_unlock(handle)
    code,status=run_once('temporary-main');thread.join()
    assert closed['closed'] and code==0 and not status['errors'] and len(status['eligible_sessions'])==1
    assert status['manifest_read_events'][0]['recovered']
    results.append({'name':'main_temporary_real_lock_success_without_error_latch','passed':True,
                    'status':status,'IO':'real filesystem locks, synthetic registry root and empty dialog enumeration'})

    reset();handle=lock()
    try:code,status=run_once('persistent-main')
    finally:assert kernel.CloseHandle(handle)
    assert code==1 and status['errors'] and not status['eligible_sessions']
    assert status['manifest_read_events'][0]['exhausted']
    results.append({'name':'main_persistent_real_lock_fail_closed_status_errors','passed':True,
                    'status':status,'IO':'real filesystem locks, synthetic registry root and empty dialog enumeration'})

    reset();module.assertion_dialogs=lambda:[{'pid':os.getpid(),'hwnd':1234}]
    module.known_disabled_skin_assertion=lambda row:False
    actions=[];module.post_owned_ignore=lambda *args:actions.append(args)
    code,status=run_once('unknown-assertion-main')
    assert status['other_assertions'] and not status['known_assert_recoveries'] and not actions
    results.append({'name':'main_unknown_assertion_still_reported_no_ignore_action','passed':True,
                    'status':status,'IO':'explicit synthetic unknown dialog, no OS dialog action'})

    report={'schema':1,'checked_at':time.time(),'candidate_sha256':sha(TARGET),'test_host_sha256':sha(Path(__file__)),
        'passed':all(row['passed'] for row in results),'controls':results,'MC_started':False,
        'production_source_changed':False,'qualification':False,
        'limits':['Windows lock controls use actual CreateFileW share=0 handles on test manifests.',
            'Main-loop controls replace registry discovery and native dialog enumeration explicitly.',
            'Actual creation identity negative uses this test Python process; no PID reuse is claimed.',
            'These controls do not establish real MC startup success or measure the original incident winerror.']}
    with output.open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'passed':report['passed'],'controls':len(results),'report_sha256':sha(output),
                     'candidate_sha256':sha(TARGET),'MC_started':False}))


if __name__=='__main__':main()
