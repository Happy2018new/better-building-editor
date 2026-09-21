"""Profile a fixed maximum document without changing library/world."""
import json
import time
import verify_ui as ui
from verify_materials_paste import game
from mcdk import Client


def main():
    with Client() as client:
        job=client.call('mc_profiler',{'op':'/start','args':{'kind':'python.cpu','target':'client','clock':'wall','duration_seconds':18,'storage':'disk'}})['structuredContent']['job']['id']
    payload=(ui.OUT/'stage51_max_shell.json').read_text(encoding='utf8')
    game('import json\nfrom HelloScript.projection.model import Document\ns._loaded(Document.from_data(json.loads('+repr(payload)+')))\ns.emit()\n_result=True')
    for unused in range(36):time.sleep(.5)
    with Client() as client:result=client.call('mc_profiler',{'op':'/query','args':{'job_id':job,'view':'hotspots','limit':35}})
    (ui.OUT/'stage51_build_profile.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    for row in result['structuredContent']['data']['records']:
        d={k:v['value'] for k,v in row['fields'].items()}
        print(d['module'],d['name'],d['calls'],round(d['total_time'],3),flush=True)


if __name__=='__main__':main()
