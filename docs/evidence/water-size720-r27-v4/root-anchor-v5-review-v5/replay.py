# -*- coding: utf-8 -*-
"""Execute every actual CONFIGURE payload against original pure Python classes.

The fake engine boundary only supplies bridge.geometry and UI setter state.
No ModSDK, MC process, RPC, rendering or game acceptance is claimed.
"""
from __future__ import print_function
import hashlib
import imp
import json
import os
import sys

WORK='D:\\HAPPY2~1\\GitHub\\BETTER~1\\RUNTIM~1\\ROC5E3~1\\WA19DE~1'
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(WORK)))
PROJECT=os.path.join(ROOT,'.runtime','projects','water-r27-anchor-diagnostic-v1')
sys.path.insert(0,os.path.join(PROJECT,'behavior_pack'))
from modern_projection.projection.liquid_transport import validate_uniforms,pack_group
from modern_projection.projection.model import Document


def sha(path):
    with open(path,'rb') as stream:return hashlib.sha256(stream.read()).hexdigest()


def main():
    assert sys.version_info[:2]==(2,7)
    output='D:\\HAPPY2~1\\GitHub\\BETTER~1\\RUNTIM~1\\ROC5E3~1\\RO2DE1~1\\controls.json'
    assert not os.path.exists(output)
    source=os.path.join(WORK,'anchor_game.py')
    game=imp.load_source('water_private_anchor_game_v5',source)
    with open(os.path.join(ROOT,'.runtime','round-20261022','water-anchor-calibration-v4','plan-v1.json'),'rb') as stream:
        plan=json.load(stream)
    configs=[]
    for window in plan['windows']:
        gui=window['expected_integer_gui']
        # This is synthetic logical size, not a native screen observation.
        logical=[float(value)/gui for value in window['physical_client']]
        for rectangle in plan['rectangles']:
            rect=[rectangle['fractions'][i]*logical[i%2] for i in range(4)]
            for pose in plan['poses']:
                base={'position':plan['position'],'pose':pose['rotation'],'rect':rect,'unit_fraction':plan['unit_fraction']}
                prefix='_'.join((window['label'],rectangle['label'],pose['label']))
                for variant in plan['variants']:
                    factor={'zero':0.,'quarter':.25,'inverse_gui':1./gui}[variant['offset']]
                    configs.append((prefix+'_'+variant['label'],dict(base,mode=variant['mode'],model=variant['model'],offset_factor=factor)))
                for selected,name in enumerate(plan['matrix_selected']):
                    configs.append((prefix+'_matrix_'+name,dict(base,mode='matrix',model='modern_projection_r27_anchor_matrix',offset_factor=0.,matrix_selected=selected)))
                control=plan['axis_controls']
                if (window['label'],rectangle['label'],pose['label'])==(control['window'],control['rectangle'],control['pose']):
                    for axis,position in enumerate(control['positions']):
                        for label in control['variants']:
                            variant=next(v for v in plan['variants'] if v['label']==label)
                            factor={'zero':0.,'quarter':.25,'inverse_gui':1./gui}[variant['offset']]
                            configs.append((prefix+'_axis'+str(axis)+'_'+label,dict(base,position=position,mode=variant['mode'],model=variant['model'],offset_factor=factor)))
    assert len(configs)==138
    class Bridge(object):
        calls=[]
        def geometry(self,document):
            assert isinstance(document,Document)
            self.calls.append(document)
            return 'synthetic_stone_geometry'
    bridge=Bridge()
    class System(object):pass
    system=System();system.bridge=bridge
    class API(object):
        def GetSystem(self,namespace,name):
            assert (namespace,name)==('ModernProjection','ModernProjectionClientSystem')
            return system
    api=API();rows=[]
    try:
        for label,config in configs:
            setter_calls=[]
            sys._r27_water_anchor_ui={'set_config':setter_calls.append}
            namespace={'sys':sys,'json':json,'api':api}
            payload=game.CONFIGURE%(config,)
            exec(compile(payload,'actual_CONFIGURE_'+label,'exec'),namespace)
            saved=sys._r27_water_anchor_ui;result=json.loads(namespace['_result'])
            validate_uniforms(result['payload'] and tuple(tuple(v) for v in result['payload']))
            assert setter_calls==[config] and saved['config']==config
            assert saved['ready'] is False and saved['stable_frames']==0
            assert saved['stone_visible']==(config['mode']=='stone')
            assert (saved['group'] is None)==(config['mode'] in ('empty','stone'))
            if saved['group'] is not None:
                assert saved['group'].model_name==config['model']
                validate_uniforms(saved['group'].uniforms)
            rows.append({'label':label,'passed':True,'mode':config['mode'],
                'payload_sha256':hashlib.sha256(payload).hexdigest(),'uniforms':result['payload']})
        # Execute the original first cell to prove the reported error remains
        # reproducible instead of merely testing an isolated helper directly.
        old=imp.load_source('water_retained_anchor_game_v4',os.path.join(ROOT,'.runtime','round-20261022','water-anchor-calibration-v4','anchor_game.py'))
        sys._r27_water_anchor_ui={'set_config':lambda value:None}
        try:exec(compile(old.CONFIGURE%(configs[0][1],),'retained_original_CONFIGURE','exec'),{'sys':sys,'json':json,'api':api})
        except ValueError as error:
            assert str(error)=='Invalid liquid tint channel'
            original_failure={'reproduced':True,'type':'ValueError','message':str(error)}
        else:raise AssertionError('Original float tint was unexpectedly accepted')
    finally:
        if hasattr(sys,'_r27_water_anchor_ui'):del sys._r27_water_anchor_ui
    report={'schema':1,'python_version':sys.version,'actual_CONFIGURE_sha256':sha(source),
        'test_host_sha256':sha(__file__),'passed':True,'rows':rows,'original_failure':original_failure,
        'stone_geometry_fake_boundary_calls':len(bridge.calls),'MC_started':False,'RPC_dispatched':False,
        'native_rendering_performed':False,'production_admission_performed':False,'manual_closures_added':0,
        'limits':'Synthetic engine/bridge/setter boundary, original Document and pack/validate modules run in actual Python 2.7.'}
    with open(output,'wb') as stream:stream.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'actual_payload_cells':len(rows),'report_sha256':sha(output),'original_failure_reproduced':True,'MC_started':False}))


if __name__=='__main__':main()
