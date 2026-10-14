"""Measure the native enchanting-table red motif at matched body-test cameras."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def motif(record):
    path=Path(record['path'])
    if not record.get('reliable') or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
        raise ValueError('Invalid native body image: '+str(path))
    with Image.open(path) as image:
        w,h=image.size
        bounds=(w//2-160,h//2-150,w//2+160,h//2+240)
        pixels=np.array(image.convert('RGB').crop(bounds),dtype=np.float32)
    r,g,b=np.moveaxis(pixels,-1,0)
    mask=(r>50)&(r>g*2)&(b>g*1.2)&(b<r)
    ys,xs=np.nonzero(mask)
    if len(xs)<200:raise ValueError('Red table-body reference is absent: '+str(path))
    return mask,{'pixels':len(xs),'bounds':[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1],
                 'center':[float(xs.mean()),float(ys.mean())],'image_crop':bounds}


def align(reference,candidate):
    best=(-1.,0,0)
    # Keep the same unwarped pixel masks. This reports a translation estimate,
    # never moves the images to turn an incorrect placement into acceptance.
    for dy in range(-32,33):
        for dx in range(-2,3):
            shifted=np.roll(candidate,(dy,dx),(0,1))
            if dy>0:shifted[:dy]=False
            elif dy<0:shifted[dy:]=False
            if dx>0:shifted[:,:dx]=False
            elif dx<0:shifted[:,dx:]=False
            score=float((reference&shifted).sum())/max(1,(reference|shifted).sum())
            if score>best[0]:best=(score,dx,dy)
    original=float((reference&candidate).sum())/max(1,(reference|candidate).sum())
    return {'unshifted_iou':original,'best_translation_pixels':best[1:],'translated_iou':best[0]}


def analyze(source,output):
    raw=source.read_bytes();report=json.loads(raw)
    if not all(report.get(k) for k in ('completed','restored','source_unchanged')) or report.get('cleanup_errors'):
        raise ValueError('Native body test did not complete and restore')
    result={'schema':1,'source_sha256':hashlib.sha256(raw).hexdigest(),'product_qualified':False,
            'scope':'Visible red body-motif placement only; not book, complete silhouette or texture acceptance.',
            'views':{}}
    for view in ('south','north','east','west'):
        reference,measurement=motif(report['captures']['world_'+view])
        rows={}
        for label,record in report['captures'].items():
            if not label.endswith('_'+view) or label.startswith(('world_','empty_')):continue
            candidate,observed=motif(record)
            rows[label]=dict(align(reference,candidate),observed=observed)
        result['views'][view]={'reference':measurement,'candidates':rows}
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
    print(json.dumps({view:{name:{k:row[k] for k in ('unshifted_iou','best_translation_pixels')}
                           for name,row in data['candidates'].items()}
                      for view,data in result['views'].items()}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();analyze(args.source,args.output)
