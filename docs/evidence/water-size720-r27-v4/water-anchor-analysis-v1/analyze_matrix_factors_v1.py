"""Unfitted matrix factor consistency with the declared signed24 error bound."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

EPSILON=1./4096.
MATRIX_NAMES=('WORLDVIEWPROJ','WORLDVIEW','PROJ','WORLD','BONE')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def factor_check(wvp,projection,worldview):
    product=projection@worldview
    # For true P=p+dp, V=v+dv and C=c+dc with each absolute error <=e:
    # |p*v-c| <= sum(e*|p| + e*|v| + e^2) + e, elementwise.
    bounds=np.empty((4,4))
    for row in range(4):
        for column in range(4):
            bounds[row,column]=sum(EPSILON*abs(projection[row,k])+EPSILON*abs(worldview[k,column])+
                EPSILON**2 for k in range(4))+EPSILON
    residual=np.abs(product-wvp)
    return {'PROJ_times_WORLDVIEW':product.tolist(),'absolute_residual':residual.tolist(),
        'quantization_absolute_bound':bounds.tolist(),
        'consistent_with_independent_element_quantization':bool(np.all(residual<=bounds)),
        'maximum_absolute_residual':float(residual.max()),
        'maximum_residual_over_bound':float((residual/bounds).max())}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args();assert not args.output.exists()
    capture=json.loads(args.capture.read_bytes())
    if not args.allow_partial:assert capture['completed'] and capture['restored'] and not capture.get('restore_unknown')
    groups={}
    for row in capture['rows']:
        if not row.get('completed') or row['config']['mode']!='matrix':continue
        prefix,name=row['label'].split('_matrix_',1)
        groups.setdefault(prefix,{})[name]=row
    report={'schema':1,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'capture_sha256':sha(args.capture),'analysis_host_sha256':sha(Path(__file__)),
        'matrix_element_order':'column major','quantization_max_error_per_element':EPSILON,
        'partial':args.allow_partial,'no_fit_or_search':True,'rows':[],
        'formal_A_accepted':False,'production_admission_performed':False,'manual_closures_added':0,
        'limits':['Matrices come from separate frozen static captures, not simultaneous hardware register reads.',
            'Elementwise quantization consistency is diagnostic and does not establish scene or product correctness.',
            'Screen anchor displacement uses actual capture dimensions, without FOV, offset or phase fitting.']}
    for prefix,rows in sorted(groups.items()):
        record={'label':prefix,'matrix_names':sorted(rows),'complete':all(name in rows for name in MATRIX_NAMES)}
        report['rows'].append(record)
        if not record['complete']:continue
        matrices={name:np.asarray(rows[name]['matrix']['elements']).reshape((4,4),order='F') for name in MATRIX_NAMES}
        record['matrices']={name:value.tolist() for name,value in matrices.items()}
        record['factor_consistency']=factor_check(matrices['WORLDVIEWPROJ'],matrices['PROJ'],matrices['WORLDVIEW'])
        record['PROJ_bottom_row']=matrices['PROJ'][3].tolist()
        record['WORLDVIEW_axis_lengths']=[float(np.linalg.norm(matrices['WORLDVIEW'][:3,index])) for index in range(3)]
        record['WORLDVIEW_translation']=matrices['WORLDVIEW'][:3,3].tolist()
        record['WORLD_translation']=matrices['WORLD'][:3,3].tolist()
        geometry={name:[{key:control[key] for key in ('position','global_position','size')}
            for control in rows[name]['before']['native']] for name in MATRIX_NAMES}
        record['native_control_geometry_equal_across_five']=all(
            geometry[name]==geometry['WORLDVIEWPROJ'] for name in MATRIX_NAMES)
        record['native_model_ids']={name:[control.get('model_id') for control in rows[name]['before']['native']]
            for name in MATRIX_NAMES}
        record['capture_sha256']={name:rows[name]['capture']['sha256'] for name in MATRIX_NAMES}
        with Image.open(rows['WORLDVIEWPROJ']['capture']['path']) as image:
            size=image.size
        wvp=matrices['WORLDVIEWPROJ'];origin=wvp@np.asarray((0.,0.,0.,1.));anchor=wvp@np.asarray((0.,1.5,0.,1.))
        if abs(origin[3])>1e-8 and abs(anchor[3])>1e-8:
            delta=anchor[:2]/anchor[3]-origin[:2]/origin[3]
            record['plus_1p5_entity_y_screen_displacement']=[float(delta[0]*size[0]/2),float(-delta[1]*size[1]/2)]
            record['capture_size']=size
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'matrix_groups':len(report['rows']),
        'complete_groups':sum(r['complete'] for r in report['rows']),
        'report_sha256':sha(args.output),'formal_A_accepted':False}))


if __name__=='__main__':main()
