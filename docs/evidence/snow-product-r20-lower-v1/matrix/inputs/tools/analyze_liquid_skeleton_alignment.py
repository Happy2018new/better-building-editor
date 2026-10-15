"""Compare supplied opaque liquid silhouettes with native stone UI references."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def mask(path, background, roi):
    pixels=np.asarray(Image.open(path).convert('RGB'),dtype=np.int16)
    changed=np.max(np.abs(pixels-background),axis=2)>8
    left,top,right,bottom=roi
    result=np.zeros(changed.shape,dtype=bool)
    result[top:bottom,left:right]=changed[top:bottom,left:right]
    return result


def bounds(value):
    ys,xs=np.nonzero(value)
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None


def centroid(value):
    ys,xs=np.nonzero(value)
    return [float(xs.mean()),float(ys.mean())] if len(xs) else None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a fresh analysis report')
    source=json.loads(args.report.read_bytes())
    captures=source['captures']
    background=np.asarray(Image.open(captures['empty']['path']).convert('RGB'),dtype=np.int16)
    height,width=background.shape[:2]
    roi=(8,round(height*.15),width-8,round(height*.9))
    rows=[]
    for label in ('pose0','pose1','pose2','axis0','axis1','axis2'):
        if label+'_stone' not in captures or label+'_water' not in captures:continue
        stone=mask(captures[label+'_stone']['path'],background,roi)
        liquid=mask(captures[label+'_water']['path'],background,roi)
        union=int(np.count_nonzero(stone|liquid))
        intersection=int(np.count_nonzero(stone&liquid))
        a,b=bounds(stone),bounds(liquid)
        ca,cb=centroid(stone),centroid(liquid)
        edge_error=max(abs(x-y) for x,y in zip(a,b)) if a and b else None
        center_error=max(abs(x-y) for x,y in zip(ca,cb)) if ca and cb else None
        iou=intersection/float(union) if union else 0.
        passed=bool(a and b and iou>=.97 and edge_error<=2. and center_error<=1.5)
        rows.append(dict(case=label,stone_pixels=int(stone.sum()),liquid_pixels=int(liquid.sum()),
                         stone_bounds=a,liquid_bounds=b,iou=iou,max_edge_error=edge_error,
                         max_centroid_error=center_error,passed=passed))
    report=dict(schema=1,completed=source.get('completed'),restored=source.get('restored'),
                source_sha256=hashlib.sha256(args.report.read_bytes()).hexdigest(),
                analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                roi=roi,thresholds={'rgb_delta':8,'min_iou':.97,'max_edge_error':2.,'max_centroid_error':1.5},
                results=rows,passed=bool(rows and all(row['passed'] for row in rows)),
                scope='Supplied full-height UI silhouettes only; no native height, UV, alpha or Scene acceptance')
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
