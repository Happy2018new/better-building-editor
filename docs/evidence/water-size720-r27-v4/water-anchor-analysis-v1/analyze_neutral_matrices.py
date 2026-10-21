"""Compare predeclared neutral/stone pixels and project cube corners from native WVP.

No ROI search, offset fit, FOV fit, phase fit, threshold adjustment or product edits.
All outputs are diagnostic; the original failed water flow rows stay unchanged.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFilter

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
CANDIDATE=ROOT/'.runtime/round-20261022/water-camera-signal-v2/candidate/tools/verify_camera_projection.py'
CANDIDATE_SHA='261e2fb407ceee541cf800a28dd7e56778d33b579f72159ee54620c684609f8a'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def hull(points):
    ordered=sorted(set(tuple(point) for point in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[]
    for point in ordered:
        while len(lower)>=2 and cross(lower[-2],lower[-1],point)<=0:lower.pop()
        lower.append(point)
    upper=[]
    for point in reversed(ordered):
        while len(upper)>=2 and cross(upper[-2],upper[-1],point)<=0:upper.pop()
        upper.append(point)
    return lower[:-1]+upper[:-1]


def metrics(a,b):
    aa=np.asarray(a)>0;bb=np.asarray(b)>0
    union=int(np.count_nonzero(aa|bb));intersection=int(np.count_nonzero(aa&bb))
    # Fixed two-pixel Chebyshev neighbourhood, recorded in both directions.
    da=np.asarray(a.filter(ImageFilter.MaxFilter(5)))>0
    db=np.asarray(b.filter(ImageFilter.MaxFilter(5)))>0
    return {'a_pixels':int(aa.sum()),'b_pixels':int(bb.sum()),'intersection':intersection,'union':union,
            'iou':intersection/union if union else None,
            'a_recall_within_2px_of_b':float(np.count_nonzero(aa&db)/aa.sum()) if aa.any() else None,
            'b_recall_within_2px_of_a':float(np.count_nonzero(bb&da)/bb.sum()) if bb.any() else None,
            'a_bounds':a.getbbox(),'b_bounds':b.getbbox()}


def neutral_mask(path,empty):
    with Image.open(path) as image,Image.open(empty) as background:
        a=np.asarray(image.convert('RGB')).astype(np.int16)
        b=np.asarray(background.convert('RGB')).astype(np.int16)
    assert a.shape==b.shape
    signal=(np.abs(a-64)<=5).all(axis=2)&(np.abs(a-b).max(axis=2)>20)
    return Image.fromarray(np.uint8(signal)*255)


def prediction(row,matrix_row,gui,size,variant=None):
    numbers=matrix_row['matrix']['elements']
    assert len(numbers)==16 and max(abs(value) for value in numbers)<4095.
    matrix=np.asarray(numbers).reshape((4,4),order='F')
    anchor=0. if row['config']['model'].endswith('_0') else 1.5
    position=row['config']['position']
    old=np.asarray(matrix_row['before']['native'][0]['global_position'])
    actual=np.asarray(row['before']['native'][0]['global_position'])
    translation=(actual-old)*gui
    if variant=='wrong_GUI_half':translation*=.5
    elif variant=='wrong_GUI_double':translation*=2.
    elif variant=='wrong_offset_sign':translation*=-1.
    corners=[];ndc=[]
    for delta in itertools.product((0.,1.),repeat=3):
        local=np.asarray(position,dtype=float)+np.asarray(delta)-2.
        if variant=='wrong_axis_y_z':
            entity=np.asarray((-local[0],-local[1]+anchor,-local[2],1.))
        elif variant=='wrong_axis_x_sign':
            entity=np.asarray((local[0],-local[2]+anchor,-local[1],1.))
        elif variant=='wrong_axis_y_sign':
            entity=np.asarray((-local[0],local[2]+anchor,-local[1],1.))
        else:
            entity=np.asarray((-local[0],-local[2]+anchor,-local[1],1.))
        clip=matrix@entity
        assert abs(clip[3])>1e-8
        value=clip[:3]/clip[3]
        point=np.asarray(((value[0]+1.)*size[0]/2.,(1.-value[1])*size[1]/2.))+translation
        corners.append(point.tolist());ndc.append(value.tolist())
    polygon=hull(corners)
    mask=Image.new('L',size)
    ImageDraw.Draw(mask).polygon(polygon,fill=255)
    return mask,{'corners':corners,'ndc':ndc,'hull':polygon,'anchor':anchor,
                 'WVP_elements':numbers,'WVP_column_major':True,
                 'control_translation_logical':(actual-old).tolist(),
                 'control_translation_physical_by_integer_GUI':translation.tolist(),
                 'translation_hypothesis_requires_native_controls':bool(np.any(translation)),
                 'diagnostic_variant':variant,
                 'matrix_quantization_max_error':1/4096.}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args()
    assert not args.output.exists()
    capture=json.loads(args.capture.read_bytes())
    if not args.allow_partial:assert capture['completed'] and capture['restored'] and not capture.get('restore_unknown')
    assert sha(CANDIDATE)==CANDIDATE_SHA
    sys.path.insert(0,str(ROOT/'tools'))
    spec=importlib.util.spec_from_file_location('anchor_private_camera_v2',CANDIDATE)
    signal=importlib.util.module_from_spec(spec);spec.loader.exec_module(signal)
    rows={row['label']:row for row in capture['rows'] if row.get('completed')}
    windows={row['label']:row for row in capture['window_rows'] if 'opened' in row}
    report={'schema':1,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'capture_path':str(args.capture),'capture_sha256':sha(args.capture),'host_sha256':sha(Path(__file__)),
        'source_contract_sha256':capture['source_contract_sha256'],'formal_A_accepted':False,
        'production_admission_performed':False,'water_flow_ROI_modified':False,'manual_closures_added':0,
        'partial':args.allow_partial,'predeclared_neutral_rgb':[64,64,64],'neutral_tolerance':5,
        'contribution_greater_than':20,'matrix_candidate_sha256':CANDIDATE_SHA,'rows':[],
        'no_fit_or_search':True,'negative_controls':[],
        'negative_control_interpretation':'Fixed alternatives, declared before observing new pixels. Symmetric cells may coincide; report metrics without manufacturing pass/fail labels.'}
    for label,row in rows.items():
        if row['config']['mode']!='neutral':continue
        window,rectangle,pose,*suffix=label.split('_')
        prefix='_'.join((window,rectangle,pose))
        empty=rows.get(prefix+'_empty');stone=rows.get(prefix+'_stone');matrix=rows.get(prefix+'_matrix_WORLDVIEWPROJ')
        if not all((empty,stone,matrix)):
            report['rows'].append({'label':label,'analyzed':False,'reason':'Missing empty/stone/native WVP reference'})
            continue
        actual=neutral_mask(row['capture']['path'],empty['capture']['path'])
        stone_mask=signal.stone_signal(stone['capture']['path'],empty['capture']['path'])
        size=actual.size;gui=windows[window]['opened']['gui']
        predicted,details=prediction(row,matrix,gui,size)
        record={'label':label,'analyzed':True,'actual_sha256':row['capture']['sha256'],
                'neutral_vs_stone':metrics(actual,stone_mask),'neutral_vs_native_WVP':metrics(actual,predicted),
                'native_WVP_prediction':details,'viewport':row['before']['native'],
                'known_GUI_hypothesis':gui}
        # Axis controls compare with their matching stone cell, never the base stone position.
        if suffix and suffix[0].startswith('axis'):
            axis_stone=rows.get(prefix+'_'+suffix[0]+'_stone')
            if axis_stone:
                axis_mask=signal.stone_signal(axis_stone['capture']['path'],empty['capture']['path'])
                record['neutral_vs_matching_axis_stone']=metrics(actual,axis_mask)
        for offset in (-20,20):
            shifted=Image.new('L',size);shifted.paste(predicted,(0,offset))
            report['negative_controls'].append({'label':label,'kind':'fixed_physical_y_translation',
                                                'offset':offset,'metrics':metrics(actual,shifted)})
        variants=['wrong_axis_y_z','wrong_axis_x_sign','wrong_axis_y_sign']
        if details['translation_hypothesis_requires_native_controls']:
            variants+=['wrong_GUI_half','wrong_GUI_double','wrong_offset_sign']
        for variant in variants:
            alternate,alternate_details=prediction(row,matrix,gui,size,variant=variant)
            report['negative_controls'].append({'label':label,'kind':variant,
                'metrics':metrics(actual,alternate),'native_WVP_prediction':alternate_details})
        if rectangle=='wide' and pose=='front' and not (suffix and suffix[0].startswith('axis')):
            with Image.open(row['capture']['path']).convert('RGB') as image:
                draw=ImageDraw.Draw(image);polygon=details['hull'];draw.line(polygon+[polygon[0]],fill=(255,50,50),width=2)
                target=args.output.with_name(args.output.stem+'_'+label+'.png')
                image.save(target)
                record['overlay']={'path':str(target),'sha256':sha(target),'scope':'Unfitted native WVP corner prediction'}
        report['rows'].append(record)
    for prefix in sorted({label.rsplit('_empty',1)[0] for label,row in rows.items() if row['config']['mode']=='empty'}):
        empty=rows[prefix+'_empty']
        mask=neutral_mask(empty['capture']['path'],empty['capture']['path'])
        report['negative_controls'].append({'label':prefix,'kind':'shown_equals_hidden',
                                            'pixels':int(np.count_nonzero(np.asarray(mask)))})
        assert not mask.getbbox()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'rows':len(report['rows']),'negative_controls':len(report['negative_controls']),
                      'report_sha256':sha(args.output),'formal_A_accepted':False}))


if __name__=='__main__':main()
