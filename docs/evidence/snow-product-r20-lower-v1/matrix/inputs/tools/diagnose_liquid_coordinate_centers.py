"""Freeze geometry-derived absolute texel centers before new offline extraction."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

import numpy as np
from PIL import Image

from camera_projection import project_points
from diagnose_liquid_coordinate_background import diagnose
from liquid_coordinate_markers import (LIMITS,check_frozen_sources,checked_capture_image,
                                       fingerprint,validate_sequences,write)
from measure_native_liquid_side_uv import FACE_CORNERS,bilinear


def center_grid(surface):
    origin=np.asarray(surface['cell_origin'],float);heights=np.asarray(surface['corner_heights'],float)
    side=surface['side']
    if side not in ('north','west') or origin.shape!=(3,) or heights.shape!=(4,):
        raise ValueError('Declared independent north/west geometry is required')
    first,second=FACE_CORNERS[side]
    grid={key:[] for key in ('u','height','top','world_points','source_texels')}
    for j in range(16):
        u=(j+.5)/16.
        if not .12<=u<=.88:continue
        top=heights[first]*(1-u)+heights[second]*u
        for k in reversed(range(16)):
            height=1-(k+.5)/16.
            if not .12<=height/top<=.88:continue
            offset=(u,height,0.) if side=='north' else (0.,height,1-u)
            grid['u'].append(u);grid['height'].append(height);grid['top'].append(float(top))
            grid['world_points'].append((origin+offset).tolist());grid['source_texels'].append([j,k])
    if not grid['u']:raise ValueError('Declared geometry contains no legal absolute texel centers')
    return grid


def prepare(input_path,plan_path):
    baseline=json.loads(input_path.read_bytes())
    validate_sequences(baseline['sampled_sequences'])
    original=json.loads(Path(baseline['plan']['path']).read_bytes())
    if fingerprint(baseline['plan']['path'])!=baseline['plan']:raise ValueError('Original plan changed')
    check_frozen_sources(original);sequences=[]
    for row in original['geometry_sequences']:
        depth=row['case'].split('_depth_')[1].split('_')[0]
        for side in ('north','west'):
            grid={key:[] for key in ('u','height','top','world_points','source_texels')};surfaces=[]
            for surface in row['surfaces']:
                if surface['side']!=side:continue
                fixed=center_grid(surface);start=len(grid['u'])
                for key in grid:grid[key].extend(fixed[key])
                surfaces.append({'geometry':surface,'start':start,'count':len(fixed['u'])})
            sequences.append({'id':depth+'/'+side,'case':row['case'],'role':original['geometry_roles'][depth],
                              'grid':grid,'surfaces':surfaces})
    validate_sequences(sequences)
    sources={name:fingerprint(Path(__file__).with_name(name)) for name in (
        'diagnose_liquid_coordinate_centers.py','diagnose_liquid_coordinate_background.py',
        'diagnose_liquid_coordinate_sampling.py')}
    plan={'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),'diagnostic_only':True,
          'post_observation_sampling_locations':True,'input':fingerprint(input_path),'original_plan':baseline['plan'],
          'sources':sources,'sequences':sequences,'limits':LIMITS,
          'sample_design':{'coordinate_family':'nw/bottom/identity/edges',
                           'u':'(j+.5)/16 for j0..15, retaining .12<=u<=.88',
                           'height':'1-(k+.5)/16 for k0..15, retaining .12<=height/independent_top(u)<=.88',
                           'selection':'Only fixed independent geometry; no observed pixels, coordinate fitting, or post-extraction exclusions'},
          'samplers':['bilinear','nearest'],'hypotheses_per_sampler':240,
          'required_properties':['region','v_basis','pixel_mapping'],
          'photometry':'Raw RGB channel ranks; no background subtraction, gain, bias, or fitted terms',
          'native_uv_accepted':False,'production_accepted':False,
          'identification_limit':'Nearest pixel-center and pixel-edge mappings can select identical texels at these locations; absolute sequence success cannot alone identify pixel_mapping',
          'acceptance_limit':'Sampling family was proposed after native residual inspection; all original gates remain. This offline diagnostic does not accept native UV and does not cold-launch a world.'}
    write(plan_path,plan);return fingerprint(plan_path)


def analyze(plan_path,output):
    plan=json.loads(plan_path.read_bytes())
    validate_sequences(plan['sequences'])
    for reference in [plan['input'],plan['original_plan']]+list(plan['sources'].values()):
        if fingerprint(reference['path'])!=reference:raise ValueError('Frozen center diagnostic source changed')
    baseline=json.loads(Path(plan['input']['path']).read_bytes())
    validate_sequences(baseline['sampled_sequences'])
    if baseline['capture_failures']:raise ValueError('Native capture provenance failed')
    if fingerprint(baseline['source']['path'])!=baseline['source']:raise ValueError('Frozen native report changed')
    raw=json.loads(Path(baseline['source']['path']).read_bytes())
    original=json.loads(Path(plan['original_plan']['path']).read_bytes());check_frozen_sources(original)
    if fingerprint(raw['calibration']['path'])['sha256']!=raw['calibration']['sha256']:
        raise ValueError('Independent calibration changed')
    calibration=json.loads(Path(raw['calibration']['path']).read_bytes())
    if not all(calibration[key] for key in ('completed','passed','restored')) or calibration['cleanup_errors']:
        raise ValueError('Independent camera calibration did not pass')
    cases={row['case']:row for row in raw['cases']};camera=raw['camera'];engine=camera['stable']['screen']
    sequences=[]
    for sequence in plan['sequences']:
        capture=cases[sequence['case']]['controls']['supported_positive']['capture'];native=capture['size']
        projected=project_points(sequence['grid']['world_points'],camera['position'],camera['target'],engine,
                                 calibration['vertical_fov'])
        if not all(row['isInScreen'] and row['depth']>.05 for row in projected):
            raise ValueError('Declared texel center is outside the native camera')
        points=np.asarray([[row['screenX']*native[0]/engine[0],row['screenY']*native[1]/engine[1]] for row in projected])
        with checked_capture_image(capture) as image:rgb=np.asarray(image,float)
        observed=bilinear(rgb,points[:,0],points[:,1])
        sequences.append(dict(sequence,observed=observed.tolist(),native_sample_points=points.tolist()))
    asset=next(row for row in original['assets'] if Path(row['generated']['path']).name=='water_flow_grey.png')
    if fingerprint(asset['generated']['path'])!=asset['generated']:raise ValueError('Frozen marker changed')
    with Image.open(asset['generated']['path']) as image:frame=np.asarray(image.convert('RGBA'))[:asset['dimensions'][0]]
    result=diagnose(frame,sequences)
    result.update(schema=1,plan=fingerprint(plan_path),sampled_sequences=sequences,limits=plan['limits'],
                  diagnostic_only=True,post_observation_sampling_locations=True,
                  original_bilinear_passed=baseline['passed'],original_bilinear_training_rank_rmse=baseline['training_rank_rmse'],
                  identification_limit=plan['identification_limit'],acceptance_limit=plan['acceptance_limit'])
    write(output,result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=('prepare','analyze'));parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.step=='prepare':
        if args.input is None:parser.error('--input is required')
        print(json.dumps(prepare(args.input,args.plan)))
    else:
        if args.output is None:parser.error('--output is required')
        result=analyze(args.plan,args.output)
        print(json.dumps({key:result[key] for key in ('selected','selected_sampler','training_rank_rmse','all_sequence_gates_passed','diagnostic_gates_passed','identification')}))


if __name__=='__main__':main()
