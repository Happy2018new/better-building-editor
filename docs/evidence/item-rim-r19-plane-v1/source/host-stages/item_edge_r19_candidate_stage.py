import json
import os
from pathlib import Path
import subprocess
import sys
import time
import shutil

ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT/'.runtime/item-edge-r19-candidate-control-v2'
CONTROL.mkdir(exist_ok=False)
for name in ('candidate.json','launch-sources.json'):
    shutil.copy2(ROOT/'.runtime/item-edge-r19-candidate-control'/name,CONTROL/name)
sys.path.insert(0,str(ROOT/'tools'))
from item_sprite_capture_contract import snapshot_sources,snapshot_digest
freeze=json.loads((CONTROL/'launch-sources.json').read_bytes())
assert snapshot_digest(snapshot_sources(Path(freeze['project'])))==freeze['sha256']
prior=json.loads(Path('C:/Users/Happy2018new/.pyreact-debug/instances/89265eabf8f34877a4bb7f7af895789a/session.json').read_bytes())
assert prior['state']=='stopped'
guard=prior['noactivation']
instances=ROOT/'.agents/skills/pyreact-debugging/scripts/instances.py'
command=[sys.executable,'-X','utf8',str(instances),'start','--project',freeze['project'],'--owner','item-plane-r19',
    '--name','item-plane-r19-v2','--port','19370','--wait','180','--preset','ui',
    '--mcdk',guard['mcdk']['path'],'--noactivate-mcdk-sha256',guard['mcdk']['sha256'],
    '--noactivate-dll',guard['dll']['path'],'--noactivate-sha256',guard['dll']['sha256']]
environment=dict(os.environ,MCDEV_ALLOW_USER_FOREGROUND='1')
start=subprocess.run(command,cwd=str(ROOT),env=environment,capture_output=True,text=True,encoding='utf-8',timeout=300)
(CONTROL/'start.stdout.txt').write_text(start.stdout,encoding='utf-8')
(CONTROL/'start.stderr.txt').write_text(start.stderr,encoding='utf-8')
assert start.returncode==0,'Startup failed; inspect ignored logs'
session=json.loads(start.stdout)
(CONTROL/'ready-summary.json').write_text(json.dumps({key:session.get(key) for key in
    ('id','owner','state','session_file','game_pid','game_identity','mcdk_pid','mcdk_identity')},indent=2)+'\n',encoding='utf-8')
environment.update(MCDEV_SESSION_FILE=session['session_file'],MCDEV_OWNER=session['owner'],MCDEV_MCP_URL=session['mcp_url'])
os.environ.update(environment)
wgc=ROOT/'.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
try:
    sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
    from mcdk import Client,return_value
    deadline=time.monotonic()+90
    with Client(timeout=15) as client:
        ready=False
        while time.monotonic()<deadline and not ready:
            value=client.call('execute_code',{'is_client':True,'direct_return':True,'code':
                "import mod.client.extraClientApi as api\nowner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n"
                "_result=bool(owner is not None and owner.session is not None and owner.bridge is not None)"})
            ready=return_value(value) is True
            if not ready:time.sleep(.5)
        assert ready,'Workspace not initialized'
    for label,angle in [('front',0),('side',45)]:
        output=ROOT/'.runtime'/('item-plane-r19-'+label+'-v2')
        command=[sys.executable,'-X','utf8',str(ROOT/'tools/run_visible_items_r16.py'),
            '--session',session['session_file'],'--owner',session['owner'],'--output',str(output),'--wgc',str(wgc),
            '--skip-closeup','--orientation-matrix','--orientation-cases','frame_f2_r1','--icons-only',
            '--editor-zoom','5','--near-distance','3','--maximum-handles','250000','--native-target-plain',
            '--view-angle',str(angle),'--candidate-geometry',str(CONTROL/'candidate.json')]
        (CONTROL/(label+'-command.json')).write_text(json.dumps(command,indent=2)+'\n',encoding='utf-8')
        with (CONTROL/(label+'.stdout.txt')).open('w',encoding='utf-8') as stdout, \
            (CONTROL/(label+'.stderr.txt')).open('w',encoding='utf-8') as stderr:
            result=subprocess.run(command,cwd=str(ROOT),env=environment,stdout=stdout,stderr=stderr,timeout=1800)
        assert result.returncode==0,label+' failed; inspect ignored logs'
        report=json.loads((output/'report.json').read_bytes())
        print(json.dumps({'stage':label,'completed':report.get('completed'),'source_unchanged':report.get('source_unchanged'),
            'cleanup_errors':report.get('cleanup_errors'),'error_present':bool(report.get('error'))}),flush=True)
        assert report['completed'] and report['source_unchanged'] and not report['cleanup_errors'],label+' incomplete'
finally:
    for attempt in range(3):
        stopped=subprocess.run([sys.executable,'-X','utf8',str(instances),'stop','--session',session['session_file'],
            '--owner',session['owner']],cwd=str(ROOT),capture_output=True,text=True,encoding='utf-8',timeout=50)
        (CONTROL/('stop-'+str(attempt)+'.stdout.txt')).write_text(stopped.stdout,encoding='utf-8')
        (CONTROL/('stop-'+str(attempt)+'.stderr.txt')).write_text(stopped.stderr,encoding='utf-8')
        if stopped.returncode==0:break
    state=json.loads(Path(session['session_file']).read_bytes())
    print(json.dumps({'stop_returncode':stopped.returncode,'state':state['state'],'owner':state['owner']}),flush=True)
