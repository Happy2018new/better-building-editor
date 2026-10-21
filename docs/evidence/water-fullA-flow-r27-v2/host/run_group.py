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
    assert grant['schema']==1
    assert grant['begin']<=time.time()<grant['until']-300
    assert datetime.now(timezone.utc)<datetime.fromisoformat('2026-10-21T23:20:00+00:00'),'Insufficient time before 07:25 capture cutoff'
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
        import verify_debug_blueprints as blueprints
        from flow_restore import restore_scene
        check={'schema':1,'owner':binding['owner'],'restored':False,'restore_unknown':True,'checked_at':time.time()}
        try:
            with base.Client(timeout=20) as client:
                check['scene']=restore_scene(client,base.run,blueprints)
                from world_readback import readback, compare
                baseline=json.loads((WORK/'world-baseline-v1.json').read_bytes())
                check['world']=readback(client,base.run)
                check['world_verdict']=compare(check['world'],baseline['state'])
            check['source_unchanged']=all(sha(Path(binding['project'])/name)==expected for name,expected in
                                        dict(binding['source_sha256'],**binding['auxiliary_sha256']).items())
            check['restored']=check['scene']['restored'] and check['source_unchanged'] and check['world_verdict']['restored']
            check['restore_unknown']=False
        except Exception as error:
            check['error']={'type':type(error).__name__,'message':str(error)}
            raise
        finally:
            with (WORK/('independent-restore-v1.json' if label=='final' else 'independent-restore-'+label+'.json')).open('x',encoding='utf-8') as stream:json.dump(check,stream,indent=2)
        assert check['restored'],check

    

    save()
    try:
        command('assert-watch-start','start_assert_watch.py')
        command('launch','launch_r25.py')
        launch=json.loads((WORK/'launch/launch.json').read_bytes())
        command('ordinary-cold-init','observe_cold_default.py')
        command('resize','resize_background.py')
        command('world-baseline','world_readback.py')
        command('camera','run_camera.py',('camera',),timeout=480)
        independent_restore('after-camera')
        command('A','run_flow.py',('A',),timeout=1800)
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
