"""Copy frozen SDK observer host bytes and add only bounded root follow-up."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
ROUND = Path(__file__).resolve().parent.parent
BASE = ROUND / 'water-ui-geometry-observer-v1'
WORK = ROUND / 'water-ui-geometry-observer-v2'
OWNER = 'water-r27-ui-geometry-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name, value):
    (WORK / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf8', newline='\n')


def main():
    WORK.mkdir(exist_ok=False)
    old_hosts = json.loads((BASE / 'prelaunch-host-binding-v1.json').read_bytes())
    for name in old_hosts['host_sha256']:
        (WORK / name).write_bytes((BASE / name).read_bytes())
    for name in ('diagnostic-source-v1.json', 'final-source-binding-v1.json'):
        (WORK / name).write_bytes((BASE / name).read_bytes())
    for name in ('launch_r25.py',):
        text = (WORK / name).read_text('utf8').replace("OWNER = 'water-r27-ui-geometry-v1'", "OWNER = %r" % OWNER)
        (WORK / name).write_text(text, encoding='utf8', newline='\n')
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    binding.update(owner=OWNER, bootstrap_receipt_marker='_water_r27_ui_geometry_bootstrap_v2',
        previous_host_binding_sha256=sha(BASE / 'prelaunch-host-binding-v1.json'),
        frozen_at_utc=datetime.now(timezone.utc).isoformat())
    dump('final-source-binding-v1.json', binding)
    group = (WORK / 'run_geometry_group.py').read_text('utf8')
    group = group.replace("    def independent_restore():", "    def independent_restore(label='final'):")
    group = group.replace("with (WORK/'independent-restore-v1.json').open('x',encoding='utf-8')", "with (WORK/('independent-restore-v1.json' if label=='final' else 'independent-restore-'+label+'.json')).open('x',encoding='utf-8')")
    group = group.replace("    def command(label,filename,arguments=(),guard=True):", "    def command(label,filename,arguments=(),guard=True,timeout=None):")
    group = group.replace("result=subprocess.run(step['command'],cwd=ROOT,env=env,stdout=out,stderr=err)", "result=subprocess.run(step['command'],cwd=ROOT,env=env,stdout=out,stderr=err,timeout=timeout)")
    needle = "    save()\n    try:\n        command('assert-watch-start','start_assert_watch.py')"
    assert needle in group
    hold = '''    def bounded_root_hold():
        from hold_policy import validate_hold, validate_job, validate_release
        policy=validate_hold(grant,binding['owner'],sha(WORK/'plan-v1.json'),time.time())
        independent_restore('hold-entry')
        started=time.time()
        until=min(started+policy['max_seconds'],grant['until']-120.)
        assert until>started
        session=json.loads(Path(launch['session_file']).read_bytes())
        queue=WORK/'root-followup-authorizations'
        queue.mkdir(exist_ok=False)
        ready={'schema':1,'owner':binding['owner'],'plan_sha256':grant['plan_sha256'],
            'session_id':session['id'],'session_file':launch['session_file'],
            'source_contract_sha256':binding['source_contract_sha256'],
            'initial_observation_sha256':sha(WORK/'geometry-observation-v1.json'),
            'initial_independent_restore_sha256':sha(WORK/'independent-restore-hold-entry.json'),
            'started_at':started,'hold_until':until,'authorization_directory':str(queue),
            'release_file':str(WORK/'root-hold-release-v1.json'),
            'max_jobs':policy['max_jobs'],'max_job_seconds':policy['max_job_seconds'],
            'restored_before_ready':True,'source_unchanged':True,
            'formal_A_accepted':False,'production_admission_performed':False}
        with (WORK/'hold-ready-v1.json').open('x',encoding='utf8') as stream:json.dump(ready,stream,indent=2)
        row['hold']={'ready':ready,'jobs':[],'resource_samples':[],'ended_reason':None}
        save()
        next_job=1;last_resource=0.
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
                row['hold']['resource_samples'].append(sample)
                save()
                assert sample['available_commit_bytes']>=6*1024**3
                assert all(sample['identities_verified'].values())
                last_resource=now
            job_path=queue/('job-%03d.json'%next_job)
            if next_job<=policy['max_jobs'] and job_path.exists():
                request=json.loads(job_path.read_bytes())
                job=validate_job(request,binding['owner'],grant['plan_sha256'],session['id'],
                    next_job,ROOT,policy,now,until)
                independent_restore('before-job-%03d'%next_job)
                receipt={'number':next_job,'authorization_sha256':sha(job_path),
                    'authorization':request,'script_sha256':sha(Path(job['script'])),'started_at':time.time()}
                row['hold']['jobs'].append(receipt);save()
                # Python argv only; no shell or implicit folder scans dispatch jobs.
                command('root-followup-%03d'%next_job,job['script'],
                    ('--session',launch['session_file'],'--root-grant',str(args.root_grant.resolve(strict=True)),
                     *job['arguments']),timeout=job['timeout_seconds'])
                independent_restore('after-job-%03d'%next_job)
                receipt.update(completed=True,ended_at=time.time(),restored=True)
                save();next_job+=1
            else:
                time.sleep(.25)
        row['hold']['ended_at']=time.time()
        save()

    save()
    try:
        command('assert-watch-start','start_assert_watch.py')'''
    group = group.replace(needle, hold)
    group = group.replace("        row['completed']=True\n    except BaseException", "        bounded_root_hold()\n        row['completed']=True\n    except BaseException")
    (WORK / 'run_geometry_group.py').write_text(group, encoding='utf8', newline='\n')
    # Standalone pure policy is inserted separately before final freeze.
    dump('preparation-pending-v2.json', {'owner':OWNER,'copied_from':str(BASE),
        'source_archive_reused':True,'MC_started':False,'hold_policy_and_final_freeze_pending':True})
    print(json.dumps({'prepared_skeleton':True,'MC_started':False,'owner':OWNER}))


if __name__ == '__main__':
    main()
