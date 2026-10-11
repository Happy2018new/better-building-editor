"""Compare supplied black world silhouettes against native stone reference cells."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def pixels(path):return np.asarray(Image.open(path).convert('RGB'),dtype=np.int16)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a fresh report')
    source=json.loads(args.report.read_bytes())
    captures=source['captures']
    background=pixels(captures['reference_restored']['path'])
    height,width=background.shape[:2]
    roi=(round(width*.4),round(height*.315),round(width*.63),round(height*.59))
    selected=np.zeros((height,width),dtype=bool)
    left,top,right,bottom=roi
    selected[top:bottom,left:right]=True
    stone=pixels(captures['reference_cells']['path'])
    liquid=pixels(captures['full_height']['path'])
    changed=np.max(np.abs(stone-background),axis=2)>8
    stone_mask=changed & (np.max(stone,axis=2)-np.min(stone,axis=2)<=3) & (stone.mean(axis=2)>40) & (stone.mean(axis=2)<205) & selected
    liquid_mask=(np.max(liquid,axis=2)<8) & selected
    union=int(np.count_nonzero(stone_mask|liquid_mask))
    intersection=int(np.count_nonzero(stone_mask&liquid_mask))
    iou=intersection/float(union) if union else 0.
    ys,xs=np.nonzero(stone_mask)
    yl,xl=np.nonzero(liquid_mask)
    a=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None
    b=[int(xl.min()),int(yl.min()),int(xl.max()+1),int(yl.max()+1)] if len(xl) else None
    edge=max(abs(x-y) for x,y in zip(a,b)) if a and b else None
    center=max(abs(xs.mean()-xl.mean()),abs(ys.mean()-yl.mean())) if a and b else None
    passed=bool(a and b and iou>=.97 and edge<=2. and center<=1.5)
    report=dict(schema=1,completed=source.get('completed'),restored=source.get('restored'),
                source_sha256=hashlib.sha256(args.report.read_bytes()).hexdigest(),
                analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),roi=roi,
                thresholds={'rgb_delta':8,'stone_gray_tolerance':3,'liquid_black_max':7,'min_iou':.97,'max_edge_error':2.,'max_centroid_error':1.5},
                stone_pixels=int(stone_mask.sum()),liquid_pixels=int(liquid_mask.sum()),
                stone_bounds=a,liquid_bounds=b,iou=iou,max_edge_error=edge,max_centroid_error=center,
                passed=passed,scope='Supplied opaque placement against native stone, not native liquid UV/alpha/height or WorldProjection acceptance')
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps(report))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
