"""Bounded Python 2 editor benchmark; scratch documents, no world/library writes."""
import argparse
import base64
import json
import time
import verify_ui as ui
from verify_font_share_polish import game


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', default='before')
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    if args.install:
        for name in ('storage','jobs'):
            source=base64.b64encode((ui.ROOT/('behavior_pack/modern_projection/projection/'+name+'.py')).read_bytes()).decode('ascii')
            game('import base64\nfrom modern_projection.projection import '+name+' as module\n'
                 'scope=dict(module.__dict__)\nexec(compile(base64.b64decode('+repr(source)+'),'+repr(name+'.py')+',"exec"),scope)\n'+
                 ('module.BlockStore.fill_mask=scope["BlockStore"].fill_mask.im_func\n' if name=='storage' else
                  'module.__dict__.update(scope)\n')+'_result=True')
    reports = []
    for case in ('fill', 'shell', 'masked_fill', 'partial_erase'):
        game('''import time
from modern_projection.projection.model import Document,Editor
from modern_projection.projection.jobs import EditJob
from modern_projection.projection.storage import Selection
scratch=Editor(Document((64,128,64)))
case='''+repr(case)+'''
if case in ('masked_fill','partial_erase'):
    scratch.run('fill')
    scratch.select_box((1,1,1),(62,126,62))
    scratch.material=('minecraft:wool',3)
    scratch.locked_layers=set([3,63,126])
    if case=='masked_fill':scratch.mask='solid'
job=EditJob(scratch,'erase' if case=='partial_erase' else 'fill' if case=='masked_fill' else case)
api._job_perf={'done':False,'costs':[],'started':time.clock()}
def instrument(job,editor,record,bridge,clock):
    def step():
        start=clock()
        job.step()
        record['costs'].append((clock()-start)*1000.)
        if not job.done:
            bridge.next_frame(step)
            return
        record.update(done=True,error=job.error,changed=job.changed,blocks=len(editor.document.blocks),
                      wall_ms=(clock()-record['started'])*1000.)
        start=clock();editor.undo();record['undo_ms']=(clock()-start)*1000.
        start=clock();editor.redo();record['redo_ms']=(clock()-start)*1000.
    return step
s.bridge.next_frame(instrument(job,scratch,api._job_perf,s.bridge,time.clock))
_result=True''')
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            result = game('_result=api._job_perf')
            if result['done']:break
            time.sleep(.2)
        assert result['done'] and not result['error'], result
        result.update(case=case, cpu_ms=sum(result['costs']), peak_step_ms=max(result['costs']))
        reports.append(result)
        print(json.dumps({k:v for k,v in result.items() if k!='costs'}), flush=True)
    (ui.OUT/('perf67_jobs_'+args.label+'.json')).write_text(json.dumps(reports,indent=2),encoding='utf8')


if __name__=='__main__':main()
