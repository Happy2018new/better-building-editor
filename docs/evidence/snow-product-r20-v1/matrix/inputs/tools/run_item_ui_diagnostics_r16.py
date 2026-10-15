"""Measure the isolated alpha, depth and clip probes with public frame payloads."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client
from capture_native_window import capture
from verify_debug_blueprints import BlueprintCheck,INSTALL_PROBE,RESTORE
from run_visible_items_r16 import EDITOR_HIDE,EDITOR_SHOW
from run_item_sprite_product import STATE
from item_sprite_capture_contract import snapshot_sources,snapshot_digest,scene_layout


def main():
    import numpy as np
    from PIL import Image
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--wgc',type=Path,required=True)
    args=parser.parse_args()
    os.environ['MCDEV_ALLOW_USER_FOREGROUND']='1'
    session=json.loads(args.session.read_bytes())
    assert session['owner']==args.owner and session['state']=='ready'
    args.output.mkdir(parents=True,exist_ok=False)
    sources=snapshot_sources(Path(session['project']))
    report={'schema':1,'completed':False,'session':session,'source_sha256':snapshot_digest(sources),
            'sources':sources,'cases':[],'cleanup_errors':[],'production_qualified':False}
    def persist():
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    with Client(timeout=20) as client:
        check=BlueprintCheck(client,args.output/'blueprints.json',30)
        saved=profile_saved=False
        try:
            check.run(INSTALL_PROBE)
            saved=True
            check.run("sys._item_ui_probe_profile=s.item_profile\n_result=True")
            profile_saved=True
            source=check.run('from modern_projection.projection.debug_item_blueprints import CATALOGUE_CASES\n'
                '_result=next((identity,row["id"]) for identity,rows in CATALOGUE_CASES.items() for row in rows '
                'if row["item"]==("minecraft:diamond_sword",0))')
            for name in ('baseline','legacy','alpha','depth','clip','all'):
                profile='candidate_profile()' if name=='legacy' else "candidate_profile('3.10.0.420447')"
                modifier=("profile.items=dict((key,dict(row)) for key,row in profile.items.items())\n"
                          "profile.items[('minecraft:diamond_sword',0)]['ui_model']=%r\n" %
                          ('modern_projection_item_ui_probe_'+name)) if name not in ('baseline','legacy') else ''
                check.run('from modern_projection.projection.item_sprite_profile import candidate_profile\n'
                          'from modern_projection.projection.debug_item_blueprints import catalogue_document\n'
                          'profile='+profile+'\n'+modifier+'s.item_profile=profile\n'
                          's._loaded(catalogue_document(%r,%r))\ns.display_mode("full")\ns.grid=False\n'
                          's.camera_view(180.,0.,3.5)\nowner.open_workspace()\n_result=True' % tuple(source))
                check.wait('workspace open',lambda row:row['open'] and not row['transition'],check.navigation)
                state=check.wait(name+' ready',lambda row:row['plan_ready'] and not row['pending'] and not row['error'],
                                 lambda:check.run(STATE))
                time.sleep(.5)
                row={'name':name,'state':state,'captures':[]}
                report['cases'].append(row)
                for mode in ('hidden_before','shown','hidden_after'):
                    hide=mode.startswith('hidden')
                    if hide:
                        check.run(EDITOR_HIDE)
                    try:
                        time.sleep(.2)
                        before=check.run(STATE)
                        image=capture(session['session_file'],args.owner,args.output/(name+'_'+mode+'.png'),args.wgc)
                        after=check.run(STATE)
                        assert scene_layout(before)==scene_layout(after)
                        row['captures'].append({'mode':mode,'capture':image,'state':before,'state_after':after})
                        persist()
                    finally:
                        if hide:
                            check.run(EDITOR_SHOW)
                arrays=[np.asarray(Image.open(item['capture']['path']).convert('RGB')).astype(np.int16) for item in row['captures']]
                stable=np.max(np.abs(arrays[0]-arrays[2]),axis=2)<3
                signal=np.minimum(np.max(np.abs(arrays[1]-arrays[0]),axis=2),np.max(np.abs(arrays[1]-arrays[2]),axis=2))>8
                # Only the scene rectangle is eligible; dynamic developer text is outside it.
                roi=np.zeros_like(signal)
                height,width=signal.shape
                roi[int(height*.32):int(height*.75),int(width*.235):int(width*.775)]=True
                row['body_signal_pixels']=int(np.count_nonzero(signal&stable&roi))
                mask=(signal&stable&roi).astype(np.uint8)*255
                Image.fromarray(mask).save(args.output/(name+'_signal.png'))
                persist()
            report['completed']=True
        except Exception as error:
            report['error']=type(error).__name__+': '+str(error)
        finally:
            if saved:
                try:
                    check.run(RESTORE)
                except Exception as error:
                    report['cleanup_errors'].append('blueprint: '+str(error))
            if profile_saved:
                try:
                    check.run('s.item_profile=sys._item_ui_probe_profile\ndel sys._item_ui_probe_profile\n_result=True')
                except Exception as error:
                    report['cleanup_errors'].append('profile: '+str(error))
            report['sources_unchanged']=sources==snapshot_sources(Path(session['project']))
            persist()
    print(json.dumps({'completed':report['completed'],'error':report.get('error'),
                      'signals':dict((row['name'],row.get('body_signal_pixels')) for row in report['cases'])}))
    return 0 if report['completed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
