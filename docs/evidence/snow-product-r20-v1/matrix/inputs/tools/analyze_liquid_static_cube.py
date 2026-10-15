"""Score opaque same-alias cube faces independently of the water candidate."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import analyze_liquid_static_coordinates as static
from liquid_coordinate_markers import fingerprint, write
from liquid_static_coordinate_epochs import check


def analyze(plan_path, paths, output):
    if output.exists():
        raise ValueError('Choose a fresh same-alias analysis report')
    plan = json.loads(plan_path.read_bytes())
    check(plan)
    plan['_path'] = str(plan_path.resolve())
    cube_plan = deepcopy(plan)
    cube_plan['sample_grid'] = plan['cube_sample_grid']
    for row in cube_plan['geometry_sequences']:
        row['surfaces'] = plan['cube_surfaces']
    water, cube = {}, {}
    for path in paths:
        report = json.loads(path.read_bytes())
        epoch = report['static_epoch']
        if epoch in water:
            raise ValueError('Each cold immutable epoch must be unique')
        if (report['opaque_cube_alias'] != plan['cube_alias_override']
                or report['opaque_cube_surfaces'] != plan['cube_surfaces']):
            raise ValueError('Native opaque witness or resource alias differs from predeclared input')
        water[epoch] = static.samples(path, plan)
        cube[epoch] = static.samples(path, cube_plan)
    if set(water) != set(plan['epochs']):
        raise ValueError('Four fresh immutable static epochs are required')
    water_result = static.measure(water, plan)
    faces = {}
    for side in ('north', 'west'):
        measured = static.measure({epoch: [row for row in rows if row['id'].endswith('/' + side)]
                                   for epoch, rows in cube.items()}, cube_plan)
        eligible = (all(row['passed'] for row in measured['sequences'].values())
                    and all(row['passed'] for row in measured['stability'].values())
                    and all(measured['identification'][key]['identified'] for key in ('region', 'pixel_mapping')))
        measured.update(cube_spatial_candidate_observed=eligible,
            degenerate_v_basis='Unit cube top=1 makes bottom and stretch exactly identical; not claimed',
            photometry='Same native cube pixel LOW/HIGH references; no water material or phase fitted',
            native_uv_accepted=False, production_accepted=False)
        faces[side] = measured
    shared = (all(row['cube_spatial_candidate_observed'] for row in faces.values())
              and len({(row['selected']['region'], row['selected']['pixel_mapping'], row['sampler'])
                       for row in faces.values()}) == 1)
    result = {'schema': 1, 'plan': fingerprint(plan_path), 'inputs': [fingerprint(path) for path in paths],
        'water': water_result, 'cube_faces': faces, 'cube_shared_spatial_candidate_observed': shared,
        'sampled_water_epochs': water, 'sampled_cube_epochs': cube,
        'native_uv_accepted': False, 'production_accepted': False,
        'scope': 'Independent static opaque cube source/filter and guarded water measurements; all-FOV provenance review and water single-plane identifiability remain separate'}
    write(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--input', type=Path, nargs=4, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.plan.resolve(), args.input, args.output)
    print(json.dumps({'cube': {side: {key: row[key] for key in
          ('selected', 'sampler', 'training_rgb_rmse', 'cube_spatial_candidate_observed')}
          for side, row in result['cube_faces'].items()},
          'cube_shared_spatial_candidate_observed': result['cube_shared_spatial_candidate_observed'],
          'water_observed': result['water']['native_side_uv_observed']}))
