"""Exercise bounded coordinator policy without processes, MC, RPC or waits."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
HOST = ROOT / '.runtime/round-20261022/water-ui-geometry-observer-v2/hold_policy.py'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',required=True,type=Path)
    args=parser.parse_args();out=args.output_root.resolve();out.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('owned_hold_policy',HOST)
    policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)
    grant={'schema':2,'owner':'control-owner','plan_sha256':'control-plan','begin':0.,'until':1000.,
        'hold':{'enabled':True,'max_seconds':600,'max_jobs':4,'max_job_seconds':180}}
    source=out/'allowed-no-execution.py';source.write_bytes(b'raise RuntimeError("must not execute")\n')
    request={'schema':1,'root_authorized':True,'owner':'control-owner','plan_sha256':'control-plan',
        'session_id':'control-session','number':1,'script':str(source),
        'script_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'arguments':[],
        'timeout_seconds':60,'diagnostic_only':True,'source_mutation_allowed':False,
        'production_admission_performed':False}
    rows=[]
    def check(label,callback,expected):
        try:callback()
        except (AssertionError,ValueError,FileNotFoundError):actual=False
        else:actual=True
        assert actual==expected,(label,actual)
        rows.append({'name':label,'expected_accept':expected,'passed':True})
    check('bounded_valid_grant',lambda:policy.validate_hold(grant,'control-owner','control-plan',100.),True)
    for name,mutate in (
        ('bool_not_integer_limit',lambda d:d['hold'].update(max_seconds=True)),
        ('unbounded_hold_rejected',lambda d:d['hold'].update(max_seconds=901)),
        ('expired_grant_rejected',lambda d:d.update(until=200.)),
        ('wrong_owner_rejected',lambda d:d.update(owner='wrong'))):
        value=copy.deepcopy(grant);mutate(value)
        check(name,lambda:policy.validate_hold(value,'control-owner','control-plan',100.),False)
    limits=policy.validate_hold(grant,'control-owner','control-plan',100.)
    def validate(value,now=100.):return policy.validate_job(value,'control-owner','control-plan','control-session',1,ROOT,limits,now,800.)
    check('exact_script_hash_python_argv_job',lambda:validate(request),True)
    for name,mutate in (
        ('missing_root_authorization',lambda d:d.update(root_authorized=False)),
        ('wrong_script_bytes',lambda d:d.update(script_sha256='0'*64)),
        ('wrong_session',lambda d:d.update(session_id='other')),
        ('session_override_arg',lambda d:d.update(arguments=['--session=other'])),
        ('source_mutation_rejected',lambda d:d.update(source_mutation_allowed=True)),
        ('job_timeout_bound',lambda d:d.update(timeout_seconds=181)),
        ('production_admission_rejected',lambda d:d.update(production_admission_performed=True))):
        value=copy.deepcopy(request);mutate(value)
        check(name,lambda:validate(value),False)
    check('insufficient_job_cleanup_time',lambda:validate(request,now=690.),False)
    release={'schema':1,'root_authorized':True,'owner':'control-owner','plan_sha256':'control-plan',
        'session_id':'control-session','release':True}
    check('exact_session_release',lambda:policy.validate_release(release,'control-owner','control-plan','control-session'),True)
    bad=copy.deepcopy(release);bad['session_id']='other'
    check('other_session_release_rejected',lambda:policy.validate_release(bad,'control-owner','control-plan','control-session'),False)
    report={'schema':1,'checked_at':time.time(),'passed':True,'rows':rows,
        'host_sha256':hashlib.sha256(HOST.read_bytes()).hexdigest(),
        'MC_started':False,'script_dispatched':False,'processes_started':False,'formal_A_accepted':False,
        'limits':'Policy controls do not claim live waiting, cleanup, RPC or shutdown behavior.'}
    target=out/'hold-policy-controls-v2.json'
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'controls':len(rows),'report_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
