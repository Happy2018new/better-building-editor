"""Independent hand-calculated orthographic and perspective corner controls."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from PIL import Image,ImageDraw

WORK=Path(__file__).resolve().parent
TARGET=WORK/'analyze_neutral_matrices.py'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output=WORK/'projection-math-controls-v1.json';assert not output.exists()
    fixture=WORK/'projection-math-fixture-v1';fixture.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('private_anchor_analysis',TARGET)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    row={'config':{'model':'modern_projection_r27_anchor_15','position':[1,1,1]},
        'before':{'native':[{'global_position':[100.,110.]}]}}
    # The explicit columns below are deliberately written by hand, separately
    # from the analyzer's entity mapping and matrix construction.
    orthographic=[.25,0.,0.,0., 0.,.5,0.,0., 0.,0.,.75,0., -.25,-1.,.5,1.]
    reference={'matrix':{'elements':orthographic},'before':{'native':[{'global_position':[100.,100.]}]}}
    mask,details=module.prediction(row,reference,2,(800,600))
    assert mask.getbbox()==(300,245,401,396),mask.getbbox()
    assert sorted(set(tuple(p) for p in details['corners']))==[
        (300.,245.),(300.,395.),(400.,245.),(400.,395.)]
    controls=[{'name':'hand_orthographic_scale_translation_and_gui_delta','passed':True,
        'expected_bounds':[300,245,401,396],'observed_bounds':mask.getbbox()}]
    for variant in ('wrong_GUI_half','wrong_GUI_double','wrong_offset_sign','wrong_axis_x_sign','wrong_axis_y_sign'):
        other,alternate=module.prediction(row,reference,2,(800,600),variant=variant)
        comparison=module.metrics(mask,other)
        assert comparison['iou']<.95,(variant,comparison)
        controls.append({'name':'fixed_negative_'+variant,'passed':True,'metrics':comparison})
    # Full-cube y/z permutation is intentionally symmetric in the base cell.
    # An axis-shift control must break the symmetry instead of fabricating a
    # rejection for the symmetric cell.
    same,_=module.prediction(row,reference,2,(800,600),variant='wrong_axis_y_z')
    assert module.metrics(mask,same)['iou']==1.
    shifted={'config':dict(row['config'],position=[1,2,1]),'before':row['before']}
    shifted_mask,_=module.prediction(shifted,reference,2,(800,600))
    swapped,_=module.prediction(shifted,reference,2,(800,600),variant='wrong_axis_y_z')
    assert module.metrics(shifted_mask,swapped)['iou']<.95
    controls.append({'name':'axis_permutation_symmetric_base_retained_shifted_axis_rejects','passed':True})

    perspective=[.5,0.,0.,0., 0.,.25,0.,0., 0.,0.,1.,.25, 0.,0.,0.,1.]
    per_ref={'matrix':{'elements':perspective},'before':{'native':[{'global_position':[100.,110.]}]}}
    _,per_details=module.prediction(row,per_ref,2,(800,600))
    # Expected points use already-decoded entity ranges x,z=0..1, y=1.5..2.5.
    expected=sorted((400.+200.*x/(1.+.25*z),300.-75.*y/(1.+.25*z))
        for x,y,z in itertools.product((0.,1.),(1.5,2.5),(0.,1.)))
    actual=sorted(tuple(p) for p in per_details['corners'])
    assert np.allclose(actual,expected,atol=1e-10),(actual,expected)
    controls.append({'name':'hand_perspective_w_division_all_eight_corners','passed':True,
                     'maximum_error':float(np.max(np.abs(np.asarray(actual)-expected)))})
    invalid={'matrix':{'elements':[0.]*16},'before':reference['before']}
    try:module.prediction(row,invalid,2,(800,600))
    except AssertionError:pass
    else:raise AssertionError('Zero clip w accepted')
    controls.append({'name':'zero_clip_w_rejected','passed':True})

    # End-to-end synthetic IO validates real label joining and axis matching.
    rows=[]
    def picture(label,polygon,color):
        image=Image.new('RGB',(800,600),(240,240,240))
        if polygon:ImageDraw.Draw(image).polygon(polygon,fill=(color,)*3)
        p=fixture/(label+'.png');image.save(p)
        return {'path':str(p),'sha256':sha(p)}
    def add(label,mode,position,polygon=None,color=64,global_y=100.,matrix=None):
        value={'label':label,'completed':True,
            'config':{'mode':mode,'model':'modern_projection_r27_anchor_15','position':position},
            'before':{'native':[{'global_position':[100.,global_y]}]},
            'capture':picture(label,polygon,color)}
        if matrix:value['matrix']={'elements':matrix}
        rows.append(value)
    prefix='gui2_wide_tilted'
    add(prefix+'_empty','empty',[1,1,1])
    add(prefix+'_stone','stone',[1,1,1],[(300,225),(400,225),(400,375),(300,375)],100)
    add(prefix+'_matrix_WORLDVIEWPROJ','matrix',[1,1,1],matrix=orthographic)
    add(prefix+'_a15_inverse_gui','neutral',[1,1,1],[(300,245),(400,245),(400,395),(300,395)],global_y=110.)
    add(prefix+'_axis0_stone','stone',[2,1,1],[(200,225),(300,225),(300,375),(200,375)],100)
    add(prefix+'_axis0_a15_inverse_gui','neutral',[2,1,1],[(200,245),(300,245),(300,395),(200,395)],global_y=110.)
    capture={'schema':1,'completed':True,'restored':True,'restore_unknown':False,
        'source_contract_sha256':'synthetic_math_control_no_product_source',
        'rows':rows,'window_rows':[{'label':'gui2','opened':{'gui':2}}]}
    capture_path=fixture/'synthetic-capture.json';capture_path.write_text(json.dumps(capture,indent=2),encoding='utf8')
    analyzed=fixture/'synthetic-analysis.json'
    result=subprocess.run([sys.executable,'-B','-X','utf8',str(TARGET),'--capture',str(capture_path),
                           '--output',str(analyzed)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    report=json.loads(analyzed.read_bytes())
    assert len(report['rows'])==2 and all(r['neutral_vs_native_WVP']['iou']==1. for r in report['rows'])
    axis=next(r for r in report['rows'] if '_axis0_' in r['label'])
    # The GUI compensation intentionally separates stone and neutral here;
    # matching-axis comparison must still be materially better than base.
    assert axis['neutral_vs_matching_axis_stone']['iou']>axis['neutral_vs_stone']['iou']
    controls.append({'name':'actual_analysis_main_synthetic_label_axis_reference_join','passed':True,
                     'analysis_sha256':sha(analyzed),'no_MC':True})
    final={'schema':1,'checked_at':time.time(),'analysis_sha256':sha(TARGET),
        'test_host_sha256':sha(Path(__file__)),'passed':True,'controls':controls,
        'MC_started':False,'native_pixels_observed':False,'formal_A_accepted':False,
        'manual_closures_added':0,'limits':'Synthetic known matrices and PNGs validate arithmetic and label joining only.'}
    with output.open('x',encoding='utf8') as stream:json.dump(final,stream,indent=2)
    print(json.dumps({'passed':True,'controls':len(controls),'report_sha256':sha(output),'MC_started':False}))


if __name__=='__main__':main()
