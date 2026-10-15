"""Replay cold marker UV ranks on independently declared native geometry."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from liquid_coordinate_markers import (check_frozen_sources,checked_capture_image,fingerprint,
                                       measure,validate_sequences,write)
from measure_native_liquid_side_uv import bilinear,side_grid
from camera_projection import project_points
from analyze_liquid_workspace import capture_failures
from capture_frozen_liquid_controls import native_gate
from capture_pure_liquid_native_controls import fixed_viewport


def analyze(path,frozen_source_archive=False):
    source=json.loads(path.read_bytes())
    plan_ref=source['coordinate_plan'];plan_path=Path(plan_ref['path'])
    if fingerprint(plan_path)!=plan_ref:
        raise ValueError('Frozen coordinate plan changed')
    plan=json.loads(plan_path.read_bytes())
    source_verification=check_frozen_sources(plan,allow_archive=frozen_source_archive)
    if fingerprint(source['calibration']['path'])['sha256'] != source['calibration']['sha256']:
        raise ValueError('Independent camera calibration fingerprint changed')
    calibration=json.loads(Path(source['calibration']['path']).read_bytes())
    if not all(calibration.get(key) for key in ('completed','passed','restored')) or calibration.get('cleanup_errors'):
        raise ValueError('Independent camera calibration did not pass')
    if Path(calibration['session_file']).resolve()!=Path(source['session_file']).resolve():
        raise ValueError('Calibration belongs to a different native session')
    failures=[];captures={};sequences=[]
    if not source['completed'] or not source['restored'] or source['cleanup_errors'] or not source['background_only']:
        failures.append('Native experiment incomplete or state not restored')
    reference={row['case']:row for row in plan['geometry_sequences']}
    validate_sequences([{'id':row['case'].split('_depth_')[1].split('_')[0]+'/'+side,
                         'role':plan['geometry_roles'][row['case'].split('_depth_')[1].split('_')[0]]}
                        for row in plan['geometry_sequences'] for side in ('north','west')])
    if [row['case'] for row in source['cases']] != [row['case'] for row in plan['geometry_sequences']]:
        raise ValueError('Declared geometry sequences were not captured exactly')
    for row in source['cases']:
        geometry=reference[row['case']]
        if not row['completed'] or set(row['controls']) != set(plan['controls']):
            raise ValueError('A declared native control is incomplete or missing')
        if row['source']['controls']!=geometry['controls']:
            failures.append(row['case']+':source differs from independent geometry')
        observed=None
        for control,item in row['controls'].items():
            if not item['completed']:
                raise ValueError('Native frame did not complete')
            capture=item['capture']
            receipt=capture['capture']
            captures[row['case']+'/'+control]=receipt
            with checked_capture_image(capture) as image:
                if control==plan['sample_control']:observed=np.asarray(image,float)
            fixed_viewport(capture,source['camera'])
            gate=native_gate(item['native_before_capture'],item['native_after_capture'],row['source'],
                             row['source']['controls'][control]['cells'])
            if not gate['public_snapshot_unchanged']:failures.append(row['case']+'/'+control+':native context changed')
        capture=row['controls'][plan['sample_control']]['capture']
        camera=source['camera'];engine=camera['stable']['screen'];native=capture['size']
        for side in ('north','west'):
            arrays={key:[] for key in ('u','height','top')};samples=[];points=[]
            for surface in geometry['surfaces']:
                if surface['side']!=side:continue
                grid=side_grid(surface['cell_origin'],surface['corner_heights'],side,
                               plan['sample_grid']['u'],plan['sample_grid']['vertical_fraction'])
                projected=project_points(grid['world_points'].tolist(),camera['position'],camera['target'],
                                         engine,calibration['vertical_fov'])
                xy=np.asarray([[point['screenX']*native[0]/engine[0],point['screenY']*native[1]/engine[1]]
                               for point in projected])
                if not all(point['isInScreen'] and point['depth']>.05 for point in projected):
                    raise ValueError('Fixed geometry samples fall outside the native camera')
                samples.extend(bilinear(observed,xy[:,0],xy[:,1]).tolist())
                points.extend(xy.tolist())
                for key in arrays:arrays[key].extend(grid[key].tolist())
            depth=row['case'].split('_depth_')[1].split('_')[0]
            sequences.append({'id':depth+'/'+side,'role':plan['geometry_roles'][depth],
                              'grid':arrays,'observed':samples,'native_sample_points':points})
    failures.extend(capture_failures(captures,source['session_binding']))
    asset=next(row for row in plan['assets'] if Path(row['generated']['path']).name=='water_flow_grey.png')
    if fingerprint(asset['generated']['path'])!=asset['generated']:
        raise ValueError('Frozen flow marker changed')
    with Image.open(asset['generated']['path']) as image:
        frame=np.asarray(image.convert('RGBA'))[:asset['dimensions'][0]]
    result=measure(frame,sequences)
    result.update(source=fingerprint(path),plan=plan_ref,capture_failures=failures,
                  analyzer=fingerprint(Path(__file__)),frozen_source_verification=source_verification,
                  sampled_sequences=sequences,camera_calibration=source['calibration'],
                  native_side_sampling_observed=result['passed'] and not failures,
                  scope='Cold conventional flow bitmap fixed-grid UV discrimination only; no original artwork cadence, top UV, general states, or production acceptance')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--frozen-source-archive',action='store_true',
                        help='Verify exact recorded source archives while permitting updated live tools')
    args=parser.parse_args();result=analyze(args.input,args.frozen_source_archive)
    write(args.output,result)
    print(json.dumps({key:result[key] for key in ('selected','passed','native_side_sampling_observed','capture_failures','identification')}))
    return 0 if result['native_side_sampling_observed'] else 1


if __name__=='__main__':raise SystemExit(main())
