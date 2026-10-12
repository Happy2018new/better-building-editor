"""Diagnose fixed UV ranks after independently measured background transmission."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

import numpy as np
from PIL import Image

from diagnose_liquid_coordinate_sampling import nearest_templates
from liquid_coordinate_markers import (LIMITS,check_frozen_sources,fingerprint,hypotheses,
                                       measure,passed,score,write)
from measure_native_liquid_side_uv import bilinear,spatial_templates
from analyze_liquid_workspace import capture_failures

PROPERTIES=('region','v_basis','pixel_mapping')


def subtract_background(observed,background,transmission):
    if not isinstance(transmission,(int,float)) or not np.isfinite(transmission) or not 0<transmission<1:
        raise ValueError('One finite independently declared transmission is required')
    observed,background=np.asarray(observed,float),np.asarray(background,float)
    if observed.shape!=background.shape or observed.ndim!=2 or observed.shape[1]!=3:
        raise ValueError('Background must have the identical fixed RGB sample positions')
    return observed-transmission*background


def diagnose(frame,sequences):
    if {row['role'] for row in sequences}!={'training','holdout'}:
        raise ValueError('Original training and geometry holdouts are required')
    candidates=[]
    for sampler in ('bilinear','nearest'):
        for hypothesis in hypotheses():
            rows={}
            for row in sequences:
                grid={key:np.asarray(row['grid'][key],float) for key in ('u','height','top')}
                expected=(nearest_templates(frame,grid,hypothesis) if sampler=='nearest' else
                          spatial_templates(frame[None,:,:,:3].astype(float),grid,hypothesis)[0])
                rows[row['id']]=score(expected,np.asarray(row['observed'],float))
            training=float(np.mean([rows[row['id']]['rank_rmse'] for row in sequences if row['role']=='training']))
            candidates.append((training,sampler,hypothesis,rows))
    candidates.sort(key=lambda row:row[0]);error,sampler,best,rows=candidates[0]
    identification={}
    for prop in PROPERTIES:
        alternative=next(row for row in candidates if getattr(row[2],prop)!=getattr(best,prop))
        margin=alternative[0]-error
        rejected=any(not passed(alternative[3][row['id']]) for row in sequences if row['role']=='holdout')
        identification[prop]={'identified':margin>=LIMITS['minimum_wrong_property_margin'] and rejected,
            'training_margin_rank_rmse':margin,'alternative_sampler':alternative[1],
            'alternative':alternative[2].__dict__,'alternative_holdout_rejected':rejected}
    alternative_sampler=next(row for row in candidates if row[1]!=sampler)
    return {'selected':best.__dict__,'selected_sampler':sampler,'training_rank_rmse':error,
            'sequences':rows,'identification':identification,'hypotheses_tested':len(candidates),
            'alternative_sampler_training_rank_rmse':alternative_sampler[0],
            'all_sequence_gates_passed':all(passed(row) for row in rows.values()),
            'diagnostic_gates_passed':all(passed(row) for row in rows.values()) and
                                     all(row['identified'] for row in identification.values()),
            'native_side_sampling_observed':False,'native_uv_accepted':False,'production_accepted':False}


def prepare(input_path,contrast_path,plan_path):
    baseline=json.loads(input_path.read_bytes());contrast=json.loads(contrast_path.read_bytes())
    region=contrast['contrast_controls']['native']['regions']['behind_block']
    if contrast['capture_failures'] or region['status']!='OBSERVED':
        raise ValueError('Independent contrast evidence did not pass')
    plan={'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),'diagnostic_only':True,
          'post_observation_model':True,'input':fingerprint(input_path),'original_plan':baseline['plan'],
          'independent_contrast':fingerprint(contrast_path),'contrast_region':'native/behind_block',
          'transmission':region['transmission'],'independent_contrast_rgb_rmse':region['rgb_rmse'],
          'background_control':'supported_negative','background_sampling':'Identical frozen native sample points, bilinear PNG sampling',
          'photometry':'Observed RGB minus one fixed scalar transmission times background RGB; no clipping, fitting, gain, bias, or per-candidate terms',
          'samplers':['bilinear','nearest'],'hypotheses':[row.__dict__ for row in hypotheses()],
          'limits':LIMITS,'required_properties':list(PROPERTIES),'sampler_identification_required':False,
          'sources':{'background_tool':fingerprint(Path(__file__)),
                     'nearest_tool':fingerprint(Path(__file__).with_name('diagnose_liquid_coordinate_sampling.py'))},
          'native_uv_accepted':False,'production_accepted':False,
          'acceptance_limit':'Background model and sampler family were proposed after observing native residuals. Diagnostic success cannot replace frozen raw-rank v2 acceptance; transmission transfers between different exact native fixtures and is not directly measured for marker cases.'}
    write(plan_path,plan);return fingerprint(plan_path)


def analyze(plan_path,output):
    plan=json.loads(plan_path.read_bytes())
    for reference in [plan['input'],plan['original_plan'],plan['independent_contrast']]+list(plan['sources'].values()):
        if fingerprint(reference['path'])!=reference:
            raise ValueError('Frozen diagnostic evidence or source changed')
    baseline=json.loads(Path(plan['input']['path']).read_bytes())
    if baseline['capture_failures']:raise ValueError('Native capture provenance failed')
    original=json.loads(Path(plan['original_plan']['path']).read_bytes());check_frozen_sources(original)
    raw_path=Path(baseline['source']['path'])
    if fingerprint(raw_path)!=baseline['source']:raise ValueError('Frozen native report changed')
    raw=json.loads(raw_path.read_bytes());controls={row['case']:row for row in raw['cases']}
    receipts={row['case']:row['controls'][plan['background_control']]['capture']['capture'] for row in raw['cases']}
    failures=capture_failures(receipts,raw['session_binding'])
    if failures:raise ValueError('Native background PNG provenance failed: '+str(failures))
    sequences=[]
    for sequence in baseline['sampled_sequences']:
        depth=sequence['id'].split('/')[0]
        row=next(row for row in raw['cases'] if '_depth_'+depth+'_' in row['case'])
        capture=row['controls'][plan['background_control']]['capture']
        points=np.asarray(sequence['native_sample_points'],float)
        with Image.open(capture['path']) as image:rgb=np.asarray(image.convert('RGB'),float)
        background=bilinear(rgb,points[:,0],points[:,1])
        residual=subtract_background(sequence['observed'],background,plan['transmission'])
        sequences.append(dict(sequence,observed=residual.tolist(),background_samples=background.tolist()))
    asset=next(row for row in original['assets'] if Path(row['generated']['path']).name=='water_flow_grey.png')
    if fingerprint(asset['generated']['path'])!=asset['generated']:raise ValueError('Frozen marker changed')
    with Image.open(asset['generated']['path']) as image:frame=np.asarray(image.convert('RGBA'))[:asset['dimensions'][0]]
    result=diagnose(frame,sequences)
    result.update(schema=1,plan=fingerprint(plan_path),input=plan['input'],transmission=plan['transmission'],
                  diagnostic_only=True,post_observation_model=True,
                  original_bilinear_passed=baseline['passed'],original_bilinear_training_rank_rmse=baseline['training_rank_rmse'],
                  sampled_sequences=sequences,limits=plan['limits'],background_capture_failures=failures,
                  background_context_limit='Removing water may alter light transport even when all retained block states and camera are fixed',
                  acceptance_limit=plan['acceptance_limit'])
    write(output,result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=('prepare','analyze'));parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--input',type=Path);parser.add_argument('--contrast',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.step=='prepare':
        if args.input is None or args.contrast is None:parser.error('--input and --contrast are required')
        print(json.dumps(prepare(args.input,args.contrast,args.plan)))
    else:
        if args.output is None:parser.error('--output is required')
        result=analyze(args.plan,args.output)
        print(json.dumps({key:result[key] for key in ('selected','selected_sampler','training_rank_rmse','diagnostic_gates_passed','identification')}))


if __name__=='__main__':main()
