"""Run the predeclared neutral/matrix probe on a separately granted exact owner."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock,load_session,process_identity
from _window import _list_windows
sys.path.insert(0,str(ROOT/'.runtime/round-20261022/water-size720-v3'))
from resize_adapter import resize_exact,user32
from run_size_group import available_commit
import anchor_game as game


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True)
    parser.add_argument('--capture-exe',type=Path,required=True)
    parser.add_argument('--root-grant',type=Path,required=True)
    args=parser.parse_args()
    plan_path=WORK/'plan-v1.json'
    plan=json.loads(plan_path.read_bytes())
    manifest_path=WORK/'diagnostic-source-v1.json'
    manifest=json.loads(manifest_path.read_bytes())
    output=WORK/'anchor-capture-v1.json'
    assert not output.exists(),'Preserve every prior result'
    assert sha(manifest_path)==plan['diagnostic_source_manifest_sha256']
    assert all(sha(WORK/name)==expected for name,expected in plan['host_code_sha256'].items())
    project=Path(plan['project']).resolve(strict=True)
    assert all(sha(project/name)==expected for name,expected in
               dict(manifest['source_sha256'],**manifest['auxiliary_sha256']).items())
    grant=json.loads(args.root_grant.read_bytes())
    assert grant['owner']==plan['owner'] and grant['begin']<=time.time()<grant['until']-120
    assert grant['plan_sha256']==sha(plan_path)
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),
                      MCDEV_OWNER=plan['owner'],MCDEV_ALLOW_USER_FOREGROUND='0')
    session=load_session(args.session,plan['owner'],live=True)
    assert Path(session['project']).resolve()==project
    sys.path.insert(0,str(project/'tools'))
    import probe_liquid_pose_channel as base
    from probe_liquid_skeleton_matrix import decode
    import capture_native_window
    capture_native_window.ROOT=ROOT
    assert sha(args.capture_exe.resolve(strict=True))==plan["capture_exe_sha256"]
    assert base.ROOT.resolve()==project
    assert user32.SetProcessDPIAware(),'Existing resize DPI setup must succeed'
    report={'schema':1,'owner':plan['owner'],'source_contract_sha256':manifest['source_contract_sha256'],
            'source_manifest_sha256':sha(manifest_path),'plan_sha256':sha(plan_path),
            'host_sha256':sha(Path(__file__)),'started_at_utc':datetime.now(timezone.utc).isoformat(),
            'completed':False,'restored':False,'source_unchanged':False,'rows':[],
            'window_rows':[],'cleanup':[],'formal_A_accepted':False,'production_admission_performed':False}

    def save():
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')

    def run(client,code):return base.run(client,code)

    def preflight():
        assert time.time()<grant['until']-60,'Leave time for restoration'
        assert process_identity(session['game_pid'])==session['game_identity']
        value=available_commit()
        assert value>=plan['resource_gates']['min_available_commit_bytes'],value
        return {'available_commit_bytes':value,'checked_at':time.time()}

    def ready(client,code=game.STATUS,key='ready'):
        deadline=time.monotonic()+15
        while True:
            row=run(client,code)
            if row[key]:return row
            if time.monotonic()>=deadline:raise RuntimeError('UI readiness deadline: '+repr(row))
            time.sleep(.1)

    def cleanup(client,label):
        row={'label':label,'clean_return':run(client,game.CLEAN)}
        row['state']=ready(client,game.CLEAN_READY,'restored')
        report['cleanup'].append(row)
        save()
        assert row['clean_return'] is True and row['state']['restored']

    def capture(client,label,config):
        row={'label':label,'config':config,'preflight':preflight()}
        report['rows'].append(row)
        save()
        row['configured']=run(client,game.CONFIGURE%(config,))
        row['before']=ready(client)
        expected=config['rect'][2:]
        assert len(row['before']['native'])==3
        for control in row['before']['native']:
            assert all(abs(a-b)<.05 for a,b in zip(control['size'],expected)),control
        row['capture']=base.capture(args.session,plan['owner'],WORK/'captures'/(label+'.png'),args.capture_exe)
        row['after']=run(client,game.STATUS)
        for key in ('config','native','logical','screen_view_info'):
            assert row['before'][key]==row['after'][key],key
        if config['mode']=='matrix':
            row['matrix']=decode(Path(row['capture']['path']))
            assert row['matrix']['control_tiles']==[0.,0.],row['matrix']
        row['completed']=True
        save()

    opened=False
    save()
    with base.Client(timeout=45) as client:
        try:
            for window in plan['windows']:
                preflight()
                winrow={'label':window['label'],'requested':window}
                report['window_rows'].append(winrow)
                with desktop_lock():
                    windows=[value for value in _list_windows() if value['pid']==session['game_pid']]
                    assert len(windows)==1,windows
                    resize_exact(windows[0]['hwnd'],session['game_pid'],session['game_identity'],
                                 *window['physical_client'],winrow)
                winrow['opened']=run(client,game.OPEN)
                opened=True
                logical=winrow['opened']['logical']
                gui=winrow['opened']['gui']
                assert gui==window['expected_integer_gui'],winrow
                for rectangle in plan['rectangles']:
                    rect=[rectangle['fractions'][index]*logical[index%2] for index in range(4)]
                    for pose in plan['poses']:
                        baseconfig={'position':plan['position'],'pose':pose['rotation'],
                                    'rect':rect,'unit_fraction':plan['unit_fraction']}
                        for variant in plan['variants']:
                            factor={'zero':0.,'quarter':.25,'inverse_gui':1./gui}[variant['offset']]
                            config=dict(baseconfig,mode=variant['mode'],model=variant['model'],offset_factor=factor)
                            capture(client,'_'.join((window['label'],rectangle['label'],pose['label'],variant['label'])),config)
                        for selected,name in enumerate(plan['matrix_selected']):
                            config=dict(baseconfig,mode='matrix',model='modern_projection_r27_anchor_matrix',
                                        offset_factor=0.,matrix_selected=selected)
                            capture(client,'_'.join((window['label'],rectangle['label'],pose['label'],'matrix',name)),config)
                        control=plan['axis_controls']
                        if (window['label'],rectangle['label'],pose['label'])==(control['window'],control['rectangle'],control['pose']):
                            for axis,position in enumerate(control['positions']):
                                for label in control['variants']:
                                    variant=next(value for value in plan['variants'] if value['label']==label)
                                    factor={'zero':0.,'quarter':.25,'inverse_gui':1./gui}[variant['offset']]
                                    config=dict(baseconfig,position=position,mode=variant['mode'],model=variant['model'],offset_factor=factor)
                                    capture(client,'_'.join((window['label'],rectangle['label'],pose['label'],'axis'+str(axis),label)),config)
                cleanup(client,window['label'])
                opened=False
            report['completed']=True
        except BaseException as error:
            report['error']={'type':type(error).__name__,'message':str(error)}
            raise
        finally:
            if opened:
                try:cleanup(client,'finally')
                except Exception as error:report['cleanup_error']={'type':type(error).__name__,'message':str(error)}
            report['restored']=run(client,game.CLEAN_READY)['restored']
            report['source_unchanged']=all(sha(project/name)==expected for name,expected in
                dict(manifest['source_sha256'],**manifest['auxiliary_sha256']).items())
            report['ended_at_utc']=datetime.now(timezone.utc).isoformat()
            save()
    assert report['completed'] and report['restored'] and report['source_unchanged']
    print(json.dumps({'completed':True,'row_count':len(report['rows']),'restored':True,
                      'source_unchanged':True,'formal_A_accepted':False}))


if __name__=='__main__':main()
