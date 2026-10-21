"""Explicit exact-owner cold lifecycle; plan-only performs no process actions."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
import trial_capture_v5 as trial
import session_reader_v2 as reader
import lifecycle_cleanup_v3 as cleanup

OWNER='wire-r27-crc32-phase-v5'
PROJECT=ROOT/'.runtime/projects'/OWNER
SOURCE_PROJECT=ROOT/'.runtime/projects/wire-r27-small-retirement-v3'
SOURCE_MANIFEST=HERE/'project-manifest-v3.json'
MCDK=ROOT/'.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
GUARD=ROOT/'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
MCDK_SHA='b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
GUARD_SHA='04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
WATCH_UNTIL=datetime(2026,10,21,23,45,tzinfo=timezone.utc)
EXTERNAL=('tools/watch_intrinsic_glint_exit_r21.py',
 '.agents/skills/pyreact-debugging/scripts/instances.py',
 '.agents/skills/pyreact-debugging/scripts/_session.py',
 'tools/census_intrinsic_glint_ui_r21.py',
 '.runtime/round-20261022/concrete-support-v3-runtime/lifecycle.py')
LOCAL=('cold_lifecycle_v6.py','lifecycle_cleanup_v3.py','test_cleanup_v3.py','watch_exact_exit_v2.py','session_reader_v2.py',
 'frozen-trial-plan-v5.json','trial_capture_v5.py','phase_transport_v5.py','test_phase_transport_v5.py','project-manifest-v3.json','source-binding-v2.json')


def freeze_plan():
    return {'schema':'wire-r27-cold-lifecycle-v6-game-crc32-host-SHA256','owner':OWNER,'project':str(PROJECT),
      'diagnostic_deadline_utc':trial.DEADLINE.isoformat(),'watch_until_utc':WATCH_UNTIL.isoformat(),
      'mcdk_sha256':MCDK_SHA,'guard_sha256':GUARD_SHA,
      'reviewed_reader_sha256':reader.READER_SHA,'reviewed_watcher_sha256':reader.WATCHER_SHA,
      'local_inputs':[{'path':name,'sha256':trial.sha(HERE/name)} for name in LOCAL],
      'external_inputs':[{'path':name,'sha256':trial.sha(ROOT/name)} for name in EXTERNAL],
      'source_snapshot_manifest_sha256':trial.sha(SOURCE_MANIFEST),
      'source_snapshot_project':str(SOURCE_PROJECT),
      'prepare_source':'Exact verified previous cold-source bytes only; no live-root or world copy.',
      'noactivation':True,'available_commit_minimum_gib':6,'maximum_mc_instances':5,
      'handle_limit':250000,'maximum_handle_growth':10000,
      'runtime_calls':0,'prepared_runtime':True,'starts_MC':False,
      'failure_cleanup':'Finally retains original creation identities and calls ordinary owned stop once; no force/restart. Errors or timeout remain explicit.',
      'shutdown':'Ordinary exact-owner stop only; retain exact handles and report actual game/MCDK exit codes independently of command return code.'}


def verify_plan(path):
    frozen=json.loads(path.read_bytes())
    assert frozen==json.loads(json.dumps(freeze_plan())),'Frozen lifecycle host input changed'
    reader.approved()
    assert trial.sha(MCDK)==MCDK_SHA and trial.sha(GUARD)==GUARD_SHA
    return frozen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('plan-only','prepare','start','stop','check'))
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.operation=='plan-only':
        target=trial.within_here(args.plan)
        with target.open('xb') as stream:stream.write((json.dumps(freeze_plan(),indent=2)+'\n').encode('ascii'))
        print(json.dumps({'plan':str(target),'sha256':trial.sha(target),'runtime_calls':0}));return
    frozen=verify_plan(args.plan)
    assert args.manifest and args.output
    folder=trial.within_here(args.output)
    if args.operation=='prepare':
        assert not args.manifest.exists() and not PROJECT.exists()
        folder.mkdir(parents=True,exist_ok=False)
        PROJECT.mkdir(parents=True,exist_ok=False)
        trial.runtime_matches(SOURCE_PROJECT,SOURCE_MANIFEST)
        original=json.loads(SOURCE_MANIFEST.read_bytes())
        source_rows=[]
        for row in original['source_files']:
            relative=Path(row['path'])
            source=(SOURCE_PROJECT/relative).resolve(strict=True)
            assert source.is_relative_to(SOURCE_PROJECT.resolve())
            assert relative.as_posix()=='.mcdev.json' or relative.parts[0] in ('behavior_pack','resource_pack')
            raw=source.read_bytes()
            assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
            if relative.as_posix()=='.mcdev.json':
                config=json.loads(raw)
                assert all(config[key] is False for key in ('auto_hot_reload_mods','auto_hot_reload_ui','auto_hot_reload_shaders','auto_hot_reload_materials'))
            target=PROJECT/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:stream.write(raw)
            source_rows.append(dict(row))
        assert source_rows==original['source_files']
        trial.runtime_matches(SOURCE_PROJECT,SOURCE_MANIFEST)
        trial.write(args.manifest,{'schema':'wire-r27-new-cold-base-source-v6-byte-identical','owner':OWNER,
          'project':str(PROJECT),'source_files':sorted(source_rows,key=lambda row:row['path']),
          'head':original['head'],
          'source_snapshot_manifest_sha256':trial.sha(SOURCE_MANIFEST),
          'source_snapshot_project':str(SOURCE_PROJECT),
          'trial_plan_sha256':trial.sha(HERE/'frozen-trial-plan-v5.json'),
          'lifecycle_plan_sha256':trial.sha(args.plan),'source_binding_sha256':trial.sha(HERE/'source-binding-v2.json')})
        trial.runtime_matches(PROJECT,args.manifest)
        trial.write(folder/'prepared.json',{'manifest_sha256':trial.sha(args.manifest),'files':len(source_rows),
          'source_bytes':sum(row['bytes'] for row in source_rows),'MC_started':False,'world_or_MC_copied':False})
        print(json.dumps({'prepared':True,'files':len(source_rows),'MC_started':False}));return
    # Native/process imports and operations begin only below explicit start/check/stop.
    sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'.agents/skills/pyreact-debugging/scripts'),
      str(ROOT/'.runtime/round-20261022/concrete-support-v3-runtime')]
    from _session import process_identity,registry_dir
    import lifecycle
    events=[]
    trial.runtime_matches(PROJECT,args.manifest)
    def save(name,value):trial.write(folder/name,value)
    def same(row):
        assert row['owner']==OWNER and Path(row['project']).resolve()==PROJECT.resolve()
    def health(row,previous):
        same(row)
        sample=lifecycle.snapshot(row)
        assert sample['memory']['commit_available_bytes']>=6*1024**3
        for name in ('game','mcdk'):
            handles=sample[name]['handles']
            if handles is not None:
                assert handles<250000 and (name not in previous or handles-previous[name]<10000)
                previous[name]=handles
        watch=reader.read_json(folder/'assert-watch/status.json',events)
        assert watch['owners']==[OWNER] and not watch['errors'] and not watch['other_assertions']
        assert 0<=(datetime.now(timezone.utc)-datetime.fromisoformat(watch['checked_at'])).total_seconds()<60
        return sample
    if args.operation=='check':
        launch=reader.read_json(folder/'launch.json',events)
        row=reader.load_session(launch['session_file'],OWNER,True,events);same(row)
        print(json.dumps({'healthy':True,'sample':health(row,{}),'read_events':events}));return
    if args.operation=='stop':
        launch=reader.read_json(folder/'launch.json',events)
        row=reader.load_session(launch['session_file'],OWNER,False,events);same(row)
        assert all(row[key]==launch[key] for key in ('game_pid','game_identity','mcdk_pid','mcdk_identity'))
        before=lifecycle.snapshot(row)
        observer=reader.read_json(folder/'exact-exit.json',events)
        assert observer['owner']==OWNER and observer['session']==row['id']
        command=[sys.executable,'-B','-X','utf8',str(ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'),
          'stop','--session',row['session_file'],'--owner',OWNER]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=40)
        (folder/'stop.stdout').write_bytes(result.stdout);(folder/'stop.stderr').write_bytes(result.stderr)
        end=time.monotonic()+45
        states=[]
        while True:
            state=lifecycle.snapshot(row);states.append(state)
            if all(state[name]['actual_identity'] is None for name in ('game','mcdk')):break
            if time.monotonic()>=end:
                save('stop.json',{'before':before,'ordinary_returncode':result.returncode,'states':states,
                  'force_executed':False,'still_live':True,'read_events':events})
                raise RuntimeError('Owned processes remain; no forced termination or relaunch performed')
            time.sleep(.5)
        end=time.monotonic()+5
        while True:
            observer=reader.read_json(folder/'exact-exit.json',events)
            if observer['completed']:break
            assert time.monotonic()<end,'Exact retained-handle exit observer did not complete'
            time.sleep(.2)
        save('stop.json',{'before':before,'ordinary_returncode':result.returncode,'states':states,
          'force_executed':False,'still_live':False,'exact_exit':observer,'read_events':events,
          'all_actual_exit_codes_zero':all(value['exit_code']==0 for value in observer['processes'].values())})
        print(json.dumps({'stopped':True,'ordinary_returncode':result.returncode,
          'actual_exit_codes':{name:value['exit_code_hex'] for name,value in observer['processes'].items()}}));return
    assert args.operation=='start'
    assert datetime.now(timezone.utc)<trial.DEADLINE
    assert folder.exists() and (folder/'prepared.json').exists() and not (folder/'launch.json').exists()
    assert lifecycle.commit_at_boundary()['commit_available_bytes']>=6*1024**3
    for manifest in registry_dir().glob('*/session.json'):
        row=reader.read_json(manifest,events)
        assert row.get('owner')!=OWNER,'Exact cold owner must be new'
    raw=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
      '@(Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress'],text=True).strip()
    pids=json.loads(raw) if raw else []
    if isinstance(pids,int):pids=[pids]
    assert len([pid for pid in pids if process_identity(pid)])<5
    watcher=reader.approved()
    watcher_path=Path(watcher.__file__).resolve()
    command=[sys.executable,'-B','-X','utf8',str(watcher_path),'--owner',OWNER,
      '--until',WATCH_UNTIL.isoformat(),'--output',str(folder/'assert-watch'),'--detach']
    result=subprocess.run(command,cwd=ROOT,capture_output=True,check=True,timeout=15)
    binding=json.loads(result.stdout)
    binding.update(watcher_sha256=reader.WATCHER_SHA,reader_sha256=reader.READER_SHA,command=command)
    save('watch-binding.json',binding)
    end=time.monotonic()+10
    while not (folder/'assert-watch/status.json').exists():
        assert time.monotonic()<end;time.sleep(.1)
    status=reader.read_json(folder/'assert-watch/status.json',events)
    assert status['owners']==[OWNER] and not status['errors'] and not status['other_assertions']
    command=[sys.executable,'-B','-X','utf8',str(ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'),
      'start','--project',str(PROJECT),'--owner',OWNER,'--name',OWNER,'--preset','ui','--wait','180',
      '--mcdk',str(MCDK),'--noactivate-dll',str(GUARD),'--noactivate-sha256',GUARD_SHA,
      '--noactivate-mcdk-sha256',MCDK_SHA]
    report={'owner':OWNER,'project':str(PROJECT),'plan_sha256':trial.sha(args.plan),
      'manifest_sha256':trial.sha(args.manifest),'command':command,'samples':[],'read_events':events,
      'started_at':datetime.now(timezone.utc).isoformat(),'ready':False}
    retained=cleanup.RetainedProcesses()
    previous={};observed=False;bound=None
    try:
        with (folder/'stdout.json').open('xb') as out,(folder/'stderr.txt').open('xb') as err:
            process=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,stdin=subprocess.DEVNULL,
              env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MCDEV_ALLOW_USER_FOREGROUND='0'),creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(launcher_pid=process.pid,launcher_identity=process_identity(process.pid));save('launch.json',report)
        while process.poll() is None:
            assert datetime.now(timezone.utc)<trial.DEADLINE
            paths=[]
            for path in registry_dir().glob('*/session.json'):
                row=reader.read_json(path,events)
                if row.get('owner')==OWNER:paths.append((path,row))
            assert len(paths)<=1
            if paths:
                path,row=paths[0];same(row)
                if bound is None:bound=dict(row)
                retained.bind(row)
                report['session_file']=str(path)
                report['samples'].append(health(row,previous))
                for key in ('game_pid','game_identity','mcdk_pid','mcdk_identity'):report[key]=row.get(key)
                save('launch.json',report)
                if row.get('game_identity') and not observed:
                    cmd=[sys.executable,'-B','-X','utf8',str(HERE/'watch_exact_exit_v2.py'),
                      '--session',str(path),'--owner',OWNER,'--project',str(PROJECT),
                      '--output',str(folder/'exact-exit.json')]
                    with (folder/'exit-observer.stdout').open('xb') as out,(folder/'exit-observer.stderr').open('xb') as err:
                        observer=subprocess.Popen(cmd,cwd=ROOT,stdout=out,stderr=err,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                    report.update(observer_pid=observer.pid,observer_identity=process_identity(observer.pid));observed=True
            time.sleep(.5)
        report['launcher_returncode']=process.returncode
        assert process.returncode==0,'Cold launcher failed'
        result=reader.read_json(folder/'stdout.json',events)
        row=reader.load_session(result['session_file'],OWNER,True,events);same(row)
        if bound is None:bound=dict(row)
        retained.bind(row)
        report.update(session_file=row['session_file'])
        assert observed and (folder/'exact-exit.json').exists(),'Retained exit handles required before diagnostics'
        health(row,previous);trial.runtime_matches(PROJECT,args.manifest)
        report['ready']=True
        print(json.dumps({'ready':True,'session_file':row['session_file'],'owner':OWNER,
          'watch_binding':str(folder/'watch-binding.json'),'watch':str(folder/'assert-watch/status.json')}))
    except Exception as error:
        report['error']='%s: %s'%(type(error).__name__,error)
        report['requires_exact_owned_stop']=True
        raise
    finally:
        try:
            if not report['ready'] and retained.rows and bound is not None:
                def read_bound_session():
                    return reader.load_session(bound['session_file'],OWNER,False,events)
                def stop_once(current):
                    stop_command=[sys.executable,'-B','-X','utf8',str(ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'),
                      'stop','--session',current['session_file'],'--owner',OWNER]
                    result=subprocess.run(stop_command,cwd=ROOT,capture_output=True,timeout=40)
                    (folder/'failure-stop.stdout').write_bytes(result.stdout)
                    (folder/'failure-stop.stderr').write_bytes(result.stderr)
                    return result
                report['failure_cleanup']=cleanup.ordinary_stop_retained(bound,retained,read_bound_session,
                    process_identity,stop_once)
                report['requires_exact_owned_stop']=not report['failure_cleanup']['completed']
            elif not report['ready']:
                report['failure_cleanup']={'ordinary_stop_attempted':False,'reason':'No exact owned process identity had been retained','force_executed':False,'restarted':False}
        except Exception as cleanup_error:
            report['failure_cleanup_error']='%s: %s'%(type(cleanup_error).__name__,cleanup_error)
            report['requires_exact_owned_stop']=True
        finally:
            retained.close()
            save('launch.json',report)


if __name__=='__main__':main()
