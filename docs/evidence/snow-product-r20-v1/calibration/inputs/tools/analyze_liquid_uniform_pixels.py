"""Replay exact diagnostic colors without accepting liquid shapes or rules."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROI = (500,350,1500,780)
MIN_PIXELS = 100
TOLERANCE = 1
ANIMATION_POLYGON = ((811,527),(948,550),(948,666),(816,624))
ANIMATION_EROSION = 11
ANIMATION_CROSSHAIR = (973,528,1014,568)


def plane_masks(path, expected):
    with Image.open(path).convert('RGB') as image:
        return [{(x,y) for y in range(ROI[1],ROI[3]) for x in range(ROI[0],ROI[2])
                 if max(abs(a-b) for a,b in zip(image.getpixel((x,y)),color))<=TOLERANCE}
                for color in expected]


def color_counts(path, expected, masks):
    counts=[0]*len(expected)
    bounds=[[999999,999999,-1,-1] for value in expected]
    with Image.open(path).convert('RGB') as image:
        for index,(color,mask) in enumerate(zip(expected,masks)):
            for x,y in mask:
                pixel=image.getpixel((x,y))
                if max(abs(a-b) for a,b in zip(pixel,color))<=TOLERANCE:
                    counts[index]+=1
                    box=bounds[index]
                    box[0]=min(box[0],x);box[1]=min(box[1],y)
                    box[2]=max(box[2],x+1);box[3]=max(box[3],y+1)
    return [{'expected_rgb':color,'pixels':count,'bounds':box if count else None,
             'passed':count>=MIN_PIXELS} for color,count,box in zip(expected,counts,bounds)]


def animation_observation(captures):
    first,later=captures['live_native_tile'],captures['live_native_tile_later']
    with Image.open(first['path']).convert('RGB') as a, Image.open(later['path']).convert('RGB') as b:
        if a.size!=b.size:
            raise ValueError('Animation frames have different sizes')
        mask=Image.new('L',a.size)
        ImageDraw.Draw(mask).polygon(ANIMATION_POLYGON,fill=255)
        mask=mask.filter(ImageFilter.MinFilter(ANIMATION_EROSION))
        ImageDraw.Draw(mask).rectangle(ANIMATION_CROSSHAIR,fill=0)
        delta=ImageChops.difference(a,b)
        values=[max(delta.getpixel((x,y))) for y in range(a.height) for x in range(a.width) if mask.getpixel((x,y))]
    elapsed=(later['frame']['frame_qpc_100ns']-first['frame']['frame_qpc_100ns'])/10000000.
    return {'polygon':ANIMATION_POLYGON,'erosion_pixels':ANIMATION_EROSION,
            'excluded_crosshair':ANIMATION_CROSSHAIR,'mask_pixels':len(values),
            'changed_pixels':sum(value>0 for value in values),
            'pixels_delta_gt_12':sum(value>12 for value in values),
            'mean_max_channel_delta':sum(values)/float(max(1,len(values))),
            'maximum_delta':max(values) if values else None,'frame_separation_seconds':elapsed,
            'attachment_identity_verified':False,
            'scope':'Fixed front-side interior pixel change only; no sampling negative control or full animation acceptance'}


def analyze(report_path):
    report=json.loads(report_path.read_bytes())
    rows={}
    expected={'heights_012':[list(value[:3]) for value in report['height_codes']],
              'height_3':[[value[3],slot*85,0] for slot,value in enumerate(report['height_codes'])],
              'cell_addresses':[[round(index/63.*255),slot*85,0]
                                for slot,index in enumerate((0,5,42,63))]}
    identity=None
    captures_verified=True
    masks={key:plane_masks(Path(report['captures'][key+'_heights_012']['path']),expected['heights_012'])
           for key in ('live','roundtrip')}
    for label,capture in report['captures'].items():
        path=Path(capture['path'])
        captured_identity=(capture['owner'],capture['game_pid'],capture['game_identity'])
        identity=identity or captured_identity
        captures_verified=captures_verified and captured_identity==identity and capture['reliable'] and \
            capture['background_safe'] and capture['frame']['frame_qpc_100ns']>=capture['frame']['request_qpc_100ns'] and \
            hashlib.sha256(path.read_bytes()).hexdigest()==capture['sha256']
        for suffix,colors in expected.items():
            if label.endswith('_'+suffix):
                rows[label]=color_counts(path,colors,masks[label.split('_')[0]])
    accepted=bool(report['completed'] and report['restored'] and not report['cleanup_errors'] and
                  captures_verified and len(rows)==6 and all(row['passed'] for values in rows.values() for row in values))
    animation=animation_observation(report['captures'])
    animation['attachment_identity_verified']=(report['same_attachment_before']==report['same_attachment_after'])
    return {'schema':2,'input_report':str(report_path.resolve()),
            'input_report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'roi':ROI,'minimum_pixels':MIN_PIXELS,'rgb_tolerance':TOLERANCE,'rows':rows,
            'plane_mask_source':'Independent heights_012 captures in each live/roundtrip path',
            'plane_mask_pixels':{key:[len(mask) for mask in values] for key,values in masks.items()},
            'same_attachment_still_water_observation':animation,
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
