"""Freeze and replay a post-observation nearest-texel diagnostic, never acceptance."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

import numpy as np
from PIL import Image

from liquid_coordinate_markers import (LIMITS,check_frozen_sources,fingerprint,hypotheses,
                                       passed,score,write)
from measure_native_liquid_side_uv import oriented_uv


def nearest_templates(frame,grid,hypothesis):
    width=frame.shape[0]
    if frame.shape!=(width,width,4):
        raise ValueError('A fixed RGBA square marker frame is required')
    u,height,top=(np.asarray(grid[key],float) for key in ('u','height','top'))
    v={'bottom':lambda:1-height,'top':lambda:height,
       'stretch':lambda:1-height/top}[hypothesis.side_v]()
    u,v=oriented_uv(u,v,hypothesis.orientation)
    span=width if hypothesis.region=='full' else width/2.
    offset_x=span if hypothesis.region in ('ne','se') else 0.
    offset_y=span if hypothesis.region in ('sw','se') else 0.
    if hypothesis.pixel_mapping=='centers':
        x,y=offset_x+u*(span-1),offset_y+v*(span-1)
    else:
        x,y=offset_x+u*span-.5,offset_y+v*span-.5
    x=np.clip(np.floor(x+.5).astype(int),0,width-1)
    y=np.clip(np.floor(y+.5).astype(int),0,width-1)
    return frame[y,x,:3].astype(float)


def diagnose(frame,sequences):
    if {row['role'] for row in sequences}!={'training','holdout'}:
        raise ValueError('Original training and geometry holdout roles are required')
    candidates=[]
    for hypothesis in hypotheses():
        rows={row['id']:score(nearest_templates(frame,row['grid'],hypothesis),
                              np.asarray(row['observed'],float)) for row in sequences}
        training=float(np.mean([rows[row['id']]['rank_rmse'] for row in sequences if row['role']=='training']))
        candidates.append((training,hypothesis,rows))
    candidates.sort(key=lambda row:row[0]);error,best,rows=candidates[0]
    identification={}
    for prop in ('region','v_basis','pixel_mapping'):
        alternative=next(row for row in candidates if getattr(row[1],prop)!=getattr(best,prop))
        margin=alternative[0]-error
        rejected=any(not passed(alternative[2][row['id']]) for row in sequences if row['role']=='holdout')
        identification[prop]={'identified':margin>=LIMITS['minimum_wrong_property_margin'] and rejected,
            'training_margin_rank_rmse':margin,'alternative':alternative[1].__dict__,
            'alternative_holdout_rejected':rejected}
    return {'selected':best.__dict__,'training_rank_rmse':error,'sequences':rows,
            'identification':identification,'hypotheses_tested':len(candidates),
            'all_sequence_gates_passed':all(passed(row) for row in rows.values()),
            'diagnostic_gates_passed':all(passed(row) for row in rows.values()) and
                                     all(row['identified'] for row in identification.values()),
            'native_side_sampling_observed':False,'native_uv_accepted':False,'production_accepted':False}


def prepare(input_path,plan_path):
    baseline=json.loads(input_path.read_bytes())
    plan={'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),
          'diagnostic_only':True,'post_observation_sampler_family':True,
          'input':fingerprint(input_path),'original_plan':baseline['plan'],
          'diagnostic_tool':fingerprint(Path(__file__)),'sampler':'Nearest texel: floor(pixel_coordinate+.5)',
          'sample_grid_and_camera':'Unchanged samples from frozen bilinear analysis; no resampling or image fitting',
          'texture_coordinates':'Exact original region, height/stretch, D4, and pixel-center/edge formulas; full-frame clamp unchanged',
          'limits':LIMITS,'required_properties':['region','v_basis','pixel_mapping'],
          'hypotheses':[row.__dict__ for row in hypotheses()],
          'training_ids':[row['id'] for row in baseline['sampled_sequences'] if row['role']=='training'],
          'holdout_ids':[row['id'] for row in baseline['sampled_sequences'] if row['role']=='holdout'],
          'native_uv_accepted':False,'production_accepted':False,
          'acceptance_limit':'Sampler was proposed after observing native residuals; diagnostic success cannot replace the preserved v2 failure or establish native acceptance'}
    write(plan_path,plan)
    return fingerprint(plan_path)


def analyze(plan_path,output):
    plan=json.loads(plan_path.read_bytes())
    if fingerprint(Path(__file__))!=plan['diagnostic_tool']:
        raise ValueError('Frozen diagnostic sampler changed')
    if fingerprint(plan['input']['path'])!=plan['input']:
        raise ValueError('Frozen native sample analysis changed')
    baseline=json.loads(Path(plan['input']['path']).read_bytes())
    if baseline['capture_failures']:
        raise ValueError('Native captures failed provenance gates')
    original=json.loads(Path(plan['original_plan']['path']).read_bytes())
    if fingerprint(plan['original_plan']['path'])!=plan['original_plan']:
        raise ValueError('Original bilinear plan changed')
    check_frozen_sources(original)
    asset=next(row for row in original['assets'] if Path(row['generated']['path']).name=='water_flow_grey.png')
    if fingerprint(asset['generated']['path'])!=asset['generated']:
        raise ValueError('Frozen flow marker changed')
    with Image.open(asset['generated']['path']) as image:
        frame=np.asarray(image.convert('RGBA'))[:asset['dimensions'][0]]
    result=diagnose(frame,baseline['sampled_sequences'])
    result.update(schema=1,plan=fingerprint(plan_path),input=plan['input'],
                  diagnostic_only=True,post_observation_sampler_family=True,
                  original_bilinear_passed=baseline['passed'],
                  original_bilinear_training_rank_rmse=baseline['training_rank_rmse'],limits=plan['limits'],
                  photometric_model='Unchanged candidate-independent channel ranks; no gain, bias, opacity, lighting, coordinate, geometry, or camera fitting')
    write(output,result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=('prepare','analyze'))
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.step=='prepare':
        if args.input is None:parser.error('--input is required to freeze a plan')
        print(json.dumps(prepare(args.input,args.plan)))
    else:
        if args.output is None:parser.error('--output is required for a fresh result')
        result=analyze(args.plan,args.output)
        print(json.dumps({key:result[key] for key in ('selected','training_rank_rmse','diagnostic_gates_passed','identification')}))


if __name__=='__main__':main()
