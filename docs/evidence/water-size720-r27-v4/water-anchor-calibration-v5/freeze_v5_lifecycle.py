"""Freeze only the integer-RGB diagnostic-payload correction and new owner."""
import ast
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import subprocess,sys,zipfile

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
OLD=WORK.with_name('water-anchor-calibration-v4')
OWNER='water-r27-anchor-calibration-v3'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name,value):
    with (WORK/name).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def main():
    assert not (WORK/'plan-v1.json').exists()
    oldhost=json.loads((OLD/'prelaunch-host-binding-v1.json').read_bytes())
    names=('anchor_game.py','bootstrap_payload.py','candidate_bootstrap.py','guard_policy.py','launch_r25.py',
        'modal_guard.py','retire_bootstrap_marker.py','retire_helpers.py','run_anchor_calibration.py',
        'run_anchor_group.py','run_candidate_bootstrap.py','start_assert_watch.py','watch_handles.py')
    for name in names:
        assert sha(OLD/name)==oldhost['host_sha256'][name],name
        expected=(OLD/name).read_text('utf8').replace('water-r27-anchor-calibration-v2',OWNER)
        if name=='anchor_game.py':expected=expected.replace('(0.,0.,0.),1.,1.)','(0,0,0),1.,1.)',1)
        assert (WORK/name).read_text('utf8')==expected,name
    controls=json.loads((WORK/'configure-py2-execution-controls-v1.json').read_bytes())
    assert controls['passed'] and len(controls['rows'])==138 and controls['original_failure']['reproduced']
    assert controls['actual_CONFIGURE_sha256']==sha(WORK/'anchor_game.py')
    binding=json.loads((OLD/'final-source-binding-v1.json').read_bytes())
    binding.update(owner=OWNER,bootstrap_receipt_marker='_water_r27_anchor_bootstrap_v3',
        previous_host_binding_sha256=sha(OLD/'prelaunch-host-binding-v1.json'),
        previous_failed_attempt_review_sha256=sha(OLD/'payload-failure-review-v1.json'))
    write('final-source-binding-v1.json',binding)
    inputs=json.loads((OLD/'product-v2-launch-inputs.json').read_bytes());inputs['owner']=OWNER
    write('product-v2-launch-inputs.json',inputs)
    plan=json.loads((OLD/'plan-v1.json').read_bytes())
    plan.update(schema=5,owner=OWNER,declared_at_utc=datetime.now(timezone.utc).isoformat(),
        previous_plan_sha256=sha(OLD/'plan-v1.json'),
        changed_condition='Diagnostic pack_group RGB corrected from invalid floats to integer bytes; actual Py2 CONFIGURE executed for all 138 predeclared cells before launch.',
        previous_attempt_outcome='First empty CONFIGURE failed strict integer tint-channel validation; no captures.',
        configure_py2_execution_controls_sha256=sha(WORK/'configure-py2-execution-controls-v1.json'))
    plan['host_code_sha256']={name:sha(WORK/name) for name in ('anchor_game.py','run_anchor_calibration.py')}
    write('plan-v1.json',plan)
    stage=json.loads((OLD/'stage-r25.json').read_bytes());stage.update(owner=OWNER,plan_sha256=sha(WORK/'plan-v1.json'))
    write('stage-r25.json',stage)
    sys.path.insert(0,str(WORK));import anchor_game
    from bootstrap_payload import dispatch_code
    payloads={name:getattr(anchor_game,name) for name in ('OPEN','CONFIGURE','STATUS','CLEAN','CLEAN_READY')}
    payloads['bootstrap']=dispatch_code((WORK/'candidate_bootstrap.py').read_text('utf8'),binding)
    compile_rows=[]
    for name,text in payloads.items():
        filename='dispatched-bootstrap-payload.py' if name=='bootstrap' else 'compile-'+name+'.py'
        if name=='CONFIGURE':text=text%({'mode':'empty','model':'modern_projection_r27_anchor_15','rect':[1,2,3,4],
            'position':[1,1,1],'pose':[0.,0.,0.],'unit_fraction':.18,'offset_factor':0.},)
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
    external=oldhost['external_host_sha256'];assert all(sha(ROOT/name)==v for name,v in external.items())
    for path in WORK.glob('*.py'):ast.parse(path.read_bytes(),filename=str(path))
    hosts={path.name:sha(path) for path in WORK.glob('*.py')}|{name:sha(WORK/name) for name in ('product-v2-launch-inputs.json','stage-r25.json','plan-v1.json')}
    write('prelaunch-host-binding-v1.json',{'schema':5,'source_binding_sha256':sha(WORK/'final-source-binding-v1.json'),
        'host_sha256':hosts,'external_host_sha256':external,'MC_started':False,
        'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'previous_host_binding_sha256':sha(OLD/'prelaunch-host-binding-v1.json')})
    review={'schema':5,'MC_started':False,'owner':OWNER,'source_count':len(binding['source_sha256']),
        'auxiliary_count':len(binding['auxiliary_sha256']),'source_unchanged':True,'archive_reused_without_rezip':True,
        'archive_entries_individually_reverified':len(files),'archive_sha256':sha(archive),
        'plan_sha256':sha(WORK/'plan-v1.json'),'host_binding_sha256':sha(WORK/'prelaunch-host-binding-v1.json'),
        'host_files':len(hosts),'external_hosts':len(external),'true_python2_compile':compile_rows,
        'actual_python2_CONFIGURE_cells':138,'configure_controls_sha256':sha(WORK/'configure-py2-execution-controls-v1.json'),
        'original_failure_reproduced':True,'formal_A_accepted':False,'production_admission_performed':False,'manual_closures_added':0}
    write('v5-preparation-review-v1.json',review)
    print(json.dumps({k:review[k] for k in ('MC_started','owner','plan_sha256','host_binding_sha256','host_files','external_hosts','actual_python2_CONFIGURE_cells')}))


if __name__=='__main__':main()
