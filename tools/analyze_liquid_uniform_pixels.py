"""Replay exact diagnostic colors without accepting liquid shapes or rules."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROI = (500,350,1500,780)
MIN_PIXELS = 100
TOLERANCE = 1


def color_counts(path, expected):
    counts=[0]*len(expected)
    bounds=[[999999,999999,-1,-1] for value in expected]
    with Image.open(path).convert('RGB') as image:
        image=image.crop(ROI)
        for y in range(image.height):
            for x in range(image.width):
                pixel=image.getpixel((x,y))
                for index,color in enumerate(expected):
                    if max(abs(a-b) for a,b in zip(pixel,color))<=TOLERANCE:
                        counts[index]+=1
                        box=bounds[index]
                        box[0]=min(box[0],x+ROI[0]);box[1]=min(box[1],y+ROI[1])
                        box[2]=max(box[2],x+ROI[0]+1);box[3]=max(box[3],y+ROI[1]+1)
    return [{'expected_rgb':color,'pixels':count,'bounds':box if count else None,
             'passed':count>=MIN_PIXELS} for color,count,box in zip(expected,counts,bounds)]


def analyze(report_path):
    report=json.loads(report_path.read_bytes())
    rows={}
    expected={'heights_012':[list(value[:3]) for value in report['height_codes']],
              'height_3':[[value[3],slot*85,0] for slot,value in enumerate(report['height_codes'])],
              'cell_addresses':[[round(index/63.*255),slot*85,0]
                                for slot,index in enumerate((0,5,42,63))]}
    identity=None
    captures_verified=True
    for label,capture in report['captures'].items():
        path=Path(capture['path'])
        captured_identity=(capture['owner'],capture['game_pid'],capture['game_identity'])
        identity=identity or captured_identity
        captures_verified=captures_verified and captured_identity==identity and capture['reliable'] and \
            capture['background_safe'] and capture['frame']['frame_qpc_100ns']>=capture['frame']['request_qpc_100ns'] and \
            hashlib.sha256(path.read_bytes()).hexdigest()==capture['sha256']
        for suffix,colors in expected.items():
            if label.endswith('_'+suffix):
                rows[label]=color_counts(path,colors)
    accepted=bool(report['completed'] and report['restored'] and not report['cleanup_errors'] and
                  captures_verified and len(rows)==6 and all(row['passed'] for values in rows.values() for row in values))
    return {'schema':1,'input_report':str(report_path.resolve()),
            'input_report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'roi':ROI,'minimum_pixels':MIN_PIXELS,'rgb_tolerance':TOLERANCE,'rows':rows,
            'captures_verified':captures_verified,'supplied_uniform_codes_observed':accepted,
            'native_input_format_accepted':False,'native_geometry_accepted':False,
            'accuracy_accepted':False,'production_memory_accepted':False,'animated_sampling_accepted':False,
            'scope':'Explicit supplied 8-bit codes and cell addresses in four uniform slots only'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    result=analyze(args.report)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
    print(json.dumps(result))
    return 0 if result['supplied_uniform_codes_observed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
