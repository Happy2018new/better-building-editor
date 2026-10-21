"""Exercise the actual per-capture gate at fixed limits with synthetic Win32 IO."""
import ast
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time

WORK=Path(__file__).resolve().parent


def main():
    path=WORK/'run_anchor_calibration.py'
    tree=ast.parse(path.read_bytes())
    function=next(node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name=='resource_sample')
    body=ast.Module(body=[function],type_ignores=[])
    observations=[]
    cases=[('below-both-limits',249999,240000,6*1024**3,False,True),
           ('handle-limit-rejected',250000,240001,6*1024**3,False,False),
           ('growth-limit-rejected',11000,1000,6*1024**3,False,False),
           ('decrease-is-not-growth',500,11000,6*1024**3,False,True),
           ('commit-below-minimum-rejected',500,500,6*1024**3-1,False,False),
           ('creation-identity-rejected',500,500,6*1024**3,True,False)]
    for label,count,prior,commit,changed_identity,expected in cases:
        identities={'game':'synthetic-game','mcdk':'synthetic-mcdk'}
        report={'resource_samples':[{'processes':{kind:{'identity':identity,'handles':prior}
                                                 for kind,identity in identities.items()}}]}
        closed=[];saves=[]

        def get_count(handle,pointer):pointer._obj.value=count;return True

        kernel=SimpleNamespace(GetProcessHandleCount=get_count,OpenProcess=lambda access,inherit,pid:pid,
                               CloseHandle=lambda handle:closed.append(handle))
        session={'game_pid':1,'mcdk_pid':2,'game_identity':identities['game'],'mcdk_identity':identities['mcdk']}
        scope=dict(ctypes=ctypes,wintypes=wintypes,time=time,session=session,report=report,
                   plan={'resource_gates':{'min_available_commit_bytes':6*1024**3,'max_handles':250000,'max_adjacent_growth':10000}},
                   _kernel=lambda:kernel,_identity=lambda kernel,handle:'changed' if changed_identity else identities['game' if handle==1 else 'mcdk'],
                   save=lambda:saves.append(True),available_commit=lambda:commit)
        exec(compile(body,str(path)+'::actual-resource-sample','exec'),scope)
        try:scope['resource_sample'](label)
        except AssertionError:passed=False
        else:passed=True
        assert passed==expected,(label,passed,expected)
        assert closed==([1] if changed_identity else [1,2]),closed
        assert bool(saves)==(not changed_identity)
        observations.append({'label':label,'accepted':passed,'expected':expected,
                             'all_opened_handles_closed':True,'counts_saved_before_numeric_rejection':bool(saves)})
    result={'schema':1,'MC_started':False,'real_process_opened':False,'subprocess_dispatched':False,
            'scope':'Actual resource_sample AST, synthetic Win32 IO and process identities',
            'host_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cases':observations}
    with (WORK/'resource-gate-review-v1.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'passed':True,'controls':len(observations),'MC_started':False,'real_process_opened':False}))


if __name__=='__main__':main()
