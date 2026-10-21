"""One root-granted diagnostic cold start with ordinary stop on every exit."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity
sys.path.insert(0,str(ROOT/'.runtime/round-20261022/water-size720-v3'))
from run_size_group import available_commit
sys.path.pop(0)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-grant',type=Path,required=True)
    args=parser.parse_args()
    binding=json.loads((WORK/'final-source-binding-v1.json').read_bytes())
    grant=json.loads(args.root_grant.read_bytes())
    assert grant['owner']==binding['owner'] and grant['plan_sha256']==sha(WORK/'plan-v1.json')
    from hold_policy import validate_hold
    validate_hold(grant,binding['owner'],sha(WORK/'plan-v1.json'),time.time())
    assert grant['begin']<=time.time()<grant['until']-300
    assert datetime.now(timezone.utc)<datetime.fromisoformat('2026-10-21T23:30:00+00:00')
    output=WORK/'group-execution-v1.json'
    assert not output.exists()
    row={'schema':1,'owner':binding['owner'],'completed':False,'started_at':time.time(),'steps':[],
         'formal_A_accepted':False,'production_admission_performed':False,'manual_closures_added':0,
         'host_sha256':sha(Path(__file__)),'plan_sha256':grant['plan_sha256']}
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MCDEV_ALLOW_USER_FOREGROUND='0')
    launch=None

    def save():output.write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')

    def command(label,filename,arguments=(),guard=True,timeout=None):
        step={'label':label,'started_at':time.time(),'command':[sys.executable,'-B','-X','utf8',str(WORK/filename),*arguments]}
        row['steps'].append(step)
        save()
        if guard:
            step['available_commit_bytes']=available_commit()
            assert step['available_commit_bytes']>=6*1024**3
            assert time.time()<grant['until']-60
        with (WORK/(label+'.stdout.txt')).open('xb') as out,(WORK/(label+'.stderr.txt')).open('xb') as err:
            result=subprocess.run(step['command'],cwd=ROOT,env=env,stdout=out,stderr=err,timeout=timeout)
        step.update(exit_code=result.returncode,elapsed_seconds=time.time()-step['started_at'])
        save()
        result.check_returncode()

    def independent_restore(label='final'):
        os.environ.update(MCDEV_SESSION_FILE=launch['session_file'],MCDEV_OWNER=binding['owner'],MCDEV_ALLOW_USER_FOREGROUND='0')
        sys.path.insert(0,str(Path(binding['project'])/'tools'))
        import probe_liquid_pose_channel as base
        import observer_game as game
        check={'schema':1,'owner':binding['owner'],'restored':False,'restore_unknown':True,'checked_at':time.time()}
        try:
            with base.Client(timeout=15) as client:
                check['before']=base.run(client,'''from modern_projection.pyreact import navigator
_result=json.dumps({'anchor_marker':hasattr(sys,'_r27_water_anchor_ui'),'navigator_transitioning':navigator.is_transitioning,
 'navigator_top':None if navigator.top is None else navigator.top.key})
''')
                if check['before']['anchor_marker']:
                    check['explicit_clean_return']=base.run(client,game.CLEAN)
                deadline=time.monotonic()+10
                while True:
                    check['after']=base.run(client,game.CLEAN_READY)
                    if check['after']['restored']:break
                    if time.monotonic()>deadline:raise RuntimeError('Independent UI cleanup deadline')
                    time.sleep(.1)
                check['actors']=base.run(client,'''system=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
s=system.session;b=system.bridge
_result=json.dumps({'busy':s.busy,'edit_job':s.edit_job is not None,'io_job':s.io_job is not None,
 'projection_active':s.projection_active,'world_actors':len(b.projection_entities)+int(bool(b.entity)),
 'preparing_entity':bool(b.preparing_entity)})
''')
            check['source_unchanged']=all(sha(Path(binding['project'])/name)==expected for name,expected in
                                        dict(binding['source_sha256'],**binding['auxiliary_sha256']).items())
            check['restored']=check['after']['restored'] and not any(check['actors'].values()) and check['source_unchanged']
            check['restore_unknown']=False
        except Exception as error:
            check['error']={'type':type(error).__name__,'message':str(error)}
            raise
        finally:
            with (WORK/('independent-restore-v1.json' if label=='final' else 'independent-restore-'+label+'.json')).open('x',encoding='utf-8') as stream:json.dump(check,stream,indent=2)
        assert check['restored'],check

    def bounded_root_hold():
        from hold_policy import validate_hold, validate_authorization, validate_release
        policy=validate_hold(grant,binding['owner'],sha(WORK/'plan-v1.json'),time.time())
        independent_restore('hold-entry')
        started=time.time()
        until=min(started+policy['max_seconds'],grant['until']-120.)
        assert until>started
        session=json.loads(Path(launch['session_file']).read_bytes())
        ready={'schema':1,'owner':binding['owner'],'plan_sha256':grant['plan_sha256'],
            'session_id':session['id'],'session_file':launch['session_file'],
            'source_contract_sha256':binding['source_contract_sha256'],
            'initial_observation_sha256':sha(WORK/'geometry-observation-v1.json'),
            'initial_independent_restore_sha256':sha(WORK/'independent-restore-hold-entry.json'),
            'started_at':started,'hold_until':until,'fixed_followup_script':str(WORK/'root-followup.py'),
            'authorization_file':str(WORK/'root-followup-authorization-v1.json'),
            'release_file':str(WORK/'root-hold-release-v1.json'),
            'followup_timeout_seconds':policy['followup_timeout_seconds'],
            'restored_before_ready':True,'source_unchanged':True,
            'formal_A_accepted':False,'production_admission_performed':False}
        with (WORK/'hold-ready-v1.json').open('x',encoding='utf8') as stream:json.dump(ready,stream,indent=2)
        row['hold']={'ready':ready,'followup':None,'resource_samples':[],'ended_reason':None}
        save()
        followup_done=False;last_resource=0.
        while True:
            now=time.time()
            if now>=until:
                row['hold']['ended_reason']='bounded_hold_deadline'
                break
            release=WORK/'root-hold-release-v1.json'
            if release.exists():
                value=json.loads(release.read_bytes())
                validate_release(value,binding['owner'],grant['plan_sha256'],session['id'])
                row['hold']['release']={'sha256':sha(release),'request':value}
                row['hold']['ended_reason']='root_release'
                break
            if now-last_resource>=5.:
                sample={'at':now,'available_commit_bytes':available_commit(),
                    'identities_verified':{kind:process_identity(launch[kind+'_pid'])==launch[kind+'_identity']
                        for kind in ('game','mcdk')}}
                row['hold']['resource_samples'].append(sample);save()
                assert sample['available_commit_bytes']>=6*1024**3
                assert all(sample['identities_verified'].values())
                last_resource=now
            authorization=WORK/'root-followup-authorization-v1.json'
            if not followup_done and authorization.exists():
                request=json.loads(authorization.read_bytes())
                script=WORK/'root-followup.py'
                validate_authorization(request,binding['owner'],grant['plan_sha256'],session['id'],
                    sha(script),now,until,policy['followup_timeout_seconds'])
                independent_restore('before-followup')
                row['hold']['followup']={'authorization_sha256':sha(authorization),
                    'authorization':request,'script_sha256':sha(script),'started_at':time.time()}
                save()
                command('root-followup','root-followup.py',
                    ('--session',launch['session_file'],'--root-grant',str(args.root_grant.resolve(strict=True))),
                    timeout=policy['followup_timeout_seconds'])
                independent_restore('after-followup')
                row['hold']['followup'].update(completed=True,ended_at=time.time(),restored=True)
                save();followup_done=True
            else:
                time.sleep(.25)
        row['hold']['ended_at']=time.time();save()

    save()
    try:
        command('assert-watch-start','start_assert_watch.py')
        command('launch','launch_r25.py')
        launch=json.loads((WORK/'launch/launch.json').read_bytes())
        command('bootstrap','run_candidate_bootstrap.py')
        command('geometry','run_geometry_observation.py',('--session',launch['session_file'],
                '--root-grant',str(args.root_grant.resolve(strict=True))))
        bounded_root_hold()
        row['completed']=True
    except BaseException as error:
        row['error']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
        raise
    finally:
        path=WORK/'launch/launch.json'
        if launch is None and path.exists():launch=json.loads(path.read_bytes())
        if launch and launch.get('ready'):
            try:independent_restore()
            except Exception as error:row['independent_restore_error']={'type':type(error).__name__,'message':str(error)}
            bootstrap=WORK/'candidate-bootstrap-execution-v1.json'
            if bootstrap.exists() and json.loads(bootstrap.read_bytes()).get('completed'):
                try:command('retire-bootstrap-marker','retire_bootstrap_marker.py',guard=False)
                except Exception as error:row['bootstrap_retire_error']={'type':type(error).__name__,'message':str(error)}
        try:
            if not (launch and launch.get('session_file')) and (WORK/'assert-watch-start.json').exists():
                command('retire-helpers','retire_helpers.py',guard=False)
            if launch and launch.get('session_file'):
                stopcommand=[sys.executable,'-B','-X','utf8',str(ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'),
                             'stop','--session',launch['session_file'],'--owner',binding['owner']]
                try:
                    result=subprocess.run(stopcommand,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
                    row['ordinary_stop']={'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
                except Exception as error:
                    result=None
                    row['ordinary_stop_error']={'type':type(error).__name__,'message':str(error)}
                exact={kind:(launch.get(kind+'_pid'),launch.get(kind+'_identity')) for kind in ('game','mcdk')}
                deadline=time.monotonic()+45
                while time.monotonic()<deadline and any(pid and identity and process_identity(pid)==identity for pid,identity in exact.values()):time.sleep(.25)
                row['exact_identities_absent']={kind:bool(pid and identity and process_identity(pid)!=identity) for kind,(pid,identity) in exact.items()}
                if all(row['exact_identities_absent'].values()):
                    if result is not None and result.returncode:
                        result=subprocess.run(stopcommand,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
                        row['registry_finalize']={'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
                    try:command('retire-helpers','retire_helpers.py',guard=False)
                    except Exception as error:row['helper_retire_error']={'type':type(error).__name__,'message':str(error)}
                exactexit=WORK/'launch/exact-exit.json'
                if exactexit.exists():row['same_handle_exit']=json.loads(exactexit.read_bytes())
        except Exception as error:
            row['stop_cleanup_error']={'type':type(error).__name__,'message':str(error)}
        finally:
            row['elapsed_seconds']=time.time()-row['started_at']
            save()
            print(json.dumps({'completed':row['completed'],'elapsed_seconds':row['elapsed_seconds'],'formal_A_accepted':False}),flush=True)


if __name__=='__main__':main()
