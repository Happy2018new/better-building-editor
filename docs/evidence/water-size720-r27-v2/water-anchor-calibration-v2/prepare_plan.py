"""Declare neutral geometry comparisons before any native observation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

WORK=Path(__file__).resolve().parent


def main():
    source=json.loads((WORK/'diagnostic-source-v1.json').read_bytes())
    plan={
        'schema':1,'declared_at_utc':datetime.now(timezone.utc).isoformat(),
        'owner':'water-r27-anchor-calibration-v1','project':source['private_project'],
        'diagnostic_source_manifest_sha256':hashlib.sha256((WORK/'diagnostic-source-v1.json').read_bytes()).hexdigest(),
        'source_contract_sha256':source['source_contract_sha256'],
        'scope':'Opaque neutral cube UI anchor and native shader matrices only; not water A or owner/default qualification',
        'MC_started':False,'production_admission_performed':False,'formal_A_accepted':False,
        'windows':[
            {'label':'gui4','physical_client':[1994,1105],'expected_integer_gui':4},
            {'label':'gui3','physical_client':[1600,900],'expected_integer_gui':3},
            {'label':'gui2','physical_client':[1280,720],'expected_integer_gui':2}],
        'rectangles':[
            {'label':'wide','fractions':[.12,.19,.76,.62]},
            {'label':'tall','fractions':[.27,.10,.46,.80]}],
        'poses':[{'label':'front','rotation':[0.,0.,0.]},
                 {'label':'tilted','rotation':[25.,0.,35.]}],
        'position':[1,1,1],'unit_fraction':.18,
        'variants':[
            {'label':'empty','mode':'empty','model':'modern_projection_r27_anchor_15','offset':'zero'},
            {'label':'stone','mode':'stone','model':'modern_projection_r27_anchor_15','offset':'zero'},
            {'label':'a15_zero','mode':'neutral','model':'modern_projection_r27_anchor_15','offset':'zero'},
            {'label':'a15_quarter','mode':'neutral','model':'modern_projection_r27_anchor_15','offset':'quarter'},
            {'label':'a15_inverse_gui','mode':'neutral','model':'modern_projection_r27_anchor_15','offset':'inverse_gui'},
            {'label':'a0_zero','mode':'neutral','model':'modern_projection_r27_anchor_0','offset':'zero'}],
        'axis_controls':{'window':'gui2','rectangle':'wide','pose':'tilted',
                         'positions':[[2,1,1],[1,2,1],[1,1,2]],
                         'variants':['stone','a15_inverse_gui']},
        'matrix_selected':['WORLDVIEWPROJ','WORLDVIEW','PROJ','WORLD','BONE'],
        'matrix_quantization_max_error':1/4096.,
        'shader_anchor_hypotheses':[1.5,0.],
        'logical_offset_hypotheses':['zero','min(control_size)/4','min(control_size)/integer_gui'],
        'negative_controls':['axis signs and permutations','wrong integer GUI',
            'constant +/-20 physical pixel translation','wrong offset sign','shown equals hidden'],
        'measurement':{
            'neutral_color_rgb':[64,64,64],'neutral_color_tolerance_per_channel':5,
            'foreground_signal_requires_shown_minus_empty_gt':20,
            'hull_thresholds_are_not_fitted_to_water':True,
            'record_actual_native_control_geometry_before_and_after':True,
            'require_three_ready_animation_frames':True,
            'remount_after_each_resize':True,
            'matrix_control_tiles_22_23_must_be_zero':True,
            'no_texture_ROI_search':True,'no_phase_fit':True,
            'water_flow_ROI_unchanged':True},
        'retained_original_animation_gates':{'preparation_ms':1500,'measurement_ms':3200,
            'max_gap_ms':150,'max_accounted_bytes':536870912,'not_exercised_by_this_static_probe':True},
        'resource_gates':{'min_available_commit_bytes':6*1024**3,'max_handles':250000,'max_adjacent_growth':10000},
        'estimated_exclusive_MC_minutes':18,
        'lifecycle':'root schedule -> exact frozen source archive/binding -> known assertion watcher -> ordinary cold start -> neutral/matrix host -> explicit UI marker cleanup -> source audit -> ordinary stop -> actual same-handle exit -> exact watcher retirement',
        'uniform_removal_goal':'Derive UI anchoring from native WORLDVIEWPROJ/WORLDVIEW/PROJ independently of physical resolution; SDK integer GUI correction remains a hypothesis until measured.',
        'production_no_Win32_WGC_dependency':True,
        'host_code_sha256':{name:hashlib.sha256((WORK/name).read_bytes()).hexdigest()
                             for name in ('anchor_game.py','run_anchor_calibration.py')}}
    with (WORK/'plan-v1.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(plan,stream,indent=2)
        stream.write('\n')
    print(json.dumps({'prepared':True,'MC_started':False,'plan_sha256':hashlib.sha256((WORK/'plan-v1.json').read_bytes()).hexdigest()}))


if __name__=='__main__':main()
