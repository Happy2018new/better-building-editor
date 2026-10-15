"""Prepare complement coordinate markers; native phase proof is still required."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

import numpy as np
from PIL import Image

from diagnose_liquid_coordinate_sampling import nearest_templates
from liquid_coordinate_markers import (NATIVE,check_frozen_sources,fingerprint,hypotheses,
                                       manifest,validate_sequences,write)
from measure_native_liquid_side_uv import side_grid,spatial_templates

ROOT=Path(__file__).resolve().parents[1]
LOW,HIGH=16,240
BITS=10
PROPERTIES=('region','v_basis','pixel_mapping')
LIMITS={'minimum_green_blue_difference':6.,'minimum_source_difference':64.,
        'maximum_contradictions':0,'minimum_wrong_property_training_contradictions':1,
        'minimum_wrong_property_holdout_contradictions':1}
GRID=[float(value) for value in np.linspace(.12,.88,16)]


def marker_frames():
    coordinates=np.arange(32,dtype=np.uint8)
    gray=coordinates^(coordinates>>1);frames=[];schedule=[]
    for axis in ('x','y'):
        for bit in range(5):
            values=(gray>>bit)&1
            plane=np.broadcast_to(values[None,:] if axis=='x' else values[:,None],(32,32))
            for complement in (False,True):
                pixels=np.where(plane^complement,HIGH,LOW).astype(np.uint8)
                frame=np.empty((32,32,4),dtype=np.uint8)
                frame[:,:,:3]=pixels[:,:,None];frame[:,:,3]=255;frames.append(frame)
                schedule.append({'frame':len(frames)-1,'kind':'coordinate_bit','axis':axis,
                                 'bit':bit,'complement':complement})
    for index in range(12):
        frame=np.full((32,32,4),LOW if index%2==0 else HIGH,dtype=np.uint8)
        frame[:,:,3]=255;frames.append(frame)
        schedule.append({'frame':len(frames)-1,'kind':'uniform_reference','level':LOW if index%2==0 else HIGH})
    return np.asarray(frames),schedule


def validate_phases(records,evidence_kind):
    if evidence_kind!='synthetic_exact_frames':
        raise ValueError('No audited independent native frame/mixture provider; native analysis is unavailable')
    if len(records)!=2*BITS:
        raise ValueError('Every coordinate bit and complement requires its own exact frame proof')
    for index,row in enumerate(records):
        if (row.get('kind')!='synthetic_exact_frame' or type(row.get('frame')) is not int or
                row['frame']!=index or row.get('interpolation_fraction')!=0.):
            raise ValueError('Independent exact frame order and zero interpolation are required')


def complement_differences(observed,phases,evidence_kind):
    validate_phases(phases,evidence_kind)
    values=np.asarray(observed,float)
    if values.ndim!=3 or values.shape[0]!=2*BITS or values.shape[2]!=3 or not np.isfinite(values).all():
        raise ValueError('Twenty finite frame-by-fixed-sample RGB arrays are required')
    return np.transpose(values[::2]-values[1::2],(1,0,2))


def expected_frames(frames,grid,hypothesis,sampler):
    if sampler=='nearest':
        return np.asarray([nearest_templates(frame,grid,hypothesis) for frame in frames[:2*BITS]])
    if sampler=='bilinear':
        return spatial_templates(frames[:2*BITS,:,:,:3].astype(float),grid,hypothesis)
    raise ValueError('Only frozen bilinear and nearest diagnostic families are declared')


def measure(frames,sequences,evidence_kind):
    sequences=validate_sequences(sequences)
    if np.asarray(frames).shape!=(32,32,32,4):
        raise ValueError('The unchanged 32-frame RGBA flow-strip dimensions are required')
    observations={}
    for row in sequences:
        differences=complement_differences(row['observed_frames'],row['phase_records'],evidence_kind)
        if len(differences)!=len(row['grid']['u']):
            raise ValueError('Complement observations must retain every frozen sample position')
        relevant=differences[:,:,1:3]
        if (np.any(np.abs(relevant)<LIMITS['minimum_green_blue_difference']) or
                np.any(np.sign(relevant[:,:,0])!=np.sign(relevant[:,:,1]))):
            raise ValueError('Every predeclared green/blue bit must have sufficient agreeing signal')
        observations[row['id']]=np.sign(relevant[:,:,0])
    candidates=[]
    for sampler in ('bilinear','nearest'):
        for hypothesis in hypotheses():
            rows={}
            for sequence in sequences:
                grid={key:np.asarray(sequence['grid'][key],float) for key in ('u','height','top')}
                expected=expected_frames(frames,grid,hypothesis,sampler)
                difference=(expected[::2]-expected[1::2])[:,:,0].T
                confident=np.abs(difference)>=LIMITS['minimum_source_difference']
                contradictions=confident&(np.sign(difference)!=observations[sequence['id']])
                rows[sequence['id']]={'contradictions':int(contradictions.sum()),
                    'source_ambiguous_bits':int((~confident).sum()),'total_bits':int(difference.size)}
            training=sum(rows[row['id']]['contradictions'] for row in sequences if row['role']=='training')
            uncertain=sum(rows[row['id']]['source_ambiguous_bits'] for row in sequences if row['role']=='training')
            candidates.append((training,uncertain,sampler,hypothesis,rows))
    candidates.sort(key=lambda row:(row[0],row[1]));error,uncertain,sampler,best,rows=candidates[0]
    identification={}
    for prop in PROPERTIES:
        alternatives=[row for row in candidates if getattr(row[3],prop)!=getattr(best,prop)]
        training_min=min(row[0] for row in alternatives)
        holdout_min=min(sum(row[4][sequence['id']]['contradictions'] for sequence in sequences
                            if sequence['role']=='holdout') for row in alternatives)
        identification[prop]={'identified':training_min>=LIMITS['minimum_wrong_property_training_contradictions'] and
                              holdout_min>=LIMITS['minimum_wrong_property_holdout_contradictions'],
            'minimum_wrong_property_training_contradictions':training_min,
            'minimum_wrong_property_holdout_contradictions':holdout_min}
    passed=all(row['contradictions']==0 and row['source_ambiguous_bits']==0 for row in rows.values())
    return {'schema':1,'evidence_kind':evidence_kind,'selected':best.__dict__,'selected_sampler':sampler,
        'training_contradictions':error,'training_source_ambiguous_bits':uncertain,'sequences':rows,
        'identification':identification,'hypotheses_tested':len(candidates),'limits':LIMITS,
        'all_sequence_gates_passed':passed,
        'synthetic_contract_passed':passed and all(row['identified'] for row in identification.values()),
        'native_executed':False,'native_phase_provider_available':False,'native_uv_accepted':False,
        'production_accepted':False,
        'uncertainty_rule':'All declared samples remain; uncertain source predictions cannot contradict data and prevent sequence acceptance',
        'photometry':'Per-pixel complementary signed green/blue differences; no gain, bias, transmission, UV shift or camera fitting'}


def prepare(project,base,geometry_plan_path):
    if base.exists():raise ValueError('Choose a fresh complement-code evidence directory')
    original=json.loads(geometry_plan_path.read_bytes())
    verification=check_frozen_sources(original,allow_archive=True)
    frames,schedule=marker_frames();source=NATIVE/'textures/blocks/water_flow_grey.png'
    with Image.open(source) as image:
        if image.size!=(32,1024):raise ValueError('Installed conventional flow dimensions differ from the fixed design')
    generated=base/'assets/water_flow_grey.png';generated.parent.mkdir(parents=True)
    Image.fromarray(frames.reshape(1024,32,4)).save(generated)
    sequences=[]
    for row in original['geometry_sequences']:
        depth=row['case'].split('_depth_')[1].split('_')[0]
        for side in ('north','west'):
            arrays={key:[] for key in ('u','height','top','world_points')}
            for surface in row['surfaces']:
                if surface['side']!=side:continue
                grid=side_grid(surface['cell_origin'],surface['corner_heights'],side,GRID,GRID)
                for key in arrays:arrays[key].extend(grid[key].tolist())
            sequences.append({'id':depth+'/'+side,'case':row['case'],'role':original['geometry_roles'][depth],
                              'grid':arrays,'controls':row['controls']})
    validate_sequences(sequences)
    sources={}
    for name in ('liquid_coordinate_bitplanes.py','liquid_coordinate_markers.py',
                 'diagnose_liquid_coordinate_sampling.py','measure_native_liquid_side_uv.py','camera_projection.py'):
        live=ROOT/'tools'/name;archive=base/'sources/tools'/name;archive.parent.mkdir(parents=True,exist_ok=True)
        archive.write_bytes(live.read_bytes());sources[name]={'live':fingerprint(live),'archive':fingerprint(archive)}
    plan={'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),'project':str(project),
        'original_geometry_plan':fingerprint(geometry_plan_path),'original_source_verification':verification,
        'frozen_sources':sources,'marker':fingerprint(generated),'installed_source':fingerprint(source),
        'target':str(project/'resource_pack/textures/blocks/water_flow_grey.png'),
        'baseline_resource_manifest':manifest(project),'dimensions':[32,1024],'levels':[LOW,HIGH],
        'schedule':schedule,'sequences':sequences,'controls':original['controls'],
        'native_name':'minecraft:water','origin':original['origin'],'camera_offset':original['camera_offset'],
        'sample_control':'supported_positive','sample_grid':{'u':GRID,'vertical_fraction':GRID},
        'samplers':['bilinear','nearest'],'hypotheses':[row.__dict__ for row in hypotheses()],
        'required_properties':list(PROPERTIES),'limits':LIMITS,
        'phase_contract':{'cadence_assumed':False,'timing_only_proof_allowed':False,
            'uv_candidate_phase_inference_allowed':False,'uniform_reference_frames_are_phase_proof':False,
            'required':'Audited independent frame identity and zero texture-frame interpolation for every capture, bound to exact asset/PNG bytes; existing ModSDK atlas lookup is insufficient',
            'provider_available':False},
        'native_prerequisites':['Independent audited texture-frame/mixture provider',
            'Fresh same-session independent stone calibration and fixed native viewport',
            'Exact frozen source/neighborhood gates before and after every capture',
            'Background-only WGC with exact wrapper/receipt payload binding',
            'Complete complement pairs and all four controls for every geometry sequence',
            'Repeated reference observations must confirm stable camera/light/alpha/background over each pair',
            'Full original resource/world restoration and identity-bound ordinary stop'],
        'source_changes':'One conventional flow PNG only; unchanged atlas, flipbook, still texture, shaders and materials',
        'no_native_launch_after_shanghai':'2026-10-12T16:10:00+08:00',
        'stop_native_and_restore_by_shanghai':'2026-10-12T16:50:00+08:00',
        'native_ready':False,'native_executed':False,'marker_installed':False,
        'native_uv_accepted':False,'production_accepted':False,
        'acceptance_limit':'Offline marker/analysis design only. Synthetic phase receipts cannot authorize native analysis. Original raw-rank gates/reports are unchanged.'}
    write(base/'plan.json',plan)
    return {'prepared':True,'plan':fingerprint(base/'plan.json'),'marker':fingerprint(generated),
            'native_ready':False,'native_executed':False,'marker_installed':False}


def analyze_synthetic(input_path):
    source=json.loads(input_path.read_bytes());reference=source['plan']
    if fingerprint(reference['path'])!=reference:raise ValueError('Frozen bit-plane plan changed')
    plan=json.loads(Path(reference['path']).read_bytes());check_frozen_sources(plan)
    validate_sequences(source['sequences']);validate_sequences(plan['sequences'])
    keys=('id','role','case','grid','controls')
    declarations=[{key:row[key] for key in keys} for row in source['sequences']]
    if declarations!=[{key:row[key] for key in keys} for row in plan['sequences']]:
        raise ValueError('Frozen sequence, source/control identity or geometry samples changed')
    frames,schedule=marker_frames()
    if fingerprint(plan['marker']['path'])!=plan['marker'] or schedule!=plan['schedule']:
        raise ValueError('Frozen complement marker or frame schedule changed')
    with Image.open(plan['marker']['path']) as image:
        if image.format!='PNG' or image.size!=(32,1024) or not np.array_equal(np.asarray(image.convert('RGBA')).reshape(frames.shape),frames):
            raise ValueError('Frozen marker pixels differ from the exact code design')
    result=measure(frames,source['sequences'],source['evidence_kind'])
    result.update(input=fingerprint(input_path),plan=reference,analyzer=fingerprint(Path(__file__)))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=('prepare','analyze-synthetic'))
    parser.add_argument('--base',type=Path);parser.add_argument('--geometry-plan',type=Path)
    parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.step=='prepare':
        if args.base is None or args.geometry_plan is None:parser.error('--base and --geometry-plan are required')
        result=prepare(ROOT,args.base.resolve(),args.geometry_plan.resolve())
    else:
        if args.input is None or args.output is None:parser.error('--input and --output are required')
        result=analyze_synthetic(args.input)
        write(args.output,result)
    print(json.dumps(result))


if __name__=='__main__':main()
