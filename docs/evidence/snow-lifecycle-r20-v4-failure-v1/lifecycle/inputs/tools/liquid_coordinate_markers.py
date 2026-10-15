"""Cold, reversible spatial water markers and fixed UV rank discrimination."""
import argparse
import hashlib
import itertools
import json
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from measure_native_liquid_side_uv import Hypothesis, ORIENTATIONS, REGIONS, SIDE_V, bilinear, spatial_templates

ROOT = Path(__file__).resolve().parents[1]
NATIVE = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/data/resource_packs/vanilla')
LIMITS = {'maximum_rank_rmse': .09, 'minimum_rank_correlation': .95,
          'minimum_wrong_property_margin': .025, 'minimum_observed_channel_std': 3.}
GRID = [float(value) for value in np.linspace(.12, .88, 16)]
GEOMETRY_CONTRACT = Path('C:/Users/Happy2018new/.pyreact-debug/instances/78a2769a6c8946989c1e42bdac3e66a8/artifacts/native-water-side-contract-r10-v3.json')


def fingerprint(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def manifest(project):
    return {path.relative_to(project).as_posix(): fingerprint(path)['sha256']
            for path in sorted((project/'resource_pack').rglob('*')) if path.is_file()}


def check_frozen_sources(plan,allow_archive=False):
    fallbacks=[]
    for name, row in plan['frozen_sources'].items():
        if fingerprint(row['archive']['path']) != row['archive'] or row['archive']['sha256'] != row['live']['sha256']:
            raise ValueError('Frozen experiment source changed: '+name+'/archive')
        live=Path(row['live']['path'])
        current=fingerprint(live) if live.is_file() else None
        if current != row['live']:
            if not allow_archive:
                raise ValueError('Frozen experiment source changed: '+name+'/live')
            fallbacks.append({'source':name,'recorded_live':row['live'],'current_live':current,
                              'verified_archive':row['archive']})
    return {'archive_fallback_enabled':allow_archive,'archive_fallbacks':fallbacks}


def validate_sequences(sequences):
    rows=list(sequences);identifiers=set();roles=set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError('Every sequence must be a declared object')
        identifier=row.get('id')
        if not isinstance(identifier,str) or not identifier.strip() or identifier in identifiers:
            raise ValueError('Every sequence ID must be a unique nonempty string')
        role=row.get('role')
        if role not in ('training','holdout'):
            raise ValueError('Every sequence role must be training or holdout')
        identifiers.add(identifier);roles.add(role)
    if roles != {'training','holdout'}:
        raise ValueError('Independent declared training and geometry holdout sequences are required')
    return rows


def checked_capture_image(record):
    receipt=record['capture']
    path=Path(record['path']).resolve()
    if path != Path(receipt['path']).resolve():
        raise ValueError('Capture wrapper path differs from native receipt')
    payload=path.read_bytes();digest=hashlib.sha256(payload).hexdigest()
    if any(row.get('sha256') != digest or row.get('bytes') != len(payload) for row in (record,receipt)):
        raise ValueError('Opened PNG bytes differ from capture wrapper or native receipt')
    dimensions=[receipt.get('width'),receipt.get('height')];frame=receipt.get('frame',{})
    if record.get('mime') != 'image/png' or record.get('size') != dimensions or dimensions != [frame.get('width'),frame.get('height')]:
        raise ValueError('Capture wrapper or native frame dimensions differ')
    # Decode the verified bytes, so later path changes cannot replace the sampled image.
    with Image.open(BytesIO(payload)) as image:
        if image.format != 'PNG' or list(image.size) != dimensions:
            raise ValueError('Opened native capture has incorrect encoding or dimensions')
        return image.convert('RGB')


def freeze_sources(project, base):
    paths = {name:project/name for name in (
        'tools/liquid_coordinate_markers.py', 'tools/capture_liquid_coordinate_markers.py',
        'tools/analyze_liquid_coordinate_markers.py', 'tools/measure_native_liquid_side_uv.py',
        'tools/camera_projection.py', 'tools/analyze_liquid_workspace.py',
        'tools/capture_frozen_liquid_controls.py', 'tools/capture_pure_liquid_native_controls.py',
        'tools/verify_dripstone_direct_seed.py', 'tools/verify_wet_actor_visuals.py',
        'tools/verify_sign_visuals.py', 'tools/capture_native_window.py',
        'tools/verify_camera_projection.py', '.runtime/capture_static_water_controls_r9.py',
        '.runtime/calibrate_close_water_camera_r9.py')}
    paths['reviewed_frozen_harness.py'] = project.parents[1]/'tools/capture_frozen_liquid_controls.py'
    result = {}
    for name, path in paths.items():
        archive = base/'sources'/name
        archive.parent.mkdir(parents=True,exist_ok=True)
        archive.write_bytes(path.read_bytes())
        result[name] = {'live':fingerprint(path),'archive':fingerprint(archive)}
    return result


def marker_frame(width, seed):
    """Each quadrant has equal channel histograms but a different spatial code."""
    if width < 8 or width % 2:
        raise ValueError('Coordinate markers require an even square of at least eight pixels')
    side = width // 2
    result = np.zeros((width,width,4),dtype=np.uint8)
    levels = np.linspace(40,232,side*side,dtype=np.uint8)
    for quadrant in range(4):
        rng = np.random.RandomState(seed+quadrant*97)
        x,y = (quadrant%2)*side,(quadrant//2)*side
        for channel in range(3):
            result[y:y+side,x:x+side,channel] = rng.permutation(levels).reshape(side,side)
    result[:,:,3] = 255
    return result


def hypotheses():
    return [Hypothesis(region,v,orientation,1.,False,0.,mapping)
            for region,v,orientation,mapping in itertools.product(REGIONS,SIDE_V,ORIENTATIONS,('centers','edges'))]


def ranks(values):
    values = np.asarray(values,float)
    if values.ndim != 2 or values.shape[1] != 3 or not np.isfinite(values).all():
        raise ValueError('Finite three-channel samples are required')
    result = np.empty_like(values)
    for channel in range(3):
        column = values[:,channel]
        order = np.argsort(column,kind='stable')
        sorted_column = column[order]
        starts = np.r_[0,np.nonzero(np.diff(sorted_column))[0]+1]
        ends = np.r_[starts[1:],len(column)]
        for start,end in zip(starts,ends):
            result[order[start:end],channel] = (start+end-1)/2.
    return result/max(1,len(values)-1)


def score(expected,observed):
    first,second = ranks(expected),ranks(observed)
    correlations = []
    for channel in range(3):
        a,b = first[:,channel]-first[:,channel].mean(),second[:,channel]-second[:,channel].mean()
        denominator = np.sqrt(np.sum(a*a)*np.sum(b*b))
        correlations.append(float(np.sum(a*b)/denominator) if denominator else 0.)
    return {'rank_rmse':float(np.sqrt(np.mean((first-second)**2))),
            'rank_correlation':correlations, 'observed_channel_std':observed.std(axis=0).tolist()}


def passed(row):
    return (row['rank_rmse'] <= LIMITS['maximum_rank_rmse']
            and min(row['rank_correlation']) >= LIMITS['minimum_rank_correlation']
            and min(row['observed_channel_std']) >= LIMITS['minimum_observed_channel_std'])


def measure(frame,sequences):
    """No gain, bias, opacity, shift, camera, or geometry is fitted per hypothesis."""
    sequences=validate_sequences(sequences)
    sequences = [dict(row,grid={key:np.asarray(row['grid'][key],float)
                               for key in ('u','height','top')}) for row in sequences]
    candidates = []
    for hypothesis in hypotheses():
        rows = {}
        for sequence in sequences:
            expected = spatial_templates(frame[None,:,:,:3].astype(float),sequence['grid'],hypothesis)[0]
            rows[sequence['id']] = score(expected,np.asarray(sequence['observed'],float))
        training = np.mean([rows[row['id']]['rank_rmse'] for row in sequences if row['role']=='training'])
        candidates.append((float(training),hypothesis,rows))
    candidates.sort(key=lambda row:row[0])
    error,best,rows = candidates[0]
    identification = {}
    for prop in ('region','v_basis','pixel_mapping'):
        alternative = next(row for row in candidates if getattr(row[1],prop)!=getattr(best,prop))
        margin = alternative[0]-error
        holdout_rejected = any(not passed(alternative[2][row['id']]) for row in sequences if row['role']=='holdout')
        identification[prop] = {'identified':margin>=LIMITS['minimum_wrong_property_margin'] and holdout_rejected,
            'training_margin_rank_rmse':margin, 'alternative':alternative[1].__dict__,
            'alternative_holdout_rejected':holdout_rejected}
    return {'schema':1,'selected':best.__dict__,'training_rank_rmse':error,'sequences':rows,
            'identification':identification,'limits':LIMITS,'hypotheses_tested':len(candidates),
            'all_sequence_gates_passed':all(passed(row) for row in rows.values()),
            'passed':all(passed(row) for row in rows.values()) and all(row['identified'] for row in identification.values()),
            'native_uv_accepted':False,'production_accepted':False,
            'photometric_model':'Candidate-independent rank order only; no candidate-specific fitted parameters',
            'orientation_scope':'Top/bottom and D4 labels can be redundant; selected compound mapping is reported without claiming independent orientation identification'}


def write(path,value):
    if path.exists():
        raise ValueError('Preserve existing evidence: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='ascii')


def prepare(project,base):
    if base.exists():
        raise ValueError('Choose a fresh marker evidence directory')
    assets=[]
    for name,seed in (('water_still_grey.png',143),('water_flow_grey.png',271)):
        source=NATIVE/'textures/blocks'/name
        with Image.open(source) as image:
            width,height=image.size
        frame=marker_frame(width,seed)
        generated=base/'assets'/name
        generated.parent.mkdir(parents=True,exist_ok=True)
        Image.fromarray(np.tile(frame,(height//width,1,1))).save(generated)
        target=project/'resource_pack/textures/blocks'/name
        original=fingerprint(target) if target.exists() else None
        backup=base/'backups'/name
        if original:
            backup.parent.mkdir(parents=True,exist_ok=True)
            backup.write_bytes(target.read_bytes())
        assets.append({'source':fingerprint(source),'generated':fingerprint(generated),'target':str(target),
                       'original':original,'backup':fingerprint(backup) if original else None,
                       'dimensions':[width,height],'seed':seed,'repeat_each_square_frame':True,'marker_alpha':255})
    geometry=json.loads(GEOMETRY_CONTRACT.read_bytes())
    shape=json.loads(Path(geometry['shape_analysis']['path']).read_bytes())
    if not shape['all_selected_silhouettes_passed']:
        raise ValueError('Frozen independent geometry did not pass')
    plan={'schema':1,'project':str(project),'assets':assets,'baseline_resource_manifest':manifest(project),
          'generator':fingerprint(Path(__file__)),'frozen_sources':freeze_sources(project,base),
          'sample_grid':{'u':GRID,'vertical_fraction':GRID},
          'hypotheses':[row.__dict__ for row in hypotheses()],'required_properties':['region','v_basis','pixel_mapping'],
          'photometric_model':'Candidate-independent channel rank order; no candidate-specific gain/bias or coordinate fit',
          'limits':LIMITS,'native_name':'minecraft:water','depths':[0,1,3],
          'geometry_roles':{'0':'training','1':'holdout','3':'holdout'},'origin':[6,96,6],
          'camera_offset':[-2.5,2.,-3.5],'fixed_backdrop':'Unchanged quartz at sourceY-3, Chebyshev separation >=2',
          'camera_prerequisite':'Independent same-session stone calibration with unchanged gates',
          'shape_prerequisite':fingerprint(ROOT/'tools/data/native_liquid_shape_candidate_nemc_3.9.0.401155.json'),
          'geometry_contract':fingerprint(GEOMETRY_CONTRACT),'geometry_analysis':geometry['shape_analysis'],
          'geometry_analysis_sources':[shape['report'],shape['profile'],shape['analyzer']]+list(shape['sources'].values()),
          'geometry_sequences':[{'id':row['id'],'case':row['case'],'surfaces':row['surfaces'],
              'controls':row['source_plan']['controls']} for row in geometry['sequences']],
          'controls':['supported_positive','supported_negative','liquid_only','empty'],
          'sample_control':'supported_positive','sample_photometry':'Raw native RGB ranks; background gradients are not fitted away',
          'resource_changes':'Only two conventional bitmap overrides; no atlas, flipbook, metadata, material, shader, or netease bitmap edits',
          'stop_long_experiment_shanghai':'2026-10-12T16:20:00+08:00','restore_deadline_shanghai':'2026-10-12T16:35:00+08:00',
          'native_uv_accepted':False,'production_accepted':False}
    write(base/'plan.json',plan)
    return {'prepared':True,'plan':fingerprint(base/'plan.json')}


def install_restore(base,operation):
    plan=json.loads((base/'plan.json').read_bytes());project=Path(plan['project'])
    if operation=='install' and manifest(project)!=plan['baseline_resource_manifest']:
        raise ValueError('Resources changed after plan freeze')
    for row in plan['assets']:
        target=Path(row['target']);generated=Path(row['generated']['path'])
        if fingerprint(generated)!=row['generated']:
            raise ValueError('Frozen marker changed')
        if operation=='install':
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(generated.read_bytes())
        else:
            if target.exists() and fingerprint(target)['sha256']!=row['generated']['sha256']:
                raise ValueError('Another edit changed a marker; restoration refused')
            if row['original']:
                backup=Path(row['backup']['path'])
                if fingerprint(backup)!=row['backup']:
                    raise ValueError('Original resource backup changed')
                target.write_bytes(backup.read_bytes())
            elif target.exists():target.unlink()
    equal=manifest(project)==plan['baseline_resource_manifest']
    if operation=='restore' and not equal:
        raise ValueError('Full resource restoration does not match baseline')
    report={operation:True,'plan':fingerprint(base/'plan.json'),'baseline_resource_manifest_equal':equal}
    write(base/(operation+'-receipt.json'),report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('prepare','install','restore'))
    parser.add_argument('--base',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(ROOT,args.base.resolve()) if args.operation=='prepare'
                     else install_restore(args.base.resolve(),args.operation)))


if __name__=='__main__':main()
