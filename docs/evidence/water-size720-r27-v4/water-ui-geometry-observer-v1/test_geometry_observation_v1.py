"""Explicit synthetic parent/active/hidden controls, including hidden zero size."""
import copy,hashlib,json,time
from pathlib import Path
from geometry_observation import describe_snapshot

WORK=Path(__file__).resolve().parent


def main():
    output=WORK/'geometry-synthetic-controls-v1.json';assert not output.exists()
    hidden={'position':[0.,0.],'global_position':[10.,20.],'size':[0.,0.],
            'actual_visible':False,'model_id':-1}
    base={'ready':True,'config':{'mode':'empty','rect':[10.,20.,200.,100.],'offset_factor':0.},
        'viewport_parent':{'global_position':[10.,20.],'size':[200.,100.],'actual_visible':True},
        'native':[copy.deepcopy(hidden) for _ in range(3)],
        'renderer':{'visible':[False,False],'ids':[None,None]}}
    rows=[]
    def check(label,snapshot,expected):
        result=describe_snapshot(snapshot)
        assert result['contract_observation_complete']==expected,(label,result)
        rows.append({'name':label,'expected_complete':expected,'passed':True,'result':result})
    check('empty_hidden_zero_dims_parent_positive',base,True)
    stone=copy.deepcopy(base);stone['config']['mode']='stone'
    stone['native'][2].update(size=[200.,100.],actual_visible=True,model_id=55)
    check('stone_only_visible_actual_model',stone,True)
    neutral=copy.deepcopy(base);neutral['config'].update(mode='neutral',offset_factor=.25)
    neutral['native'][1].update(size=[200.,100.],actual_visible=True,model_id=77,global_position=[10.,45.])
    neutral['renderer'].update(visible=[False,True],ids=[None,77])
    check('neutral_active_slot1_parent_offset_hidden0',neutral,True)
    for name,mutate in [
        ('hidden_parent',lambda value:value['viewport_parent'].update(actual_visible=False)),
        ('zero_parent_size',lambda value:value['viewport_parent'].update(size=[0.,0.])),
        ('wrong_parent_position',lambda value:value['viewport_parent'].update(global_position=[11.,20.])),
        ('zero_active_size',lambda value:value['native'][1].update(size=[0.,0.])),
        ('wrong_active_position',lambda value:value['native'][1].update(global_position=[10.,20.])),
        ('missing_active_model',lambda value:value['native'][1].update(model_id=-1)),
        ('wrong_renderer_id',lambda value:value['renderer'].update(ids=[None,78])),
        ('both_skeleton_banks_visible',lambda value:value['renderer'].update(visible=[True,True])),
        ('hidden_slot_actually_visible',lambda value:value['native'][0].update(actual_visible=True))]:
        negative=copy.deepcopy(neutral);mutate(negative);check(name,negative,False)
    report={'schema':1,'checked_at':time.time(),'passed':True,'controls':rows,
        'host_sha256':hashlib.sha256((WORK/'geometry_observation.py').read_bytes()).hexdigest(),
        'MC_started':False,'native_observation_performed':False,'formal_A_accepted':False}
    with output.open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'passed':True,'controls':len(rows),'report_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
