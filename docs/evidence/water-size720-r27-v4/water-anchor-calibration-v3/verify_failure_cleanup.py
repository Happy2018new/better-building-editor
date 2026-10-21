"""Exercise the actual AST finally blocks with RPC/stop faults; no MC or RPC."""
import ast
import contextlib
from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import textwrap
import time
from types import SimpleNamespace

WORK=Path(__file__).resolve().parent
OUT=WORK/'offline-failure-controls-v2'


def final_body(path,with_context):
    tree=ast.parse(path.read_bytes())
    main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
    container=next(node for node in main.body if isinstance(node,ast.With)) if with_context else main
    item=next(node for node in container.body if isinstance(node,ast.Try) and node.finalbody)
    return ast.unparse(ast.Module(body=item.finalbody,type_ignores=[]))


def wrapper(body):
    return 'def exercise():\n try:\n  if primary:raise ValueError("original-primary-failure")\n finally:\n'+textwrap.indent(body,'  ')+'\n'


def main():
    assert not OUT.exists()
    OUT.mkdir()
    host=WORK/'run_anchor_calibration.py'
    hostbody=final_body(host,True)
    observations=[]
    cases=[('primary-rpc-cleanup-fault',True,True,True,False,True),
           ('rpc-fault-only',False,True,False,False,True),
           ('primary-source-audit-fault',True,False,False,True,True),
           ('all-clean',False,False,False,False,True),
           ('known-not-restored',False,False,False,False,False)]
    for label,primary,rpc_error,cleanup_error,source_error,restored in cases:
        report={'restored':False,'restore_unknown':True,'source_unchanged':False,'cleanup_errors':[]}
        saved=[]

        def run(client,code):
            if rpc_error:raise RuntimeError('injected-final-readonly-RPC-failure')
            return {'restored':restored}

        def cleanup(client,label):
            if cleanup_error:raise RuntimeError('injected-explicit-cleanup-failure')

        def sha(path):
            if source_error:raise OSError('injected-source-audit-failure')
            return 'expected'

        def save():
            saved.append(json.loads(json.dumps(report)))
            (OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

        scope=dict(primary=primary,report=report,opened=True,client=None,game=SimpleNamespace(CLEAN_READY='readonly'),
                   run=run,cleanup=cleanup,sha=sha,save=save,project=OUT,
                   manifest={'source_sha256':{'dummy.txt':'expected'},'auxiliary_sha256':{}},datetime=datetime,timezone=timezone)
        exec(compile(wrapper(hostbody),str(host)+'::actual-finally','exec'),scope)
        original=None
        try:scope['exercise']()
        except ValueError as error:original=str(error)
        assert bool(original)==primary
        assert not primary or original=='original-primary-failure'
        assert len(saved)==1 and 'ended_at_utc' in saved[0]
        assert report['restore_unknown']==rpc_error
        assert report['restored']==(restored and not rpc_error)
        assert report['source_unchanged']==(not source_error)
        assert len(report['cleanup_errors'])==sum((rpc_error,cleanup_error,source_error))
        observations.append({'label':label,'original_error_preserved':primary,'final_report_saved':True,
                             'restore_unknown':report['restore_unknown'],'cleanup_errors':report['cleanup_errors']})
    group=WORK/'run_anchor_group.py'
    groupbody=final_body(group,False)
    report={'completed':False,'started_at':time.time()}

    def stopped(*args,**kwargs):raise TimeoutError('injected-ordinary-stop-timeout')

    def command(*args,**kwargs):raise RuntimeError('injected-helper-retirement-failure')

    def save_group():
        (OUT/'group-stop-fault.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

    scope=dict(primary=True,WORK=OUT,initial_launch={'ready':False,'session_file':'synthetic-not-live',
               'game_pid':1,'game_identity':'synthetic-game','mcdk_pid':2,'mcdk_identity':'synthetic-mcdk'},
               row=report,save=save_group,binding={'owner':'synthetic-not-live'},env={},
               ROOT=OUT,sys=SimpleNamespace(executable='not-executed'),
               subprocess=SimpleNamespace(run=stopped),command=command,process_identity=lambda value:None,
               Path=Path,json=json,time=time)
    groupwrapper=wrapper(groupbody).replace('def exercise():\n','def exercise():\n launch=initial_launch\n')
    exec(compile(groupwrapper,str(group)+'::actual-finally','exec'),scope)
    with contextlib.redirect_stdout(io.StringIO()):
        try:scope['exercise']()
        except ValueError as error:assert str(error)=='original-primary-failure'
        else:raise AssertionError('Primary exception was lost')
    assert report['ordinary_stop_error']['type']=='TimeoutError'
    assert all(report['exact_identities_absent'].values())
    assert (OUT/'group-stop-fault.json').is_file()
    result={'schema':1,'MC_started':False,'RPC_dispatched':False,'subprocess_dispatched':False,
            'source':'Actual parsed finally blocks; fault stubs only replace IO/RPC/process operations',
            'host_sha256':hashlib.sha256(host.read_bytes()).hexdigest(),
            'group_sha256':hashlib.sha256(group.read_bytes()).hexdigest(),
            'host_cases':observations,'group_stop_timeout_primary_preserved':True,
            'group_final_report_saved':True,'manual_closures_added':0}
    with (WORK/'failure-cleanup-review-v1.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'passed':True,'host_cases':len(observations),'group_cases':1,
                      'MC_started':False,'RPC_dispatched':False,'subprocess_dispatched':False}))


if __name__=='__main__':main()
